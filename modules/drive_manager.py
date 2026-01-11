import streamlit as st
import json
import os
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_creds():
    """Obtiene credenciales desde secrets o variables de entorno."""
    try:
        # Intento 1: Local (secrets.toml)
        json_content = st.secrets["gcp_service_account"]["json_content"]
        info = json.loads(json_content)
    except Exception:
        # Intento 2: Servidor (Coolify Environment Variable)
        # La variable en Coolify se debe llamar: GCP_JSON_KEY
        json_content = os.environ.get("GCP_JSON_KEY")
        if not json_content:
            st.error("⚠️ No se encontraron las credenciales de Google (GCP_JSON_KEY).")
            return None
        info = json.loads(json_content)
        
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return creds

def load_sheet_data(sheet_name):
    try:
        creds = get_creds()
        if not creds: return pd.DataFrame()
        
        client = gspread.authorize(creds)
        sheet = client.open(sheet_name).sheet1
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error conectando a Google Sheets: {e}")
        return pd.DataFrame()

def upload_pdf(file_path, folder_id=None):
    try:
        creds = get_creds()
        service = build('drive', 'v3', credentials=creds)
        
        file_metadata = {'name': file_path.split("/")[-1]}
        if folder_id:
            file_metadata['parents'] = [folder_id]
            
        media = MediaFileUpload(file_path, mimetype='application/pdf')
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        return file.get('id')
    except Exception as e:
        st.error(f"Error subiendo a Drive: {e}")
        return None

# --- NUEVAS FUNCIONES PARA MANUALES DE FUNCIONES ---
def get_or_create_manuals_folder():
    """Busca o crea la subcarpeta 'MANUALES_FUNCIONES' en Drive."""
    creds = get_creds()
    service = build('drive', 'v3', credentials=creds)
    folder_name = "MANUALES_FUNCIONES"
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    folders = results.get('files', [])
    if folders:
        return folders[0]['id']
    # Si no existe, la crea
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    folder = service.files().create(body=file_metadata, fields='id').execute()
    return folder.get('id')

def find_manual_in_drive(cargo, folder_id):
    """Busca si ya existe un manual PDF para el cargo en la subcarpeta."""
    creds = get_creds()
    service = build('drive', 'v3', credentials=creds)
    filename = f"Manual_{cargo.replace(' ', '_').upper()}.pdf"
    query = f"'{folder_id}' in parents and name='{filename}' and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])
    if files:
        return files[0]['id']
    return None

def download_manual_from_drive(file_id):
    """Descarga el PDF del manual desde Drive y lo retorna como bytes."""
    creds = get_creds()
    service = build('drive', 'v3', credentials=creds)
    request = service.files().get_media(fileId=file_id)
    import io
    fh = io.BytesIO()
    from googleapiclient.http import MediaIoBaseDownload
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    return fh.read()

def upload_manual_to_drive(file_path, folder_id):
    """Sube el PDF generado a la subcarpeta de manuales."""
    creds = get_creds()
    service = build('drive', 'v3', credentials=creds)
    from googleapiclient.http import MediaFileUpload
    file_metadata = {
        'name': file_path.split("/")[-1],
        'parents': [folder_id]
    }
    media = MediaFileUpload(file_path, mimetype='application/pdf')
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()
    return file.get('id')
