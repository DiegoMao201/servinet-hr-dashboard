# pages/8_📊_Dashboard_Global.py
import streamlit as st
import pandas as pd
from modules.database import connect_to_drive, SPREADSHEET_ID

st.set_page_config(page_title="Dashboard Global", page_icon="📊", layout="wide")
st.title("📊 Dashboard Global de RRHH")

client = connect_to_drive()
spreadsheet = client.open_by_key(SPREADSHEET_ID)
# Ejemplo: desempeño
sheet_eval = spreadsheet.worksheet("2_evaluaciones")
df_eval = pd.DataFrame(sheet_eval.get_all_records())
if not df_eval.empty and "PUNTAJE" in df_eval.columns:
    st.subheader("Desempeño Promedio")
    st.bar_chart(df_eval.groupby("CARGO")["PUNTAJE"].mean())
    st.subheader("Ranking de Empleados")
    st.dataframe(df_eval.groupby("NOMBRE")["PUNTAJE"].mean().sort_values(ascending=False))
else:
    st.info("No hay datos de desempeño.")