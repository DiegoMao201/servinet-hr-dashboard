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
    Obtiene las credenciales de forma SEGURA.
    Prioridad:
    1. Variable de Entorno de Coolify (GCP_JSON_KEY)
    2. Archivo local secrets.toml (Solo para desarrollo en PC)
    """
    
    # --- INTENTO 1: Variable de Entorno (Producción / Coolify) ---
    env_json = os.environ.get("GCP_JSON_KEY")
    if env_json:
        try:
            info = json.loads(env_json)
            return Credentials.from_service_account_info(info, scopes=SCOPES)
        except Exception as e:
            st.error(f"Error leyendo la llave de Coolify: {e}")
            return None

    # --- INTENTO 2: Archivo Local secrets.toml (Desarrollo) ---
    # Usamos un try-except ESPECÍFICO para evitar el error "SecretNotFoundError"
    try:
        # Solo intentamos acceder si existe la sección, si no, saltará al except
        if st.secrets and "gcp_service_account" in st.secrets:
            info = json.loads(st.secrets["gcp_service_account"]["json_content"])
            return Credentials.from_service_account_info(info, scopes=SCOPES)
    except Exception:
        # Si no hay archivo secrets.toml (como en Coolify), ignoramos el error silenciosamente
        pass
            
    # Si llegó aquí, no encontró ni la variable de entorno ni el archivo
    st.error("❌ ERROR CRÍTICO: No se encontraron credenciales.")
    st.warning("En Coolify: Verifica que la variable se llame EXACTAMENTE 'GCP_JSON_KEY' y tenga el JSON pegado.")
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

        # LIMPIEZA: Normalizar nombres de columnas (quitar espacios extra)
        df.columns = [str(c).strip() for c in df.columns]
        
        # Filtrar vacíos si existe la columna clave
        if not df.empty and "NOMBRE COMPLETO" in df.columns:
            df = df[df["NOMBRE COMPLETO"] != ""]
            
        return df
    except Exception as e:
        # Mostramos el error exacto para depurar
        st.error(f"Error conectando a la hoja de cálculo: {e}")
        return pd.DataFrame()
