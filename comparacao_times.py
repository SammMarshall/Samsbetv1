import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from utils import load_leagues_data, get_leagues_by_country, select_country_and_league, get_league_info
from api_utils import (
    get_player_stats, 
    process_finalizacoes_data, 
    get_event_details, 
    get_shots_data,
    make_api_request,
    API_BASE_URL
)
from datetime import datetime

def comparacao_times():
    st.title('Comparação de Finalizações entre Times de Ligas Diferentes')

    # Carregar dados das ligas
    leagues_data = load_leagues_data()
    leagues_by_country = get_leagues_by_country(leagues_data)

    # Layout em duas colunas para os times
    col1, col2 = st.columns(2)

    with col1:
        st.subheader('Primeiro Time')
        country1, league1, leagues_in_country1 = select_country_and_league(leagues_by_country, key_prefix="team1_")
        league_id1, season_id1 = get_league_info(leagues_in_country1, league1)
        team1 = st.selectbox('Selecione o primeiro time:', 
                           [team['nome'] for team in leagues_data[league1]['teams']], 
                           key="team1_select")
        # Opção de mandante/visitante para o primeiro time
        local_team1 = st.radio(
            "Condição do primeiro time:",
            ["Casa", "Fora", "Ambos"],
            key="local_team1"
        )

    with col2:
        st.subheader('Segundo Time')
        country2, league2, leagues_in_country2 = select_country_and_league(leagues_by_country, key_prefix="team2_")
        league_id2, season_id2 = get_league_info(leagues_in_country2, league2)
        team2 = st.selectbox('Selecione o segundo time:', 
                           [team['nome'] for team in leagues_data[league2]['teams']], 
                           key="team2_select")
        # Opção de mandante/visitante para o segundo time
        local_team2 = st.radio(
            "Condição do segundo time:",
            ["Casa", "Fora", "Ambos"],
            key="local_team2"
        )

    if st.button('Comparar Times'):
        # Obter dados para o primeiro time
        team1_id = next(team['id'] for team in leagues_data[league1]['teams'] if team['nome'] == team1)
        data1 = get_player_stats(
            league_id1, season_id1, 50, 
            f"%2Cteam.in.{team1_id}", 
            local_team1,  # Usando a condição selecionada
            "position.in.D~M~F", 
            "-shotsOnTarget",
            "totalShots%2CshotsOnTarget%2Cappearances%2CmatchesStarted%2CminutesPlayed"
        )
        df1 = process_finalizacoes_data(data1)

        # Obter dados para o segundo time
        team2_id = next(team['id'] for team in leagues_data[league2]['teams'] if team['nome'] == team2)
        data2 = get_player_stats(
            league_id2, season_id2, 50, 
            f"%2Cteam.in.{team2_id}", 
            local_team2,  # Usando a condição selecionada
            "position.in.D~M~F", 
            "-shotsOnTarget",
            "totalShots%2CshotsOnTarget%2Cappearances%2CmatchesStarted%2CminutesPlayed"
        )
        df2 = process_finalizacoes_data(data2)

        # Adicionar informação da condição ao título do time
        team1_display = f"{team1} ({local_team1})"
        team2_display = f"{team2} ({local_team2})"

        # Obter dados da última partida
        last_match_data1 = get_last_match_data(leagues_data[league1]['teams'], team1, league_id1, season_id1)
        last_match_data2 = get_last_match_data(leagues_data[league2]['teams'], team2, league_id2, season_id2)

        # Adicionar dados da última partida aos DataFrames
        df1 = add_last_match_info(df1, last_match_data1, team1)
        df2 = add_last_match_info(df2, last_match_data2, team2)

        # Calcular estatísticas do time
        team1_stats = calculate_team_stats(df1)
        team2_stats = calculate_team_stats(df2)

        # Mostrar tabela detalhada com jogadores
        show_detailed_player_table(df1, df2, team1_display, team2_display)

        # Criar gráfico de radar
        create_radar_chart(team1_display, team2_display, team1_stats, team2_stats)

        # Mostrar tabela comparativa
        show_comparison_table(team1_display, team2_display, team1_stats, team2_stats)

def get_team_last_event(team_id: int) -> dict:
    """
    Busca o último evento de um time diretamente da API
    """
    url = f'https://api.sofascore.com/api/v1/team/{team_id}/events/last/0'
    try:
        data = make_api_request(url)
        events = data.get('events', [])
        if events:
            return events[-1]  # Retorna o evento mais recente
    except Exception as e:
        st.error(f"Falha ao obter o último evento para o time {team_id}: {str(e)}")
    return None

def get_last_match_data(teams, team_name, league_id, season_id):
    """
    Busca dados do último jogo e estatísticas gerais do time
    """
    # Encontra o ID do time
    team = next(team for team in teams if team['nome'] == team_name)
    team_id = team['id']
    
    # Busca estatísticas gerais do time
    url_stats = f"{API_BASE_URL}/team/{team_id}/unique-tournament/{league_id}/season/{season_id}/statistics/overall"
    team_stats = make_api_request(url_stats).get('statistics', {})
    print(team_stats)

    # Calcula médias por partida
    matches = team_stats.get('matches', 0)
    if matches > 0:
        team_averages = {
            'Chutes por jogo': round(team_stats.get('shots', 0) / matches, 2),
            'Chutes no alvo por jogo': round(team_stats.get('shotsOnTarget', 0) / matches, 2),
            'Defesas por jogo': round(team_stats.get('saves', 0) / matches, 2),
            'Total de jogos': matches
        }
    else:
        print(f"Não foi possível calcular médias para {team_name}")
    
    # Busca o último evento
    last_event = get_team_last_event(team_id)
    
    if not last_event:
        st.warning(f"Não foi possível obter o último evento para {team_name}")
        return {
            'home_team': 'Desconhecido',
            'away_team': 'Desconhecido',
            'shots_data': {'home': [], 'away': []},
            'team_stats': team_averages
        }
    
    # Busca os detalhes do evento
    event_id = last_event['id']
    home_team, away_team = get_event_details(event_id)
    shots_data = get_shots_data(event_id)
    
    # Adiciona informações do evento e estatísticas
    match_info = {
        'home_team': home_team,
        'away_team': away_team,
        'shots_data': shots_data,
        'date': datetime.fromtimestamp(last_event['startTimestamp']).strftime('%d/%m/%Y %H:%M'),
        'tournament': last_event['tournament']['name'],
        'status': last_event['status']['description'],
        'team_stats': team_averages
    }
    
    # Exibe informações do jogo e estatísticas
    st.info(f"""
        Último jogo de {team_name}:
        {home_team} vs {away_team}
        Data: {match_info['date']}
        Torneio: {match_info['tournament']}
        Status: {match_info['status']}
        
        Estatísticas da temporada:
        • Média de chutes: {team_averages['Chutes por jogo']}
        • Média de chutes no alvo: {team_averages['Chutes no alvo por jogo']}
        • Média de defesas: {team_averages['Defesas por jogo']}
        • Total de jogos: {team_averages['Total de jogos']}
    """)
    
    return match_info

def add_last_match_info(df, last_match_data, team_name):
    home_team = last_match_data['home_team']
    away_team = last_match_data['away_team']
    shots_data = last_match_data['shots_data']

    team_type = 'home' if team_name == home_team else 'away'
    
    last_match_shots = {}
    for player in shots_data[team_type]:
        last_match_shots[player['name']] = {
            'shots_on_target': player['shots_on_target'],
            'total_shots': player['total_shots']
        }

    df['Chutes alvo (last)'] = df['Jogador'].map(lambda x: last_match_shots.get(x, {}).get('shots_on_target', 0))
    df['Chutes (last)'] = df['Jogador'].map(lambda x: last_match_shots.get(x, {}).get('total_shots', 0))

    return df

def calculate_team_stats(df):
    """
    Calcula estatísticas do time usando o DataFrame já processado por process_finalizacoes_data
    """
    total_chutes = df['Total de chutes'].sum()
    chutes_no_alvo = df['Chutes no alvo'].sum()
    max_partidas = df['Partidas jogadas'].max()
    
    # Usando as mesmas métricas de api_utils.py
    stats = {
        'Total de chutes': total_chutes,
        'Chutes no alvo': chutes_no_alvo,
        'Eficiência': (chutes_no_alvo / total_chutes * 100).round(2),
        'Chutes/P': (total_chutes / max_partidas).round(2),
        'Chutes Alvo/P': (chutes_no_alvo / max_partidas).round(2),
        'Partidas jogadas': max_partidas,
        'Poisson_Prob_0.5': df['Poisson_Prob_0.5'].mean(),
        'Poisson_Prob_1.5': df['Poisson_Prob_1.5'].mean(),
        'Odd_Poisson_0.5': df['Odd_Poisson_0.5'].mean(),
        'Odd_Poisson_1.5': df['Odd_Poisson_1.5'].mean(),
        'IC_Superior': df['IC_Superior'].mean(),
        'IC_Inferior': df['IC_Inferior'].mean(),
        'Consistência': df['Consistência'].mode()[0],  # Pega a consistência mais comum
        'Odd_Mercado_Ref': df['Odd_Mercado_Ref'].mean()
    }
    return stats

def create_radar_chart(team1, team2, team1_stats, team2_stats):
    # Adicionando mais métricas ao gráfico radar
    categories = [
        'Total de chutes', 'Chutes no alvo', 'Eficiência', 
        'Chutes/P', 'Chutes Alvo/P', 'Poisson_Prob_0.5',
        'Odd_Poisson_0.5', 'IC_Superior'
    ]
    
    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=[team1_stats[cat] for cat in categories],
        theta=categories,
        fill='toself',
        name=team1
    ))
    fig.add_trace(go.Scatterpolar(
        r=[team2_stats[cat] for cat in categories],
        theta=categories,
        fill='toself',
        name=team2
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, max(max(team1_stats[cat] for cat in categories), 
                            max(team2_stats[cat] for cat in categories))]
            )),
        showlegend=True,
        title='Comparação de Finalizações entre Times'
    )

    st.plotly_chart(fig)

def show_comparison_table(team1, team2, team1_stats, team2_stats):
    comparison_df = pd.DataFrame({
        'Estatística': team1_stats.keys(),
        team1: team1_stats.values(),
        team2: team2_stats.values()
    })
    st.table(comparison_df)

def show_detailed_player_table(df1, df2, team1, team2):
    st.subheader('Tabela Detalhada de Jogadores')
    
    # Adicionar coluna de time aos DataFrames
    df1['Time'] = team1
    df2['Time'] = team2
    
    # Combinar os DataFrames
    df_combined = pd.concat([df1, df2])
    
    # Ordenar por total de chutes (decrescente)
    df_combined = df_combined.sort_values('Total de chutes', ascending=False)
    
    # Selecionar e renomear colunas para exibição, incluindo as estatísticas avançadas
    columns_to_display = [
        'Time', 'Jogador', 
        'Total de chutes', 'Chutes no alvo', 'Eficiência',
        'Chutes/P', 'Chutes Alvo/P', 
        'Partidas jogadas', 'Min/Jogados', 'Min/P',
        'Chutes alvo (last)', 'Chutes (last)',
        'Poisson_Prob_0.5', 'Poisson_Prob_1.5',
        'Odd_Poisson_0.5', 'Odd_Poisson_1.5',
        'IC_Superior', 'IC_Inferior',
        'Consistência', 'Odd_Mercado_Ref'
    ]
    
    df_display = df_combined[columns_to_display]
    
    # Exibir a tabela com colunas fixas
    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        column_order=["Time", "Jogador"] + [col for col in df_display.columns if col not in ["Time", "Jogador"]]
    )

if __name__ == "__main__":
    comparacao_times()
