import json
from datetime import datetime
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from api_utils import make_api_request

def get_last_event_id(team_id):
    url = f'https://api.sofascore.com/api/v1/team/{team_id}/events/last/0'
    try:
        data = make_api_request(url)
        events = data.get('events', [])
        if events:
            last_event = events[-1]
            start_timestamp = last_event['startTimestamp']
            start_date = datetime.fromtimestamp(start_timestamp)
            return {
                'id': last_event['id'],
                'startDate': start_date.strftime('%d/%m/%Y %H:%M'),
                'slug': last_event['slug']
            }
    except Exception as e:
        print(f"Falha ao obter o último evento para o time {team_id}: {str(e)}")
    return None

def get_league_data(league_id, season_id):
    url = f"https://www.sofascore.com/api/v1/unique-tournament/{league_id}/season/{season_id}/standings/total"
    data = make_api_request(url)
    
    country = data['standings'][0]['tournament']['uniqueTournament']['category']['name']
    league_name = data['standings'][0]['tournament']['uniqueTournament']['name']
    
    teams_info = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_team = {executor.submit(get_last_event_id, team['team']['id']): team for standing in data['standings'] for team in standing['rows']}
        for future in as_completed(future_to_team):
            team = future_to_team[future]
            last_event = future.result()
            teams_info.append({
                "id": team['team']['id'],
                "nome": team['team']['name'],
                "lastEvent": last_event
            })
    
    return country, league_name, teams_info

def load_existing_data():
    if os.path.exists('all_leagues_info.json'):
        with open('all_leagues_info.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_data(data):
    with open('all_leagues_info.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def add_new_league(all_leagues_data):
    print("\nAdicionar nova liga:")
    league_id = input("ID da liga: ")
    season_id = input("ID da temporada: ")
    
    country, league_name, league_data = get_league_data(league_id, season_id)
    
    if league_name in all_leagues_data:
        overwrite = input(f"A liga {league_name} já existe. Deseja sobrescrever? (s/n): ").lower()
        if overwrite != 's':
            print("Operação cancelada.")
            return
    
    all_leagues_data[league_name] = {
        "league_id": league_id,
        "season_id": season_id,
        "country": country,
        "teams": league_data
    }
    print(f"Dados coletados para {league_name} ({country})")
    save_data(all_leagues_data)
    print(f"Liga {league_name} adicionada com sucesso!")

def overwrite_all_data():
    leagues = [
        {"id": 17, "season": 61627}, #"nome": "Premiere League (24/25)"},
    #{"id": 18, "season": 61961}, #"nome": "Championship (24/25)"},
    {"id": 155, "season": 57478}, #"nome": "Liga Profesional de Fútbol (24)"},
    #{"id": 13475, "season": 57487}, #"nome": "Copa de la Liga Profesional (24)"},
    {"id": 8, "season": 61643}, #"nome": "La Liga (24/25)"},
    {"id": 325, "season": 58766}, #"nome": "Brasileirão Série A (24)"},
    #{"id": 390, "season": 59015}, #"nome": "Brasileirão Série B (24)"},
    #{"id": 11539, "season": 57374}, #"nome": "Primera A, Apertura (24)"},
    {"id": 34, "season": 61736}, #"nome": "Ligue 1 (24/25)"},
    #{"id": 238, "season": 63670}, #"nome": "Liga Portugal Betclic (24)"},
    #{"id": 52, "season": 63814}, #"nome": "Trendyol Süper Lig(24)"},
    #{"id": 955, "season": 63998}, #"nome": "Saudi Pro League (24)"},
    {"id": 35, "season": 63516}, #"nome": "Bundesliga (24/25)"},
    {"id": 23, "season": 63515}, #"nome": "Serie A TIM (24/25)"},
    #{"id": 44, "season": 63514}, #"nome": "2. Bundesliga (24/25)"},
    #{"id": 37, "season": 61666}, #"nome": "Eredivisie (24)"},
    #{"id": 7, "season": 61644}, #"nome": "Champions League (24/25)"},
    #{"id": 384, "season": 57296}, #"nome": "CONMEBOL Libertadores (24)"},
    #{"id": 480, "season": 57297}, #"nome": "CONMEBOL Sudamericana (24)"},
    #{"id": 679, "season": 61645}, #"nome": "UEFA Europa League (24/25)"},
    #{"id": 17015, "season": 61648}, #"nome": "UEFA Europa Conference League (24/25)"},
    # Adicione mais ligas conforme necessário
    ]
    
    new_data = {}
    for league in leagues:
        country, league_name, league_data = get_league_data(league['id'], league['season'])
        new_data[league_name] = {
            "league_id": league['id'],
            "season_id": league['season'],
            "country": country,
            "teams": league_data
        }
        print(f"Dados coletados para {league_name} ({country})")
    
    save_data(new_data)
    print("\nTodos os dados foram sobrescritos e salvos em 'all_leagues_info.json'")

def update_last_events(all_leagues_data):
    print("\nAtualizando os últimos eventos para todas as equipes...")
    for league_name, league_info in all_leagues_data.items():
        print(f"\nAtualizando {league_name}...")
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_team = {executor.submit(get_last_event_id, team['id']): team for team in league_info['teams']}
            for future in as_completed(future_to_team):
                team = future_to_team[future]
                last_event = future.result()
                if last_event:
                    team['lastEvent'] = last_event
                    print(f"  Atualizado: {team['nome']}")
                else:
                    print(f"  Falha ao atualizar: {team['nome']}")
    
    save_data(all_leagues_data)
    print("\nTodos os últimos eventos foram atualizados e salvos em 'all_leagues_info.json'")

def remove_league(all_leagues_data):
    print("\nLigas existentes:")
    leagues = list(all_leagues_data.keys())
    for index, league in enumerate(leagues, 1):
        print(f"{index}. {league} ({all_leagues_data[league]['country']})")
    
    choice = input("\nEscolha o número da liga que deseja remover (ou 'c' para cancelar): ")
    
    if choice.lower() == 'c':
        print("Operação cancelada.")
        return
    
    try:
        index = int(choice) - 1
        league_name = leagues[index]
        
        confirm = input(f"Tem certeza que deseja remover a liga {league_name}? (s/n): ").lower()
        if confirm == 's':
            del all_leagues_data[league_name]
            save_data(all_leagues_data)
            print(f"Liga {league_name} removida com sucesso.")
        else:
            print("Operação cancelada.")
    except (ValueError, IndexError):
        print("Escolha inválida. Operação cancelada.")

def show_menu():
    print("\nMenu:")
    print("1. Adicionar nova liga")
    print("2. Mostrar ligas existentes")
    print("3. Sobrescrever todos os dados")
    print("4. Atualizar últimos eventos")
    print("5. Remover liga")
    print("6. Sair")
    return input("Escolha uma opção: ")

def main():
    all_leagues_data = load_existing_data()
    
    while True:
        choice = show_menu()
        
        if choice == '1':
            add_new_league(all_leagues_data)
        elif choice == '2':
            print("\nLigas existentes:")
            for league in all_leagues_data:
                print(f"- {league} ({all_leagues_data[league]['country']})")
        elif choice == '3':
            confirm = input("Tem certeza que deseja sobrescrever todos os dados? (s/n): ").lower()
            if confirm == 's':
                overwrite_all_data()
                all_leagues_data = load_existing_data()
            else:
                print("Operação cancelada.")
        elif choice == '4':
            update_last_events(all_leagues_data)
        elif choice == '5':
            remove_league(all_leagues_data)
        elif choice == '6':
            print("Saindo...")
            break
        else:
            print("Opção inválida. Tente novamente.")

if __name__ == "__main__":
    main()