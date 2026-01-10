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
    Obtiene las credenciales de forma ROBUSTA.
    Corrige errores de formato comunes (comillas simples vs dobles).
    """
    
    # --- INTENTO 1: Variable de Entorno (Producción / Coolify) ---
    env_json = os.environ.get("GCP_JSON_KEY")
    
    if env_json:
        try:
            # --- FASE DE LIMPIEZA INTELIGENTE ---
            # Muchos errores ocurren porque al copiar/pegar se usan comillas simples (')
            # o booleanos de Python (True) en lugar de JSON (true).
            
            # 1. Si parece un dict de Python, forzar comillas dobles
            if "'" in env_json:
                env_json = env_json.replace("'", '"')
            
            # 2. Corregir booleanos de Python a JSON
            env_json = env_json.replace("True", "true").replace("False", "false")

            # 3. Intentar parsear
            info = json.loads(env_json)
            return Credentials.from_service_account_info(info, scopes=SCOPES)
            
        except json.JSONDecodeError as e:
            st.error(f"Error de Formato JSON en Coolify: {e}")
            st.code(env_json) # Muestra qué está intentando leer para que veas el error
            return None
        except Exception as e:
            st.error(f"Error general leyendo la llave: {e}")
            return None

    # --- INTENTO 2: Archivo Local secrets.toml (Desarrollo) ---
    try:
        if st.secrets and "gcp_service_account" in st.secrets:
            # Aquí leemos el string y también aplicamos limpieza por si acaso
            raw_json = st.secrets["gcp_service_account"]["json_content"]
            raw_json = raw_json.replace("'", '"').replace("True", "true").replace("False", "false")
            info = json.loads(raw_json)
            return Credentials.from_service_account_info(info, scopes=SCOPES)
    except Exception:
        pass
            
    st.error("❌ ERROR CRÍTICO: No se encontraron credenciales (GCP_JSON_KEY).")
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

        # LIMPIEZA: Normalizar nombres de columnas
        df.columns = [str(c).strip() for c in df.columns]
        
        # Filtrar vacíos
        if not df.empty and "NOMBRE COMPLETO" in df.columns:
            df = df[df["NOMBRE COMPLETO"] != ""]
            
        return df
    except Exception as e:
        st.error(f"Error conectando a la hoja de cálculo: {e}")
        return pd.DataFrame()
