# pages/5_📅_Capacitaciones.py
import streamlit as st
import pandas as pd
from modules.database import connect_to_drive, SPREADSHEET_ID

st.set_page_config(page_title="Capacitaciones", page_icon="📅", layout="wide")
st.title("📅 Cronograma de Capacitaciones")

client = connect_to_drive()
spreadsheet = client.open_by_key(SPREADSHEET_ID)
sheet = spreadsheet.worksheet("3_capacitaciones")
data = sheet.get_all_records()
df = pd.DataFrame(data)

st.dataframe(df)
st.markdown("### Registrar nueva capacitación")
nombre = st.selectbox("Empleado", df["NOMBRE"].unique())
tema = st.text_input("Tema")
estado = st.selectbox("Estado", ["Pendiente", "Realizada"])
if st.button("Registrar capacitación"):
    import datetime
    cargo = df[df["NOMBRE"] == nombre]["CARGO"].iloc[0]
    sheet.append_row([
        nombre, cargo, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        tema, estado, ""
    ])
    st.success("Capacitación registrada.")