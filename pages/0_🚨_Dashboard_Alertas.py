import streamlit as st
import pandas as pd
from modules.database import get_employees, get_saved_content

st.set_page_config(page_title="Dashboard de Alertas", page_icon="🚨", layout="wide")
st.image("logo_servinet.jpg", width=120)
st.title("🚨 Dashboard de Alertas y Pendientes")

# Cachea empleados
if "df_empleados" not in st.session_state:
    st.session_state["df_empleados"] = get_employees()
df = st.session_state["df_empleados"]

if df.empty:
    st.warning("No hay datos de empleados.")
    st.stop()

# Opcional: Cachea resultados de get_saved_content en session_state para cada cargo
if "alertas_manual" not in st.session_state or "alertas_eval" not in st.session_state:
    st.session_state["alertas_manual"] = {}
    st.session_state["alertas_eval"] = {}
    for _, row in df.iterrows():
        cargo = row.get("CARGO", "")
        nombre = row.get("NOMBRE COMPLETO", "")
        manual = get_saved_content(cargo, "PERFIL")
        evaluacion = get_saved_content(cargo, "EVALUACION")
        st.session_state["alertas_manual"][nombre] = manual
        st.session_state["alertas_eval"][nombre] = evaluacion

sin_manual = [nombre for nombre, manual in st.session_state["alertas_manual"].items() if not manual]
sin_eval = [nombre for nombre, evalua in st.session_state["alertas_eval"].items() if not evalua]

col1, col2 = st.columns(2)
with col1:
    st.subheader("⚠️ Empleados sin Manual de Funciones")
    if sin_manual:
        st.error(f"{len(sin_manual)} empleados sin manual:")
        st.write(", ".join(sin_manual))
    else:
        st.success("Todos los empleados tienen manual de funciones.")

with col2:
    st.subheader("⚠️ Empleados sin Evaluación")
    if sin_eval:
        st.error(f"{len(sin_eval)} empleados sin evaluación:")
        st.write(", ".join(sin_eval))
    else:
        st.success("Todos los empleados tienen evaluación registrada.")

st.markdown("---")
st.info("Este dashboard se actualiza en tiempo real según la base de datos.")