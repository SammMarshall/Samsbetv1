import json
import time
from api_utils import (
    make_api_request,
    get_event_details,
    get_shots_data,
    get_player_stats,
    process_finalizacoes_data
)

# Carregar o arquivo JSON com codificação UTF-8
try:
    with open('all_leagues_info.json', 'r', encoding='utf-8') as file:
        leagues_data = json.load(file)
except UnicodeDecodeError:
    # Se UTF-8 falhar, tente com ISO-8859-1
    with open('all_leagues_info.json', 'r', encoding='iso-8859-1') as file:
        leagues_data = json.load(file)

# Iterar sobre todas as ligas no JSON
for league_name, league_info in leagues_data.items():
    print(f"\n{'='*50}")
    print(f"Liga: {league_name}")
    print(f"{'='*50}")
    
    league_id = league_info.get('id')
    season_id = league_info.get('currentSeason', {}).get('id')
    
    if league_id and season_id:
        # Exemplo de uso da função get_player_stats
        player_stats = get_player_stats(
            league_id=league_id,
            season_id=season_id,
            quantidade=20,
            team_filter="",
            game_type="Ambos",
            position_filter="",
            order_by="-totalShots",
            fields="player.name,team.name,totalShots,shotsOnTarget,appearances,matchesStarted,minutesPlayed"
        )
        
        # Processar e exibir estatísticas de finalizações
        df_finalizacoes = process_finalizacoes_data(player_stats)
        print("\nEstatísticas de Finalizações:")
        print(df_finalizacoes.to_string(index=False))
    
    teams = league_info.get('teams', [])
    
    for team in teams:
        team_name = team['nome']
        last_event_id = team['lastEvent']['id']
        
        home_team, away_team = get_event_details(last_event_id)
        
        print(f"\nConfronto: {home_team} vs {away_team}")
        print(f"ID do evento: {last_event_id}")
        
        shots_data = get_shots_data(last_event_id)
        
        if shots_data['home'] or shots_data['away']:
            print(f"\nJogadores do {home_team} (casa) com chutes:")
            if shots_data['home']:
                for player in shots_data['home']:
                    print(f"- {player['name']}: {player['total_shots']} chute(s) no total, {player['shots_on_target']} no gol")
            else:
                print("Nenhum chute registrado.")
            
            print(f"\nJogadores do {away_team} (fora) com chutes:")
            if shots_data['away']:
                for player in shots_data['away']:
                    print(f"- {player['name']}: {player['total_shots']} chute(s) no total, {player['shots_on_target']} no gol")
            else:
                print("Nenhum chute registrado.")
        else:
            print("Nenhum dado de chute encontrado ou erro na requisição.")
        
        print("\n" + "-"*50)  # Separador entre confrontos
        
        # Intervalo entre as requisições
        time.sleep(5)
    
    if not teams:
        print(f"Nenhum time encontrado para a liga {league_name}.")

if not leagues_data:
    print("Nenhuma liga encontrada no JSON.")