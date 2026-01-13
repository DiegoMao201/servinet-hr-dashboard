# pages/6_🌤️_Clima_Laboral.py
import streamlit as st
from modules.database import connect_to_drive, SPREADSHEET_ID

st.set_page_config(page_title="Clima Laboral", page_icon="🌤️", layout="wide")
st.title("🌤️ Encuesta de Clima Laboral")

preguntas = [
    "¿Te sientes valorado en tu equipo?",
    "¿Recomendarías Servinet como lugar de trabajo?",
    "¿Sientes pertenencia con la empresa?",
    "¿Cómo calificarías el ambiente laboral?"
]
respuestas = {}
with st.form("clima_form"):
    for p in preguntas:
        respuestas[p] = st.slider(p, 0, 10, 5)
    enviado = st.form_submit_button("Enviar encuesta")
if enviado:
    client = connect_to_drive()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    sheet = spreadsheet.worksheet("4_clima_laboral")
    import datetime
    sheet.append_row([
        st.session_state.get("usuario", "Anonimo"),
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        *[respuestas[p] for p in preguntas]
    ])
    st.success("Encuesta registrada.")