# samsbet/api/sofascore_client.py

import time
import os
import random
import requests
from typing import Dict, Any, List, Optional
from datetime import date
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from samsbet.core.disk_cache import get_from_disk_cache, set_to_disk_cache

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SofaScoreClient:
    API_BASE_URL =  "https://samsbet-proxy.onrender.com" #"https://www.sofascore.com/api/v1"
    REQUEST_INTERVAL_SECONDS = 0.2
    # TTL máximo para persistência em disco (padrão: 24h)
    MAX_DISK_CACHE_TTL = int(os.environ.get("SAMSBET_DISK_CACHE_MAX_TTL", "86400"))

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
            return self.MAX_DISK_CACHE_TTL  # 10 min
        if endpoint.endswith("/standings/total"):
            return self.MAX_DISK_CACHE_TTL  # 1h
        if "/statistics" in endpoint:
            return self.MAX_DISK_CACHE_TTL  # 30 min
        if endpoint.endswith("/events/last/0"):
            return self.MAX_DISK_CACHE_TTL  # 15 min
        if endpoint.endswith("/lineups"):
            return self.MAX_DISK_CACHE_TTL  # 30 min
        if endpoint.endswith("/h2h/events"):
            return self.MAX_DISK_CACHE_TTL  # 1h
        if endpoint.startswith("event/"):
            return self.MAX_DISK_CACHE_TTL  # 15 min para detalhes de evento
        return self.MAX_DISK_CACHE_TTL  # padrão

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

        # Tenta cache em disco compartilhado (namespaced p/ invalidar versões antigas)
        cache_key = f"v2:{endpoint}"
        disk_cached = get_from_disk_cache(cache_key)
        if isinstance(disk_cached, dict) and disk_cached:
            logging.info(f"Servindo do cache em disco: {url}")
            return disk_cached
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
                # Persiste também em disco para compartilhar entre processos
                try:
                    set_to_disk_cache(cache_key, data, min(ttl, self.MAX_DISK_CACHE_TTL))
                except Exception:
                    pass
            return data
        except requests.exceptions.JSONDecodeError:
            logging.error(f"Falha ao decodificar JSON da URL: {url}")
            return {}
        except requests.exceptions.RequestException as e:
            logging.error(f"Erro na requisição para {url}: {e}")
            # Cacheia vazios curtos para evitar bombardeio em endpoints problemáticos
            try:
                set_to_disk_cache(endpoint, {}, ttl_seconds=300)
            except Exception:
                pass
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

    def get_team_stats_for_event(self, event_id: int) -> Dict[str, Dict[str, Any]]:
        """
        Obtém dados de estatísticas gerais de um evento (apenas tempo regulamentar - 1ST + 2ND).
        """
        endpoint = f"event/{event_id}/statistics"
        default_stats = {
            'home': {
                #Shots
                'total_shots': 0,
                'shots_on_target': 0,
                'hit_woodwork': 0, #chutes na trave
                #Match overview
                'expected_goals': 0.0, #expectativa de gols (float)
                'corner_kicks': 0, #escanteios
                'fouls': 0,
                'yellow_cards': 0,
                'red_cards': 0,
                'ball_possession': 0,
                #Attack
                'offsides': 0, #impedimento
                #Passes
                'throw_ins': 0, #laterais
                #Defending
                'total_tackles': 0, #desarmes
                #Goalkeeping
                'goal_kicks': 0, #tiro de meta
                'saves': 0
            },
            'away': {
                #Shots
                'total_shots': 0,
                'shots_on_target': 0,
                'hit_woodwork': 0, #chutes na trave
                #Match overview
                'expected_goals': 0.0, #expectativa de gols (float)
                'corner_kicks': 0, #escanteios
                'fouls': 0,
                'yellow_cards': 0,
                'red_cards': 0,
                'ball_possession': 0,
                #Attack
                'offsides': 0, #impedimento
                #Passes
                'throw_ins': 0, #laterais
                #Defending
                'total_tackles': 0, #desarmes
                #Goalkeeping
                'goal_kicks': 0, #tiro de meta
                'saves': 0
            }
        }   

        try:
            data = self._make_request(endpoint)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logging.warning(f"Dados de estatísticas não encontrados para o evento {event_id} (404).")
                return default_stats
            else:
                raise

        if not data or 'statistics' not in data or not data.get('statistics'):
            return default_stats

        # Função auxiliar para processar um período
        def process_period(period_groups, stats_dict):
            for group in period_groups:
                group_name = group.get('groupName', '')
                
                # Extrai estatísticas de Shots
                if group_name == 'Shots':
                    for stat in group.get('statisticsItems', []):
                        key = stat.get('key', '')
                        home_value = stat.get('homeValue', 0)
                        away_value = stat.get('awayValue', 0)
                        
                        if key == 'totalShotsOnGoal':
                            stats_dict['home']['total_shots'] += home_value
                            stats_dict['away']['total_shots'] += away_value
                        elif key == 'shotsOnGoal':
                            stats_dict['home']['shots_on_target'] += home_value
                            stats_dict['away']['shots_on_target'] += away_value
                        elif key == 'hitWoodwork':
                            stats_dict['home']['hit_woodwork'] += home_value
                            stats_dict['away']['hit_woodwork'] += away_value
                
                # Extrai estatísticas de Goalkeeping
                elif group_name == 'Goalkeeping':
                    for stat in group.get('statisticsItems', []):
                        key = stat.get('key', '')
                        home_value = stat.get('homeValue', 0)
                        away_value = stat.get('awayValue', 0)
                        
                        if key == 'goalkeeperSaves':
                            stats_dict['home']['saves'] += home_value
                            stats_dict['away']['saves'] += away_value
                        elif key == 'goalKicks':
                            stats_dict['home']['goal_kicks'] += home_value
                            stats_dict['away']['goal_kicks'] += away_value

                # Extrai estatísticas de Match Overview
                elif group_name == 'Match overview':
                    for stat in group.get('statisticsItems', []):
                        key = stat.get('key', '')
                        home_value = stat.get('homeValue', 0)
                        away_value = stat.get('awayValue', 0)

                        if key == 'expectedGoals':
                            stats_dict['home']['expected_goals'] += float(home_value)
                            stats_dict['away']['expected_goals'] += float(away_value)
                        elif key == 'cornerKicks':
                            stats_dict['home']['corner_kicks'] += home_value
                            stats_dict['away']['corner_kicks'] += away_value
                        elif key == 'fouls':
                            stats_dict['home']['fouls'] += home_value
                            stats_dict['away']['fouls'] += away_value
                        elif key == 'yellowCards':
                            stats_dict['home']['yellow_cards'] += home_value
                            stats_dict['away']['yellow_cards'] += away_value
                        elif key == 'redCards':
                            stats_dict['home']['red_cards'] += home_value
                            stats_dict['away']['red_cards'] += away_value
                        elif key == 'ballPossession':
                            # Para posse de bola, fazemos média ao invés de somar
                            stats_dict['home']['ball_possession'] += home_value / 2
                            stats_dict['away']['ball_possession'] += away_value / 2
        
                # Extrai estatísticas de Attack
                elif group_name == 'Attack':
                    for stat in group.get('statisticsItems', []):
                        key = stat.get('key', '')
                        home_value = stat.get('homeValue', 0)
                        away_value = stat.get('awayValue', 0)

                        if key == 'offsides':
                            stats_dict['home']['offsides'] += home_value
                            stats_dict['away']['offsides'] += away_value

                # Extrai estatísticas de Passes
                elif group_name == 'Passes':
                    for stat in group.get('statisticsItems', []):
                        key = stat.get('key', '')
                        home_value = stat.get('homeValue', 0)
                        away_value = stat.get('awayValue', 0)
                        
                        if key == 'throwIns':
                            stats_dict['home']['throw_ins'] += home_value
                            stats_dict['away']['throw_ins'] += away_value
                
                # Extrai estatísticas de Defending
                elif group_name == 'Defending':
                    for stat in group.get('statisticsItems', []):
                        key = stat.get('key', '')
                        home_value = stat.get('homeValue', 0)
                        away_value = stat.get('awayValue', 0)
                        
                        if key == 'totalTackle':
                            stats_dict['home']['total_tackles'] += home_value
                            stats_dict['away']['total_tackles'] += away_value

        # Alguns eventos trazem apenas período agregado (ex.: 'ALL')
        periods = data['statistics']
        has_first_second = any(p.get('period') in ['1ST', '2ND'] for p in periods)
        for period_data in periods:
            period = period_data.get('period')
            if has_first_second:
                if period in ['1ST', '2ND']:
                    groups = period_data.get('groups', [])
                    process_period(groups, default_stats)
            else:
                # Se não houver 1ST/2ND, processa todos os períodos disponíveis (ex.: 'ALL')
                groups = period_data.get('groups', ['ALL'])
                process_period(groups, default_stats)
        
        # Arredonda valores finais
        default_stats['home']['expected_goals'] = round(default_stats['home']['expected_goals'], 2)
        default_stats['away']['expected_goals'] = round(default_stats['away']['expected_goals'], 2)
        default_stats['home']['ball_possession'] = round(default_stats['home']['ball_possession'])
        default_stats['away']['ball_possession'] = round(default_stats['away']['ball_possession'])
        
        return default_stats

    def get_player_stats_for_event(self, event_id: int) -> Dict[str, List[Dict[str, Any]]]:
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
    
