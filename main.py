import streamlit as st
from finalizacoes import analise_finalizacoes
from defesa import analise_defesa
from comparacao_times import comparacao_times
from get_league_data import update_last_events, add_new_league, load_existing_data, save_data, remove_league

def main():
    st.sidebar.title('Navegação')
    opcao = st.sidebar.radio(
        "Escolha o tipo de análise ou ação:",
        ('Finalizações', 'Defesas (Goleiros)', 'Comparação de Times', 'Ligas')
    )

    if opcao == 'Finalizações':
        analise_finalizacoes()
    elif opcao == 'Defesas (Goleiros)':
        analise_defesa()
    elif opcao == 'Comparação de Times':
        comparacao_times()
    elif opcao == 'Ligas':
        gerenciar_ligas()

def gerenciar_ligas():
    st.subheader("Gerenciamento de Ligas")
    
    acao = st.radio(
        "Escolha uma ação:",
        ('Mostrar Ligas Existentes', 'Atualizar Últimos Eventos', 'Adicionar Nova Liga', 'Remover Liga')
    )
    
    if acao == 'Mostrar Ligas Existentes':
        mostrar_ligas_existentes()
    elif acao == 'Atualizar Últimos Eventos':
        atualizar_eventos_selecionados()
    elif acao == 'Adicionar Nova Liga':
        adicionar_nova_liga()
    elif acao == 'Remover Liga':
        remover_liga()

def mostrar_ligas_existentes():
    st.subheader("Ligas Existentes")
    all_leagues_data = load_existing_data()
    if all_leagues_data:
        for league, info in all_leagues_data.items():
            st.write(f"- {league} ({info['country']})")
    else:
        st.write("Não há ligas cadastradas.")

def atualizar_eventos_selecionados():
    st.subheader("Atualizar Últimos Eventos")
    all_leagues_data = load_existing_data()
    ligas = list(all_leagues_data.keys())
    
    ligas_selecionadas = st.multiselect("Selecione as ligas para atualizar:", ligas)
    
    if st.button("Atualizar Eventos Selecionados"):
        if not ligas_selecionadas:
            st.warning("Por favor, selecione pelo menos uma liga para atualizar.")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            def update_progress(current, total, message):
                progress = current / total
                progress_bar.progress(progress)
                status_text.text(f"{message} - {current}/{total}")
            
            ligas_para_atualizar = {liga: all_leagues_data[liga] for liga in ligas_selecionadas}
            update_last_events(ligas_para_atualizar, update_progress)
            
            save_data(all_leagues_data)
            st.success("Últimos eventos das ligas selecionadas foram atualizados com sucesso!")

def adicionar_nova_liga():
    st.subheader("Adicionar Nova Liga")
    league_id = st.text_input("ID da liga:")
    season_id = st.text_input("ID da temporada:")
    if st.button("Adicionar Liga"):
        all_leagues_data = load_existing_data()
        try:
            updated_data = add_new_league(all_leagues_data, league_id, season_id)
            save_data(updated_data)
            st.success("Nova liga adicionada com sucesso!")
        except Exception as e:
            st.error(f"Erro ao adicionar nova liga: {str(e)}")

def remover_liga():
    st.subheader("Remover Liga")
    all_leagues_data = load_existing_data()
    ligas = list(all_leagues_data.keys())
    
    liga_para_remover = st.selectbox("Selecione a liga que deseja remover:", ligas)
    
    if st.button("Remover Liga"):
        confirm = st.checkbox("Tem certeza que deseja remover esta liga?")
        if confirm:
            try:
                updated_data = remove_league(all_leagues_data, liga_para_remover)
                save_data(updated_data)
                st.success(f"Liga {liga_para_remover} removida com sucesso!")
            except Exception as e:
                st.error(f"Erro ao remover liga: {str(e)}")
        else:
            st.warning("Por favor, confirme a remoção da liga.")

if __name__ == '__main__':
    main()
