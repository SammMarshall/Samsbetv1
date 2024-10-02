import streamlit as st
import plotly.express as px
import pandas as pd
from utils import *
from column_config import get_defesa_column_config
from api_utils import get_player_stats, process_defesa_data

def analise_defesa():
    st.title('Análise Estatística de Defesas de Goleiros no Futebol')

    leagues_data = load_leagues_data()
    leagues_by_country = get_leagues_by_country(leagues_data)
    selected_country, selected_league, leagues_in_country = select_country_and_league(leagues_by_country)
    league_id, season_id = get_league_info(leagues_in_country, selected_league)
    selected_teams, game_type, teams = select_teams_and_game_type(leagues_data, selected_league)
    
    quantidade = st.slider('Número de jogadores:', 30, 50)
    team_filter = get_team_filter(selected_teams, teams)

    data = get_player_stats(
        league_id, season_id, quantidade, team_filter, game_type,
        "position.in.G",
        "-saves",
        "saves%2CgoalsConcededInsideTheBox%2CgoalsConcededOutsideTheBox%2CmatchesStarted%2Cappearances%2CminutesPlayed"
    )

    df = process_defesa_data(data)
    column_config = get_defesa_column_config()
    st.dataframe(df, column_config=column_config)
    show_column_legend(column_config)

    create_defesas_chart(df, quantidade, game_type)
    analyze_player(df)

def create_defesas_chart(df, quantidade, game_type):
    fig = px.bar(df, x='Jogador', y='Defesas', title=f'Top {quantidade} goleiros por total de defesas ({game_type})')
    st.plotly_chart(fig)

def analyze_player(df):
    st.subheader('Análise Adicional')
    selected_player = st.selectbox('Selecione um goleiro para análise detalhada:', df['Jogador'])
    player_data = df[df['Jogador'] == selected_player].iloc[0]

    st.write(f"Estatísticas detalhadas para {selected_player}:")
    for col in df.columns:
        st.write(f"{col}: {player_data[col]}")

if __name__ == "__main__":
    analise_defesa()