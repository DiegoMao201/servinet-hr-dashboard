import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import json

def connect_to_drive():
    # En producción (Coolify), las credenciales vendrán de st.secrets
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    # Cargamos el JSON desde los secretos de Streamlit
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

def get_employees():
    client = connect_to_drive()
    sheet = client.open("BD EMPLEADOS- EX EMPLEADOS ").sheet1 # Nombre de tu archivo en Drive
    data = sheet.get_all_records()
    return pd.DataFrame(data)
