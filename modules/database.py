import streamlit as st
import gspread
import pandas as pd
import json
import os
import ast  # <--- ESTA ES LA CLAVE NUEVA
from google.oauth2.service_account import Credentials

# Permisos requeridos por Google
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_creds():
    """
    Obtiene las credenciales usando 'ast' para leer diccionarios de Python
    que se hacen pasar por JSON.
    """
    
    # --- INTENTO 1: Variable de Entorno (Producción / Coolify) ---
    env_data = os.environ.get("GCP_JSON_KEY")
    
    if env_data:
        try:
            # ESTRATEGIA 1: Intentar leer como JSON estándar (Lo ideal)
            info = json.loads(env_data)
        except json.JSONDecodeError:
            try:
                # ESTRATEGIA 2 (LA SOLUCIÓN): Leer como estructura de Python
                # Esto acepta {'type': 'service_account'} con comillas simples
                info = ast.literal_eval(env_data)
            except Exception as e:
                st.error(f"❌ La llave en Coolify está corrupta o incompleta. Error: {e}")
                # Imprimimos los primeros 50 caracteres para que veas qué está leyendo
                st.write(f"Inicio de la llave leída: {env_data[:50]}...")
                return None
        
        # Si logramos obtener 'info' (ya sea por JSON o AST), creamos la credencial
        try:
            return Credentials.from_service_account_info(info, scopes=SCOPES)
        except Exception as e:
            st.error(f"El formato es válido, pero Google lo rechaza: {e}")
            return None

    # --- INTENTO 3: Archivo Local secrets.toml (Desarrollo) ---
    try:
        if st.secrets and "gcp_service_account" in st.secrets:
            # Aquí también aplicamos la lógica doble por seguridad
            raw_data = st.secrets["gcp_service_account"]["json_content"]
            try:
                info = json.loads(raw_data)
            except:
                info = ast.literal_eval(raw_data)
            return Credentials.from_service_account_info(info, scopes=SCOPES)
    except Exception:
        pass
            
    st.error("❌ ERROR CRÍTICO: No se encontró la variable GCP_JSON_KEY en Coolify.")
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

        # LIMPIEZA
        df.columns = [str(c).strip() for c in df.columns]
        
        if not df.empty and "NOMBRE COMPLETO" in df.columns:
            df = df[df["NOMBRE COMPLETO"] != ""]
            
        return df
    except Exception as e:
        st.error(f"Error conectando a la hoja de cálculo: {e}")
        return pd.DataFrame()
