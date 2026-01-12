import streamlit as st
import json
import os
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import pickle
import base64
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets"
]

# Cambia esto por el ID de tu Unidad Compartida
SHARED_DRIVE_ID = os.environ.get("SHARED_DRIVE_ID") or "TU_ID_UNIDAD_COMPARTIDA"

def get_creds():
    creds = None
    # Token desde variable de entorno
    token_b64 = os.environ.get("GOOGLE_TOKEN_PICKLE_B64")
    if token_b64:
        creds = pickle.loads(base64.b64decode(token_b64))
    # Si no, desde archivo
    elif os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # Si no hay token válido, inicia flujo OAuth2
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
        else:
            # Decodifica client_secret.json desde variable de entorno
            secret_b64 = os.environ.get("GOOGLE_CLIENT_SECRET_JSON_B64")
            if secret_b64:
                secret_json = base64.b64decode(secret_b64).decode("utf-8")
                with open("client_secret.json", "w", encoding="utf-8") as f:
                    f.write(secret_json)
            from google_auth_oauthlib.flow import InstalledAppFlow
            flow = InstalledAppFlow.from_client_secrets_file(
                "client_secret.json", SCOPES)
            creds = flow.run_console()
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
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
    """Busca o crea la subcarpeta 'MANUALES_FUNCIONES' en Mi unidad."""
    creds = get_creds()
    service = build('drive', 'v3', credentials=creds)
    folder_name = "MANUALES_FUNCIONES"
    query = (
        f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' "
        f"and trashed=false"
    )
    results = service.files().list(
        q=query,
        fields="files(id, name)"
    ).execute()
    folders = results.get('files', [])
    if folders:
        return folders[0]['id']
    # Si no existe, la crea en Mi unidad
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    folder = service.files().create(
        body=file_metadata,
        fields='id'
    ).execute()
    return folder.get('id')

def find_manual_in_drive(cargo, folder_id):
    creds = get_creds()
    service = build('drive', 'v3', credentials=creds)
    filename = f"Manual_{cargo.replace(' ', '_').upper()}.pdf"
    query = (
        f"'{folder_id}' in parents and name='{filename}' and trashed=false"
    )
    results = service.files().list(
        q=query,
        fields="files(id, name)"
    ).execute()
    files = results.get('files', [])
    if files:
        return files[0]['id']
    return None

def download_manual_from_drive(file_id):
    creds = get_creds()
    service = build('drive', 'v3', credentials=creds)
    request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
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
    creds = get_creds()
    service = build('drive', 'v3', credentials=creds)
    from googleapiclient.http import MediaFileUpload
    file_metadata = {
        'name': file_path.split("/")[-1],
        'parents': [folder_id]
    }
    media = MediaFileUpload(file_path, mimetype='application/pdf')
    try:
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id',
            supportsAllDrives=True
        ).execute()
        return file.get('id')
    except Exception as e:
        st.error(f"Error subiendo a Drive: {e}")
        st.info("¿La cuenta de servicio tiene permisos de 'Administrador de contenido' en la Unidad Compartida?")
        return None
