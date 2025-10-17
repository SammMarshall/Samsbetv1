# dashboard/app.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import streamlit as st
from datetime import date, timedelta
import pandas as pd

# Importamos nosso serviço
from samsbet.services.match_service import get_daily_matches_dataframe

# --- Configuração da Página ---
st.set_page_config(
    page_title="SamsBet V2 - Jogos do Dia",
    page_icon="⚽",
    layout="wide"
)

# --- Funções ---
@st.cache_data(ttl=86400)
def load_data(for_date: date) -> pd.DataFrame:
    """Carrega os dados dos jogos para a data selecionada."""
    return get_daily_matches_dataframe(for_date)

# --- Título e Filtros ---
st.title("⚽ SamsBet V2 - Dashboard de Jogos")
st.sidebar.header("Filtros")
selected_date = st.sidebar.date_input(
    "Selecione a data", value=date.today(),
    format="DD/MM/YYYY"
)

# --- Conteúdo Principal ---
st.header(f"Jogos para {selected_date.strftime('%d/%m/%Y')}")

with st.spinner("Buscando dados no SofaScore... 🤖"):
    matches_df = load_data(selected_date)

if not matches_df.empty:
    # Garantir que o DataFrame original está no session_state para comparação
    if "original_matches_df" not in st.session_state or not st.session_state["original_matches_df"].equals(matches_df):
        matches_df_with_selection = matches_df.copy()
        matches_df_with_selection.insert(0, "Analisar", False)
        
        # Criar coluna com horário ajustado (-3 horas)
        matches_df_with_selection['display_time'] = pd.to_datetime(matches_df_with_selection['start_time']) - timedelta(hours=3)
        
        st.session_state["original_matches_df"] = matches_df
        st.session_state["edited_matches_df"] = matches_df_with_selection

    # Criar uma cópia para exibição com horário ajustado
    display_df = st.session_state["edited_matches_df"].copy()
    
    # Garantir que a coluna display_time existe e está atualizada
    if 'display_time' not in display_df.columns:
        display_df['display_time'] = pd.to_datetime(display_df['start_time']) - timedelta(hours=3)

    # Usamos o st.data_editor, que retorna o dataframe editado
    edited_df = st.data_editor(
        display_df,
        width='stretch',
        hide_index=True,
        column_order=(
            "Analisar", "display_time", "tournament_name", "country", "home_team", "away_team", "status"
        ),
        column_config={
            "Analisar": st.column_config.CheckboxColumn("Analisar", width="small"),
            "display_time": st.column_config.TimeColumn("Horário", format="HH:mm"),
            "tournament_name": "Campeonato",
            "country": "Local",
            "home_team": "Time da Casa",
            "away_team": "Time Visitante",
            "status": "Status",
            "start_time": None,  # Oculta a coluna original
        },
        disabled=["display_time", "tournament_name", "country", "home_team", "away_team", "status"]
    )
    
    # Verificamos se alguma linha foi marcada
    selected_row = edited_df[edited_df["Analisar"]]
    
    if not selected_row.empty:
        # Pega a primeira linha que foi marcada
        match = selected_row.iloc[0]
        
        # Armazena as informações na sessão
        st.session_state['selected_event_id'] = match['event_id']
        st.session_state['selected_home_team'] = match['home_team']
        st.session_state['selected_away_team'] = match['away_team']
        st.session_state['selected_custom_id'] = match['customId']


        # Limpa a seleção para o próximo rerun
        st.session_state["edited_matches_df"]["Analisar"] = False
        
        # Navega para a página de análise
        st.switch_page("pages/1_📊_Análise_do_Jogo.py")

else:
    st.warning("Nenhum jogo encontrado para a data selecionada.")