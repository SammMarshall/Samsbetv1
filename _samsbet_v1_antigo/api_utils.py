#api_utils.py
import requests
import time
import numpy as np
from scipy.stats import poisson
import pandas as pd
from typing import Dict, List, Any
import streamlit as st

# Constantes
API_BASE_URL = "https://www.sofascore.com/api/v1"
REQUEST_INTERVAL = 1  # segundos

# Variável global para armazenar o timestamp da última requisição
last_request_time = 0

@st.cache_data(ttl=3600)  # Cache por 1 hora
def make_api_request(url: str) -> Dict[str, Any]:
    """
    Faz uma requisição à API com controle de intervalo entre chamadas.
    
    Args:
        url (str): URL da API para fazer a requisição
    
    Returns:
        Dict[str, Any]: Resposta da API em formato JSON
    """
    global last_request_time
    
    try:
        current_time = time.time()
        if current_time - last_request_time < REQUEST_INTERVAL:
            time.sleep(REQUEST_INTERVAL - (current_time - last_request_time))
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(url, headers=headers)
        
        response.raise_for_status()  # Levanta exceção para códigos de erro HTTP (não 2xx)
        
        last_request_time = time.time()
        return response.json()
    
    except requests.exceptions.RequestException as e:
        print(f"Ocorreu um erro na requisição: {e}")
        return {}

def get_team_stats(team_id: int, tournament_id: int, season_id: int) -> Dict[str, Any]:
    """
    Busca estatísticas de um time específico da API.
    
    Args:
        team_id (int): ID do time
        tournament_id (int): ID do torneio
        season_id (int): ID da temporada
    
    Returns:
        Dict[str, Any]: Estatísticas do time
    """
    url = f"{API_BASE_URL}/team/{team_id}/unique-tournament/{tournament_id}/season/{season_id}/statistics/overall"
    print(url)
    return make_api_request(url)['statistics']

def get_player_stats(league_id: int, season_id: int, quantidade: int, team_filter: str, game_type: str, position_filter: str, order_by: str, fields: str) -> Dict[str, Any]:
    """
    Busca estatísticas de jogadores da API.
    
    Args:
        league_id (int): ID da liga
        season_id (int): ID da temporada
        quantidade (int): Número de jogadores para retornar
        team_filter (str): Filtro de time
        game_type (str): Tipo de jogo (Casa, Fora, Ambos)
        position_filter (str): Filtro de posição
        order_by (str): Campo para ordenação
        fields (str): Campos a serem retornados
    
    Returns:
        Dict[str, Any]: Estatísticas dos jogadores
    """
    type_filter = ""
    if game_type == "Casa":
        type_filter = "type.EQ.home%2C"
    elif game_type == "Fora":
        type_filter = "type.EQ.away%2C"

    url = f"{API_BASE_URL}/unique-tournament/{league_id}/season/{season_id}/statistics?limit={quantidade}&order={order_by}&accumulation=total&fields={fields}&filters={type_filter}{position_filter}{team_filter}"
    print(url)
    return make_api_request(url)
    

def process_finalizacoes_data(data: Dict[str, Any]) -> pd.DataFrame:
    all_data = []
    for player in data['results']:
        all_data.append({
            'Jogador': player['player']['name'],
            'Time': player['team']['name'],  # Certifique-se de que esta linha está correta
            'Total de chutes': player['totalShots'],
            'Chutes no alvo': player['shotsOnTarget'],
            'Partidas jogadas': player['appearances'],
            'Titular': player['matchesStarted'],
            'Min/Jogados': player['minutesPlayed']  # Certifique-se de que esta linha está correta
        })
    
    df = pd.DataFrame(all_data)
    df['Min/Chute Alvo'] = (df['Min/Jogados'] / df['Chutes no alvo']).round(2)
    df['Min/Chute'] = (df['Min/Jogados'] / df['Total de chutes']).round(2)
    df['Min/P'] = (df['Min/Jogados'] / df['Partidas jogadas']).round(2)
    df['Chutes/P'] = (df['Total de chutes'] / df['Partidas jogadas']).round(2)
    df['Chutes Alvo/P'] = (df['Chutes no alvo'] / df['Partidas jogadas']).round(2)
    df['Eficiência'] = df.apply(
            lambda row: f"{(row['Chutes no alvo'] / row['Total de chutes'] * 100):.2f}%" 
            if row['Total de chutes'] > 0 else "0.00%", 
            axis=1
        )
    # Cálculos usando Poisson
    def calc_poisson_prob(row, k, lambda_param):
        """
        Calcula a probabilidade de Poisson
        k: número de eventos (chutes)
        lambda_param: média de eventos por partida
        """
        if row['Partidas jogadas'] >= 5:  # Mínimo de 5 jogos para análise
            return poisson.pmf(k, lambda_param)
        return None

    def calc_poisson_prob_over(row, k, lambda_param):
        """
        Calcula a probabilidade de ter mais que k eventos
        """
        if row['Partidas jogadas'] >= 5:
            # 1 - P(X ≤ k) = 1 - P(X < k+1)
            return 1 - poisson.cdf(k, lambda_param)
        return None

    # Probabilidades Poisson para chutes ao gol
    df['Poisson_Prob_0.5'] = df.apply(
        lambda row: calc_poisson_prob_over(
            row, 
            0,  # Mais que 0 chutes (over 0.5)
            row['Chutes Alvo/P']  # Lambda = média de chutes ao gol por partida
        ),
        axis=1
    )

    df['Poisson_Prob_1.5'] = df.apply(
        lambda row: calc_poisson_prob_over(
            row, 
            1,  # Mais que 1 chute (over 1.5)
            row['Chutes Alvo/P']
        ),
        axis=1
    )

    # Odds baseadas em Poisson
    df['Odd_Poisson_0.5'] = df['Poisson_Prob_0.5'].apply(
        lambda x: round(1 / x, 2) if pd.notnull(x) and x > 0 else None
    )

    df['Odd_Poisson_1.5'] = df['Poisson_Prob_1.5'].apply(
        lambda x: round(1 / x, 2) if pd.notnull(x) and x > 0 else None
    )

    # Intervalo de confiança para média de chutes
    df['IC_Superior'] = df.apply(
        lambda row: row['Chutes Alvo/P'] + 1.96 * np.sqrt(row['Chutes Alvo/P'] / row['Partidas jogadas'])
        if row['Partidas jogadas'] >= 5 else None,
        axis=1
    )

    df['IC_Inferior'] = df.apply(
        lambda row: max(0, row['Chutes Alvo/P'] - 1.96 * np.sqrt(row['Chutes Alvo/P'] / row['Partidas jogadas']))
        if row['Partidas jogadas'] >= 5 else None,
        axis=1
    )

    # Métricas de consistência avançadas
    df['Consistência'] = df.apply(
        lambda row: "Alta" if (
            row['Partidas jogadas'] >= 5 and
            row['Chutes Alvo/P'] > 0.8 and
            row['IC_Inferior'] > 0.4  # Limite inferior do IC ainda é bom
        )
        else "Média" if (
            row['Partidas jogadas'] >= 5 and
            row['Chutes Alvo/P'] > 0.4
        )
        else "Baixa",
        axis=1
    )

    # Odd de mercado recomendada (com margem de segurança variável)
    df['Odd_Mercado_Ref'] = df.apply(
        lambda row: round(
            row['Odd_Poisson_0.5'] * (
                0.90 if row['Consistência'] == "Alta"
                else 0.85 if row['Consistência'] == "Média"
                else 0.80
            ), 2
        ) if pd.notnull(row['Odd_Poisson_0.5']) else None,
        axis=1
    )
    return df



def process_defesa_data(data: Dict[str, Any]) -> pd.DataFrame:
    """
    Processa os dados de defesa dos goleiros.
    
    Args:
        data (Dict[str, Any]): Dados brutos da API
    
    Returns:
        pd.DataFrame: DataFrame processado com as estatísticas de defesa
    """
    all_data = []
    for player in data['results']:
        all_data.append({
            'Jogador': player['player']['name'],
            'Time': player['team']['name'],
            'Defesas': player['saves'],
            'Partidas jogadas': player['appearances'],
            'Titular': player['matchesStarted'],
            'Min/Jogados': player['minutesPlayed'],
            'Gols sofridos (área)': player['goalsConcededInsideTheBox'],
            'Gols sofridos (fora da área)': player['goalsConcededOutsideTheBox']
        })
    
    df = pd.DataFrame(all_data)
    df['Total Gols/s'] = df['Gols sofridos (área)'] + df['Gols sofridos (fora da área)']
    df['Defesas /P'] = (df['Defesas'] / df['Partidas jogadas']).round(2)
    df['Min/Defesa'] = (df['Min/Jogados'] / df['Defesas']).round(2)
    return df

def get_teams_stats(league_id: int, season_id: int) -> Dict[str, Any]:
    """
    Busca estatísticas de todos os times de uma liga específica.
    
    Args:
        league_id (int): ID da liga
        season_id (int): ID da temporada
    
    Returns:
        Dict[str, Any]: Estatísticas dos times
    """
    url = f"{API_BASE_URL}/unique-tournament/{league_id}/season/{season_id}/standings/total"
    print(url)
    return make_api_request(url)

@st.cache_data(ttl=3600)
def get_event_details(event_id: int) -> tuple:
    """
    Obtém os detalhes de um evento específico.
    
    Args:
        event_id (int): ID do evento
    
    Returns:
        tuple: Nome do time da casa, nome do time visitante
    """
    url = f"{API_BASE_URL}/event/{event_id}"
    print(url)
    data = make_api_request(url)
    if data:
        home_team = data['event']['homeTeam']['name']
        away_team = data['event']['awayTeam']['name']
        return home_team, away_team
    else:
        print(f"Erro ao obter detalhes do evento {event_id}")
        return 'Time da casa desconhecido', 'Time de fora desconhecido'

@st.cache_data(ttl=3600)
def get_shots_data(event_id: int) -> Dict[str, List[Dict[str, Any]]]:
    """
    Obtém dados de chutes para um evento específico, focando apenas nos jogadores que finalizaram.
    
    Args:
        event_id (int): ID do evento
    
    Returns:
        Dict[str, List[Dict[str, Any]]]: Dados de chutes para times da casa e visitante
    """
    time.sleep(1)  # Intervalo de 1 segundo antes da requisição
    
    url = f"{API_BASE_URL}/event/{event_id}/lineups"
    print(url)
    data = make_api_request(url)
    if data:
        shots_data = {'home': [], 'away': []}
        for team_type in ['home', 'away']:
            if team_type in data and 'players' in data[team_type]:
                for player in data[team_type]['players']:
                    stats = player.get('statistics', {})
                    shots_blocked = stats.get('blockedScoringAttempt', 0)
                    shots_on_target = stats.get('onTargetScoringAttempt', 0)
                    shots_off_target = stats.get('shotOffTarget', 0)
                    total_shots = shots_on_target + shots_off_target + shots_blocked
                    if total_shots > 0:
                        shots_data[team_type].append({
                            'id': player['player']['id'],
                            'name': player['player']['name'],
                            'shots_on_target': shots_on_target,
                            'total_shots': total_shots
                        })
        return shots_data
    else:
        print(f"Erro ao obter dados para o evento {event_id}")
        return {'home': [], 'away': []}
