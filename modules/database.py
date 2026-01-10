import streamlit as st
import gspread
import pandas as pd
import json
import os
import base64
import ast
from datetime import datetime
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# --- TU ID DE HOJA DE CÁLCULO ---
SPREADSHEET_ID = "1gM534p1yT-T-lC_j6zOq-..." # <--- ¡ASEGÚRATE DE QUE ESTE SEA EL ID CORRECTO!

def get_creds():
    encoded_key = os.environ.get("GCP_JSON_KEY")
    # ... (El resto de la función de credenciales igual que antes) ...
    if not encoded_key and st.secrets and "gcp_service_account" in st.secrets:
        try:
            info = json.loads(st.secrets["gcp_service_account"]["json_content"])
            return Credentials.from_service_account_info(info, scopes=SCOPES)
        except:
            pass

    if encoded_key:
        try:
            encoded_key = encoded_key.strip()
            if "{" not in encoded_key:
                decoded_bytes = base64.b64decode(encoded_key)
                decoded_str = decoded_bytes.decode("utf-8")
                info = json.loads(decoded_str)
            else:
                try: info = json.loads(encoded_key)
                except: info = ast.literal_eval(encoded_key)
            return Credentials.from_service_account_info(info, scopes=SCOPES)
        except:
            return None
    return None

def connect_to_drive():
    creds = get_creds()
    if creds: return gspread.authorize(creds)
    return None

def get_employees():
    # ... (Igual que antes) ...
    try:
        client = connect_to_drive()
        if not client: return pd.DataFrame()
        sheet = client.open_by_key(SPREADSHEET_ID).sheet1
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        df.columns = [str(c).strip() for c in df.columns]
        if not df.empty and "NOMBRE COMPLETO" in df.columns:
            df = df[df["NOMBRE COMPLETO"] != ""]
        return df
    except: return pd.DataFrame()

# --- NUEVAS FUNCIONES DE MEMORIA ---

def init_memory():
    """Crea la hoja de MEMORIA si no existe."""
    try:
        client = connect_to_drive()
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        
        try:
            # Intentamos abrir la hoja
            worksheet = spreadsheet.worksheet("MEMORIA_IA")
        except:
            # Si falla, la creamos
            worksheet = spreadsheet.add_worksheet(title="MEMORIA_IA", rows=100, cols=5)
            # Encabezados
            worksheet.append_row(["CARGO", "TIPO_DOC", "CONTENIDO", "FECHA_ACTUALIZACION"])
            
        return worksheet
    except Exception as e:
        st.error(f"Error iniciando memoria: {e}")
        return None

def get_saved_content(cargo, tipo_doc):
    """
    Busca si ya existe un documento guardado para este cargo.
    tipo_doc puede ser: 'PERFIL' o 'EVALUACION'
    """
    try:
        worksheet = init_memory()
        if not worksheet: return None
        
        # Leemos todo y filtramos con Pandas (más rápido y fácil)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        
        if df.empty: return None
        
        # Buscamos coincidencia exacta
        resultado = df[
            (df['CARGO'].astype(str).str.upper() == cargo.upper()) & 
            (df['TIPO_DOC'] == tipo_doc)
        ]
        
        if not resultado.empty:
            return resultado.iloc[0]['CONTENIDO']
        return None
        
    except Exception as e:
        return None

def save_content_to_memory(cargo, tipo_doc, contenido):
    """Guarda o actualiza el contenido en la hoja de memoria."""
    try:
        worksheet = init_memory()
        if not worksheet: return
        
        # Buscar celda si ya existe para actualizar, o crear nueva
        cell = worksheet.find(cargo) # Búsqueda simple
        
        # Para hacerlo robusto y simple: borramos lo viejo si existe y ponemos lo nuevo
        # (Nota: En producción real haríamos update, aquí append es más seguro para empezar)
        
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Verificar si ya existe esa combinación exacta para no duplicar filas infinitamente
        all_records = worksheet.get_all_records()
        row_index = None
        
        for idx, row in enumerate(all_records):
            if row['CARGO'].upper() == cargo.upper() and row['TIPO_DOC'] == tipo_doc:
                row_index = idx + 2 # +2 porque Sheets empieza en 1 y hay header
                break
        
        if row_index:
            # Actualizar fila existente
            worksheet.update_cell(row_index, 3, contenido) # Columna 3 es CONTENIDO
            worksheet.update_cell(row_index, 4, fecha)
        else:
            # Crear nueva fila
            worksheet.append_row([cargo.upper(), tipo_doc, contenido, fecha])
            
    except Exception as e:
        st.error(f"Error guardando en memoria: {e}")
