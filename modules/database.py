import streamlit as st
import gspread
import pandas as pd
import json
import os
import base64
import ast
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# --- PEGA AQUÍ EL ID DE TU ARCHIVO EXCEL ---
# Ejemplo: "1A2B3C4D5E6F_gH7iJ8kL9mN0oP..."
SPREADSHEET_ID = "1eHDMFzGu0OswhzFITGU2czlaqd2xvBsy5gYZ0hB_Rqo"

def get_creds():
    encoded_key = os.environ.get("GCP_JSON_KEY")
    
    # Fallback local
    if not encoded_key and st.secrets and "gcp_service_account" in st.secrets:
        try:
            info = json.loads(st.secrets["gcp_service_account"]["json_content"])
            return Credentials.from_service_account_info(info, scopes=SCOPES)
        except:
            pass

    if encoded_key:
        try:
            encoded_key = encoded_key.strip()
            # Decodificación inteligente (Base64 o JSON directo)
            if "{" not in encoded_key: 
                decoded_bytes = base64.b64decode(encoded_key)
                decoded_str = decoded_bytes.decode("utf-8")
                info = json.loads(decoded_str)
            else:
                # Si el usuario pegó el JSON directo
                try:
                    info = json.loads(encoded_key)
                except:
                    info = ast.literal_eval(encoded_key)
            
            return Credentials.from_service_account_info(info, scopes=SCOPES)
        except Exception as e:
            st.error(f"❌ Error leyendo credenciales: {e}")
            return None

    st.error("❌ No se encontró la variable GCP_JSON_KEY.")
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

        # USAMOS EL ID DIRECTO (Mucho más seguro)
        try:
            # open_by_key es infalible si tienes permisos
            sheet = client.open_by_key(SPREADSHEET_ID).sheet1
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
            
            # Limpieza de columnas
            df.columns = [str(c).strip() for c in df.columns]
            
            if not df.empty and "NOMBRE COMPLETO" in df.columns:
                df = df[df["NOMBRE COMPLETO"] != ""]
            return df

        except Exception as e:
            st.error(f"❌ Error abriendo el archivo por ID: {e}")
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"⚠️ Error general de conexión: {e}")
        return pd.DataFrame()
