import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from utils import load_leagues_data, get_leagues_by_country, select_country_and_league, get_league_info
from api_utils import get_player_stats, process_finalizacoes_data, get_event_details, get_shots_data

def comparacao_times():
    st.title('Comparação de Finalizações entre Times de Ligas Diferentes')

    # Carregar dados das ligas
    leagues_data = load_leagues_data()
    leagues_by_country = get_leagues_by_country(leagues_data)

    # Seleção do primeiro time
    st.subheader('Selecione o primeiro time')
    country1, league1, leagues_in_country1 = select_country_and_league(leagues_by_country, key_prefix="team1_")
    league_id1, season_id1 = get_league_info(leagues_in_country1, league1)
    team1 = st.selectbox('Selecione o primeiro time:', [team['nome'] for team in leagues_data[league1]['teams']], key="team1_select")

    # Seleção do segundo time
    st.subheader('Selecione o segundo time')
    country2, league2, leagues_in_country2 = select_country_and_league(leagues_by_country, key_prefix="team2_")
    league_id2, season_id2 = get_league_info(leagues_in_country2, league2)
    team2 = st.selectbox('Selecione o segundo time:', [team['nome'] for team in leagues_data[league2]['teams']], key="team2_select")

    if st.button('Comparar Times'):
        # Obter dados para o primeiro time
        team1_id = next(team['id'] for team in leagues_data[league1]['teams'] if team['nome'] == team1)
        data1 = get_player_stats(
            league_id1, season_id1, 50, f"%2Cteam.in.{team1_id}", "Ambos",
            "position.in.D~M~F", "-shotsOnTarget",
            "totalShots%2CshotsOnTarget%2Cappearances%2CmatchesStarted%2CminutesPlayed"
        )
        df1 = process_finalizacoes_data(data1)

        # Obter dados para o segundo time
        team2_id = next(team['id'] for team in leagues_data[league2]['teams'] if team['nome'] == team2)
        data2 = get_player_stats(
            league_id2, season_id2, 50, f"%2Cteam.in.{team2_id}", "Ambos",
            "position.in.D~M~F", "-shotsOnTarget",
            "totalShots%2CshotsOnTarget%2Cappearances%2CmatchesStarted%2CminutesPlayed"
        )
        df2 = process_finalizacoes_data(data2)

        # Obter dados da última partida
        last_match_data1 = get_last_match_data(leagues_data[league1]['teams'], team1)
        last_match_data2 = get_last_match_data(leagues_data[league2]['teams'], team2)

        # Adicionar dados da última partida aos DataFrames
        df1 = add_last_match_info(df1, last_match_data1, team1)
        df2 = add_last_match_info(df2, last_match_data2, team2)

        # Calcular estatísticas do time
        team1_stats = calculate_team_stats(df1)
        team2_stats = calculate_team_stats(df2)

        # Mostrar tabela detalhada com jogadores
        show_detailed_player_table(df1, df2, team1, team2)

        # Criar gráfico de radar
        create_radar_chart(team1, team2, team1_stats, team2_stats)

        # Mostrar tabela comparativa
        show_comparison_table(team1, team2, team1_stats, team2_stats)

def get_last_match_data(teams, team_name):
    team = next(team for team in teams if team['nome'] == team_name)
    last_event_id = team['lastEvent']['id']
    home_team, away_team = get_event_details(last_event_id)
    shots_data = get_shots_data(last_event_id)
    return {
        'home_team': home_team,
        'away_team': away_team,
        'shots_data': shots_data
    }

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
    total_chutes = df['Total de chutes'].sum()
    chutes_no_alvo = df['Chutes no alvo'].sum()
    max_partidas = df['Partidas jogadas'].max()
    
    return {
        'Total de chutes': total_chutes,
        'Chutes no alvo': chutes_no_alvo,
        'Eficiência': (chutes_no_alvo / total_chutes * 100).round(2),
        'Chutes/P': (total_chutes / max_partidas).round(2),
        'Chutes Alvo/P': (chutes_no_alvo / max_partidas).round(2),
        'Partidas jogadas': max_partidas,
    }

def create_radar_chart(team1, team2, team1_stats, team2_stats):
    categories = ['Total de chutes', 'Chutes no alvo', 'Eficiência', 'Chutes/P', 'Chutes Alvo/P']
    
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
                range=[0, max(max(team1_stats.values()), max(team2_stats.values()))]
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
    
    # Selecionar e renomear colunas para exibição
    columns_to_display = [
        'Time', 'Jogador', 'Total de chutes', 'Chutes no alvo', 'Eficiência',
        'Chutes/P', 'Chutes Alvo/P', 'Partidas jogadas', 'Min/Jogados', 'Min/P',
        'Chutes alvo (last)', 'Chutes (last)'
    ]
    
    df_display = df_combined[columns_to_display]
    
    # Exibir a tabela
    st.dataframe(df_display, use_container_width=True)

if __name__ == "__main__":
    comparacao_times()
