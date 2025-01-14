import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import requests
from utils import *
from column_config import get_finalizacoes_column_config
from api_utils import get_player_stats, process_finalizacoes_data, get_team_stats, get_teams_stats, get_event_details, get_shots_data

@st.cache_data(ttl=3600)
def add_last_match_info(df, leagues_data, selected_league, selected_teams):
    league_info = leagues_data[selected_league]
    teams = league_info.get('teams', [])

    last_match_shots = {}
    for team in teams:
        team_name = team['nome']
        if team_name not in selected_teams:
            continue  # Pula times não selecionados
        
        last_event_id = team['lastEvent']['id']
        
        try:
            home_team, away_team = get_event_details(last_event_id)
            shots_data = get_shots_data(last_event_id)
            
            for team_type in ['home', 'away']:
                current_team = home_team if team_type == 'home' else away_team
                for player in shots_data[team_type]:
                    last_match_shots[(current_team, player['name'])] = {
                        'shots_on_target': player['shots_on_target'],
                        'total_shots': player['total_shots']
                    }
        except requests.exceptions.HTTPError as e:
            st.warning(f"Não foi possível obter dados para o time {team_name}. Erro: {e}")
            continue

    df['Chutes alvo (last)'] = df.apply(lambda row: last_match_shots.get((row['Time'], row['Jogador']), {}).get('shots_on_target', 0), axis=1)
    df['Chutes (last)'] = df.apply(lambda row: last_match_shots.get((row['Time'], row['Jogador']), {}).get('total_shots', 0), axis=1)

    return df

def analise_finalizacoes():
    st.title('Análise Estatística de Finalizações no Futebol')

    leagues_data = load_leagues_data()
    leagues_by_country = get_leagues_by_country(leagues_data)
    selected_country, selected_league, leagues_in_country = select_country_and_league(leagues_by_country)
    league_id, season_id = get_league_info(leagues_in_country, selected_league)
    selected_teams, game_type, teams = select_teams_and_game_type(leagues_data, selected_league)
    
    quantidade = st.slider('Número de jogadores:', 10, step=10)
    team_filter = get_team_filter(selected_teams, teams)

    data = get_player_stats(
        league_id, season_id, quantidade, team_filter, game_type,
        "position.in.D~M~F",
        "-shotsOnTarget",
        "totalShots%2CshotsOnTarget%2Cappearances%2CmatchesStarted%2CminutesPlayed"
    )

    df = process_finalizacoes_data(data)
    
    if 'Min/Jogados' not in df.columns:
        st.error("A coluna 'Min/Jogados' não está presente nos dados processados.")
        return
    
    if 'Time' not in df.columns:
        st.error("A coluna 'Time' não está presente nos dados processados.")
        return

    if st.button("Carregar informações da última partida"):
        df = add_last_match_info(df, leagues_data, selected_league, selected_teams)

    column_config = get_finalizacoes_column_config()
    st.dataframe(df, column_config=column_config)
    show_column_legend(column_config)

    # Calcular o total de finalizações por time
    team_shots = df.groupby('Time').agg({
        'Total de chutes': 'sum',
        'Chutes no alvo': 'sum',
        'Partidas jogadas': 'max'  # Assumindo que todos os jogadores do time jogaram o mesmo número de partidas
    }).reset_index()
    team_shots['Eficiência'] = (team_shots['Chutes no alvo'] / team_shots['Total de chutes'] * 100).round(2)
    team_shots['Chutes/P'] = (team_shots['Total de chutes'] / team_shots['Partidas jogadas']).round(2)
    team_shots['Chutes no alvo/P'] = (team_shots['Chutes no alvo'] / team_shots['Partidas jogadas']).round(2)

    # Criar gráfico de barras para finalizações por time
    fig = px.bar(team_shots, x='Time', y=['Total de chutes', 'Chutes no alvo'], 
                 title=f'Total de finalizações por time ({quantidade} maiores chutadores)',
                 labels={'value': 'Número de chutes', 'variable': 'Tipo de chute'},
                 barmode='group')
    
    # Adicionar texto de eficiência nas barras
    for i, row in team_shots.iterrows():
        fig.add_annotation(
            x=row['Time'],
            y=row['Total de chutes'],
            text=f"{row['Eficiência']}%",
            showarrow=False,
            yshift=10
        )

    st.plotly_chart(fig)

    # Comparação de times
    st.subheader('Comparação de Times')
    selected_teams_compare = st.multiselect('Selecione times para comparar:', team_shots['Time'].tolist())
    
    if len(selected_teams_compare) > 1:
        compare_teams(team_shots, selected_teams_compare)

    st.subheader('Análise Adicional')
    selected_player = st.selectbox('Selecione um jogador para análise detalhada:', df['Jogador'])
    player_data = df[df['Jogador'] == selected_player].iloc[0]

    st.write(f"Estatísticas detalhadas para {selected_player}:")
    for col in df.columns:
        st.write(f"{col}: {player_data[col]}")

def compare_teams(team_shots, selected_teams):
    comparison_df = team_shots[team_shots['Time'].isin(selected_teams)]
    
    # Criar gráfico de radar
    categories = ['Total de chutes', 'Chutes no alvo', 'Chutes/P', 'Chutes no alvo/P', 'Eficiência']
    fig = go.Figure()

    for team in selected_teams:
        team_data = comparison_df[comparison_df['Time'] == team]
        values = team_data[categories].values.flatten().tolist()
        values += values[:1]  # Repetir o primeiro valor para fechar o polígono
        
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories + [categories[0]],
            fill='toself',
            name=team
        ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, max(comparison_df[categories].max())]
            )),
        showlegend=True,
        title='Comparação de Times'
    )

    st.plotly_chart(fig)

    # Tabela de comparação
    st.subheader('Tabela de Comparação de Times')
    comparison_table = comparison_df[['Time'] + categories]
    st.table(comparison_table)

if __name__ == "__main__":
    analise_finalizacoes()
