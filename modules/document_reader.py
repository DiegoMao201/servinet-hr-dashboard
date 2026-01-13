import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import PyPDF2
from docx import Document
from modules.database import get_creds

def get_drive_service():
    creds = get_creds()
    if creds:
        return build('drive', 'v3', credentials=creds)
    return None

def download_file_content(file_id):
    service = get_drive_service()
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
        doc = Document(fh)
        text = "\n".join([para.text for para in doc.paragraphs])
        return text
    except Exception as e:
        return f"Error leyendo DOCX: {e}"

def get_company_context(folder_id):
    """
    Busca manuales en la carpeta indicada y crea el contexto para la IA.
    """
    service = get_drive_service()
    query = f"('{folder_id}' in parents) and (name contains 'MANUAL' or name contains 'Estructura')"
    results = service.files().list(q=query, fields="files(id, name, mimeType)").execute()
    files = results.get('files', [])
    full_context = ""
    for file in files:
        st.toast(f"🧠 Analizando documento: {file['name']}...")
        if "pdf" in file['mimeType']:
            full_context += f"\n--- CONTENIDO DE {file['name']} ---\n"
            full_context += read_pdf(file['id'])
        elif "word" in file['mimeType'] or "document" in file['mimeType']:
            full_context += f"\n--- CONTENIDO DE {file['name']} ---\n"
            full_context += read_docx(file['id'])
    return full_context
