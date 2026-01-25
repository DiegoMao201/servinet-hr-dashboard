import streamlit as st
import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from modules.auth import get_google_creds  # <-- MEJORA: Import centralizado
import io

@st.cache_resource(show_spinner="Conectando a Google Drive...")
def get_drive_service():
    """Obtiene el servicio de Drive usando las credenciales centralizadas."""
    creds = get_google_creds()
    if creds:
        return build('drive', 'v3', credentials=creds)
    st.error("Fallo en la autenticación con Google.")
    return None

def upload_manual_to_drive(file_path, folder_id):
    service = get_drive_service()
    if not service: return None
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
    service = get_drive_service()
    if not service: return None
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
    service = get_drive_service()
    if not service: return b""
    request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
    fh = io.BytesIO()
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
    service = get_drive_service()
    if not service: return None
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
    service = get_drive_service()
    if not service: return None
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
    service = get_drive_service()
    if not service: return None
    query = f"'{folder_id}' in parents and name='Organigrama_Cargos.pdf' and trashed=false"
    results = service.files().list(q=query, fields="files(id)").execute()
    files = results.get('files', [])
    if files:
        return files[0]['id']
    return None

def download_organigrama_from_drive(file_id):
    """Descarga el PDF del organigrama desde Drive."""
    return download_manual_from_drive(file_id)

def set_file_public(file_id):
    """
    Cambia los permisos del archivo en Drive para que cualquiera con el enlace pueda verlo.
    """
    service = get_drive_service()
    if not service:
        return False
    try:
        service.permissions().create(
            fileId=file_id,
            body={
                'type': 'anyone',
                'role': 'reader'
            },
            fields='id',
            supportsAllDrives=True
        ).execute()
        return True
    except Exception as e:
        st.error(f"Error al cambiar permisos en Drive: {e}")
        return False
