import streamlit as st
import gspread
import pandas as pd
import json
import os
from google.oauth2.service_account import Credentials

# Configuración de alcances para Google Drive API
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_creds():
    """
    Intenta obtener credenciales de 3 formas:
    1. Secrets locales (PC)
    2. Variable de entorno JSON pura (Coolify)
    3. Archivo temporal (Fallback)
    """
    # INTENTO 1: Variable de Entorno en Coolify (GCP_SERVICE_ACCOUNT)
    env_json = os.environ.get("GCP_SERVICE_ACCOUNT")
    if env_json:
        try:
            info = json.loads(env_json)
            return Credentials.from_service_account_info(info, scopes=SCOPES)
        except Exception as e:
            st.error(f"Error leyendo JSON de Coolify: {e}")

    # INTENTO 2: Secrets.toml (Local)
    if "gcp_service_account" in st.secrets:
        try:
            info = json.loads(st.secrets["gcp_service_account"]["json_content"])
            return Credentials.from_service_account_info(info, scopes=SCOPES)
        except:
            pass
            
    st.error("❌ No se encontraron credenciales. Configura GCP_SERVICE_ACCOUNT en Coolify.")
    return None

def connect_to_drive():
    creds = get_creds()
    if creds:
        return gspread.authorize(creds)
    return None

def get_employees():
    """
    Obtiene y limpia la base de datos de empleados.
    """
    try:
        client = connect_to_drive()
        if not client: return pd.DataFrame()

        # Nombre EXACTO de tu archivo en Drive
        sheet = client.open("BD EMPLEADOS- EX EMPLEADOS").sheet1
        data = sheet.get_all_records()
        df = pd.DataFrame(data)

        # Limpieza de columnas (Quitar espacios en blanco al inicio/final)
        df.columns = [c.strip() for c in df.columns]
        
        # Filtrar filas vacías si las hay
        if not df.empty:
            df = df[df["NOMBRE COMPLETO"] != ""]
            
        return df
    except Exception as e:
        st.error(f"Error obteniendo datos: {e}")
        return pd.DataFrame()
