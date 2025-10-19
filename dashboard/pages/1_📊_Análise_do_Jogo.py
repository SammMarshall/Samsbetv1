# dashboard/pages/1_📊_Análise_do_Jogo.py

import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
from samsbet.services.stats_service import get_match_analysis_data, get_goalkeeper_stats_for_match, get_h2h_data, get_summary_stats_for_event, get_h2h_goalkeeper_analysis, get_variation_level
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

# Nova função de cache para a análise H2H de goleiros
@st.cache_data(ttl=86400)
def load_h2h_gk_analysis(custom_id: str, home_team: str, away_team: str, h2h_events: list = None, detailed_stats_cache: dict = None):
    return get_h2h_goalkeeper_analysis(custom_id, home_team, away_team, h2h_events, detailed_stats_cache)

if 'selected_event_id' not in st.session_state:
    st.warning("Por favor, selecione um jogo na página principal para começar a análise.")
    st.page_link("app.py", label="Voltar para a Página Principal", icon="🏠")
else:
    main_event_id = st.session_state['selected_event_id']
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
        analysis_data = load_analysis_data(main_event_id, filter_by_location=apply_location_filter)
    
    # --- ETAPA 3: EXIBIR OS RESULTADOS ---

    if not analysis_data:
        st.error("Não foi possível carregar os dados da análise para esta partida.")
    else:

        def generate_dynamic_lines(avg: float, num_lines: int = 3) -> list:
            """Gera uma lista de linhas de aposta '.5' centradas em torno da média."""
            if avg <= 0:
                return []
            # Encontra a linha .5 mais próxima da média
            center_line = round(avg - 0.5) + 0.5
            # Gera as linhas abaixo e acima
            lines = [center_line + i for i in range(-num_lines, num_lines + 1)]
            # Garante que as linhas sejam sempre positivas
            return [line for line in lines if line > 0]
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
        

        tab1, tab2 = st.tabs(["🧙‍♂️ Predições", "Outros (Em Breve)"])

        with tab1:
            st.header("🥅 Análise de Finalizações: Temporada Completa e H2H")

            # --- ETAPA 1: CARREGAR TODOS OS DADOS NECESSÁRIOS NO INÍCIO ---
            # Carregamos os dados do H2H uma única vez e os reutilizamos em toda a página
            h2h_df = pd.DataFrame()
            enriched_h2h_df = pd.DataFrame()
            detailed_stats_cache = {}  # Cache para evitar chamadas duplicadas
            
            if custom_id:
                with st.spinner("Buscando e processando histórico de confrontos... ⏳"):
                    h2h_df = load_h2h_data(custom_id, home_team, away_team)
                    if not h2h_df.empty:
                        # Carrega as estatísticas detalhadas uma única vez e armazena em cache
                        detailed_stats_list = []
                        for _, row in h2h_df.iterrows():
                            event_id = row['event_id']
                            if event_id not in detailed_stats_cache:
                                # Evita chamadas quando o H2H indica ausência OU não fornece a flag
                                has_stats = row.get('hasEventPlayerStatistics')
                                if has_stats is not True:
                                    continue
                                detailed_stats_cache[event_id] = load_event_summary_stats(event_id)
                            detailed_stats_list.append(detailed_stats_cache.get(event_id, {}))
                        
                        home_stats_df = pd.DataFrame([item['home'] for item in detailed_stats_list]).add_prefix('Casa_')
                        away_stats_df = pd.DataFrame([item['away'] for item in detailed_stats_list]).add_prefix('Visitante_')
                        enriched_h2h_df = pd.concat([h2h_df.reset_index(drop=True), home_stats_df, away_stats_df], axis=1)
                        
                        # <<< OTIMIZAÇÃO: Armazena os eventos H2H brutos para reutilização >>>
                        # Busca os eventos H2H brutos para reutilizar na análise de goleiros
                        from samsbet.api.sofascore_client import SofaScoreClient
                        client = SofaScoreClient()
                        h2h_events_raw = client.get_h2h_events(custom_id)
           
            # --- FUNÇÃO "MESTRE" REUTILIZÁVEL PARA ANÁLISE DE ODDS ---
            def display_odds_expander(
                team_name: str,
                analysis_title: str,
                season_summary: dict,
                h2h_enriched_df: pd.DataFrame,
                season_key: str,
                h2h_home_key: str,
                h2h_away_key: str,
                num_lines_to_show: int
            ):
                with st.expander(f"📊 Ver Odds Justas de {analysis_title} para {team_name}"):
                    season_col, h2h_col = st.columns(2)
                    

                    # --- Análise da Temporada ---
                    with season_col:
                        st.markdown("###### Desempenho na Temporada")
                        avg_season = season_summary.get(season_key, 0)
                        total_jogos_temporada = season_summary.get('Total de Jogos', 0)
                        st.caption(f"Baseado em {total_jogos_temporada} jogos da temporada.")
                        st.metric(f"Média {analysis_title}/J", f"{avg_season:.2f}")
                        if avg_season > 0:
                            lines_to_show_season = generate_dynamic_lines(avg_season, num_lines=num_lines_to_show)
                            for line in lines_to_show_season:
                                k = int(line)
                                prob_under = poisson.cdf(k, avg_season)
                                odd_over = round(1 / (1 - prob_under), 2) if (1 - prob_under) > 0 else "∞"
                                odd_under = round(1 / prob_under, 2) if prob_under > 0 else "∞"
                                st.metric(f"Over/Under {line}", f"{odd_over} / {odd_under}")

                    # --- Análise do H2H ---
                    with h2h_col:
                        st.markdown("###### Desempenho no Confronto (H2H)")
                        
                        if h2h_enriched_df.empty:
                            st.info("Sem dados H2H.")
                        else:
                            # Filtra jogos com estatísticas válidas
                            h2h_with_stats_df = h2h_enriched_df[
                                (h2h_enriched_df[h2h_home_key] > 0) | (h2h_enriched_df[h2h_away_key] > 0)
                            ]

                            if h2h_with_stats_df.empty:
                                st.info("Nenhum jogo H2H com estatísticas.")
                            else:
                                st.caption(f"Baseado em {len(h2h_with_stats_df)} jogos com estatísticas.")
                                
                                h2h_values = []
                                # Iteramos sobre o DataFrame JÁ FILTRADO
                                for _, row in h2h_with_stats_df.iterrows():
                                    if row['Time da Casa'] == team_name:
                                        h2h_values.append(row[h2h_home_key])
                                    else:
                                        h2h_values.append(row[h2h_away_key])
                                
                                # O cálculo da média agora é feito sobre a amostra correta
                                avg_h2h = np.mean(h2h_values) if h2h_values else 0
                                
                                st.metric(f"Média {analysis_title}/J", f"{avg_h2h:.2f}")
                                if avg_h2h > 0:
                                    lines_to_show_h2h = generate_dynamic_lines(avg_h2h, num_lines=num_lines_to_show)
                                    for line in lines_to_show_h2h:
                                        k = int(line)
                                        prob_under = poisson.cdf(k, avg_h2h)
                                        odd_over = round(1 / (1 - prob_under), 2) if (1 - prob_under) > 0 else "∞"
                                        odd_under = round(1 / prob_under, 2) if prob_under > 0 else "∞"
                                        st.metric(f"Over/Under {line}", f"{odd_over} / {odd_under}")
                                # Consistência para o recorte específico
                                lvl = get_variation_level(h2h_values)
                                if lvl == "Alta":
                                    st.info("💡 Consistência (H2H): **alta variação** neste recorte; cuidado ao usar a média.")
                                elif lvl == "Média":
                                    st.info("ℹ️ Consistência (H2H): **variação moderada** neste recorte.")
                                else:
                                    st.info("✅ Consistência (H2H): **baixa variação**, indicando padrão estável.")

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
                def_cols[3].metric("Média Gols Sofridos/J", home_summary.get('Média Gols Contra/J', 0)) 

                st.divider()
                
                st.markdown(f"##### Odds Justas de Chutes Totais - {home_team} ⚽ ")
                display_odds_expander(
                    team_name=home_team,
                    analysis_title="Chutes Totais",
                    season_summary=home_summary,
                    h2h_enriched_df=enriched_h2h_df,
                    season_key='Média Chutes/J',
                    h2h_home_key='Casa_total_shots',
                    h2h_away_key='Visitante_total_shots',
                    num_lines_to_show=3
                )
                
                st.markdown(f"##### Odds Justas de Chutes no Alvo - {home_team} ⚽🥅")
                display_odds_expander(
                    team_name=home_team,
                    analysis_title="Chutes ao Alvo",
                    season_summary=home_summary,
                    h2h_enriched_df=enriched_h2h_df,
                    season_key='Média Chutes Alvo/J',
                    h2h_home_key='Casa_shots_on_target',
                    h2h_away_key='Visitante_shots_on_target',
                    num_lines_to_show=3
                )
                
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
                def_cols[3].metric("Média Gols Sofridos/J", away_summary.get('Média Gols Contra/J', 0)) 

                st.divider()
                
                st.markdown(f"##### Odds Justas de Chutes Totais - {away_team} ⚽")
                display_odds_expander(
                    team_name=away_team,
                    analysis_title="Chutes Totais",
                    season_summary=away_summary,
                    h2h_enriched_df=enriched_h2h_df,
                    season_key='Média Chutes/J',
                    h2h_home_key='Casa_total_shots',
                    h2h_away_key='Visitante_total_shots',
                    num_lines_to_show=3
                )
                
                st.markdown(f"##### Odds Justas de Chutes no Alvo - {away_team} ⚽🥅")
                display_odds_expander(
                    team_name=away_team,
                    analysis_title="Chutes ao Alvo",
                    season_summary=away_summary,
                    h2h_enriched_df=enriched_h2h_df,
                    season_key='Média Chutes Alvo/J',
                    h2h_home_key='Casa_shots_on_target',
                    h2h_away_key='Visitante_shots_on_target',
                    num_lines_to_show=3
                )
                
                st.divider()
                st.markdown("###### Estatísticas Individuais")
                if not away_players_df.empty:
                    st.dataframe(away_players_df.drop(columns=['Time'], errors='ignore'), hide_index=True, column_config=column_config)
                else:
                    st.info(f"Não foram encontradas estatísticas de finalização para {away_team}.")

                        # <<< NOVA SEÇÃO DE ANÁLISE GERAL DA PARTIDA >>>

            with st.expander("**🔮 Análise Geral de Finalizações da Partida (Expectativa Total)**", expanded=True):                    
                season_col, h2h_col = st.columns(2)

                # --- Análise Baseada na Temporada ---
                with season_col:
                    st.markdown("###### Baseado na Temporada")
                    
                    # Soma das médias dos dois times para criar a expectativa do jogo
                    exp_shots_season = home_summary.get('Média Chutes/J', 0) + away_summary.get('Média Chutes/J', 0)
                    exp_sot_season = home_summary.get('Média Chutes Alvo/J', 0) + away_summary.get('Média Chutes Alvo/J', 0)

                    st.metric("Expectativa de Chutes Totais", f"{exp_shots_season:.2f}")
                    st.metric("Expectativa de Chutes no Alvo", f"{exp_sot_season:.2f}")

                    with st.expander(f"📊 Ver Odds Justas de (Chutes Totais)"):

                        st.markdown("**Odds Justas (Chutes Totais)**")
                        if exp_shots_season > 0:
                            lines_to_show = generate_dynamic_lines(exp_shots_season, num_lines=2) # 2 acima, 2 abaixo
                            cols = st.columns(len(lines_to_show))
                            for i, line in enumerate(lines_to_show):
                                with cols[i]:
                                    k = int(line)
                                    prob_under = poisson.cdf(k, exp_shots_season)
                                    odd_over = round(1 / (1 - prob_under), 2) if (1 - prob_under) > 0 else "∞"
                                    odd_under = round(1 / prob_under, 2) if prob_under > 0 else "∞"
                                    st.metric(f"Over/Under {line}", f"{odd_over} / {odd_under}")

                    with st.expander(f"📊 Ver Odds Justas de (Chutes no Alvo)"):
                        st.markdown("**Odds Justas (Chutes no Alvo)**")
                        if exp_sot_season > 0:
                            lines_to_show = generate_dynamic_lines(exp_sot_season, num_lines=2) # 2 acima, 2 abaixo
                            cols = st.columns(len(lines_to_show))
                            for i, line in enumerate(lines_to_show):
                                with cols[i]:
                                    k = int(line)
                                    prob_under = poisson.cdf(k, exp_sot_season)
                                    odd_over = round(1 / (1 - prob_under), 2) if (1 - prob_under) > 0 else "∞"
                                    odd_under = round(1 / prob_under, 2) if prob_under > 0 else "∞"
                                    st.metric(f"Over/Under {line}", f"{odd_over} / {odd_under}")
                
                # --- Análise Baseada no Confronto Direto (H2H) ---
                with h2h_col:
                    st.markdown("###### Baseado no Confronto (H2H)")
                    
                    if enriched_h2h_df.empty:
                        st.info("Sem dados H2H para análise.")
                    else:
                        h2h_with_stats_df = enriched_h2h_df[(enriched_h2h_df['Casa_total_shots'] > 0) | (enriched_h2h_df['Visitante_total_shots'] > 0)]
                        
                        if h2h_with_stats_df.empty:
                            st.info("Nenhum H2H com estatísticas.")
                        else:
                            # Calcula a média de chutes totais e ao alvo por partida no H2H
                            exp_shots_h2h = (h2h_with_stats_df['Casa_total_shots'] + h2h_with_stats_df['Visitante_total_shots']).mean()
                            exp_sot_h2h = (h2h_with_stats_df['Casa_shots_on_target'] + h2h_with_stats_df['Visitante_shots_on_target']).mean()
                            
                            st.metric("Expectativa de Chutes Totais", f"{exp_shots_h2h:.2f}")
                            st.metric("Expectativa de Chutes no Alvo", f"{exp_sot_h2h:.2f}")

                            # --- Análise de Consistência (Coeficiente de Variação) ---
                            serie_totais = (h2h_with_stats_df['Casa_total_shots'] + h2h_with_stats_df['Visitante_total_shots']).tolist()
                            serie_alvo = (h2h_with_stats_df['Casa_shots_on_target'] + h2h_with_stats_df['Visitante_shots_on_target']).tolist()
                            lvl_totais = get_variation_level(serie_totais)
                            lvl_alvo = get_variation_level(serie_alvo)
                            

                            with st.expander(f"📊 Ver Odds Justas de (Chutes Totais)"):
                                st.markdown("**Odds Justas (Chutes Totais)**")
                                if exp_shots_h2h > 0:
                                    lines_to_show = generate_dynamic_lines(exp_shots_h2h, num_lines=2)
                                    cols = st.columns(len(lines_to_show))
                                    for i, line in enumerate(lines_to_show):
                                        with cols[i]:
                                            k = int(line)
                                            prob_under = poisson.cdf(k, exp_shots_h2h)
                                            odd_over = round(1 / (1 - prob_under), 2) if (1 - prob_under) > 0 else "∞"
                                            odd_under = round(1 / prob_under, 2) if prob_under > 0 else "∞"
                                            st.metric(f"Over/Under {line}", f"{odd_over} / {odd_under}")
                                        
                                if lvl_totais == "Alta":
                                    st.info("💡 Consistência (H2H): **alta variação** neste recorte; cuidado ao usar a média.")
                                elif lvl_totais == "Média":
                                    st.info("ℹ️ Consistência (H2H): **variação moderada** neste recorte.")
                                else:
                                    st.info("✅ Consistência (H2H): **baixa variação**, indicando padrão estável.")

                            with st.expander(f"📊 Ver Odds Justas de (Chutes no Alvo)"):
                                st.markdown("**Odds Justas (Chutes no Alvo)**")
                                if exp_sot_h2h > 0:
                                    lines_to_show = generate_dynamic_lines(exp_sot_h2h, num_lines=2)
                                    cols = st.columns(len(lines_to_show))
                                    for i, line in enumerate(lines_to_show):
                                        with cols[i]:
                                            k = int(line)
                                            prob_under = poisson.cdf(k, exp_sot_h2h)
                                            odd_over = round(1 / (1 - prob_under), 2) if (1 - prob_under) > 0 else "∞"
                                            odd_under = round(1 / prob_under, 2) if prob_under > 0 else "∞"
                                            st.metric(f"Over/Under {line}", f"{odd_over} / {odd_under}")
                                    
                                if lvl_alvo == "Alta":
                                    st.info("💡 Análise de Consistência: Os jogos H2H apresentam uma **alta variação** nas finalizações. Interprete a média com cautela.")
                                elif lvl_alvo == "Média":
                                    st.info("ℹ️ Análise de Consistência: Os jogos H2H apresentam **variação moderada** nas finalizações.")
                                else:
                                    st.info("✅ Análise de Consistência: Os jogos H2H apresentam **baixa variação** nas finalizações, indicando padrão estável.")

            st.divider()
            st.header("Histórico de Confrontos Diretos (H2H)")
            if not custom_id:
                st.warning("ID para H2H não encontrado.")
            elif h2h_df.empty:
                st.info("Não foram encontrados confrontos diretos recentes entre as equipes.")
            else:
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

                    # Carrega estatísticas resumidas direto na tabela usando o cache
                    display_df = h2h_df.copy()
                    # Opção para ocultar jogos sem estatísticas
                    hide_no_stats = st.toggle("Ocultar jogos H2H sem estatísticas", value=True)
                    if hide_no_stats and 'hasEventPlayerStatistics' in display_df.columns:
                        display_df = display_df[display_df['hasEventPlayerStatistics'] == True].copy()
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
                            # Usa o cache em vez de fazer nova chamada à API
                            summary = detailed_stats_cache.get(event_id_row, {})
                            home_stats = summary.get('home', {})
                            away_stats = summary.get('away', {})

                            home_total = home_stats.get('total_shots', 0)
                            away_total = away_stats.get('total_shots', 0)

                            chutes_totais_partida = home_total + away_total
                            chutes_alvo_partida = home_stats.get('shots_on_target', 0) + away_stats.get('shots_on_target', 0)
                            defesas_partida = home_stats.get('saves', 0) + away_stats.get('saves', 0)
                            escanteios_partida = home_stats.get('corner_kicks', 0) + away_stats.get('corner_kicks', 0)
                            impedimentos_partida = home_stats.get('offsides', 0) + away_stats.get('offsides', 0)

                            display_df.loc[display_df.index[i], 'Chutes Totais (Partida)'] = chutes_totais_partida
                            display_df.loc[display_df.index[i], 'Chutes no Alvo (Partida)'] = chutes_alvo_partida
                            display_df.loc[display_df.index[i], 'Defesas (Partida)'] = defesas_partida
                            display_df.loc[display_df.index[i], 'Escanteios (Partida)'] = escanteios_partida
                            display_df.loc[display_df.index[i], 'Impedimentos (Partida)'] = impedimentos_partida

                            #HOME
                            display_df.loc[display_df.index[i], 'Chutes Totais (Casa)'] = home_stats.get('total_shots', 0)
                            display_df.loc[display_df.index[i], 'Chutes no Alvo (Casa)'] = home_stats.get('shots_on_target', 0)
                            display_df.loc[display_df.index[i], 'Defesas (Casa)'] = home_stats.get('saves', 0)
                            display_df.loc[display_df.index[i], 'Escanteios (Casa)'] = home_stats.get('corner_kicks', 0)
                            display_df.loc[display_df.index[i], 'Impedimentos (Casa)'] = home_stats.get('offsides', 0)

                            #AWAY
                            display_df.loc[display_df.index[i], 'Chutes Totais (Visitante)'] = away_stats.get('total_shots', 0)
                            display_df.loc[display_df.index[i], 'Chutes no Alvo (Visitante)'] = away_stats.get('shots_on_target', 0)
                            display_df.loc[display_df.index[i], 'Defesas (Visitante)'] = away_stats.get('saves', 0)
                            display_df.loc[display_df.index[i], 'Escanteios (Visitante)'] = away_stats.get('corner_kicks', 0)
                            display_df.loc[display_df.index[i], 'Impedimentos (Visitante)'] = away_stats.get('offsides', 0)

                    cols_to_drop = ['Gols Casa', 'Gols Visitante', 'Gols Totais', 'event_id', 'hasEventPlayerStatistics']
                    try:
                        display_df_to_show = display_df.drop(columns=[c for c in cols_to_drop if c in display_df.columns])
                    except Exception:
                        display_df_to_show = display_df
                    st.dataframe(display_df_to_show, hide_index=True)

                    # Métricas de apostas esportivas baseadas no histórico H2H
                    st.subheader("📊 Métricas de Apostas - Histórico H2H")
                    
                    if not display_df.empty:
                        # Calcula médias por time e por partida
                        total_jogos = len(h2h_df)
                        
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
                        media_impedimentos_partida = df_com_stats['Impedimentos (Partida)'].mean() if not df_com_stats.empty else 0

                        # Médias de gols consideram TODOS os jogos (com e sem stats)
                        media_gols_partida = (h2h_df['Gols Casa'] + h2h_df['Gols Visitante']).mean()
                        
                        # Médias específicas por time (considerando que alternam casa/fora)
                        # Para chutes/defesas: apenas jogos com stats válidas
                        home_team_chutes = []
                        home_team_chutes_alvo = []
                        home_team_defesas = []
                        home_team_gols = []  # Todos os jogos para gols
                        home_team_escanteios = []
                        home_team_impedimentos = []
                        
                        away_team_chutes = []
                        away_team_chutes_alvo = []
                        away_team_defesas = []
                        away_team_gols = []  # Todos os jogos para gols
                        away_team_escanteios = []
                        away_team_impedimentos = []

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
                                home_team_impedimentos.append(row['Impedimentos (Casa)'])
                                
                                away_team_chutes.append(row['Chutes Totais (Visitante)'])
                                away_team_chutes_alvo.append(row['Chutes no Alvo (Visitante)'])
                                away_team_defesas.append(row['Defesas (Visitante)'])
                                away_team_escanteios.append(row['Escanteios (Visitante)'])
                                away_team_impedimentos.append(row['Impedimentos (Visitante)'])
                            else:
                                # home_team jogando fora
                                home_team_chutes.append(row['Chutes Totais (Visitante)'])
                                home_team_chutes_alvo.append(row['Chutes no Alvo (Visitante)'])
                                home_team_defesas.append(row['Defesas (Visitante)'])
                                home_team_escanteios.append(row['Escanteios (Casa)'])
                                home_team_impedimentos.append(row['Impedimentos (Casa)'])
                                
                                away_team_chutes.append(row['Chutes Totais (Casa)'])
                                away_team_chutes_alvo.append(row['Chutes no Alvo (Casa)'])
                                away_team_defesas.append(row['Defesas (Casa)'])
                                away_team_escanteios.append(row['Escanteios (Visitante)'])
                                away_team_impedimentos.append(row['Impedimentos (Visitante)'])
                                
                        # Calcula médias corretas por time
                        media_chutes_home = sum(home_team_chutes) / len(home_team_chutes) if home_team_chutes else 0
                        media_chutes_alvo_home = sum(home_team_chutes_alvo) / len(home_team_chutes_alvo) if home_team_chutes_alvo else 0
                        media_defesas_home = sum(home_team_defesas) / len(home_team_defesas) if home_team_defesas else 0
                        media_gols_home = sum(home_team_gols) / len(home_team_gols) if home_team_gols else 0
                        media_escanteios_home = sum(home_team_escanteios) / len(home_team_escanteios) if home_team_escanteios else 0
                        media_impedimentos_home = sum(home_team_impedimentos) / len(home_team_impedimentos) if home_team_impedimentos else 0
                        
                        media_chutes_away = sum(away_team_chutes) / len(away_team_chutes) if away_team_chutes else 0
                        media_chutes_alvo_away = sum(away_team_chutes_alvo) / len(away_team_chutes_alvo) if away_team_chutes_alvo else 0
                        media_defesas_away = sum(away_team_defesas) / len(away_team_defesas) if away_team_defesas else 0
                        media_gols_away = sum(away_team_gols) / len(away_team_gols) if away_team_gols else 0
                        media_escanteios_away = sum(away_team_escanteios) / len(away_team_escanteios) if away_team_escanteios else 0
                        media_impedimentos_away = sum(away_team_impedimentos) / len(away_team_impedimentos) if away_team_impedimentos else 0
                        # Exibe métricas em colunas
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.markdown("#### 📈 Por Partida")
                            st.metric("Média Chutes Totais ⚽", f"{media_chutes_totais_partida:.1f}")
                            st.metric("Média Chutes no Alvo ⚽🥅", f"{media_chutes_alvo_partida:.1f}")
                            st.metric("Média Escanteios 🚩", f"{media_escanteios_partida:.1f}")
                            st.metric("Média Defesas 🧤", f"{media_defesas_partida:.1f}")
                            st.metric("Média Gols ⚽✅", f"{media_gols_partida:.1f}")
                            st.metric("Média Impedimentos ⚠️", f"{media_impedimentos_partida:.1f}")
                            st.metric("Jogos Analisados", f"{total_jogos_analisados}/{total_jogos}")
                        
                        with col2:
                            st.markdown(f"#### 🏠 {home_team}")
                            st.metric("Média Chutes ⚽", f"{media_chutes_home:.1f}")
                            st.metric("Média Chutes Alvo ⚽🥅", f"{media_chutes_alvo_home:.1f}")
                            st.metric("Média Escanteios 🚩", f"{media_escanteios_home:.1f}")
                            st.metric("Média Defesas 🧤", f"{media_defesas_home:.1f}")
                            st.metric("Média Gols ⚽✅", f"{media_gols_home:.1f}")
                            st.metric("Média Impedimentos ⚠️", f"{media_impedimentos_home:.1f}")
                        
                        with col3:
                            st.markdown(f"#### ✈️ {away_team}")
                            st.metric("Média Chutes ⚽", f"{media_chutes_away:.1f}")
                            st.metric("Média Chutes Alvo ⚽🥅", f"{media_chutes_alvo_away:.1f}")
                            st.metric("Média Escanteios 🚩", f"{media_escanteios_away:.1f}")
                            st.metric("Média Defesas 🧤", f"{media_defesas_away:.1f}")
                            st.metric("Média Gols ⚽✅", f"{media_gols_away:.1f}")
                            st.metric("Média Impedimentos ⚠️", f"{media_impedimentos_away:.1f}")
                    st.divider()

                    st.subheader(f"Resumo do Confronto - {home_team}")
                    h2h_home_cols = st.columns(5)
                    h2h_home_cols[0].metric("✅Vitórias Totais", home_wins)
                    h2h_home_cols[1].metric("✅🏠Vitórias (Casa)", home_home_wins)
                    h2h_home_cols[2].metric("✅✈️Vitórias (Fora)", home_away_wins)
                    h2h_home_cols[3].metric("❌🏠Derrotas (Casa)", home_home_losses)
                    h2h_home_cols[4].metric("❌✈️Derrotas (Fora)", home_away_losses)
                    
                    st.subheader(f"Resumo do Confronto - {away_team}")
                    h2h_away_cols = st.columns(5)
                    h2h_away_cols[0].metric("✅Vitórias Totais", away_wins)
                    h2h_away_cols[1].metric("✅🏠Vitórias (Casa)", away_home_wins)
                    h2h_away_cols[2].metric("✅✈️Vitórias (Fora)", away_away_wins)
                    h2h_away_cols[3].metric("❌🏠Derrotas (Casa)", away_home_losses)
                    h2h_away_cols[4].metric("❌✈️Derrotas (Fora)", away_away_losses)

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

                    st.subheader("⚽ Tendências de Gols nos Confrontos (H2H)")

                    if total_jogos > 0:
                        gols_totais = h2h_df['Gols Totais']
                        zero_gols_pct = (gols_totais.eq(0).mean() * 100)

                        lines = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5]
                        over_pcts = {line: (gols_totais.gt(line).mean() * 100) for line in lines}
                        under_pcts = {line: 100 - pct for line, pct in over_pcts.items()}

                        # BTTS
                        btts_pct = (((h2h_df['Gols Casa'] > 0) & (h2h_df['Gols Visitante'] > 0)).mean() * 100)
                        ambas_n_pct = 100 - btts_pct

                        # Exibição compacta das tendências
                        labels_values = [("Partida Sem Gols", zero_gols_pct)] \
                                        + [(f"Mais de {line} Gols", over_pcts[line]) for line in lines] \
                                        + [("Ambas Marcam", btts_pct), ("Ambas Não Marcam", ambas_n_pct)]

                        tendencia_cols = st.columns(len(labels_values))
                        for idx, (label, value) in enumerate(labels_values):
                            tendencia_cols[idx].metric(label=label, value=f"{value:.1f}%")

                        # Compatibilidade com blocos seguintes (odds), mantendo variáveis nomeadas
                        over_0_5_pct = over_pcts[0.5]
                        over_1_5_pct = over_pcts[1.5]
                        over_2_5_pct = over_pcts[2.5]
                        over_3_5_pct = over_pcts[3.5]
                        over_4_5_pct = over_pcts[4.5]
                        over_5_5_pct = over_pcts[5.5]
                        over_6_5_pct = over_pcts[6.5]
                        over_7_5_pct = over_pcts[7.5]

                        under_0_5_pct = under_pcts[0.5]
                        under_1_5_pct = under_pcts[1.5]
                        under_2_5_pct = under_pcts[2.5]
                        under_3_5_pct = under_pcts[3.5]
                        under_4_5_pct = under_pcts[4.5]
                        under_5_5_pct = under_pcts[5.5]
                        under_6_5_pct = under_pcts[6.5]
                        under_7_5_pct = under_pcts[7.5]
                    else:
                        st.info("Dados insuficientes para calcular tendências de gols.")

                    # Cálculo das Odds Justas
                    total_jogos = len(h2h_df)
                    if total_jogos > 0:
                        # Função auxiliar para calcular Odd Justa
                        def calcular_odd_justa(pct):
                            if pct > 0:
                                return round(1 / (pct / 100), 2)
                            return "∞"  # Infinito se a probabilidade é zero

                        def format_odd(value):
                            return f"{value:.2f}" if isinstance(value, (int, float)) else value

                        lines = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5]

                        odd_justa_o0 = calcular_odd_justa(zero_gols_pct)
                        over_odds = {f"Odd Justa +{line}": calcular_odd_justa(over_pcts[line]) for line in lines}
                        under_odds = {f"Odd Justa -{line}": calcular_odd_justa(under_pcts[line]) for line in lines}


                        st.markdown("##### 📈 Odds Justas Over (+)")
                        cols_over = st.columns(len(lines) + 1) 
                        cols_over[0].metric(label="&nbsp;", value="", label_visibility="collapsed")
                        for i, line in enumerate(lines):
                            cols_over[i + 1].metric(
                                label=f"Odd Justa +{line}", 
                                value=format_odd(over_odds[f"Odd Justa +{line}"])
                            )

                        st.markdown("##### 📉 Odds Justas Under (-)")
                        cols_under = st.columns(len(lines) + 1)
                        cols_under[0].write("")
                        for i, line in enumerate(lines):
                            cols_under[i + 1].metric(
                                label=f"Odd Justa -{line}", 
                                value=format_odd(under_odds[f"Odd Justa -{line}"])
                            )

                        st.markdown("##### Odds Justas Ambas")
                        odd_justa_btts = calcular_odd_justa(btts_pct)
                        odd_justa_n = calcular_odd_justa(ambas_n_pct)
                        cols_ambas = st.columns(9)
                        cols_ambas[0].metric(label="Ambas Marcam", value=format_odd(odd_justa_btts))
                        cols_ambas[1].metric(label="Ambas Não Marcam", value=format_odd(odd_justa_n))

                        with st.expander("⚽🉐 Análise Avançada: Odds Justas de Gols Asiáticos (H2H)"):
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
                        
                    else:
                        st.info("Dados insuficientes para calcular tendências.")
            
            
            st.header("🚩 Análise de Escanteios (Temporada Completa)")

            # Pega os dados de resumo que já foram carregados
            home_summary = analysis_data['home']['summary']
            away_summary = analysis_data['away']['summary']

            col1, col2 = st.columns(2)
            with col1:
                st.subheader(f"Média de Escanteios - {home_team}")
                st.metric(
                    label=f"{home_team} (Pró)",
                    value=f"{home_summary.get('Média Escanteios/J', 0):.2f}"
                )
                st.metric(
                    label=f"{home_team} (Contra)",
                    value=f"{home_summary.get('Média Escanteios Contra/J', 0):.2f}"
                )
                st.metric(
                    label=f"{home_team} (Total por Jogo)",
                    value=f"{home_summary.get('Média Escanteios/J', 0) + home_summary.get('Média Escanteios Contra/J', 0):.2f}"
                )

            with col2:
                st.subheader(f"Média de Escanteios - {away_team}")
                st.metric(
                    label=f"{away_team} (Pró)",
                    value=f"{away_summary.get('Média Escanteios/J', 0):.2f}"
                )
                st.metric(
                    label=f"{away_team} (Contra)",
                    value=f"{away_summary.get('Média Escanteios Contra/J', 0):.2f}"
                )
                st.metric(
                    label=f"{away_team} (Total por Jogo)",
                    value=f"{away_summary.get('Média Escanteios/J', 0) + away_summary.get('Média Escanteios Contra/J', 0):.2f}"
                )
            
            with st.expander("📊 Ver Odds Justas de Escanteios (Temporada)"):
                # Odds Justas de Escanteios (Temporada)
                st.subheader("Odds Justas de Escanteios (Temporada)")
                lambda_escanteios_season = (
                    home_summary.get('Média Escanteios/J', 0) + away_summary.get('Média Escanteios/J', 0)
                )
                st.write(f"Baseado em uma média de temporada de **{lambda_escanteios_season:.2f}** escanteios por jogo (soma dos times).")

                season_corner_lines = [4.5, 5.5, 6.5, 7.5, 8.5, 9.5, 10.5, 11.5, 12.5, 13.5, 14.5]

                def calcular_odd_justa_pct(pct):
                    if pct > 0:
                        return round(1 / (pct / 100), 2)
                    return float('inf')

                st.markdown("#### 📈 Odds Justas Over (+)")
                season_over_cols = st.columns(len(season_corner_lines))
                for i, line in enumerate(season_corner_lines):
                    k = int(line)
                    prob_over_pct = (1 - poisson.cdf(k, lambda_escanteios_season)) * 100
                    odd_over = calcular_odd_justa_pct(prob_over_pct)
                    with season_over_cols[i]:
                        st.metric(label=f"Over {line}", value=odd_over)

                st.markdown("#### 📉 Odds Justas Under (-)")
                season_under_cols = st.columns(len(season_corner_lines))
                for i, line in enumerate(season_corner_lines):
                    k = int(line)
                    prob_under_pct = poisson.cdf(k, lambda_escanteios_season) * 100
                    odd_under = calcular_odd_justa_pct(prob_under_pct)
                    with season_under_cols[i]:
                        st.metric(label=f"Under {line}", value=odd_under)

            with st.expander("📊 Ver Odds Justas de Escanteios (H2H)"):
                st.subheader("Odds Justas de Escanteios (H2H)")
                if total_jogos_analisados > 0:
                    lambda_escanteios = media_escanteios_partida
                    st.write(f"Baseado em uma média histórica de **{lambda_escanteios:.2f}** escanteios por jogo nos confrontos diretos.")

                    corner_lines = [4.5, 5.5, 6.5, 7.5, 8.5, 9.5, 10.5, 11.5, 12.5, 13.5, 14.5]

                    # Função auxiliar (pode estar fora do bloco, mas ok aqui)
                    def calcular_odd_justa(pct):
                        if pct > 0:
                            return round(1 / (pct / 100), 2)
                        return float('inf')  # ou "∞", mas float('inf') é mais fácil para exibição

                    # === Linha 1: Over ===
                    st.markdown("#### 📈 Odds Justas Over (+)")
                    over_cols = st.columns(len(corner_lines))
                    for i, line in enumerate(corner_lines):
                        k = int(line)
                        prob_over = (1 - poisson.cdf(k, lambda_escanteios)) * 100
                        odd_justa_over = calcular_odd_justa(prob_over)
                        with over_cols[i]:
                            st.metric(label=f"Over {line}", value=odd_justa_over)

                    # Espaçamento visual (opcional)
                    st.write("")  # ou st.divider() se quiser separar mais

                    # === Linha 2: Under ===
                    st.markdown("#### 📉 Odds Justas Under (-)")
                    under_cols = st.columns(len(corner_lines))
                    for i, line in enumerate(corner_lines):
                        k = int(line)
                        prob_under = poisson.cdf(k, lambda_escanteios) * 100
                        odd_justa_under = calcular_odd_justa(prob_under)
                        with under_cols[i]:
                            st.metric(label=f"Under {line}", value=odd_justa_under)

                    # Consistência (CV) para escanteios no H2H
                    if not df_com_stats.empty and 'Escanteios (Partida)' in df_com_stats.columns:
                        serie_corners = df_com_stats['Escanteios (Partida)'].dropna().tolist()
                        lvl_corners = get_variation_level(serie_corners)
                        if lvl_corners == "Alta":
                            st.info("💡 Consistência (Escanteios H2H): **alta variação**; interprete a média com cautela.")
                        elif lvl_corners == "Média":
                            st.info("ℹ️ Consistência (Escanteios H2H): **variação moderada**.")
                        else:
                            st.info("✅ Consistência (Escanteios H2H): **baixa variação**, indicando padrão estável.")

                else:
                    st.info("Dados de escanteios insuficientes para calcular as odds justas.")


            
            st.header("🧤 Análise de Goleiros (Temporada Completa)")
            
            with st.spinner("Buscando dados dos goleiros... 🧤"):
            # Reutiliza os dados de 'analysis_data' para otimizar as chamadas
                home_last_event_id = analysis_data.get("home_last_event_id")
                away_last_event_id = analysis_data.get("away_last_event_id")
                last_match_saves_map = analysis_data.get("last_match_saves_map")
    
                gk_stats = load_gk_stats(main_event_id, home_last_event_id, away_last_event_id, last_match_saves_map)
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
                    st.markdown("##### Odds Justas por Goleiro")
        
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

            st.divider()
            st.subheader("Desempenho da Posição (Confronto Direto - H2H)")

            if not custom_id:
                st.warning("ID para H2H não encontrado.")
            else:
                with st.spinner("Analisando histórico de defesas no H2H... 🕵️"):
                    # <<< OTIMIZAÇÃO: Passa os eventos H2H já carregados para evitar requisições duplicadas >>>
                    h2h_events_to_pass = h2h_events_raw if 'h2h_events_raw' in locals() else None
                    # <<< CORREÇÃO: Passa também o cache de estatísticas para evitar requisições duplicadas >>>
                    h2h_gk_data = load_h2h_gk_analysis(custom_id, home_team, away_team, h2h_events_to_pass, detailed_stats_cache)
                
                if not h2h_gk_data.get('home') and not h2h_gk_data.get('away'):
                    st.info("Não há dados de defesas suficientes no histórico de confrontos para esta análise.")
                else:
                    h2h_col1, h2h_col2 = st.columns(2)
                    
                    def display_h2h_gk_analysis(team_name, h2h_data):
                        """
                        Função para renderizar a análise H2H de goleiros para um time,
                        agora com odds justas lateralizadas.
                        """
                        st.markdown(f"**{team_name}**")
                        avg_saves = h2h_data.get('avg_saves', None)
                        st.metric("Média de Defesas/J no H2H", value=avg_saves if avg_saves is not None else 'N/A')
                        
                        with st.expander("Ver Odds Justas (H2H)"):
                            # Garante que temos dados para processar
                            if not h2h_data or h2h_data.get('avg_saves') is None:
                                st.info("Nenhuma odd para exibir.")
                            else:
                                lines_to_show = [0.5, 1.5, 2.5, 3.5, 4.5]
                                # <<< MUDANÇA CRUCIAL AQUI: Criamos as colunas ANTES do loop >>>
                                odd_cols = st.columns(len(lines_to_show))
                                
                                # Iteramos sobre as colunas e as linhas de aposta ao mesmo tempo
                                for i, line in enumerate(lines_to_show):
                                    with odd_cols[i]: # Entramos na coluna correta para cada linha
                                        st.markdown(f"**Linha {line}**")
                                        
                                        over_value = h2h_data.get(f"Odd_Over_{line}", "N/A")
                                        under_value = h2h_data.get(f"Odd_Under_{line}", "N/A")

                                        # Garante que valores "infinitos" ou zero sejam exibidos de forma limpa
                                        if over_value == "∞" or over_value == 0: over_value = "N/A"
                                        if under_value == "∞" or under_value == 0: under_value = "N/A"

                                        # Exibimos as duas métricas, uma abaixo da outra, DENTRO da mesma coluna
                                        st.metric(label=f"Odd Over +{line}", value=over_value)
                                        st.metric(label=f"Odd Under -{line}", value=under_value)

                        # Consistência das defesas (H2H)
                        samples = h2h_data.get('samples', []) or []
                        if samples:
                            lvl_def = get_variation_level(samples)
                            if lvl_def == "Alta":
                                st.info("💡 Consistência (Goleiros H2H): **alta variação** nas defesas por jogo; cuidado ao usar a média.")
                            elif lvl_def == "Média":
                                st.info("ℹ️ Consistência (Goleiros H2H): **variação moderada** nas defesas por jogo.")
                            else:
                                st.info("✅ Consistência (Goleiros H2H): **baixa variação** nas defesas por jogo.")

                    with h2h_col1:
                        display_h2h_gk_analysis(home_team, h2h_gk_data.get('home', {}))
                    
                    with h2h_col2:
                        display_h2h_gk_analysis(away_team, h2h_gk_data.get('away', {}))
        
