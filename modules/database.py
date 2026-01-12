import streamlit as st
import gspread
import pandas as pd
import os
import pickle
import base64
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_creds():
    creds = None
    token_b64 = os.environ.get("GOOGLE_TOKEN_PICKLE_B64")
    if token_b64:
        creds = pickle.loads(base64.b64decode(token_b64))
    elif os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            secret_b64 = os.environ.get("GOOGLE_CLIENT_SECRET_JSON_B64")
            if secret_b64:
                secret_json = base64.b64decode(secret_b64).decode("utf-8")
                with open("client_secret.json", "w", encoding="utf-8") as f:
                    f.write(secret_json)
            flow = InstalledAppFlow.from_client_secrets_file(
                "client_secret.json", SCOPES)
            creds = flow.run_console()
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
    return creds

# --- TU ID DE HOJA DE CÁLCULO ---
SPREADSHEET_ID = "1eHDMFzGu0OswhzFITGU2czlaqd2xvBsy5gYZ0hB_Rqo" # <--- ¡ASEGÚRATE DE QUE ESTE SEA EL ID CORRECTO!

def connect_to_drive():
    creds = get_creds()
    if creds: return gspread.authorize(creds)
    return None

def get_employees():
    try:
        client = connect_to_drive()
        if not client:
            st.error("No se pudo conectar a Google Drive.")
            return pd.DataFrame()
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        sheet = spreadsheet.worksheet("BD EMPLEADOS")
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        # Limpia espacios y mayúsculas en los nombres de columnas
        df.columns = [str(c).strip().upper() for c in df.columns]
        # Debug: muestra columnas encontradas
        st.write("Columnas encontradas:", df.columns.tolist())
        if not df.empty and "NOMBRE COMPLETO" in df.columns:
            df = df[df["NOMBRE COMPLETO"] != ""]
        else:
            st.error("No se encontró la columna 'NOMBRE COMPLETO' en la hoja de cálculo.")
        return df
    except Exception as e:
        st.error(f"Error leyendo empleados: {e}")
        return pd.DataFrame()

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
