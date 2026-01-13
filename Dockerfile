# Usamos Python 3.11 (Más moderno para IA)
FROM python:3.11-slim

# Directorio de trabajo
WORKDIR /app

# Instalar Graphviz, Curl y Google Chrome (versión estable)
RUN apt-get update && apt-get install -y \
    graphviz \
    curl \
    wget \
    gnupg2 \
    && rm -rf /var/lib/apt/lists/*

RUN wget -O /usr/share/keyrings/google-linux-signing-key.gpg https://dl.google.com/linux/linux_signing_key.pub
RUN echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-linux-signing-key.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list
RUN apt-get update && apt-get install -y google-chrome-stable

# Copiar archivos
COPY . .

# Instalar librerías Python
RUN pip install --no-cache-dir -r requirements.txt

# Puerto
EXPOSE 8501

# Chequeo de salud
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Comando de ejecución
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
