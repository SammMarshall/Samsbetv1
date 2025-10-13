import json
import streamlit as st
import pandas as pd

@st.cache_data(ttl=3600)
def load_leagues_data():
    with open('all_leagues_info.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def get_leagues_by_country(leagues_data):
    leagues_by_country = {}
    for league_name, league_info in leagues_data.items():
        country = league_info['country']
        if country not in leagues_by_country:
            leagues_by_country[country] = []
        leagues_by_country[country].append({
            "id": league_info["league_id"],
            "season": league_info["season_id"],
            "nome": league_name
        })
    return leagues_by_country

def select_country_and_league(leagues_by_country, key_prefix=""):
    countries = sorted(leagues_by_country.keys())
    selected_country = st.selectbox('Selecione um país:', countries, key=f"{key_prefix}country")
    leagues_in_country = leagues_by_country[selected_country]
    selected_league = st.selectbox('Selecione uma liga:', [league['nome'] for league in leagues_in_country], key=f"{key_prefix}league")
    return selected_country, selected_league, leagues_in_country

def get_league_info(leagues_in_country, selected_league):
    league_info = next((league for league in leagues_in_country if league['nome'] == selected_league), None)
    if not league_info:
        st.error('Liga não encontrada')
        st.stop()
    return league_info['id'], league_info['season']

def select_teams_and_game_type(leagues_data, selected_league):
    teams = leagues_data[selected_league]['teams']
    selected_teams = st.multiselect('Selecione os times:', [team['nome'] for team in teams])
    game_type = st.radio('Selecione o tipo de jogo:', ['Ambos', 'Casa', 'Fora'], horizontal=True)
    return selected_teams, game_type, teams

def get_team_filter(selected_teams, teams):
    if selected_teams:
        team_ids = [str(team['id']) for team in teams if team['nome'] in selected_teams]
        return f"%2Cteam.in.{'~'.join(team_ids)}"
    return ""

def show_column_legend(column_config):
    if st.button("Mostrar Legenda das Colunas"):
        with st.expander("Legenda das Colunas", expanded=True):
            for col, config in column_config.items():
                help_text = config.get('help', 'Descrição não disponível')
                st.markdown(f"**{col}**: {help_text}")