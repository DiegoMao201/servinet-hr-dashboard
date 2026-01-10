# Usar imagen base ligera de Python
FROM python:3.9-slim

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema (necesario para Graphviz)
RUN apt-get update && apt-get install -y \
    graphviz \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivos
COPY . .

# Instalar librerías Python
RUN pip install --no-cache-dir -r requirements.txt

# Exponer el puerto de Streamlit
EXPOSE 8501

# Comprobación de salud (Healthcheck)
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Comando de inicio
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
