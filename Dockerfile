# Usamos Python 3.9 versión ligera
FROM python:3.9-slim

# Directorio de trabajo
WORKDIR /app

# -------------------------------------------------------------------
# AQUI ESTA EL CAMBIO: Agregamos 'curl' a la instalación
# -------------------------------------------------------------------
RUN apt-get update && apt-get install -y \
    graphviz \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivos del proyecto
COPY . .

# Instalar librerías de Python
RUN pip install --no-cache-dir -r requirements.txt

# Exponer el puerto correcto
EXPOSE 8501

# Chequeo de salud (Ahora sí funcionará porque instalamos curl)
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Comando de arranque
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
