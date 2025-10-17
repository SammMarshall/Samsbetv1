# samsbet/services/stats_service.py

import pandas as pd
import numpy as np
from scipy.stats import poisson
from typing import List, Dict, Any
from samsbet.api.sofascore_client import SofaScoreClient

def _process_player_stats_to_dataframe(
    raw_player_stats: List[Dict[str, Any]],
    last_match_shots_map: Dict[int, Dict[str, int]]
) -> pd.DataFrame:
    """
    Processa os dados brutos de jogadores e adiciona uma camada rica de análise estatística
    e probabilidades para apostas esportivas.
    """
    if not raw_player_stats:
        return pd.DataFrame()
    
    

    all_data = []
    for player_data in raw_player_stats:
        player_info = player_data.get("player", {})
        player_id = player_info.get("id")

        last_match_stats = last_match_shots_map.get(player_id, {})

        all_data.append({
            'Jogador': player_info.get('name'),
            'Total de chutes': player_data.get('totalShots', 0),
            'Chutes no alvo': player_data.get('shotsOnTarget', 0),
            'Partidas jogadas': player_data.get('appearances', 0),
            'Min/Jogados': player_data.get('minutesPlayed', 0),
            'Chutes (Última)': last_match_stats.get('total_shots', 0),
            'Chutes Alvo (Última)': last_match_stats.get('shots_on_target', 0)
        })

    if not all_data:
        return pd.DataFrame()

    df = pd.DataFrame(all_data)

    with np.errstate(divide='ignore', invalid='ignore'):
        df['Chutes/P'] = (df['Total de chutes'] / df['Partidas jogadas']).round(2)
        df['Chutes Alvo/P'] = (df['Chutes no alvo'] / df['Partidas jogadas']).round(2)
        df['Min/Chute'] = (df['Min/Jogados'] / df['Total de chutes']).round(2)
        df['Min/Chute Alvo'] = (df['Min/Jogados'] / df['Chutes no alvo']).round(2)
        df['Min/Partida'] = (df['Min/Jogados'] / df['Partidas jogadas']).round(2)
        df['Eficiência %'] = (df['Chutes no alvo'] / df['Total de chutes'] * 100).round(1)
    df = df.fillna(0)

    min_jogos = 5
    jogos_validos = df['Partidas jogadas'] >= min_jogos
    lambda_chutes_alvo = df.loc[jogos_validos, 'Chutes Alvo/P']

    df['Prob_Over_0.5'] = np.nan
    df.loc[jogos_validos, 'Prob_Over_0.5'] = 1 - poisson.cdf(0, lambda_chutes_alvo)

    df['Prob_Over_1.5'] = np.nan
    df.loc[jogos_validos, 'Prob_Over_1.5'] = 1 - poisson.cdf(1, lambda_chutes_alvo)

    df['Odd_Over_0.5'] = (1 / df['Prob_Over_0.5']).round(2)
    df['Odd_Over_1.5'] = (1 / df['Prob_Over_1.5']).round(2)

    erro_padrao = np.sqrt(df['Chutes Alvo/P'] / df['Partidas jogadas'])
    df['IC_Inferior'] = np.nan
    df.loc[jogos_validos, 'IC_Inferior'] = (df['Chutes Alvo/P'] - 1.96 * erro_padrao).round(2)
    
    df['IC_Superior'] = np.nan
    df.loc[jogos_validos, 'IC_Superior'] = (df['Chutes Alvo/P'] + 1.96 * erro_padrao).round(2)

    condicoes_alta = (jogos_validos) & (df['Chutes Alvo/P'] > 0.8) & (df['IC_Inferior'] > 0.4)
    condicoes_media = (jogos_validos) & (df['Chutes Alvo/P'] > 0.4)
    df['Consistência'] = np.select(
        [condicoes_alta, condicoes_media],
        ['Alta', 'Média'],
        default='Baixa'
    )

    df = df.sort_values(by="Chutes Alvo/P", ascending=False).reset_index(drop=True)

    ordem_colunas = [
        'Jogador', 'Chutes Alvo/P', 'Partidas jogadas', 'Min/Partida', 'Consistência', 'Chutes (Última)', 'Chutes Alvo (Última)',
        'Odd_Over_0.5', 'Odd_Over_1.5', 'Prob_Over_0.5', 'Prob_Over_1.5', 'Eficiência %', 'Total de chutes', 'Chutes no alvo',
        'Chutes/P', 'Min/Jogados', 'Min/Chute', 'Min/Chute Alvo', 'IC_Inferior', 'IC_Superior'
    ]
    
    # <<< MUDANÇA AQUI >>>
    # Apenas reordenamos as colunas. Não usamos mais o .fillna('-') aqui.
    # O DataFrame agora manterá os valores NaN, que são numericamente corretos.
    df_final = df.reindex(columns=ordem_colunas)

    df_final = df_final.fillna(0)

    return df_final

def _process_goalkeeper_stats_to_dataframe(
    raw_gk_stats: List[Dict[str, Any]],
    last_match_saves_map: Dict[str, int] # O mapa usa NOME (str) como chave
) -> pd.DataFrame:
    """
    Processa a lista bruta de estatísticas de goleiros e a transforma em um DataFrame,
    adicionando as defesas da última partida.
    """
    if not raw_gk_stats:
        return pd.DataFrame()

    all_data = []
    for gk_data in raw_gk_stats:
        player_info = gk_data.get("player", {})
        player_name = player_info.get("name")
        
        all_data.append({
            'Goleiro': player_name,
            'Partidas': gk_data.get('appearances', 0),
            'Sem Sofrer Gol': gk_data.get('cleanSheet', 0),
            'Defesas': gk_data.get('saves', 0),
            'Defesas (Dentro da Área)': gk_data.get('savedShotsFromInsideTheBox', 0),
            'Defesas (Fora da Área)': gk_data.get('savedShotsFromOutsideTheBox', 0),
            'Defesas (Última)': last_match_saves_map.get(player_name, 0)
        })
    
    df = pd.DataFrame(all_data)
    
    with np.errstate(divide='ignore', invalid='ignore'):
        df['Defesas/J'] = (df['Defesas'] / df['Partidas']).round(2)
        df['Jogos s/ Sofrer Gol (%)'] = (df['Sem Sofrer Gol'] / df['Partidas'] * 100).round(1)
    
    df = df.fillna(0)

    # <<< NOVO BLOCO DE ANÁLISE DE ODDS >>>
    min_jogos = 5
    jogos_validos = df['Partidas'] >= min_jogos
    lambda_defesas = df.loc[jogos_validos, 'Defesas/J']

    # Linhas de aposta que vamos calcular (1.5, 2.5, 3.5)
    for line in [0.5, 1.5, 2.5, 3.5, 4.5]:
        k = int(line) # O valor para o CDF (ex: para Over 2.5, k=2)
        
        # Probabilidade de Over (1 - P(defesas <= k))
        prob_over = 1 - poisson.cdf(k, lambda_defesas)
        df[f'Prob_Over_{line}'] = np.nan
        df.loc[jogos_validos, f'Prob_Over_{line}'] = prob_over

        # Probabilidade de Under (P(defesas <= k))
        prob_under = poisson.cdf(k, lambda_defesas)
        df[f'Prob_Under_{line}'] = np.nan
        df.loc[jogos_validos, f'Prob_Under_{line}'] = prob_under

        # Odds Justas
        df[f'Odd_Over_{line}'] = (1 / df[f'Prob_Over_{line}']).round(2)
        df[f'Odd_Under_{line}'] = (1 / df[f'Prob_Under_{line}']).round(2)
    
    df = df.fillna(0)
    return df.sort_values(by="Partidas", ascending=False).reset_index(drop=True)

def get_match_analysis_data(
    event_id: int, filter_by_location: bool = False
) -> Dict[str, Any]:
    """
    Orquestrador que busca DADOS COMPLETOS (jogadores, time e posição) para a análise.
    """
    client = SofaScoreClient()
    event_details = client.get_event_details(event_id)
    if not event_details: return {}

    tournament = event_details.get("tournament", {})
    tournament_id = event_details.get("tournament", {}).get("id")
    uniqueTournament_id = event_details.get("tournament", {}).get("uniqueTournament", {}).get("id")
    season_id = event_details.get("season", {}).get("id")
    home_team_id = event_details.get("homeTeam", {}).get("id")
    away_team_id = event_details.get("awayTeam", {}).get("id")
    if not all([tournament_id, season_id, home_team_id, away_team_id]): return {}

    # <<< PASSO ADICIONAL 1: Buscar a tabela de classificação >>>
    # <<< MUDANÇA 1: Criamos um mapa mais completo para os dados da tabela >>>
    standings_data = client.get_league_standings(tournament_id, season_id)
    standings_info_map = {} # De 'positions_map' para 'standings_info_map'
    if standings_data and 'standings' in standings_data and standings_data['standings']:
        rows = standings_data['standings'][0].get('rows', [])
        for row in rows:
            team_id = row.get('team', {}).get('id')
            if team_id:
                standings_info_map[team_id] = {
                    "position": row.get('position'),
                    "matches": row.get('matches'),
                    "scoresFor": row.get('scoresFor'),
                    "scoresAgainst": row.get('scoresAgainst')
                }

    home_last_event = client.get_team_last_event(home_team_id)
    away_last_event = client.get_team_last_event(away_team_id)

    # 2. Construir um mapa unificado de chutes da última partida (player_id -> stats)
    last_match_shots_map = {}
    if home_last_event_id := home_last_event.get("id"):
        shots_data = client.get_player_stats_for_event(home_last_event_id)
        for team_type in ['home', 'away']:
            for player in shots_data[team_type]:
                last_match_shots_map[player['player_id']] = player

    if away_last_event_id := away_last_event.get("id"):
        shots_data = client.get_player_stats_for_event(away_last_event_id)
        for team_type in ['home', 'away']:
            for player in shots_data[team_type]:
                # Adiciona ou sobrescreve, garantindo os dados do evento mais recente de cada jogador
                last_match_shots_map[player['player_id']] = player            

    home_match_type = "home" if filter_by_location else None
    away_match_type = "away" if filter_by_location else None
    
    raw_players_home = client.get_player_stats_for_team(uniqueTournament_id, season_id, home_team_id, match_type=home_match_type)
    raw_players_away = client.get_player_stats_for_team(uniqueTournament_id, season_id, away_team_id, match_type=away_match_type)

    team_stats_home = client.get_team_stats(home_team_id, uniqueTournament_id, season_id)
    team_stats_away = client.get_team_stats(away_team_id, uniqueTournament_id, season_id)
    
    home_players_df = _process_player_stats_to_dataframe(raw_players_home, last_match_shots_map)
    away_players_df = _process_player_stats_to_dataframe(raw_players_away, last_match_shots_map)

    def _create_summary(stats: Dict, team_id: int) -> Dict:
        # Pega os dados específicos deste time do nosso mapa
        team_standings_info = standings_info_map.get(team_id, {})
        
        matches = team_standings_info.get('matches', 0) # Usamos o 'matches' da tabela, que é mais confiável
        summary = {
            'Posição': team_standings_info.get('position', 'N/A'),
            'Total de Jogos': matches
        }
        
        # Se não houver jogos, retorna o resumo com zeros para evitar erros de divisão
        if matches == 0:
            default_metrics = {
                'Média Chutes/J': 0, 'Média Chutes Alvo/J': 0,
                'Grandes Chances Criadas/J': 0, 'Índice de Perigo (%)': 0,
                'Conversão de Grandes Chances (%)': 0,
                'Grandes Chances Cedidas/J': 0, 'Média Chutes Alvo Cedidos/J': 0,
                'Média Defesas/J': 0, 'Média Gols Pró/J': 0,
                'Média Gols Contra/J': 0,
                'Média Escanteios/J': 0,
                'Média Escanteios Contra/J': 0
            }
            summary.update(default_metrics)
            return summary

        # --- Métricas Ofensivas (Pró) ---
        summary['Média Chutes/J'] = round(stats.get('shots', 0) / matches, 2)
        summary['Média Chutes Alvo/J'] = round(stats.get('shotsOnTarget', 0) / matches, 2)
        summary['Grandes Chances Criadas/J'] = round(stats.get('bigChancesCreated', 0) / matches, 2)
        summary['Média Gols Pró/J'] = round(team_standings_info.get('scoresFor', 0) / matches, 2)
        
        total_shots = stats.get('shots', 0)
        if total_shots > 0:
            summary['Índice de Perigo (%)'] = round((stats.get('shotsFromInsideTheBox', 0) / total_shots) * 100, 1)
        else:
            summary['Índice de Perigo (%)'] = 0

        big_chances_created = stats.get('bigChancesCreated', 0)
        if big_chances_created > 0:
            goals = stats.get('goalsScored', 0) - stats.get('penaltyGoals', 0)
            summary['Conversão de Grandes Chances (%)'] = round((goals / big_chances_created) * 100, 1)
        else:
            summary['Conversão de Grandes Chances (%)'] = 0
            
        # --- Métricas Defensivas (Contra) ---
        summary['Grandes Chances Cedidas/J'] = round(stats.get('bigChancesAgainst', 0) / matches, 2)
        summary['Média Chutes Alvo Cedidos/J'] = round(stats.get('shotsOnTargetAgainst', 0) / matches, 2)
        summary['Média Defesas/J'] = round(stats.get('saves', 0) / matches, 2)
        summary['Média Gols Contra/J'] = round(team_standings_info.get('scoresAgainst', 0) / matches, 2)

        # Média de escanteios >>>
        summary['Média Escanteios/J'] = round(stats.get('corners', 0) / matches, 2)
        summary['Média Escanteios Contra/J'] = round(stats.get('cornersAgainst', 0) / matches, 2)

        return summary

    # Constrói um mapa de defesas da última partida por nome do jogador (para reuso na aba de goleiros)
    last_match_saves_map_by_name: Dict[str, int] = {}
    for player_stats in last_match_shots_map.values():
        saves_val = player_stats.get('saves', 0)
        if saves_val and saves_val > 0:
            player_name = player_stats.get('player_name')
            if player_name:
                last_match_saves_map_by_name[player_name] = saves_val

    analysis_data = {
        "tournament_name": tournament.get("name", "Campeonato"),
        # IDs de último jogo para reuso em outras consultas (ex.: goleiros)
        "home_last_event_id": home_last_event.get("id"),
        "away_last_event_id": away_last_event.get("id"),
        # Repassa também defesas da última partida já coletadas
        "last_match_saves_map": last_match_saves_map_by_name,
        "home": {
            "players": home_players_df,
            "summary": _create_summary(team_stats_home, home_team_id)
        },
        "away": {
            "players": away_players_df,
            "summary": _create_summary(team_stats_away, away_team_id)
        }
    }
    return analysis_data

def get_goalkeeper_stats_for_match(
    event_id: int,
    home_last_event_id: int | None = None,
    away_last_event_id: int | None = None,
    last_match_saves_map_prefetched: Dict[str, int] | None = None,
) -> Dict[str, pd.DataFrame]:
    """
    Orquestrador dedicado a buscar e processar as estatísticas de goleiros,
    incluindo dados da última partida.
    """
    client = SofaScoreClient()
    event_details = client.get_event_details(event_id)
    if not event_details:
        return {"home": pd.DataFrame(), "away": pd.DataFrame()}

    uniqueTournament_id = event_details.get("tournament", {}).get("uniqueTournament", {}).get("id")
    season_id = event_details.get("season", {}).get("id")
    home_team_id = event_details.get("homeTeam", {}).get("id")
    away_team_id = event_details.get("awayTeam", {}).get("id")

    if not all([uniqueTournament_id, season_id, home_team_id, away_team_id]):
        return {"home": pd.DataFrame(), "away": pd.DataFrame()}

    # --- Busca e construção do mapa de defesas da última partida ---
    if last_match_saves_map_prefetched is not None:
        last_match_saves_map = last_match_saves_map_prefetched
    else:
        # Reutiliza IDs de último jogo se fornecidos para evitar chamadas extras
        if home_last_event_id is None:
            home_last_event = client.get_team_last_event(home_team_id)
            home_last_event_id = home_last_event.get("id")
        if away_last_event_id is None:
            away_last_event = client.get_team_last_event(away_team_id)
            away_last_event_id = away_last_event.get("id")

        last_match_saves_map: Dict[str, int] = {}
        if home_last_event_id:
            stats_data = client.get_player_stats_for_event(home_last_event_id)
            for team_type in ['home', 'away']:
                for player in stats_data[team_type]:
                    if player.get('saves', 0) > 0:
                        last_match_saves_map[player['player_name']] = player['saves']

        if away_last_event_id:
            stats_data = client.get_player_stats_for_event(away_last_event_id)
            for team_type in ['home', 'away']:
                for player in stats_data[team_type]:
                    if player.get('saves', 0) > 0:
                        last_match_saves_map[player['player_name']] = player['saves']
        
    raw_gk_home = client.get_goalkeeper_stats_for_team(uniqueTournament_id, season_id, home_team_id)
    raw_gk_away = client.get_goalkeeper_stats_for_team(uniqueTournament_id, season_id, away_team_id)

    home_gk_df = _process_goalkeeper_stats_to_dataframe(raw_gk_home, last_match_saves_map)
    away_gk_df = _process_goalkeeper_stats_to_dataframe(raw_gk_away, last_match_saves_map)

    return {"home": home_gk_df, "away": away_gk_df}

def _process_h2h_events_to_dataframe(
    raw_h2h_events: List[Dict[str, Any]], home_team_name: str, away_team_name: str
) -> pd.DataFrame:
    """
    Processa a lista de eventos H2H, pulando o jogo futuro e corrigindo placares
    de jogos com disputas de pênaltis.
    """
    if not raw_h2h_events or len(raw_h2h_events) <= 1:
        return pd.DataFrame()

    processed_matches = []
    
    for event in raw_h2h_events[1:]:
        home_score_obj = event.get("homeScore", {})
        away_score_obj = event.get("awayScore", {})

        # <<< MUDANÇA CRUCIAL AQUI >>>
        # Subtraímos os gols de pênaltis do placar 'current' para obter o resultado do jogo.
        # Se não houver pênaltis, .get("penalties", 0) retorna 0, e o cálculo permanece correto.
        home_score = home_score_obj.get("current", 0) - home_score_obj.get("penalties", 0)
        away_score = away_score_obj.get("current", 0) - away_score_obj.get("penalties", 0)
        
        # A lógica para determinar o vencedor usa o placar corrigido do jogo.
        if home_score > away_score:
            winner = event.get("homeTeam", {}).get("name")
        elif away_score > home_score:
            winner = event.get("awayTeam", {}).get("name")
        else:
            winner = "Empate"

        processed_matches.append({
            "event_id": event.get("id"),
            "Data": pd.to_datetime(event.get("startTimestamp"), unit='s'),
            "Campeonato": event.get("tournament", {}).get("name"),
            "Time da Casa": event.get("homeTeam", {}).get("name"),
            "Placar": f"{home_score} - {away_score}",
            "Time Visitante": event.get("awayTeam", {}).get("name"),
            "Vencedor": winner,
            "Gols Casa": home_score,
            "Gols Visitante": away_score
        })
    
    if not processed_matches:
        return pd.DataFrame()

    df = pd.DataFrame(processed_matches)
    return df.sort_values(by="Data", ascending=False).reset_index(drop=True)

def get_h2h_data(custom_id: str, home_team_name: str, away_team_name: str) -> pd.DataFrame:
    """
    Orquestrador dedicado a buscar e processar os dados de confronto direto (H2H).
    """
    client = SofaScoreClient()
    raw_h2h_events = client.get_h2h_events(custom_id)
    h2h_df = _process_h2h_events_to_dataframe(raw_h2h_events, home_team_name, away_team_name)
    return h2h_df

def get_summary_stats_for_event(event_id: int) -> Dict[str, Dict[str, int]]:
    """
    Busca os dados de um evento usando o endpoint de estatísticas agregadas.
    """
    client = SofaScoreClient()
    # Chama a sua nova e poderosa função!
    stats = client.get_team_stats_for_event(event_id) 

    # Como a nova função já retorna os dados agregados, só precisamos garantir o formato.
    summary = {
        "home": {
            # Shots
            "total_shots": stats.get('home', {}).get('total_shots', 0),
            "shots_on_target": stats.get('home', {}).get('shots_on_target', 0),
            "hit_woodwork": stats.get('home', {}).get('hit_woodwork', 0),
            # Match Overview
            "expected_goals": stats.get('home', {}).get('expected_goals', 0.0),
            "corner_kicks": stats.get('home', {}).get('corner_kicks', 0),
            "fouls": stats.get('home', {}).get('fouls', 0),
            "yellow_cards": stats.get('home', {}).get('yellow_cards', 0),
            "red_cards": stats.get('home', {}).get('red_cards', 0),
            "ball_possession": stats.get('home', {}).get('ball_possession', 0),
            # Attack
            "offsides": stats.get('home', {}).get('offsides', 0),
            # Passes
            "throw_ins": stats.get('home', {}).get('throw_ins', 0),
            # Defending
            "total_tackles": stats.get('home', {}).get('total_tackles', 0),
            # Goalkeeping
            "goal_kicks": stats.get('home', {}).get('goal_kicks', 0),
            "saves": stats.get('home', {}).get('saves', 0)
        },
        "away": {
            # Shots
            "total_shots": stats.get('away', {}).get('total_shots', 0),
            "shots_on_target": stats.get('away', {}).get('shots_on_target', 0),
            "hit_woodwork": stats.get('away', {}).get('hit_woodwork', 0),
            # Match Overview
            "expected_goals": stats.get('away', {}).get('expected_goals', 0.0),
            "corner_kicks": stats.get('away', {}).get('corner_kicks', 0),
            "fouls": stats.get('away', {}).get('fouls', 0),
            "yellow_cards": stats.get('away', {}).get('yellow_cards', 0),
            "red_cards": stats.get('away', {}).get('red_cards', 0),
            "ball_possession": stats.get('away', {}).get('ball_possession', 0),
            # Attack
            "offsides": stats.get('away', {}).get('offsides', 0),
            # Passes
            "throw_ins": stats.get('away', {}).get('throw_ins', 0),
            # Defending
            "total_tackles": stats.get('away', {}).get('total_tackles', 0),
            # Goalkeeping
            "goal_kicks": stats.get('away', {}).get('goal_kicks', 0),
            "saves": stats.get('away', {}).get('saves', 0)
        }
    }

    return summary

def get_h2h_goalkeeper_analysis(custom_id: str, home_team_name: str, away_team_name: str) -> Dict[str, Any]:
    """
    Analisa o histórico de confrontos para calcular a média de defesas da POSIÇÃO de goleiro,
    usando apenas os jogos que contêm estatísticas válidas.
    """
    client = SofaScoreClient()
    h2h_events = client.get_h2h_events(custom_id)
    
    if not h2h_events or len(h2h_events) <= 1:
        return {}

    home_team_saves_list = []
    away_team_saves_list = []

    for event in h2h_events[1:]:
        event_id = event.get("id")
        if not event_id: continue
        
        stats = get_summary_stats_for_event(event_id)
        
        # <<< MUDANÇA E CORREÇÃO AQUI >>>
        # Verificamos se há dados de defesas válidos ANTES de adicioná-los à lista.
        # Isso garante que não estamos adicionando '0' de jogos sem estatísticas.
        home_saves = stats['home']['saves']
        away_saves = stats['away']['saves']
        home_total_shots = stats['home']['total_shots']
        away_total_shots = stats['away']['total_shots']

        if home_saves > 0 or away_saves > 0 or home_total_shots > 0 or away_total_shots > 0:
            if event.get("homeTeam", {}).get("name") == home_team_name:
                home_team_saves_list.append(home_saves)
                away_team_saves_list.append(away_saves)
            else:
                home_team_saves_list.append(away_saves)
                away_team_saves_list.append(home_saves)
    
    # Função auxiliar interna para calcular as odds
    def calculate_odds(saves_list: List[int]) -> Dict[str, Any]:
        if not saves_list:
            return {}
        
        avg_saves = np.mean(saves_list)
        results = {"avg_saves": round(avg_saves, 2)}
        
        # Linhas de aposta comuns para defesas de goleiro
        for line in [0.5, 1.5, 2.5, 3.5, 4.5]:
            k = int(line)
            
            # Usamos o modelo de Poisson com a média de defesas do H2H como nosso lambda
            prob_under = poisson.cdf(k, avg_saves)
            prob_over = 1 - prob_under
            
            # Converte probabilidades em Odds Justas
            results[f'Odd_Over_{line}'] = round(1 / prob_over, 2) if prob_over > 0 else "∞"
            results[f'Odd_Under_{line}'] = round(1 / prob_under, 2) if prob_under > 0 else "∞"
            
        return results

    # Retorna um dicionário com os resultados para cada time
    return {
        "home": calculate_odds(home_team_saves_list),
        "away": calculate_odds(away_team_saves_list)
    }
