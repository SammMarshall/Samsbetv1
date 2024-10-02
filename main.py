import streamlit as st
from finalizacoes import analise_finalizacoes
from defesa import analise_defesa
from comparacao_times import comparacao_times  # Adicione esta linha

def main():
    st.sidebar.title('Navegação')
    opcao = st.sidebar.radio(
        "Escolha o tipo de análise:",
        ('Finalizações', 'Defesas (Goleiros)', 'Comparação de Times')
    )

    if opcao == 'Finalizações':
        analise_finalizacoes()
    elif opcao == 'Defesas (Goleiros)':
        analise_defesa()
    elif opcao == 'Comparação de Times':
        comparacao_times()

if __name__ == '__main__':
    main()