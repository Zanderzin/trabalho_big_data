# Use a imagem oficial do Python como base
FROM python:3.8-slim

# Defina o diretório de trabalho no container
WORKDIR /app

# Copie o arquivo de requisitos para o diretório de trabalho
COPY requirements.txt .

# Instale as dependências Python listadas no requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copie TUDO (incluindo o CSV)
COPY . .

# Exponha a porta do Streamlit
EXPOSE 8501

# Comando para iniciar o aplicativo Streamlit
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
