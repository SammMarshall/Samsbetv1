import streamlit as st
import pandas as pd
from datetime import date
from typing import Dict

from samsbet.services.match_service import get_daily_matches_dataframe
from samsbet.services.stats_service import (
    get_match_analysis_data,
    get_goalkeeper_stats_for_match,
    get_h2h_data,
    get_summary_stats_for_event,
    get_h2h_goalkeeper_analysis,
)


@st.cache_data(ttl=86400)
def load_matches(for_date: date) -> pd.DataFrame:
    return get_daily_matches_dataframe(for_date)


@st.cache_data(ttl=86400)
def load_analysis_data(event_id: int, filter_by_location: bool):
    return get_match_analysis_data(event_id, filter_by_location=filter_by_location)


@st.cache_data(ttl=86400)
def load_gk_stats(
    event_id: int,
    home_last_event_id: int | None,
    away_last_event_id: int | None,
    last_match_saves_map: dict | None,
):
    return get_goalkeeper_stats_for_match(
        event_id,
        home_last_event_id=home_last_event_id,
        away_last_event_id=away_last_event_id,
        last_match_saves_map_prefetched=last_match_saves_map,
    )


@st.cache_data(ttl=86400)
def load_h2h(custom_id: str, home_team: str, away_team: str):
    return get_h2h_data(custom_id, home_team, away_team)


@st.cache_data(ttl=86400)
def load_event_summary_stats(event_id: int):
    return get_summary_stats_for_event(event_id)


@st.cache_data(ttl=86400)
def load_h2h_gk_analysis(
    custom_id: str, home_team: str, away_team: str, h2h_events: list = None, detailed_stats_cache: Dict | None = None
):
    return get_h2h_goalkeeper_analysis(custom_id, home_team, away_team, h2h_events, detailed_stats_cache)


