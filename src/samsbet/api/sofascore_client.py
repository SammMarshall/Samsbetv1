# samsbet/api/sofascore_client.py

import time
import random
import requests
from typing import Dict, Any, List, Optional
from datetime import date
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SofaScoreClient:
    API_BASE_URL = "https://samsbet-proxy.onrender.com"
    REQUEST_INTERVAL_SECONDS = 1.1

    # ... (métodos __init__, _rate_limit, _make_request, get_scheduled_events, get_event_details não mudam) ...
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Cache-Control": "no-cache",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.sofascore.com/",
            "Origin": "https://www.sofascore.com",
        })
        self._last_request_time = 0
        # Cache simples em memória: endpoint -> (expires_at_epoch, data_json)
        self._cache: Dict[str, Any] = {}

        # Configura retries com backoff para erros transitórios e bloqueios temporários
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.8,
            status_forcelist=[403, 429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _rate_limit(self):
        current_time = time.time()
        elapsed_time = current_time - self._last_request_time
        # Aplica jitter para evitar padrões previsíveis
        interval_with_jitter = self.REQUEST_INTERVAL_SECONDS + random.uniform(0.0, 0.5)
        if elapsed_time < interval_with_jitter:
            time.sleep(interval_with_jitter - elapsed_time)
        self._last_request_time = time.time()

    def _get_ttl_for_endpoint(self, endpoint: str) -> int:
        """Define TTLs diferentes por tipo de recurso."""
        if endpoint.startswith("sport/football/scheduled-events/"):
            return 600  # 10 min
        if endpoint.endswith("/standings/total"):
            return 3600  # 1h
        if "/statistics" in endpoint:
            return 1800  # 30 min
        if endpoint.endswith("/events/last/0"):
            return 900  # 15 min
        if endpoint.endswith("/lineups"):
            return 1800  # 30 min
        if endpoint.endswith("/h2h/events"):
            return 3600  # 1h
        if endpoint.startswith("event/"):
            return 900  # 15 min para detalhes de evento
        return 600  # padrão

    def _make_request(self, endpoint: str) -> Dict[str, Any]:
        self._rate_limit()
        url = f"{self.API_BASE_URL}/{endpoint}"
        logging.info(f"Fazendo requisição para: {url}")
        # Tenta cache primeiro
        current_time = time.time()
        cached = self._cache.get(endpoint)
        if cached:
            expires_at, data = cached
            if current_time < expires_at:
                logging.info(f"Servindo do cache: {url}")
                return data
            else:
                # Expirou
                self._cache.pop(endpoint, None)
        try:
            response = self.session.get(url, timeout=15)
            # Trata bloqueios/rate-limit de forma graciosa para não derrubar o app
            if response.status_code in (403, 429):
                logging.warning(
                    f"Resposta {response.status_code} para {url}. Possível bloqueio/rate-limit. Retornando vazio."
                )
                return {}
            response.raise_for_status()
            data = response.json()
            # Armazena no cache somente respostas não vazias
            if isinstance(data, dict) and data:
                ttl = self._get_ttl_for_endpoint(endpoint)
                self._cache[endpoint] = (current_time + ttl, data)
            return data
        except requests.exceptions.JSONDecodeError:
            logging.error(f"Falha ao decodificar JSON da URL: {url}")
            return {}
        except requests.exceptions.RequestException as e:
            logging.error(f"Erro na requisição para {url}: {e}")
            # Em qualquer outra exceção de rede, retorna vazio para o chamador tratar
            return {}

    def get_scheduled_events(self, event_date: date) -> List[Dict[str, Any]]:
        date_str = event_date.strftime('%Y-%m-%d')
        endpoint = f"sport/football/scheduled-events/{date_str}"
        data = self._make_request(endpoint)
        return data.get("events", [])
    
    def get_event_details(self, event_id: int) -> Dict[str, Any]:
        endpoint = f"event/{event_id}"
        data = self._make_request(endpoint)
        return data.get("event", {})

    def get_player_stats_for_team(
        self,
        uniqueTournament_id: int,
        season_id: int,
        team_id: int,
        match_type: Optional[str] = None  # Novo parâmetro opcional
    ) -> List[Dict[str, Any]]:
        """
        Busca as estatísticas dos jogadores para um time, com filtro opcional de mando.
        """
        # Monta a string de filtros dinamicamente
        filters_list = [f"team.in.{team_id}"]
        if match_type in ["home", "away"]:
            filters_list.insert(0, f"type.EQ.{match_type}")
        
        # O separador para filtros na URL é %2C (uma vírgula)
        filters_str = "%2C".join(filters_list)

        endpoint = (
            f"unique-tournament/{uniqueTournament_id}/season/{season_id}/statistics"
            f"?limit=30&order=-totalShots&accumulation=total"
            f"&fields=totalShots%2CshotsOnTarget%2Cappearances%2CmatchesStarted%2CminutesPlayed"
            f"&filters={filters_str}"
        )
        data = self._make_request(endpoint)
        return data.get("results", [])

    def get_team_stats(self, team_id: int, uniqueTournament_id: int, season_id: int) -> Dict[str, Any]:
        """Busca as estatísticas gerais de um time em um torneio/temporada."""
        endpoint = f"team/{team_id}/unique-tournament/{uniqueTournament_id}/season/{season_id}/statistics/overall"
        data = self._make_request(endpoint)
        return data.get("statistics", {})

    def get_league_standings(self, tournament_id: int, season_id: int) -> Dict[str, Any]:
        """Busca a tabela de classificação de um torneio/temporada."""
        endpoint = f"tournament/{tournament_id}/season/{season_id}/standings/total"
        return self._make_request(endpoint)

    def get_team_last_event(self, team_id: int) -> Dict[str, Any]:
        """Busca a lista dos últimos eventos de um time e retorna o mais recente."""
        endpoint = f"team/{team_id}/events/last/0"
        data = self._make_request(endpoint)
        events = data.get("events", [])
        if events:
            return events[-1]
        return {}

    def get_shots_data_for_event(self, event_id: int) -> Dict[str, List[Dict[str, Any]]]:
        """Obtém dados de estatísticas de um evento, tratando o erro 404 graciosamente."""
        endpoint = f"event/{event_id}/lineups"
        event_stats_data = {'home': [], 'away': []}
        try:
            data = self._make_request(endpoint)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logging.warning(f"Dados de lineup não encontrados para o evento {event_id} (404).")
                return event_stats_data # Retorna vazio se não encontrar
            else:
                raise # Lança outros erros HTTP
        
        if not data:
            return event_stats_data
            
        for team_type in ['home', 'away']:
            if team_type in data and 'players' in data[team_type]:
                for player in data[team_type]['players']:
                    stats = player.get('statistics', {})
                    player_info = player.get('player', {})
                    shots_on_target = stats.get('onTargetScoringAttempt', 0)
                    shots_off_target = stats.get('shotOffTarget', 0)
                    shots_blocked = stats.get('blockedScoringAttempt', 0)
                    total_shots = shots_on_target + shots_off_target + shots_blocked
                    saves = stats.get('saves', 0)

                    if total_shots > 0 or saves > 0:
                        event_stats_data[team_type].append({
                            'player_id': player_info.get('id'), 'player_name': player_info.get('name'),
                            'shots_on_target': shots_on_target, 'total_shots': total_shots, 'saves': saves
                        })
        return event_stats_data

    def get_goalkeeper_stats_for_team(
        self,
        uniqueTournament_id: int,
        season_id: int,
        team_id: int,
    ) -> List[Dict[str, Any]]:
        """
        Busca as estatísticas de GOLEIROS para um time específico em uma temporada.
        """
        # Filtro combinado para buscar apenas goleiros (position.in.G) de um time específico (team.in.{team_id})
        filters_str = f"position.in.G%2Cteam.in.{team_id}"

        # Campos específicos para análise de goleiros
        fields_str = "saves%2CsavedShotsFromInsideTheBox%2CsavedShotsFromOutsideTheBox%2Cappearances%2CcleanSheet"

        endpoint = (
            f"unique-tournament/{uniqueTournament_id}/season/{season_id}/statistics"
            f"?limit=10&order=-rating&accumulation=total"
            f"&fields={fields_str}"
            f"&filters={filters_str}"
        )
        data = self._make_request(endpoint)
        return data.get("results", [])

    def get_h2h_events(self, custom_id: str) -> List[Dict[str, Any]]:
        """Busca o histórico de confrontos diretos (H2H) para um evento."""
        endpoint = f"event/{custom_id}/h2h/events"
        data = self._make_request(endpoint)
        return data.get("events", [])
    