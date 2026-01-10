import streamlit as st
import gspread
import pandas as pd
import json
import os
import base64
from google.oauth2.service_account import Credentials

# Permisos requeridos por Google
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_creds():
    """
    Obtiene credenciales descifrando la cadena BASE64 desde Coolify.
    Esto evita cualquier error de formato, espacios o comillas.
    """
    
    # 1. Leer la variable de entorno
    encoded_key = os.environ.get("GCP_JSON_KEY")
    
    # Si no está en env, intentar buscar en secrets locales (fallback)
    if not encoded_key and st.secrets and "gcp_service_account" in st.secrets:
        try:
            # Si estamos en local, a veces guardamos el JSON directo, a veces base64.
            # Asumiremos que en local tienes el JSON normal en secrets.toml
            info = json.loads(st.secrets["gcp_service_account"]["json_content"])
            return Credentials.from_service_account_info(info, scopes=SCOPES)
        except:
            pass

    if encoded_key:
        try:
            # --- FASE DE DECODIFICACIÓN (La Magia) ---
            # Limpiamos por si quedaron espacios al copiar/pegar
            encoded_key = encoded_key.strip()
            
            # Decodificamos de Base64 a Texto normal
            decoded_bytes = base64.b64decode(encoded_key)
            decoded_str = decoded_bytes.decode("utf-8")
            
            # Ahora sí, parseamos el JSON limpio
            info = json.loads(decoded_str)
            return Credentials.from_service_account_info(info, scopes=SCOPES)

        except Exception as e:
            # Mensajes de error detallados para saber qué pasa
            st.error("❌ Error decodificando la llave.")
            st.write(f"Detalle técnico: {e}")
            return None

    st.error("❌ No se encontró la variable GCP_JSON_KEY en Coolify.")
    return None

def connect_to_drive():
    creds = get_creds()
    if creds:
        return gspread.authorize(creds)
    return None

def get_employees():
    try:
        client = connect_to_drive()
        if not client: return pd.DataFrame()

        # Nombre EXACTO de tu archivo en Drive
        sheet = client.open("BD EMPLEADOS- EX EMPLEADOS").sheet1
        data = sheet.get_all_records()
        df = pd.DataFrame(data)

        # Limpieza de columnas
        df.columns = [str(c).strip() for c in df.columns]
        
        if not df.empty and "NOMBRE COMPLETO" in df.columns:
            df = df[df["NOMBRE COMPLETO"] != ""]
            
        return df
    except Exception as e:
        st.error(f"Error conectando a la base de datos: {e}")
        return pd.DataFrame()
