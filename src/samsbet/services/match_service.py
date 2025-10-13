# samsbet/services/match_service.py

import pandas as pd
from datetime import date, datetime
from typing import List, Dict, Any

# A biblioteca padrão do Python para lidar com fusos horários (IANA)
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# Importamos nosso cliente da camada de API
from samsbet.api.sofascore_client import SofaScoreClient

def get_daily_matches_dataframe(event_date: date) -> pd.DataFrame:
    """
    Busca os jogos de uma data específica e os retorna em um DataFrame Pandas estruturado,
    respeitando o fuso horário local do usuário para a definição do "dia".
    """
    client = SofaScoreClient()
    
    try:
        # Definimos o fuso horário de referência para a nossa aplicação.
        # Isso garante que "dia 8" significa dia 8 no Brasil, não em UTC.
        user_tz = ZoneInfo("America/Sao_Paulo")
    except ZoneInfoNotFoundError:
        # Fallback para sistemas (especialmente Windows mais antigos) que podem não ter o db de timezone.
        # Em caso de erro, avise o usuário ou use um fuso padrão.
        # pip install tzdata pode ser necessário nesses sistemas.
        user_tz = ZoneInfo("Etc/GMT+3")


    raw_events: List[Dict[str, Any]] = client.get_scheduled_events(event_date)

    if not raw_events:
        return pd.DataFrame(columns=[
            'event_id', 'tournament_name', 'home_team', 'away_team', 
            'start_time', 'status', 'home_team_id', 'away_team_id', 'tournament_id', 'customId'
        ])

    processed_matches = []
    for event in raw_events:
        start_timestamp = event.get('startTimestamp')
        
        if start_timestamp:
            # 1. Criamos um datetime "ciente" (aware) de que o timestamp é UTC.
            start_time_utc = datetime.fromtimestamp(start_timestamp, tz=ZoneInfo("UTC"))
            
            # 2. Convertemos o horário UTC para o fuso horário do usuário (ex: America/Sao_Paulo).
            start_time_local = start_time_utc.astimezone(user_tz)

            # 3. AGORA SIM: Filtramos comparando a data na visão do usuário.
            if start_time_local.date() == event_date:
                processed_matches.append({
                    'event_id': event.get('id'),
                    'tournament_name': event.get('tournament', {}).get('name'),
                    'country': event.get('tournament', {}).get('category', {}).get('name'),
                    'home_team': event.get('homeTeam', {}).get('name'),
                    'away_team': event.get('awayTeam', {}).get('name'),
                    # Armazenamos o horário local, que é mais útil para exibição.
                    'start_time': start_time_local,
                    'status': event.get('status', {}).get('description'),
                    'home_team_id': event.get('homeTeam', {}).get('id'),
                    'away_team_id': event.get('awayTeam', {}).get('id'),
                    'tournament_id': event.get('tournament', {}).get('id'),
                    'customId': event.get('customId'),
                })

    df = pd.DataFrame(processed_matches)

    if not df.empty:
        df = df.sort_values(by=['country', 'tournament_name', 'start_time']).reset_index(drop=True)

    return df