# pages/7_🏅_Reconocimientos.py
import streamlit as st
from modules.database import connect_to_drive, SPREADSHEET_ID

st.set_page_config(page_title="Reconocimientos", page_icon="🏅", layout="wide")
st.title("🏅 Registro de Reconocimientos y Sanciones")

tipo = st.selectbox("Tipo", ["Reconocimiento", "Sanción"])
nombre = st.text_input("Empleado")
descripcion = st.text_area("Descripción")
if st.button("Registrar"):
    client = connect_to_drive()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    hoja = "5_reconocimientos" if tipo == "Reconocimiento" else "6_sanciones"
    sheet = spreadsheet.worksheet(hoja)
    import datetime
    sheet.append_row([
        nombre, "", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        tipo, descripcion
    ])
    st.success(f"{tipo} registrado.")