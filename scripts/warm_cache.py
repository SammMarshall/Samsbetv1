"""
Script de aquecimento de cache para a aplicação SamsBet.

Objetivo: Pré-carregar no cache (st.cache_data/HTTP cache interno do client) os dados
necessários para que a página de análise de um jogo abra rapidamente durante o dia.

Execução sugerida: diariamente às 01:00 via agendador (cron/Linux, Task Scheduler/Windows, ou GitHub Actions).

Uso local (Windows PowerShell):
  python -m scripts.warm_cache
"""
from datetime import date
from typing import Dict
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))


# Importa serviços diretamente (sem depender do Streamlit runner)
from src.samsbet.constants import PRINCIPAL_LEAGUES_IDS
from src.samsbet.services.match_service import get_daily_matches_dataframe
from src.samsbet.services.stats_service import (
    get_match_analysis_data,
    get_goalkeeper_stats_for_match,
    get_h2h_data,
    get_summary_stats_for_event,
    get_h2h_goalkeeper_analysis,
)


def warm_single_match(event_id: int, home_team: str, away_team: str, custom_id: str | None) -> None:
    """Executa todas as consultas pesadas de uma partida para aquecer o cache."""
    # 1) Dados de análise principal (times, jogadores, resumos, standings)
    analysis = get_match_analysis_data(event_id, filter_by_location=False)

    # 2) Estatísticas de goleiros por time (temporada)
    home_last_event_id = analysis.get("home_last_event_id") if analysis else None
    away_last_event_id = analysis.get("away_last_event_id") if analysis else None
    last_match_saves_map = analysis.get("last_match_saves_map") if analysis else None
    _ = get_goalkeeper_stats_for_match(
        event_id,
        home_last_event_id=home_last_event_id,
        away_last_event_id=away_last_event_id,
        last_match_saves_map_prefetched=last_match_saves_map,
    )

    if not custom_id:
        return

    # 3) H2H básico (lista)
    h2h_df = get_h2h_data(custom_id, home_team, away_team)
    if h2h_df is None or h2h_df.empty:
        return

    # 4) Para cada H2H, carregar summary stats do evento (utilizado em várias seções)
    detailed_stats_cache: Dict[int, Dict] = {}
    for _, row in h2h_df.iterrows():
        event_id_row = row.get("event_id")
        # Skip quando o H2H indica ausência OU não fornece a flag
        if row.get("hasEventPlayerStatistics") is not True:
            continue
        if event_id_row:
            detailed_stats_cache[event_id_row] = get_summary_stats_for_event(event_id_row)

    # 5) Análise específica de goleiros baseada no H2H (usa cache acima)
    # Observação: aqui não passamos h2h_events brutos, pois o serviço já se vira com o custom_id
    _ = get_h2h_goalkeeper_analysis(custom_id, home_team, away_team, h2h_events=None)


def main() -> None:
    today = date.today()
    matches_df = get_daily_matches_dataframe(today)
    if matches_df is None or matches_df.empty:
        print("Nenhum jogo encontrado para hoje.")
        return

    # Filtra pelas ligas principais
    main_leagues_df = matches_df[matches_df["uniqueTournament_id"].isin(PRINCIPAL_LEAGUES_IDS)]

    print(f"Aquecendo cache para {len(main_leagues_df)} partidas de ligas principais...")
    for _, match in main_leagues_df.iterrows():
        try:
            event_id = match["event_id"]
            home_team = match["home_team"]
            away_team = match["away_team"]
            custom_id = match.get("customId")
            print(f" - {home_team} vs {away_team} (event_id={event_id})")
            warm_single_match(event_id, home_team, away_team, custom_id)
        except Exception as e:
            print(f"Falha ao aquecer cache para o jogo event_id={match.get('event_id')}: {e}")

    print("Aquecimento concluído.")


if __name__ == "__main__":
    main()


