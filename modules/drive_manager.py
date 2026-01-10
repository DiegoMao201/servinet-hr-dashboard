import streamlit as st
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import gspread
import pandas as pd

# 1. Configuración de Autenticación segura desde Coolify
def get_creds():
    # Leemos la variable de entorno que creamos en Coolify
    creds_json_str = st.secrets["GOOGLE_CREDENTIALS"]
    creds_dict = json.loads(creds_json_str)
    
    # Definimos el alcance (Scopes)
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    creds = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=scopes
    )
    return creds

# 2. Función para LEER la Base de Datos (Sheets)
def load_database(sheet_name):
    creds = get_creds()
    client = gspread.authorize(creds)
    try:
        sheet = client.open(sheet_name).sheet1
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error leyendo la base de datos: {e}")
        return pd.DataFrame()

# 3. Función para ESCRIBIR/ACTUALIZAR datos (ej: nueva evaluación)
def append_evaluation(sheet_name, new_row_data):
    # new_row_data debe ser una lista: ["Juan", "Técnico", "90/100", "2024-01-20"]
    creds = get_creds()
    client = gspread.authorize(creds)
    sheet = client.open(sheet_name).sheet1
    sheet.append_row(new_row_data)

# 4. Función MAESTRA: Subir PDF a Drive (Resultados de IA)
def upload_pdf_to_drive(local_filename, drive_folder_id=None):
    """
    Sube un archivo local a Google Drive.
    drive_folder_id: El ID de la carpeta donde quieres guardarlo (lo sacas de la URL de Drive)
    """
    creds = get_creds()
    service = build('drive', 'v3', credentials=creds)

    file_metadata = {'name': local_filename}
    
    if drive_folder_id:
        file_metadata['parents'] = [drive_folder_id]

    media = MediaFileUpload(local_filename, mimetype='application/pdf')

    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()

    return file.get('id')
