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

def get_creds():
    """
    Decodifica la llave (Base64 o JSON) y retorna las credenciales.
    """
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
            # Intentamos limpiar y decodificar
            encoded_key = encoded_key.strip()
            
            # Si parece Base64 (no tiene llaves {})
            if "{" not in encoded_key:
                decoded_bytes = base64.b64decode(encoded_key)
                decoded_str = decoded_bytes.decode("utf-8")
                info = json.loads(decoded_str)
            else:
                # Si el usuario pegó el JSON directo (a veces pasa)
                try:
                    info = json.loads(encoded_key)
                except:
                    info = ast.literal_eval(encoded_key)
            
            return Credentials.from_service_account_info(info, scopes=SCOPES)
        except Exception as e:
            st.error(f"❌ Error leyendo la llave: {e}")
            return None

    st.error("❌ No se encontró la variable GCP_JSON_KEY.")
    return None

def connect_to_drive():
    creds = get_creds()
    if creds:
        return gspread.authorize(creds)
    return None

def get_employees():
    creds = get_creds()
    try:
        client = connect_to_drive()
        if not client: return pd.DataFrame()

        # Nombre del archivo
        nombre_archivo = "BD EMPLEADOS- EX EMPLEADOS"
        
        try:
            sheet = client.open(nombre_archivo).sheet1
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
            df.columns = [str(c).strip() for c in df.columns]
            
            if not df.empty and "NOMBRE COMPLETO" in df.columns:
                df = df[df["NOMBRE COMPLETO"] != ""]
            return df
            
        except gspread.SpreadsheetNotFound:
            st.error(f"❌ El robot no encuentra el archivo: '{nombre_archivo}'")
            st.warning(f"👉 Ve a tu Google Drive, clic derecho en el archivo -> Compartir -> Pega este correo: {creds.service_account_email}")
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"⚠️ Error de conexión: {e}")
        if creds:
             st.info(f"💡 Pista: Asegúrate de que el archivo en Drive esté compartido como EDITOR con: {creds.service_account_email}")
        return pd.DataFrame()
