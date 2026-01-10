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
