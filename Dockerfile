# Usamos Python 3.11 (Más moderno para IA)
FROM python:3.11-slim

# Directorio de trabajo
WORKDIR /app

# Instala solo lo necesario (sin Chrome, sin Kaleido)
RUN apt-get update && apt-get install -y \
    graphviz \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

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
