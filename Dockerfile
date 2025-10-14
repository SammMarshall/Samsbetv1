# Use uma imagem Python oficial e leve como base
FROM python:3.10-slim

# Defina a pasta de trabalho dentro da "caixa"
WORKDIR /app

# Copie TODOS os arquivos do seu projeto para dentro da "caixa"
COPY . .

# Instale todas as dependências do seu requirements.txt
# A flag --no-cache-dir mantém a "caixa" mais leve
RUN pip install --no-cache-dir -r requirements.txt

# Diga à "caixa" qual porta ela deve usar para se comunicar
EXPOSE 10000

# O comando que será executado quando a "caixa" for ligada
# Diz ao Streamlit para rodar na porta 10000 e aceitar conexões externas
CMD ["python", "-m", "streamlit", "run", "dashboard/app.py", "--server.port", "10000", "--server.address", "0.0.0.0"]