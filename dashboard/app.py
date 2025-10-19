# dashboard/app.py
import sys
import os
import pandas as pd
# Garante import do pacote e do script de aquecimento
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'src'))
sys.path.insert(0, PROJECT_ROOT)

import streamlit as st
from datetime import date
import pandas as pd
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from samsbet.services.match_service import get_daily_matches_dataframe
from samsbet.constants import PRINCIPAL_LEAGUES_IDS
from samsbet.core.disk_cache import _get_cache_dir

# Auto-aquecimento diário no primeiro acesso após 03:00 America/Sao_Paulo
def _auto_warm_if_needed():
    try:
        try:
            tz = ZoneInfo("America/Sao_Paulo")
        except ZoneInfoNotFoundError:
            tz = ZoneInfo("Etc/GMT+3")

        from datetime import datetime
        now_sp = datetime.now(tz)
        cache_dir = _get_cache_dir()
        marker_path = os.path.join(cache_dir, 'last_warm.txt')

        today_str = now_sp.date().isoformat()
        last_warm = None
        if os.path.exists(marker_path):
            try:
                with open(marker_path, 'r', encoding='utf-8') as f:
                    last_warm = f.read().strip()
            except Exception:
                last_warm = None

        should_warm = (last_warm != today_str) and (now_sp.hour >= 1)
        if should_warm:
            from scripts.warm_cache import main as warm_cache_main
            with st.spinner("Aquecendo cache diário... ⚙️"):
                warm_cache_main()
            try:
                os.makedirs(cache_dir, exist_ok=True)
                with open(marker_path, 'w', encoding='utf-8') as f:
                    f.write(today_str)
            except Exception:
                pass
    except Exception:
        # Não quebra a página se o aquecimento falhar
        pass

# --- Configuração da Página ---
st.set_page_config(
    page_title="SamsBet V2 - Jogos do Dia",
    page_icon="⚽",
    layout="wide"
)

# <<< PASSO 1: LIGAS PRINCIPAIS (extraídas para samsbet.constants) >>>

# --- Funções ---
@st.cache_data(ttl=86400)
def load_data(for_date: date) -> pd.DataFrame:
    """Carrega os dados dos jogos para a data selecionada."""
    return get_daily_matches_dataframe(for_date)

def display_games_table(df: pd.DataFrame, title: str, key_prefix: str):
    """
    Função auxiliar para exibir uma tabela de jogos e gerenciar a navegação.
    """
    if df.empty:
        st.info(f"Nenhum jogo encontrado para a categoria '{title}'.")
        return

    st.subheader(title)
    
    # Prepara o DataFrame para exibição
    df_display = df.copy()
    df_display['start_time'] = pd.to_datetime(df_display['start_time']) - pd.Timedelta(hours=3)
    
    df_display.insert(0, "Analisar", False)
    
    edited_df = st.data_editor(
        df_display,
        key=f"editor_{key_prefix}", # Chave única para cada tabela
        width='stretch',
        hide_index=True,
        column_order=(
            "Analisar", "start_time", "tournament_name", "country", "home_team", "away_team", "status",
            "uniqueTournament_id"
        ),
        column_config={
            "Analisar": st.column_config.CheckboxColumn("Analisar", width="small"),
            "start_time": st.column_config.TimeColumn("Horário", format="HH:mm"),
            "tournament_name": "Campeonato",
            "country": "País",
            "home_team": "Time da Casa",
            "away_team": "Time Visitante",
            "status": "Status",
            "uniqueTournament_id": "ID do Torneio",
        },
        disabled=df_display.columns.drop("Analisar")
    )
    
    selected_row = edited_df[edited_df["Analisar"]]
    
    if not selected_row.empty:
        match = selected_row.iloc[0]
        
        st.session_state['selected_event_id'] = match['event_id']
        st.session_state['selected_home_team'] = match['home_team']
        st.session_state['selected_away_team'] = match['away_team']
        st.session_state['selected_custom_id'] = match['customId']

        # Limpa a seleção para evitar re-navegação
        st.session_state[f"editor_{key_prefix}"]["edited_rows"] = {}
        
        st.switch_page("pages/1_📊_Análise_do_Jogo.py")

# --- Título e Filtros ---
st.title("⚽ SamsBet V2 - Dashboard de Jogos")
_auto_warm_if_needed()
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
    # <<< PASSO 2: DIVIDIR O DATAFRAME >>>
    main_leagues_df = matches_df[matches_df['uniqueTournament_id'].isin(PRINCIPAL_LEAGUES_IDS)]
    other_leagues_df = matches_df[~matches_df['uniqueTournament_id'].isin(PRINCIPAL_LEAGUES_IDS)]

    # <<< PASSO 3: RENDERIZAR AS DUAS TABELAS >>>
    display_games_table(main_leagues_df, "🏆 Ligas Principais", "main_leagues")
    st.divider()
    display_games_table(other_leagues_df, "🌍 Outros Jogos", "other_leagues")

else:
    st.warning("Nenhum jogo encontrado para a data selecionada.")
