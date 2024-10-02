import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from utils import *
from column_config import get_finalizacoes_column_config
from api_utils import get_player_stats, process_finalizacoes_data, get_team_stats, get_teams_stats

def analise_finalizacoes():
    st.title('Análise Estatística de Finalizações no Futebol')

    leagues_data = load_leagues_data()
    leagues_by_country = get_leagues_by_country(leagues_data)
    selected_country, selected_league, leagues_in_country = select_country_and_league(leagues_by_country)
    league_id, season_id = get_league_info(leagues_in_country, selected_league)
    selected_teams, game_type, teams = select_teams_and_game_type(leagues_data, selected_league)
    
    quantidade = st.slider('Número de jogadores:', 30, 50, 100, step=10)
    team_filter = get_team_filter(selected_teams, teams)

    data = get_player_stats(
        league_id, season_id, quantidade, team_filter, game_type,
        "position.in.D~M~F",
        "-shotsOnTarget",
        "totalShots%2CshotsOnTarget%2Cappearances%2CmatchesStarted%2CminutesPlayed"
    )

    df = process_finalizacoes_data(data)
    column_config = get_finalizacoes_column_config()
    st.dataframe(df, column_config=column_config)
    show_column_legend(column_config)

    # Calcular o total de finalizações por time
    team_shots = df.groupby('Time').agg({
        'Total de chutes': 'sum',
        'Chutes no alvo': 'sum',
        'Partidas jogadas': 'max'  # Assumindo que todos os jogadores do time jogaram o mesmo número de partidas
    }).reset_index()
    team_shots['Eficiência'] = (team_shots['Chutes no alvo'] / team_shots['Total de chutes'] * 100).round(2)
    team_shots['Chutes/P'] = (team_shots['Total de chutes'] / team_shots['Partidas jogadas']).round(2)
    team_shots['Chutes no alvo/P'] = (team_shots['Chutes no alvo'] / team_shots['Partidas jogadas']).round(2)

    # Criar gráfico de barras para finalizações por time
    fig = px.bar(team_shots, x='Time', y=['Total de chutes', 'Chutes no alvo'], 
                 title=f'Total de finalizações por time ({quantidade} maiores chutadores)',
                 labels={'value': 'Número de chutes', 'variable': 'Tipo de chute'},
                 barmode='group')
    
    # Adicionar texto de eficiência nas barras
    for i, row in team_shots.iterrows():
        fig.add_annotation(
            x=row['Time'],
            y=row['Total de chutes'],
            text=f"{row['Eficiência']}%",
            showarrow=False,
            yshift=10
        )

    st.plotly_chart(fig)

    # Comparação de times
    st.subheader('Comparação de Times')
    selected_teams_compare = st.multiselect('Selecione times para comparar:', team_shots['Time'].tolist())
    
    if len(selected_teams_compare) > 1:
        compare_teams(team_shots, selected_teams_compare)

    st.subheader('Análise Adicional')
    selected_player = st.selectbox('Selecione um jogador para análise detalhada:', df['Jogador'])
    player_data = df[df['Jogador'] == selected_player].iloc[0]

    st.write(f"Estatísticas detalhadas para {selected_player}:")
    for col in df.columns:
        st.write(f"{col}: {player_data[col]}")

def compare_teams(team_shots, selected_teams):
    comparison_df = team_shots[team_shots['Time'].isin(selected_teams)]
    
    # Criar gráfico de radar
    categories = ['Total de chutes', 'Chutes no alvo', 'Chutes/P', 'Chutes no alvo/P', 'Eficiência']
    fig = go.Figure()

    for team in selected_teams:
        team_data = comparison_df[comparison_df['Time'] == team]
        values = team_data[categories].values.flatten().tolist()
        values += values[:1]  # Repetir o primeiro valor para fechar o polígono
        
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories + [categories[0]],
            fill='toself',
            name=team
        ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, max(comparison_df[categories].max())]
            )),
        showlegend=True,
        title='Comparação de Times'
    )

    st.plotly_chart(fig)

    # Tabela de comparação
    st.subheader('Tabela de Comparação de Times')
    comparison_table = comparison_df[['Time'] + categories]
    st.table(comparison_table)

if __name__ == "__main__":
    analise_finalizacoes()