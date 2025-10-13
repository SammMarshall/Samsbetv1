# scripts/test_service.py

from datetime import date, timedelta
from samsbet.services.match_service import get_daily_matches_dataframe
import pandas as pd

# Para garantir que o pandas exiba todas as colunas no terminal
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

print("--- Testando o MatchService ---")

# Vamos buscar os jogos de amanhã (já que hoje pode ter poucos jogos restantes)
target_date = date.today() + timedelta(days=1)
# target_date = date.today() # Ou use a data de hoje

print(f"Buscando e processando jogos para a data: {target_date.strftime('%d/%m/%Y')}\n")

# A chamada agora é muito mais simples e semântica
daily_df = get_daily_matches_dataframe(target_date)

if not daily_df.empty:
    print(f"DataFrame criado com sucesso! Formato: {daily_df.shape}")
    print("Amostra dos 5 primeiros jogos:")
    print(daily_df.head())
else:
    print("Nenhum jogo encontrado para a data especificada.")