# dashboard/pages/1_📊_Análise_do_Jogo.py

import streamlit as st
import pandas as pd
from scipy.stats import poisson
from samsbet.services.stats_service import get_match_analysis_data, get_goalkeeper_stats_for_match, get_h2h_data, get_summary_stats_for_event
from samsbet.models.texts import ASIAN_ODDS_GUIDE

st.set_page_config(
    page_title="Análise da Partida",
    page_icon="📊",
    layout="wide"
)

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
    """Função de cache que chama o serviço de estatísticas de goleiros."""
    return get_goalkeeper_stats_for_match(
        event_id,
        home_last_event_id=home_last_event_id,
        away_last_event_id=away_last_event_id,
        last_match_saves_map_prefetched=last_match_saves_map,
    )

@st.cache_data(ttl=86400) # H2H muda com menos frequência, cache maior
def load_h2h_data(custom_id: str, home_team: str, away_team: str):
    return get_h2h_data(custom_id, home_team, away_team)

# <<< NOVA FUNÇÃO DE CACHE PARA STATS DE EVENTO ÚNICO >>>
@st.cache_data(ttl=86400)
def load_event_summary_stats(event_id: int):
    return get_summary_stats_for_event(event_id)

if 'selected_event_id' not in st.session_state:
    st.warning("Por favor, selecione um jogo na página principal para começar a análise.")
    st.page_link("app.py", label="Voltar para a Página Principal", icon="🏠")
else:
    event_id = st.session_state['selected_event_id']
    home_team = st.session_state['selected_home_team']
    away_team = st.session_state['selected_away_team']
    custom_id = st.session_state.get('selected_custom_id') # Pega o custom_id da sessão


    # --- ETAPA 1: RENDERIZAR TÍTULOS E CONTROLES ---
    
    # Evita chamada duplicada ao endpoint de detalhes: reutiliza o nome do torneio
    # a partir dos dados de análise carregados abaixo

    st.title(f"{home_team} vs {away_team}")
    # O subheader será definido após carregar analysis_data, reutilizando o tournament_name

    st.header("Opções de Análise")
    apply_location_filter = st.toggle(
        "Filtrar estatísticas por mando de campo (Casa/Fora)",
        value=False,
        help="Ative para ver estatísticas apenas de jogos em casa para o time da casa e fora para o visitante."
    )

    # --- ETAPA 2: BUSCAR OS DADOS COM BASE NOS CONTROLES ---
    
    with st.spinner("Buscando estatísticas detalhadas... ⏳"):
        analysis_data = load_analysis_data(event_id, filter_by_location=apply_location_filter)
    
    # --- ETAPA 3: EXIBIR OS RESULTADOS ---

    if not analysis_data:
        st.error("Não foi possível carregar os dados da análise para esta partida.")
    else:
        # Define o subheader agora que temos o nome do torneio sem nova requisição
        tournament_name = analysis_data.get('tournament_name', '')
        st.subheader(f"🏆 {tournament_name}")

        home_players_df = analysis_data['home']['players']
        home_summary = analysis_data['home']['summary']
        away_players_df = analysis_data['away']['players']
        away_summary = analysis_data['away']['summary']
        home_last_event_id = analysis_data.get('home_last_event_id')
        away_last_event_id = analysis_data.get('away_last_event_id')
        last_match_saves_map = analysis_data.get('last_match_saves_map')

        tab1, tab2 = st.tabs(["🎯 Finalizações", "🚩 Escanteios"])

        with tab1:
            st.header("Análise de Finalizações (Temporada Completa)")
            
            column_config = {
                "Chutes Alvo/P": st.column_config.NumberColumn(format="%.2f"),
                "Odd_Over_0.5": st.column_config.NumberColumn(format="%.2f"),
                "Odd_Over_1.5": st.column_config.NumberColumn(format="%.2f"),
                "Prob_Over_0.5": st.column_config.ProgressColumn("Prob. >0.5", format="%.2f%%", min_value=0, max_value=1),
                "Prob_Over_1.5": st.column_config.ProgressColumn("Prob. >1.5", format="%.2f%%", min_value=0, max_value=1),
            }

            col1, col2 = st.columns(2)
            with col1:
                home_pos = home_summary.get('Posição', '')
                home_total_jogos = home_summary.get('Total de Jogos', '')
                st.subheader(f"{home_team} ({home_pos}º) - {home_total_jogos} jogos")
                st.markdown("##### Métricas Ofensivas (Pró)")
                off_cols = st.columns(5)
                off_cols[0].metric("Média Chutes/J", home_summary.get('Média Chutes/J', 0))
                off_cols[1].metric("Média Chutes Alvo/J", home_summary.get('Média Chutes Alvo/J', 0))
                off_cols[2].metric("Grandes Chances Criadas/J", home_summary.get('Grandes Chances Criadas/J', 0))
                off_cols[3].metric(f"Índice de Perigo", f"{home_summary.get('Índice de Perigo (%)', 0)}%")
                off_cols[4].metric("Média Gols Pró/J", home_summary.get('Média Gols Pró/J', 0))
                st.markdown("##### Métricas Defensivas (Contra)")
                def_cols = st.columns(4)
                def_cols[0].metric("Média Chutes Alvo Cedidos/J", home_summary.get('Média Chutes Alvo Cedidos/J', 0))
                def_cols[1].metric("Grandes Chances Cedidas/J", home_summary.get('Grandes Chances Cedidas/J', 0))
                def_cols[2].metric("Média Defesas/J", home_summary.get('Média Defesas/J', 0)) 
                def_cols[3].metric("Média Gols Contra/J", home_summary.get('Média Gols Contra/J', 0)) 
                st.divider()
                st.markdown("###### Estatísticas Individuais")
                if not home_players_df.empty:
                    st.dataframe(home_players_df.drop(columns=['Time'], errors='ignore'), hide_index=True, column_config=column_config)
                else:
                    st.info(f"Não foram encontradas estatísticas de finalização para {home_team}.")

            with col2:
                away_pos = away_summary.get('Posição', '')
                away_total_jogos = away_summary.get('Total de Jogos', '')

                st.subheader(f"{away_team} ({away_pos}º) - {away_total_jogos} jogos")
                st.markdown("##### Métricas Ofensivas (Pró)")
                off_cols = st.columns(5)
                off_cols[0].metric("Média Chutes/J", away_summary.get('Média Chutes/J', 0))
                off_cols[1].metric("Média Chutes Alvo/J", away_summary.get('Média Chutes Alvo/J', 0))
                off_cols[2].metric("Grandes Chances Criadas/J", away_summary.get('Grandes Chances Criadas/J', 0))
                off_cols[3].metric("Índice de Perigo", f"{away_summary.get('Índice de Perigo (%)', 0)}%")
                off_cols[4].metric("Média Gols Pró/J", away_summary.get('Média Gols Pró/J', 0))
                st.markdown("##### Métricas Defensivas (Contra)")
                def_cols = st.columns(4)
                def_cols[0].metric("Média Chutes Alvo Cedidos/J", away_summary.get('Média Chutes Alvo Cedidos/J', 0))
                def_cols[1].metric("Grandes Chances Cedidas/J", away_summary.get('Grandes Chances Cedidas/J', 0))
                def_cols[2].metric("Média Defesas/J", away_summary.get('Média Defesas/J', 0))
                def_cols[3].metric("Média Gols Contra/J", away_summary.get('Média Gols Contra/J', 0)) 
                st.divider()
                st.markdown("###### Estatísticas Individuais")
                if not away_players_df.empty:
                    st.dataframe(away_players_df.drop(columns=['Time'], errors='ignore'), hide_index=True, column_config=column_config)
                else:
                    st.info(f"Não foram encontradas estatísticas de finalização para {away_team}.")

            st.divider()
            st.header("Histórico de Confrontos Diretos (H2H)")
            if not custom_id:
                st.warning("ID para H2H não encontrado.")
            else:
                with st.spinner("Buscando histórico de confrontos... ⏳"):
                    h2h_df = load_h2h_data(custom_id, home_team, away_team)
                
                if not h2h_df.empty:
                    total_jogos = len(h2h_df)
                    home_wins = (h2h_df['Vencedor'] == home_team).sum()
                    away_wins = (h2h_df['Vencedor'] == away_team).sum()
                    draws = total_jogos - home_wins - away_wins

                    # <<< MUDANÇA AQUI: Cálculos de Gols >>>
                    h2h_df['Gols Totais'] = h2h_df['Gols Casa'] + h2h_df['Gols Visitante']
                    media_gols_total = h2h_df['Gols Totais'].mean()
                    
                    gols_pro_home = (
                        h2h_df.loc[h2h_df['Time da Casa'] == home_team, 'Gols Casa'].sum() +
                        h2h_df.loc[h2h_df['Time Visitante'] == home_team, 'Gols Visitante'].sum()
                    )
                    media_gols_home = gols_pro_home / total_jogos if total_jogos > 0 else 0
                    
                    gols_pro_away = (
                        h2h_df.loc[h2h_df['Time da Casa'] == away_team, 'Gols Casa'].sum() +
                        h2h_df.loc[h2h_df['Time Visitante'] == away_team, 'Gols Visitante'].sum()
                    )
                    media_gols_away = gols_pro_away / total_jogos if total_jogos > 0 else 0

                    home_home_wins = h2h_df[(h2h_df['Time da Casa'] == home_team) & (h2h_df['Vencedor'] == home_team)].shape[0]
                    home_away_wins = h2h_df[(h2h_df['Time Visitante'] == home_team) & (h2h_df['Vencedor'] == home_team)].shape[0]
                    home_home_losses = h2h_df[(h2h_df['Time da Casa'] == home_team) & (h2h_df['Vencedor'] == away_team)].shape[0]
                    home_away_losses = h2h_df[(h2h_df['Time Visitante'] == home_team) & (h2h_df['Vencedor'] == away_team)].shape[0]

                    away_home_wins = h2h_df[(h2h_df['Time da Casa'] == away_team) & (h2h_df['Vencedor'] == away_team)].shape[0]
                    away_away_wins = h2h_df[(h2h_df['Time Visitante'] == away_team) & (h2h_df['Vencedor'] == away_team)].shape[0]
                    away_home_losses = h2h_df[(h2h_df['Time da Casa'] == away_team) & (h2h_df['Vencedor'] == home_team)].shape[0]
                    away_away_losses = h2h_df[(h2h_df['Time Visitante'] == away_team) & (h2h_df['Vencedor'] == home_team)].shape[0]

                    # Carrega estatísticas resumidas direto na tabela
                    display_df = h2h_df.copy()
                    if not display_df.empty:
                        # Exibir apenas a data (sem horário)
                        if 'Data' in display_df.columns:
                            display_df['Data'] = display_df['Data'].dt.date
                        new_cols = [
                            'Chutes no Alvo (Partida)', 'Defesas (Partida)', 'Chutes Totais (Casa)', 'Chutes no Alvo (Casa)', 
                            'Defesas (Casa)', 'Chutes Totais (Visitante)', 'Chutes no Alvo (Visitante)', 
                            'Defesas (Visitante)', 'Chutes Totais (Partida)',
                        ]
                        for col in new_cols:
                            display_df[col] = None

                        for i, (_, row) in enumerate(display_df.iterrows()):
                            event_id_row = row['event_id']
                            summary = load_event_summary_stats(event_id_row)
                            home_stats = summary.get('home', {})
                            away_stats = summary.get('away', {})

                            home_total = home_stats.get('total_shots', 0)
                            away_total = away_stats.get('total_shots', 0)

                            chutes_totais_partida = home_total + away_total
                            chutes_alvo_partida = home_stats.get('shots_on_target', 0) + away_stats.get('shots_on_target', 0)
                            defesas_partida = home_stats.get('saves', 0) + away_stats.get('saves', 0)
                            escanteios_partida = home_stats.get('corner_kicks', 0) + away_stats.get('corner_kicks', 0)

                            display_df.loc[display_df.index[i], 'Chutes Totais (Partida)'] = chutes_totais_partida
                            display_df.loc[display_df.index[i], 'Chutes no Alvo (Partida)'] = chutes_alvo_partida
                            display_df.loc[display_df.index[i], 'Defesas (Partida)'] = defesas_partida
                            display_df.loc[display_df.index[i], 'Escanteios (Partida)'] = escanteios_partida

                            #HOME
                            display_df.loc[display_df.index[i], 'Chutes Totais (Casa)'] = home_stats.get('total_shots', 0)
                            display_df.loc[display_df.index[i], 'Chutes no Alvo (Casa)'] = home_stats.get('shots_on_target', 0)
                            display_df.loc[display_df.index[i], 'Defesas (Casa)'] = home_stats.get('saves', 0)
                            display_df.loc[display_df.index[i], 'Escanteios (Casa)'] = home_stats.get('corner_kicks', 0)

                            #AWAY
                            display_df.loc[display_df.index[i], 'Chutes Totais (Visitante)'] = away_stats.get('total_shots', 0)
                            display_df.loc[display_df.index[i], 'Chutes no Alvo (Visitante)'] = away_stats.get('shots_on_target', 0)
                            display_df.loc[display_df.index[i], 'Defesas (Visitante)'] = away_stats.get('saves', 0)
                            display_df.loc[display_df.index[i], 'Escanteios (Visitante)'] = away_stats.get('corner_kicks', 0)

                    st.dataframe(
                        display_df.drop(columns=['Gols Casa', 'Gols Visitante', 'Gols Totais', 'event_id']),
                        hide_index=True
                    )

                    # Métricas de apostas esportivas baseadas no histórico H2H
                    st.subheader("📊 Métricas de Apostas - Histórico H2H")
                    
                    if not display_df.empty:
                        # Calcula médias por time e por partida
                        total_jogos = len(display_df)
                        
                        # Filtra jogos com estatísticas válidas (chutes/defesas > 0)
                        df_com_stats = display_df[
                            (display_df['Chutes Totais (Casa)'] > 0) | 
                            (display_df['Defesas (Casa)'] > 0) |
                            (display_df['Chutes Totais (Visitante)'] > 0) | 
                            (display_df['Defesas (Visitante)'] > 0)
                        ]

                        total_jogos_analisados = len(df_com_stats)
                        
                        # Médias por partida (soma dos dois times) - apenas jogos com stats
                        media_chutes_totais_partida = df_com_stats['Chutes Totais (Partida)'].mean() if not df_com_stats.empty else 0
                        media_chutes_alvo_partida = df_com_stats['Chutes no Alvo (Partida)'].mean() if not df_com_stats.empty else 0
                        media_defesas_partida = df_com_stats['Defesas (Partida)'].mean() if not df_com_stats.empty else 0
                        media_escanteios_partida = df_com_stats['Escanteios (Partida)'].mean() if not df_com_stats.empty else 0
                        
                        # Médias de gols consideram TODOS os jogos (com e sem stats)
                        media_gols_partida = (display_df['Gols Casa'] + display_df['Gols Visitante']).mean()
                        
                        # Médias específicas por time (considerando que alternam casa/fora)
                        # Para chutes/defesas: apenas jogos com stats válidas
                        home_team_chutes = []
                        home_team_chutes_alvo = []
                        home_team_defesas = []
                        home_team_gols = []  # Todos os jogos para gols
                        home_team_escanteios = []
                        
                        away_team_chutes = []
                        away_team_chutes_alvo = []
                        away_team_defesas = []
                        away_team_gols = []  # Todos os jogos para gols
                        away_team_escanteios = []
                        
                        # Processa TODOS os jogos para gols
                        for _, row in display_df.iterrows():
                            if row['Time da Casa'] == home_team:
                                home_team_gols.append(row['Gols Casa'])
                                away_team_gols.append(row['Gols Visitante'])
                            else:
                                home_team_gols.append(row['Gols Visitante'])
                                away_team_gols.append(row['Gols Casa'])
                        
                        # Processa apenas jogos COM stats para chutes/defesas
                        for _, row in df_com_stats.iterrows():
                            if row['Time da Casa'] == home_team:
                                # home_team jogando em casa
                                home_team_chutes.append(row['Chutes Totais (Casa)'])
                                home_team_chutes_alvo.append(row['Chutes no Alvo (Casa)'])
                                home_team_defesas.append(row['Defesas (Casa)'])
                                home_team_escanteios.append(row['Escanteios (Casa)'])
                                
                                away_team_chutes.append(row['Chutes Totais (Visitante)'])
                                away_team_chutes_alvo.append(row['Chutes no Alvo (Visitante)'])
                                away_team_defesas.append(row['Defesas (Visitante)'])
                                away_team_escanteios.append(row['Escanteios (Visitante)'])
                            else:
                                # home_team jogando fora
                                home_team_chutes.append(row['Chutes Totais (Visitante)'])
                                home_team_chutes_alvo.append(row['Chutes no Alvo (Visitante)'])
                                home_team_defesas.append(row['Defesas (Visitante)'])
                                home_team_escanteios.append(row['Escanteios (Casa)'])
                                
                                away_team_chutes.append(row['Chutes Totais (Casa)'])
                                away_team_chutes_alvo.append(row['Chutes no Alvo (Casa)'])
                                away_team_defesas.append(row['Defesas (Casa)'])
                                away_team_escanteios.append(row['Escanteios (Visitante)'])
                        
                        # Calcula médias corretas por time
                        media_chutes_home = sum(home_team_chutes) / len(home_team_chutes) if home_team_chutes else 0
                        media_chutes_alvo_home = sum(home_team_chutes_alvo) / len(home_team_chutes_alvo) if home_team_chutes_alvo else 0
                        media_defesas_home = sum(home_team_defesas) / len(home_team_defesas) if home_team_defesas else 0
                        media_gols_home = sum(home_team_gols) / len(home_team_gols) if home_team_gols else 0
                        media_escanteios_home = sum(home_team_escanteios) / len(home_team_escanteios) if home_team_escanteios else 0
            
                        
                        media_chutes_away = sum(away_team_chutes) / len(away_team_chutes) if away_team_chutes else 0
                        media_chutes_alvo_away = sum(away_team_chutes_alvo) / len(away_team_chutes_alvo) if away_team_chutes_alvo else 0
                        media_defesas_away = sum(away_team_defesas) / len(away_team_defesas) if away_team_defesas else 0
                        media_gols_away = sum(away_team_gols) / len(away_team_gols) if away_team_gols else 0
                        media_escanteios_away = sum(away_team_escanteios) / len(away_team_escanteios) if away_team_escanteios else 0
                        
                        # Exibe métricas em colunas
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.markdown("#### 📈 Por Partida")
                            st.metric("Média Chutes Totais", f"{media_chutes_totais_partida:.1f}")
                            st.metric("Média Chutes no Alvo", f"{media_chutes_alvo_partida:.1f}")
                            st.metric("Média Escanteios", f"{media_escanteios_partida:.1f}")
                            st.metric("Média Defesas", f"{media_defesas_partida:.1f}")
                            st.metric("Média Gols", f"{media_gols_partida:.1f}")
                            st.metric("Jogos Analisados", f"{total_jogos_analisados}/{total_jogos}")
                        
                        with col2:
                            st.markdown(f"#### 🏠 {home_team}")
                            st.metric("Média Chutes/Jogo", f"{media_chutes_home:.1f}")
                            st.metric("Média Chutes Alvo/Jogo", f"{media_chutes_alvo_home:.1f}")
                            st.metric("Média Escanteios/Jogo", f"{media_escanteios_home:.1f}")
                            st.metric("Média Defesas/Jogo", f"{media_defesas_home:.1f}")
                            st.metric("Média Gols/Jogo", f"{media_gols_home:.1f}")
                        
                        with col3:
                            st.markdown(f"#### ✈️ {away_team}")
                            st.metric("Média Chutes/Jogo", f"{media_chutes_away:.1f}")
                            st.metric("Média Chutes Alvo/Jogo", f"{media_chutes_alvo_away:.1f}")
                            st.metric("Média Escanteios/Jogo", f"{media_escanteios_away:.1f}")
                            st.metric("Média Defesas/Jogo", f"{media_defesas_away:.1f}")
                            st.metric("Média Gols/Jogo", f"{media_gols_away:.1f}")

                    st.divider()

                    st.subheader(f"Resumo do Confronto - {home_team}")
                    h2h_home_cols = st.columns(5)
                    h2h_home_cols[0].metric("Vitórias Totais", home_wins)
                    h2h_home_cols[1].metric("Vitórias (Casa)", home_home_wins)
                    h2h_home_cols[2].metric("Vitórias (Fora)", home_away_wins)
                    h2h_home_cols[3].metric("Derrotas (Casa)", home_home_losses)
                    h2h_home_cols[4].metric("Derrotas (Fora)", home_away_losses)
                    
                    st.subheader(f"Resumo do Confronto - {away_team}")
                    h2h_away_cols = st.columns(5)
                    h2h_away_cols[0].metric("Vitórias Totais", away_wins)
                    h2h_away_cols[1].metric("Vitórias (Casa)", away_home_wins)
                    h2h_away_cols[2].metric("Vitórias (Fora)", away_away_wins)
                    h2h_away_cols[3].metric("Derrotas (Casa)", away_home_losses)
                    h2h_away_cols[4].metric("Derrotas (Fora)", away_away_losses)

                    st.subheader("Resumo Geral")
                    h2h_geral_cols = st.columns(4)
                    h2h_geral_cols[0].metric("Partidas", total_jogos)
                    h2h_geral_cols[1].metric(f"Vitórias {home_team}", home_wins)
                    h2h_geral_cols[2].metric(f"Vitórias {away_team}", away_wins)
                    h2h_geral_cols[3].metric("Empates", draws)

                    h2h_gols_cols = st.columns(3)
                    h2h_gols_cols[0].metric("Média de Gols Total", f"{media_gols_total:.2f}")
                    h2h_gols_cols[1].metric(f"Média Gols {home_team}", f"{media_gols_home:.2f}")
                    h2h_gols_cols[2].metric(f"Média Gols {away_team}", f"{media_gols_away:.2f}")

                    st.divider()

                    st.subheader("📊 Tendências de Gols nos Confrontos (H2H)")

                    if total_jogos > 0:
                        # Calculando as porcentagens para os mercados de Over
                        zero_gols_pct = ((h2h_df['Gols Totais'] == 0).sum() / total_jogos) * 100
                        over_0_5_pct = ((h2h_df['Gols Totais'] > 0.5).sum() / total_jogos) * 100
                        over_1_5_pct = ((h2h_df['Gols Totais'] > 1.5).sum() / total_jogos) * 100
                        over_2_5_pct = ((h2h_df['Gols Totais'] > 2.5).sum() / total_jogos) * 100
                        over_3_5_pct = ((h2h_df['Gols Totais'] > 3.5).sum() / total_jogos) * 100
                        over_4_5_pct = ((h2h_df['Gols Totais'] > 4.5).sum() / total_jogos) * 100
                        over_5_5_pct = ((h2h_df['Gols Totais'] > 5.5).sum() / total_jogos) * 100
                        over_6_5_pct = ((h2h_df['Gols Totais'] > 6.5).sum() / total_jogos) * 100
                        over_7_5_pct = ((h2h_df['Gols Totais'] > 7.5).sum() / total_jogos) * 100

                        # Calculando a porcentagem para Ambas Marcam (BTTS)
                        btts_pct = (((h2h_df['Gols Casa'] > 0) & (h2h_df['Gols Visitante'] > 0)).sum() / total_jogos) * 100
                        # Calculando a porcentagem para Ambas Não Marcam (BTTS)
                        ambas_n_pct = 100 - btts_pct

                        # --- CÁLCULOS DE "UNDER" ---
                        under_0_5_pct = 100 - over_0_5_pct
                        under_1_5_pct = 100 - over_1_5_pct
                        under_2_5_pct = 100 - over_2_5_pct
                        under_3_5_pct = 100 - over_3_5_pct
                        under_4_5_pct = 100 - over_4_5_pct
                        under_5_5_pct = 100 - over_5_5_pct
                        under_6_5_pct = 100 - over_6_5_pct
                        under_7_5_pct = 100 - over_7_5_pct


                        # Exibindo as métricas de tendências
                        tendencia_cols = st.columns(11)
                        tendencia_cols[0].metric(label="Partida Sem Gols", value=f"{zero_gols_pct:.1f}%")
                        tendencia_cols[1].metric(label="Mais de 0.5 Gols", value=f"{over_0_5_pct:.1f}%")
                        tendencia_cols[2].metric(label="Mais de 1.5 Gols", value=f"{over_1_5_pct:.1f}%")
                        tendencia_cols[3].metric(label="Mais de 2.5 Gols", value=f"{over_2_5_pct:.1f}%")
                        tendencia_cols[4].metric(label="Mais de 3.5 Gols", value=f"{over_3_5_pct:.1f}%")
                        tendencia_cols[5].metric(label="Mais de 4.5 Gols", value=f"{over_4_5_pct:.1f}%")
                        tendencia_cols[6].metric(label="Mais de 5.5 Gols", value=f"{over_5_5_pct:.1f}%")
                        tendencia_cols[7].metric(label="Mais de 6.5 Gols", value=f"{over_6_5_pct:.1f}%")
                        tendencia_cols[8].metric(label="Mais de 7.5 Gols", value=f"{over_7_5_pct:.1f}%")
                        tendencia_cols[9].metric(label="Ambas Marcam", value=f"{btts_pct:.1f}%")
                        tendencia_cols[10].metric(label="Ambas Não Marcam", value=f"{ambas_n_pct:.1f}%")
                    else:
                        st.info("Dados insuficientes para calcular tendências.")

                    total_jogos = len(h2h_df)
                    if total_jogos > 0:
                        # Função auxiliar para calcular Odd Justa
                        def calcular_odd_justa(pct):
                            if pct > 0:
                                return round(1 / (pct / 100), 2)
                            return "∞" # Infinito se a probabilidade é zero

                        # Cálculo das Odds Justas - OVER
                        odd_justa_o0 = calcular_odd_justa(zero_gols_pct)
                        odd_justa_o0_5 = calcular_odd_justa(over_0_5_pct)
                        odd_justa_o1_5 = calcular_odd_justa(over_1_5_pct)
                        odd_justa_o2_5 = calcular_odd_justa(over_2_5_pct)
                        odd_justa_o3_5 = calcular_odd_justa(over_3_5_pct)
                        odd_justa_o4_5 = calcular_odd_justa(over_4_5_pct)
                        odd_justa_o5_5 = calcular_odd_justa(over_5_5_pct)
                        odd_justa_o6_5 = calcular_odd_justa(over_6_5_pct)
                        odd_justa_o7_5 = calcular_odd_justa(over_7_5_pct)
                        odd_justa_btts = calcular_odd_justa(btts_pct)
                        odd_justa_n = calcular_odd_justa(ambas_n_pct)

                        # --- CÁLCULO DAS ODDS JUSTAS - UNDER ---
                        odd_justa_u0_5 = calcular_odd_justa(under_0_5_pct)
                        odd_justa_u1_5 = calcular_odd_justa(under_1_5_pct)
                        odd_justa_u2_5 = calcular_odd_justa(under_2_5_pct)
                        odd_justa_u3_5 = calcular_odd_justa(under_3_5_pct)
                        odd_justa_u4_5 = calcular_odd_justa(under_4_5_pct)
                        odd_justa_u5_5 = calcular_odd_justa(under_5_5_pct)
                        odd_justa_u6_5 = calcular_odd_justa(under_6_5_pct)
                        odd_justa_u7_5 = calcular_odd_justa(under_7_5_pct)
                        
                        #Over
                        val_odd_0 = f"{odd_justa_o0:.2f}" if isinstance(odd_justa_o0, (int, float)) else odd_justa_o0
                        val_odd_0_5 = f"{odd_justa_o0_5:.2f}" if isinstance(odd_justa_o0_5, (int, float)) else odd_justa_o0_5
                        val_odd_1_5 = f"{odd_justa_o1_5:.2f}" if isinstance(odd_justa_o1_5, (int, float)) else odd_justa_o1_5
                        val_odd_2_5 = f"{odd_justa_o2_5:.2f}" if isinstance(odd_justa_o2_5, (int, float)) else odd_justa_o2_5
                        val_odd_3_5 = f"{odd_justa_o3_5:.2f}" if isinstance(odd_justa_o3_5, (int, float)) else odd_justa_o3_5
                        val_odd_4_5 = f"{odd_justa_o4_5:.2f}" if isinstance(odd_justa_o4_5, (int, float)) else odd_justa_o4_5
                        val_odd_5_5 = f"{odd_justa_o5_5:.2f}" if isinstance(odd_justa_o5_5, (int, float)) else odd_justa_o5_5
                        val_odd_6_5 = f"{odd_justa_o6_5:.2f}" if isinstance(odd_justa_o6_5, (int, float)) else odd_justa_o6_5
                        val_odd_7_5 = f"{odd_justa_o7_5:.2f}" if isinstance(odd_justa_o7_5, (int, float)) else odd_justa_o7_5
                        val_odd_abm = f"{odd_justa_btts:.2f}" if isinstance(odd_justa_btts, (int, float)) else odd_justa_btts
                        val_odd_abnm = f"{odd_justa_n:.2f}" if isinstance(odd_justa_n, (int, float)) else odd_justa_n

                        #Under
                        val_odd_u0_5 = f"{odd_justa_u0_5:.2f}" if isinstance(odd_justa_u0_5, (int, float)) else odd_justa_u0_5
                        val_odd_u1_5 = f"{odd_justa_u1_5:.2f}" if isinstance(odd_justa_u1_5, (int, float)) else odd_justa_u1_5
                        val_odd_u2_5 = f"{odd_justa_u2_5:.2f}" if isinstance(odd_justa_u2_5, (int, float)) else odd_justa_u2_5
                        val_odd_u3_5 = f"{odd_justa_u3_5:.2f}" if isinstance(odd_justa_u3_5, (int, float)) else odd_justa_u3_5
                        val_odd_u4_5 = f"{odd_justa_u4_5:.2f}" if isinstance(odd_justa_u4_5, (int, float)) else odd_justa_u4_5
                        val_odd_u5_5 = f"{odd_justa_u5_5:.2f}" if isinstance(odd_justa_u5_5, (int, float)) else odd_justa_u5_5
                        val_odd_u6_5 = f"{odd_justa_u6_5:.2f}" if isinstance(odd_justa_u6_5, (int, float)) else odd_justa_u6_5
                        val_odd_u7_5 = f"{odd_justa_u7_5:.2f}" if isinstance(odd_justa_u7_5, (int, float)) else odd_justa_u7_5

                        st.markdown("##### Odds Justas Over (+)")
                        cols_over = st.columns(11)
                        cols_over[0].metric(label="Odd Justa 0 Gols", value=val_odd_0)
                        cols_over[1].metric(label="Odd Justa 0.5", value=val_odd_0_5)
                        cols_over[2].metric(label="Odd Justa 1.5", value=val_odd_1_5)
                        cols_over[3].metric(label="Odd Justa 2.5", value=val_odd_2_5)
                        cols_over[4].metric(label="Odd Justa 3.5", value=val_odd_3_5)
                        cols_over[5].metric(label="Odd Justa 4.5", value=val_odd_4_5)
                        cols_over[6].metric(label="Odd Justa 5.5", value=val_odd_5_5)
                        cols_over[7].metric(label="Odd Justa 6.5", value=val_odd_6_5)
                        cols_over[8].metric(label="Odd Justa 7.5", value=val_odd_7_5)
                        cols_over[9].markdown("")
                        cols_over[10].markdown("")
                        
                        st.markdown("##### Odds Justas Under (-)")
                        cols_under = st.columns(11)
                        cols_under[0].markdown("")
                        cols_under[1].metric(label="Odd Justa -0.5", value=val_odd_u0_5)
                        cols_under[2].metric(label="Odd Justa -1.5", value=val_odd_u1_5)
                        cols_under[3].metric(label="Odd Justa -2.5", value=val_odd_u2_5)
                        cols_under[4].metric(label="Odd Justa -3.5", value=val_odd_u3_5)
                        cols_under[5].metric(label="Odd Justa -4.5", value=val_odd_u4_5)
                        cols_under[6].metric(label="Odd Justa -5.5", value=val_odd_u5_5)
                        cols_under[7].metric(label="Odd Justa -6.5", value=val_odd_u6_5)
                        cols_under[8].metric(label="Odd Justa -7.5", value=val_odd_u7_5)
                        cols_under[9].markdown("")
                        cols_under[10].markdown("")

                        st.markdown("##### Odds Justas Ambas")
                        cols_ambas = st.columns(2)
                        cols_ambas[0].metric(label="Odd Justa (Ambas - Sim)", value=val_odd_abm)
                        cols_ambas[1].metric(label="Odd Justa (Ambas - Não)", value=val_odd_abnm)

                        with st.expander("📊 Análise Avançada: Odds Justas de Gols Asiáticos (H2H)"):
                            total_jogos = len(h2h_df)
                            if total_jogos > 0:
                
                            # --- FUNÇÃO AUXILIAR PARA CALCULAR ODDS ASIÁTICAS ---
                                def calcular_odd_justa_asiatica(line_type, p_win=0, p_push=0, p_half_win=0, p_half_loss=0):
                                    # Converte porcentagens para decimais
                                    prob_win, prob_push, prob_half_win, prob_half_loss = p_win/100, p_push/100, p_half_win/100, p_half_loss/100
                    
                                    try:
                                        if line_type == 'cheia':
                                            # Formula: (1 - P(Push)) / P(Win)
                                            if prob_win == 0: return "∞"
                                            return round((1 - prob_push) / prob_win, 2)
                        
                                        elif line_type == 'x25':
                                            # Formula: (1 - 0.5 * P(Half Loss)) / P(Full Win)
                                            if prob_win == 0: return "∞"
                                            return round((1 - 0.5 * prob_half_loss) / prob_win, 2)

                                        elif line_type == 'x75':
                                            # Formula: (1 - 0.5 * P(Half Win)) / (P(Full Win) + 0.5 * P(Half Win))
                                            denominator = prob_win + 0.5 * prob_half_win
                                            if denominator == 0: return "∞"
                                            return round((1 - 0.5 * prob_half_win) / denominator, 2)
                                    except ZeroDivisionError:
                                        return "∞"
                                    return "N/A"

                                # --- EXIBIÇÃO DAS LINHAS ---
                                asian_lines_over = [1.0, 1.25, 1.75, 2.0, 2.25, 2.75, 3.0, 3.25, 3.75, 4.0]
                                st.markdown("###### Odds Justas para Mercados de Gols Asiáticos")

                                # Dicionários para armazenar resultados
                                odds_over = {}
                                odds_under = {}

                                for line in asian_lines_over:
                                    # Lógica para Linhas Cheias (1.0, 2.0, 3.0)
                                    if line.is_integer():
                                        # OVER
                                        wins_pct = ((h2h_df['Gols Totais'] > line).sum() / total_jogos) * 100
                                        pushes_pct = ((h2h_df['Gols Totais'] == line).sum() / total_jogos) * 100
                                        losses_pct = 100 - wins_pct - pushes_pct
                                        odd_over = calcular_odd_justa_asiatica('cheia', p_win=wins_pct, p_push=pushes_pct)

                                        # UNDER
                                        under_wins_pct = ((h2h_df['Gols Totais'] < line).sum() / total_jogos) * 100
                                        odd_under = calcular_odd_justa_asiatica('cheia', p_win=under_wins_pct, p_push=pushes_pct)

                                    # Lógica para Linhas de Quarto (X.25)
                                    elif line % 0.5 == 0.25:
                                        
                                        line_low, line_high = line - 0.25, line + 0.25

                                        # OVER
                                        full_win_pct = ((h2h_df['Gols Totais'] >= line_high).sum() / total_jogos) * 100
                                        half_loss_pct = ((h2h_df['Gols Totais'] == line_low).sum() / total_jogos) * 100
                                        full_loss_pct = 100 - full_win_pct - half_loss_pct
                                        odd_over = calcular_odd_justa_asiatica('x25', p_win=full_win_pct, p_half_loss=half_loss_pct)

                                        # UNDER
                                        full_win_under = ((h2h_df['Gols Totais'] <= line_low).sum() / total_jogos) * 100
                                        half_loss_under = ((h2h_df['Gols Totais'] == line_low).sum() / total_jogos) * 100
                                        odd_under = calcular_odd_justa_asiatica('x25', p_win=full_win_under, p_half_loss=half_loss_under)

                                    # Lógica para Linhas de Quarto (X.75)
                                    elif line % 0.5 == 0.75:
                                        line_low, line_high = line - 0.25, line + 0.25

                                        # OVER
                                        full_win_pct = ((h2h_df['Gols Totais'] > line_high).sum() / total_jogos) * 100
                                        half_win_pct = ((h2h_df['Gols Totais'] == line_high).sum() / total_jogos) * 100
                                        full_loss_pct = 100 - full_win_pct - half_win_pct
                                        odd_over = calcular_odd_justa_asiatica('x75', p_win=full_win_pct, p_half_win=half_win_pct)

                                        # UNDER
                                        full_win_under = ((h2h_df['Gols Totais'] < line_low).sum() / total_jogos) * 100
                                        half_win_under = ((h2h_df['Gols Totais'] == line_low).sum() / total_jogos) * 100
                                        odd_under = calcular_odd_justa_asiatica('x75', p_win=full_win_under, p_half_win=half_win_under)
                                    
                                    odds_over[f"Over +{line:.2f}"] = odd_over
                                    odds_under[f"Under -{line:.2f}"] = odd_under

                                # --- Layout visual lateralizado ---
                                st.markdown("#### 📈 Odds Justas Over (+)")
                                cols = st.columns(len(odds_over))
                                for i, (label, valor) in enumerate(odds_over.items()):
                                    with cols[i]:
                                        st.metric(label, valor)

                                st.markdown("#### 📉 Odds Justas Under (-)")
                                cols = st.columns(len(odds_under))
                                for i, (label, valor) in enumerate(odds_under.items()):
                                    with cols[i]:
                                        st.metric(label, valor)
                            else:
                                st.info("Dados insuficientes para calcular tendências asiáticas.")

                            with st.expander("📚 Como interpretar as Odds Asiáticas", expanded=False):
                                st.markdown(ASIAN_ODDS_GUIDE)

                        st.divider()

                        st.subheader("📊 Odds Justas de Escanteios (H2H)")

                        # Usamos total_jogos_analisados para garantir que a média é confiável
                        if total_jogos_analisados > 0:
                            # Nosso lambda é a média total de escanteios por jogo
                            lambda_escanteios = media_escanteios_partida
                            st.write(f"Baseado em uma média histórica de **{lambda_escanteios:.2f}** escanteios por jogo nos confrontos diretos.")

                            # Linhas de escanteios que vamos analisar
                            corner_lines = [4.5, 5.5, 6.5, 7.5, 8.5, 9.5, 10.5, 11.5, 12.5, 13.5, 14.5]
                            
                            # Cria as colunas para exibir as odds lado a lado
                            odd_cols = st.columns(len(corner_lines))

                            # Função auxiliar para calcular Odd Justa (já deve existir no seu código)
                            def calcular_odd_justa(pct):
                                if pct > 0:
                                    return round(1 / (pct / 100), 2)
                                return "∞"

                            for i, line in enumerate(corner_lines):
                                with odd_cols[i]:
                                    k = int(line) # O limiar para o cálculo (ex: para 9.5, k=9)
                                    
                                    # Calcula as probabilidades de Over e Under
                                    prob_under = poisson.cdf(k, lambda_escanteios) * 100
                                    prob_over = 100 - prob_under
                                    
                                    # Calcula as Odds Justas
                                    odd_justa_under = calcular_odd_justa(prob_under)
                                    odd_justa_over = calcular_odd_justa(prob_over)
                                    
                                    # Exibe as métricas
                                    st.markdown(f"**Linha {line}**")
                                    st.metric(label=f"Odd Over {line}", value=odd_justa_over)
                                    st.metric(label=f"Odd Under {line}", value=odd_justa_under)
                                    # Opcional: Exibir a probabilidade implícita
                                    # st.caption(f"Over: {prob_over:.1f}%")

                        else:
                            st.info("Dados de escanteios insuficientes para calcular as odds justas.")

                        
                        st.divider()
                        
                    else:
                        st.info("Dados insuficientes para calcular tendências.")
                else:
                    st.info("Não foram encontrados confrontos diretos recentes entre as equipes.")
            
            st.header("Análise de Goleiros (Temporada Completa)")
            
            with st.spinner("Buscando dados dos goleiros... 🧤"):
            # Reutiliza os dados de 'analysis_data' para otimizar as chamadas
                home_last_event_id = analysis_data.get("home_last_event_id")
                away_last_event_id = analysis_data.get("away_last_event_id")
                last_match_saves_map = analysis_data.get("last_match_saves_map")
    
                gk_stats = load_gk_stats(event_id, home_last_event_id, away_last_event_id, last_match_saves_map)
                home_gk_df = gk_stats.get('home')
                away_gk_df = gk_stats.get('away')

            # --- Igualando número de linhas para alinhar visualmente ---
            if home_gk_df is not None and away_gk_df is not None:
                len_home = len(home_gk_df)
                len_away = len(away_gk_df)
                max_len = max(len_home, len_away)

                def pad_df(df, target_len):
                    """Adiciona linhas em branco até atingir o tamanho desejado."""
                    if df is None or df.empty:
                        return pd.DataFrame([{}] * target_len)
                    diff = target_len - len(df)
                    if diff > 0:
                        blank_rows = pd.DataFrame([{col: "" for col in df.columns}] * diff)
                        df = pd.concat([df, blank_rows], ignore_index=True)
                    return df
                
                
                home_gk_df = pad_df(home_gk_df, max_len)
                away_gk_df = pad_df(away_gk_df, max_len)
            
            col1, col2 = st.columns(2)

            # --- FUNÇÃO AUXILIAR PARA EVITAR REPETIÇÃO DE CÓDIGO ---
            def display_gk_analysis(team_name: str, summary_data: dict, gk_df: pd.DataFrame):
                """Função para renderizar a análise completa de goleiros para um time."""
    
                st.subheader(f"Goleiros - {team_name}")
                st.metric("Média Defesas do Time/J", summary_data.get('Média Defesas/J', 0))
    
                if gk_df is not None and not gk_df.empty:
                    # 1. Tabela Principal (Enxuta e Direta)
                    display_cols = [
                        'Goleiro', 'Partidas', 'Defesas/J', 
                        'Defesas (Última)', 'Sem Sofrer Gol', 'Jogos s/ Sofrer Gol (%)'
                    ]
                    st.dataframe(gk_df[display_cols], hide_index=True, width='stretch')

        
                    st.divider()

                    # 2. Seção Interativa de Odds Justas
                    st.markdown("##### 📈 Odds Justas por Goleiro")
        
                    selected_gk = st.selectbox(
                        "Selecione um goleiro para análise de odds:",
                        options=[g for g in gk_df['Goleiro'].tolist() if g],
                        key=f"select_gk_{team_name.replace(' ', '_')}"
                    )

                    if selected_gk:
                        # Filtra os dados para o goleiro selecionado
                        player_data = gk_df[gk_df['Goleiro'] == selected_gk].iloc[0]
                        st.markdown(f"**Análise para {selected_gk} (Média: {player_data['Defesas/J']} defesas/jogo)**")
            
                        # Exibe as odds em colunas para fácil comparação
                        lines_to_show = [0.5, 1.5, 2.5, 3.5, 4.5]
                        odd_cols = st.columns(len(lines_to_show))
            
                        for i, line in enumerate(lines_to_show):
                            with odd_cols[i]:
                                st.markdown(f"**Linha {line}**")
                                over_value = player_data.get(f"Odd_Over_{line}", "N/A")
                                under_value = player_data.get(f"Odd_Under_{line}", "N/A")
                    
                                # Garante que, se o valor for 0, exibimos 'N/A'
                                if over_value == 0: over_value = "N/A"
                                if under_value == 0: under_value = "N/A"
                        
                                st.metric(label=f"Odd Over +{line}", value=over_value)
                                st.metric(label=f"Odd Under -{line}", value=under_value)
                else:
                    st.info(f"Não foram encontradas estatísticas de goleiros para {team_name}.")
            
            # --- Renderizando a análise para cada time ---
            with col1:
                display_gk_analysis(home_team, home_summary, home_gk_df)
    
            with col2:
                display_gk_analysis(away_team, away_summary, away_gk_df)
        