import streamlit as st
import gspread
import pandas as pd
import json
import os
import ast
from google.oauth2.service_account import Credentials

# Permisos requeridos por Google
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def clean_json_string(text):
    """
    Función de limpieza profunda para corregir errores de formato en llaves JSON.
    """
    if not text:
        return None
        
    text = text.strip()
    
    # 1. Quitar comillas de cierre/apertura si el usuario las pegó extra
    if text.startswith("'") and text.endswith("'"):
        text = text[1:-1]
    if text.startswith('"') and text.endswith('"'):
        # Cuidado: Solo quitamos si parece que todo el JSON está entrecomillado como string
        # Verificamos si adentro empieza con {
        if text[1:].strip().startswith("{"):
            text = text[1:-1]

    # 2. Reemplazar caracteres problemáticos
    # Espacios de no-ruptura (común al copiar de web)
    text = text.replace("\u00a0", " ")
    
    # Comillas escapadas \" -> "
    text = text.replace('\\"', '"')
    
    # Barras invertidas huerfanas (el error que tienes)
    # A veces se copian como \ seguido de espacio. Lo quitamos.
    text = text.replace("\\ ", " ")
    
    # Comillas simples a dobles (para hacer válido el JSON)
    text = text.replace("'", '"')
    
    # Booleanos de Python a JSON
    text = text.replace("True", "true").replace("False", "false")
    
    return text

def get_creds():
    """
    Obtiene las credenciales intentando múltiples estrategias de corrección.
    """
    env_data = os.environ.get("GCP_JSON_KEY")
    
    # Si no está en env, busca en secrets locales
    if not env_data and st.secrets and "gcp_service_account" in st.secrets:
        try:
            env_data = st.secrets["gcp_service_account"]["json_content"]
        except:
            pass

    if env_data:
        try:
            # FASE 1: Limpieza básica
            clean_data = clean_json_string(env_data)
            
            # FASE 2: Intentar leer como JSON
            try:
                info = json.loads(clean_data)
            except json.JSONDecodeError:
                # FASE 3: Si falla JSON, intentar evaluar como Python (ast)
                # Esto ayuda si hay saltos de línea literales en la clave privada
                try:
                    info = ast.literal_eval(clean_data)
                except:
                    # FASE 4: Último recurso - Corrección agresiva de saltos de línea
                    # A veces la clave privada pierde los escapes \\n
                    clean_data_2 = clean_data.replace('\n', '\\n')
                    info = json.loads(clean_data_2)

            return Credentials.from_service_account_info(info, scopes=SCOPES)

        except Exception as e:
            st.error(f"❌ Error de formato en la llave: {e}")
            st.warning("Consejo: Ve a Coolify, borra la variable GCP_JSON_KEY y pégala de nuevo asegurándote de no dejar espacios al final.")
            return None

    st.error("❌ No se encontraron credenciales. Configura GCP_JSON_KEY en Coolify.")
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
