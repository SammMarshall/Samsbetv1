import streamlit as st

def get_finalizacoes_column_config():
    return {
        "Jogador": st.column_config.TextColumn(
            "Jogador",
            help="Nome do jogador"
        ),
        "Time": st.column_config.TextColumn(
            "Time",
            help="Nome do time do jogador"
        ),
        "Total de chutes": st.column_config.NumberColumn(
            "Total de chutes",
            help="Número total de chutes realizados pelo jogador"
        ),
        "Chutes no alvo": st.column_config.NumberColumn(
            "Chutes no alvo",
            help="Número de chutes que acertaram o alvo"
        ),
        "Partidas jogadas": st.column_config.NumberColumn(
            "Partidas jogadas",
            help="Número total de partidas em que o jogador participou"
        ),
        "Titular": st.column_config.NumberColumn(
            "Titular",
            help="Número de partidas em que o jogador foi titular"
        ),
        "Min/Jogados": st.column_config.NumberColumn(
            "Min/Jogados",
            help="Total de minutos jogados pelo jogador"
        ),
        "Min/Chute Alvo": st.column_config.NumberColumn(
            "Min/Chute Alvo",
            help="Média de minutos jogados para cada chute no alvo"
        ),
        "Min/Chute": st.column_config.NumberColumn(
            "Min/Chute",
            help="Média de minutos jogados para cada chute"
        ),
        "Min/P": st.column_config.NumberColumn(
            "Min/P",
            help="Média de minutos jogados por partida"
        ),
        "Chutes/P": st.column_config.NumberColumn(
            "Chutes/P",
            help="Média de chutes por partida"
        ),
        "Chutes Alvo/P": st.column_config.NumberColumn(
            "Chutes Alvo/P",
            help="Média de chutes no alvo por partida"
        ),
        "Eficiência": st.column_config.TextColumn(
            "Eficiência",
            help="Porcentagem de chutes no alvo em relação ao total de chutes"
        ),
    }

def get_defesa_column_config():
    return {
        "Jogador": st.column_config.TextColumn(
            "Jogador",
            help="Nome do goleiro"
        ),
        "Time": st.column_config.TextColumn(
            "Time",
            help="Nome do time do goleiro"
        ),
        "Defesas": st.column_config.NumberColumn(
            "Defesas",
            help="Número total de defesas realizadas pelo goleiro"
        ),
        "Gols sofridos (área)": st.column_config.NumberColumn(
            "Gols sofridos (área)",
            help="Número de gols sofridos dentro da área"
        ),
        "Gols sofridos (fora da área)": st.column_config.NumberColumn(
            "Gols sofridos (fora da área)",
            help="Número de gols sofridos fora da área"
        ),
        "Partidas jogadas": st.column_config.NumberColumn(
            "Partidas jogadas",
            help="Número total de partidas em que o goleiro participou"
        ),
        "Titular": st.column_config.NumberColumn(
            "Titular",
            help="Número de partidas em que o goleiro foi titular"
        ),
        "Min/Jogados": st.column_config.NumberColumn(
            "Min/Jogados",
            help="Total de minutos jogados pelo goleiro"
        ),
        "Total Gols/s": st.column_config.NumberColumn(
            "Total Gols/s",
            help="Total de gols sofridos pelo goleiro"
        ),
        "Defesas /P": st.column_config.NumberColumn(
            "Defesas /P",
            help="Média de defesas por partida"
        ),
        "Min/Defesa": st.column_config.NumberColumn(
            "Min/Defesa",
            help="Média de minutos jogados para cada defesa"
        ),
    }