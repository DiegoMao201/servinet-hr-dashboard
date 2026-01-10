import streamlit as st
import gspread
import pandas as pd
import json
import os
from google.oauth2.service_account import Credentials

# Permisos requeridos por Google
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_creds():
    """
    Obtiene las credenciales buscando la variable EXACTA que tienes en Coolify:
    GCP_JSON_KEY
    """
    # 1. Intentamos leer la variable de entorno del servidor (Coolify)
    env_json = os.environ.get("GCP_JSON_KEY")
    
    if env_json:
        try:
            info = json.loads(env_json)
            return Credentials.from_service_account_info(info, scopes=SCOPES)
        except Exception as e:
            st.error(f"Error procesando el JSON de GCP_JSON_KEY: {e}")
            return None

    # 2. Fallback local (por si lo corres en tu PC con secrets.toml)
    if "gcp_service_account" in st.secrets:
        try:
            info = json.loads(st.secrets["gcp_service_account"]["json_content"])
            return Credentials.from_service_account_info(info, scopes=SCOPES)
        except:
            pass
            
    st.error("❌ No se encontraron credenciales. Verifica que GCP_JSON_KEY exista en Coolify.")
    return None

def connect_to_drive():
    creds = get_creds()
    if creds:
        return gspread.authorize(creds)
    return None

def get_employees():
    """
    Descarga y limpia la base de datos de empleados.
    """
    try:
        client = connect_to_drive()
        if not client: return pd.DataFrame()

        # Nombre EXACTO de tu archivo en Drive
        sheet = client.open("BD EMPLEADOS- EX EMPLEADOS").sheet1
        data = sheet.get_all_records()
        df = pd.DataFrame(data)

        # LIMPIEZA CRÍTICA: Quitamos espacios vacíos de los nombres de las columnas
        # Esto evita errores si en el Excel dice "CARGO " (con espacio)
        df.columns = [c.strip() for c in df.columns]
        
        # Filtrar filas totalmente vacías
        if not df.empty and "NOMBRE COMPLETO" in df.columns:
            df = df[df["NOMBRE COMPLETO"] != ""]
            
        return df
    except Exception as e:
        st.error(f"Error obteniendo datos: {e}")
        return pd.DataFrame()
