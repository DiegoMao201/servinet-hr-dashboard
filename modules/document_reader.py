import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import PyPDF2
from docx import Document
import time
# CORRECCIÓN: Importar la función de autenticación desde el lugar correcto (auth.py)
from modules.auth import get_google_creds

# MEJORA: Cachear el servicio de Drive para no reconectar constantemente
@st.cache_resource(show_spinner="Conectando a Google Drive...")
def get_drive_service():
    """Obtiene el servicio de Drive usando las credenciales centralizadas."""
    creds = get_google_creds()
    if creds:
        return build('drive', 'v3', credentials=creds)
    st.error("Fallo en la autenticación con Google para el lector de documentos.")
    return None

def download_file_content(file_id):
    service = get_drive_service()
    if not service: return None
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    fh.seek(0)
    return fh

def read_pdf(file_id):
    try:
        fh = download_file_content(file_id)
        if not fh: return "Error: No se pudo descargar el archivo PDF."
        reader = PyPDF2.PdfReader(fh)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return f"Error leyendo PDF: {e}"

def read_docx(file_id):
    try:
        fh = download_file_content(file_id)
        if not fh: return "Error: No se pudo descargar el archivo DOCX."
        doc = Document(fh)
        text = "\n".join([para.text for para in doc.paragraphs])
        return text
    except Exception as e:
        return f"Error leyendo DOCX: {e}"

def get_company_context(folder_id):
    """
    Busca manuales en la carpeta indicada y crea el contexto para la IA.
    Ahora con reintentos ante errores de red.
    """
    service = get_drive_service()
    if not service:
        st.error("No se pudo obtener el servicio de Drive para leer el contexto de la compañía.")
        return ""
    query = f"('{folder_id}' in parents) and (name contains 'MANUAL' or name contains 'Estructura')"
    max_retries = 3
    for intento in range(max_retries):
        try:
            results = service.files().list(q=query, fields="files(id, name, mimeType)").execute()
            break
        except Exception as e:
            if intento < max_retries - 1:
                time.sleep(2)
            else:
                st.error(f"Error de red al leer archivos de Drive: {e}")
                return ""
    files = results.get('files', [])
    full_context = ""
    for file in files:
        if "pdf" in file['mimeType']:
            full_context += f"\n--- CONTENIDO DE {file['name']} ---\n"
            full_context += read_pdf(file['id'])
        elif "word" in file['mimeType'] or "document" in file['mimeType']:
            full_context += f"\n--- CONTENIDO DE {file['name']} ---\n"
            full_context += read_docx(file['id'])
    return full_context
