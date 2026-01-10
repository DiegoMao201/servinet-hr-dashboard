import streamlit as st
import gspread
import pandas as pd
import json
import os
import ast
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_creds():
    """
    Obtiene credenciales limpiando errores comunes de copiado/pegado
    (espacios invisibles, comillas escapadas, etc).
    """
    # 1. Obtener el texto crudo de Coolify
    env_data = os.environ.get("GCP_JSON_KEY")
    
    if env_data:
        try:
            # --- FASE DE LIMPIEZA PROFUNDA ---
            # 1. Quitar espacios de no-ruptura (pasa al copiar de web)
            clean_data = env_data.replace("\u00a0", " ")
            # 2. Quitar barras invertidas extra (pasa al copiar de JSON stringified)
            clean_data = clean_data.replace('\\"', '"')
            # 3. Quitar comillas simples si las hubiera
            clean_data = clean_data.replace("'", '"')
            # 4. Corregir booleanos
            clean_data = clean_data.replace("True", "true").replace("False", "false")
            
            # --- INTENTO DE LECTURA ---
            try:
                # Intento A: JSON estándar
                info = json.loads(clean_data)
            except:
                # Intento B: Evaluación de Python (último recurso)
                info = ast.literal_eval(clean_data)
                
            return Credentials.from_service_account_info(info, scopes=SCOPES)

        except Exception as e:
            # Solo mostramos el error, NO la llave por seguridad
            st.error(f"❌ Error procesando la llave: {e}")
            return None

    # Fallback local (tu PC)
    try:
        if st.secrets and "gcp_service_account" in st.secrets:
            # Aplicamos la misma limpieza
            raw = st.secrets["gcp_service_account"]["json_content"]
            clean = raw.replace("\u00a0", " ").replace('\\"', '"')
            info = json.loads(clean)
            return Credentials.from_service_account_info(info, scopes=SCOPES)
    except:
        pass

    st.error("❌ No se encontró la configuración GCP_JSON_KEY en Coolify.")
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
        
        # CAMBIA ESTO por el nombre exacto de tu archivo en Drive
        sheet = client.open("BD EMPLEADOS- EX EMPLEADOS").sheet1
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        df.columns = [str(c).strip() for c in df.columns]
        
        if not df.empty and "NOMBRE COMPLETO" in df.columns:
            df = df[df["NOMBRE COMPLETO"] != ""]
        return df
    except Exception as e:
        st.error(f"Error base de datos: {e}")
        return pd.DataFrame()
