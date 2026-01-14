import streamlit as st
import os
import pickle
import base64
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets"
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

def get_drive_service():
    creds = get_creds()
    return build('drive', 'v3', credentials=creds)

def upload_manual_to_drive(file_path, folder_id):
    creds = get_creds()
    service = build('drive', 'v3', credentials=creds)
    file_metadata = {
        'name': os.path.basename(file_path),
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
        return None

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

def get_or_create_manuals_folder():
    """
    Busca o crea la subcarpeta 'MANUAL_FUNCIONES' dentro de 'SERVINET_APP_DATA' en Mi unidad.
    """
    creds = get_creds()
    service = build('drive', 'v3', credentials=creds)
    # Busca la carpeta principal
    parent_query = "name='SERVINET_APP_DATA' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    parent_results = service.files().list(q=parent_query, fields="files(id, name)").execute()
    parents = parent_results.get('files', [])
    if not parents:
        # Si no existe la carpeta principal, la crea
        parent_metadata = {'name': 'SERVINET_APP_DATA', 'mimeType': 'application/vnd.google-apps.folder'}
        parent = service.files().create(body=parent_metadata, fields='id').execute()
        parent_id = parent.get('id')
    else:
        parent_id = parents[0]['id']
    # Busca la subcarpeta de manuales dentro de la principal
    folder_query = f"name='MANUAL_FUNCIONES' and mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"
    folder_results = service.files().list(q=folder_query, fields="files(id, name)").execute()
    folders = folder_results.get('files', [])
    if folders:
        return folders[0]['id']
    # Si no existe, la crea dentro de la principal
    file_metadata = {'name': 'MANUAL_FUNCIONES', 'mimeType': 'application/vnd.google-apps.folder', 'parents': [parent_id]}
    folder = service.files().create(body=file_metadata, fields='id').execute()
    return folder.get('id')

def upload_organigrama_to_drive(file_path, folder_id):
    """Sube el PDF del organigrama a Drive."""
    creds = get_creds()
    service = build('drive', 'v3', credentials=creds)
    file_metadata = {
        'name': 'Organigrama_Cargos.pdf',
        'parents': [folder_id]
    }
    media = MediaFileUpload(file_path, mimetype='application/pdf')
    # Borra versiones anteriores
    query = f"'{folder_id}' in parents and name='Organigrama_Cargos.pdf' and trashed=false"
    results = service.files().list(q=query, fields="files(id)").execute()
    for f in results.get('files', []):
        service.files().delete(fileId=f['id']).execute()
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id',
        supportsAllDrives=True
    ).execute()
    return file.get('id')

def find_organigrama_in_drive(folder_id):
    """Busca el PDF del organigrama en Drive."""
    creds = get_creds()
    service = build('drive', 'v3', credentials=creds)
    query = f"'{folder_id}' in parents and name='Organigrama_Cargos.pdf' and trashed=false"
    results = service.files().list(q=query, fields="files(id)").execute()
    files = results.get('files', [])
    if files:
        return files[0]['id']
    return None

def download_organigrama_from_drive(file_id):
    """Descarga el PDF del organigrama desde Drive."""
    return download_manual_from_drive(file_id)
