import streamlit as st
import pandas as pd
from modules.database import get_employees, get_saved_content

st.set_page_config(page_title="Dashboard de Alertas", page_icon="🚨", layout="wide")
st.image("logo_servinet.jpg", width=120)
st.title("🚨 Dashboard de Alertas y Pendientes")

df = get_employees()
if df.empty:
    st.warning("No hay datos de empleados.")
    st.stop()

# Lee todos los manuales y evaluaciones de una vez (bulk)
@st.cache_data(ttl=1800)  # Cache por 30 minutos
def get_alertas(df):
    cargos = df["CARGO"].unique()
    manuales_por_cargo = {cargo: get_saved_content(cargo, "PERFIL") for cargo in cargos}
    evaluaciones_por_cargo = {cargo: get_saved_content(cargo, "EVALUACION") for cargo in cargos}
    manuales = {}
    evaluaciones = {}
    for _, row in df.iterrows():
        nombre = row.get("NOMBRE COMPLETO", "")
        cargo = row.get("CARGO", "")
        manuales[nombre] = manuales_por_cargo.get(cargo)
        evaluaciones[nombre] = evaluaciones_por_cargo.get(cargo)
    return manuales, evaluaciones

manuales, evaluaciones = get_alertas(df)

sin_manual = [nombre for nombre, manual in manuales.items() if not manual]
sin_eval = [nombre for nombre, evalua in evaluaciones.items() if not evalua]

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
st.info("Este dashboard se actualiza cada 30 minutos para evitar sobrecargar la API.")