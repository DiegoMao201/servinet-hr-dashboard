import streamlit as st
import gspread
import pandas as pd
from modules.auth import get_google_creds  # <-- MEJORA: Import centralizado

# --- TU ID DE HOJA DE CÁLCULO ---
SPREADSHEET_ID = "1eHDMFzGu0OswhzFITGU2czlaqd2xvBsy5gYZ0hB_Rqo"

@st.cache_resource(show_spinner="Conectando a Google Sheets...")
def connect_to_drive():
    """Conecta a gspread usando las credenciales centralizadas."""
    creds = get_google_creds()
    if creds:
        return gspread.authorize(creds)
    st.error("Fallo en la autenticación con Google.")
    return None

@st.cache_data(ttl=300)  # Cache por 5 minutos
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
        df.columns = [str(c).strip().upper() for c in df.columns]
        if not df.empty and "NOMBRE COMPLETO" in df.columns:
            df = df[df["NOMBRE COMPLETO"] != ""]
        else:
            st.error("No se encontró la columna 'NOMBRE COMPLETO' en la hoja de cálculo.")
        return df
    except Exception as e:
        st.error(f"Error leyendo empleados: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def get_evaluaciones():
    try:
        client = connect_to_drive()
        if not client:
            st.error("No se pudo conectar a Google Drive.")
            return pd.DataFrame()
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        sheet = spreadsheet.worksheet("2_evaluaciones")
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        df.columns = [str(c).strip().upper() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Error leyendo hoja de evaluaciones: {e}")
        return pd.DataFrame()

# --- NUEVAS FUNCIONES DE MEMORIA ---

def init_memory():
    """Crea la hoja de MEMORIA si no existe."""
    try:
        client = connect_to_drive()
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        
        try:
            worksheet = spreadsheet.worksheet("MEMORIA_IA")
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title="MEMORIA_IA", rows=100, cols=5)
            # Cambiamos "CARGO" por un ID más genérico
            worksheet.append_row(["ID_UNICO", "TIPO_DOC", "CONTENIDO", "FECHA_ACTUALIZACION"])
            
        return worksheet
    except Exception as e:
        st.error(f"Error iniciando memoria: {e}")
        return None

def get_saved_content(id_unico, tipo_doc):
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
        
        # Buscamos coincidencia exacta por ID_UNICO
        resultado = df[
            (df['ID_UNICO'].astype(str).str.upper() == str(id_unico).upper()) & 
            (df['TIPO_DOC'] == tipo_doc)
        ]
        
        if not resultado.empty:
            return resultado.iloc[0]['CONTENIDO']
        return None
        
    except Exception as e:
        return None

def save_content_to_memory(id_unico, tipo_doc, contenido):
    """Guarda o actualiza el contenido en la hoja de memoria usando un ID único."""
    try:
        worksheet = init_memory()
        if not worksheet: return
        
        import datetime
        fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        all_records = worksheet.get_all_records()
        row_index_to_update = None
        
        for idx, row in enumerate(all_records):
            if str(row.get('ID_UNICO', '')).upper() == str(id_unico).upper() and row.get('TIPO_DOC') == tipo_doc:
                row_index_to_update = idx + 2 # +2 porque Sheets empieza en 1 y hay header
                break
        
        if row_index_to_update:
            # Actualizar fila existente
            worksheet.update_cell(row_index_to_update, 3, contenido) # Columna 3 es CONTENIDO
            worksheet.update_cell(row_index_to_update, 4, fecha)
        else:
            # Crear nueva fila
            worksheet.append_row([str(id_unico).upper(), tipo_doc, contenido, fecha])
            
    except Exception as e:
        st.error(f"Error guardando en memoria: {e}")
