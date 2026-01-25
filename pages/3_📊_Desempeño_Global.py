import streamlit as st
import pandas as pd
from modules.database import get_employees, get_evaluaciones
from modules.ai_brain import analyze_results

st.set_page_config(page_title="Desempeño Global", page_icon="📊", layout="wide")
st.image("logo_servinet.jpg", width=120)
st.title("📊 Desempeño Global del Talento")

df_emp = get_employees()
df_eval = get_evaluaciones()

if df_eval.empty or df_emp.empty:
    st.warning("No hay datos de evaluaciones o empleados.")
    st.stop()

# --- Procesamiento de datos ---
if "PUNTAJE" in df_eval.columns:
    df_eval['PUNTAJE'] = pd.to_numeric(df_eval['PUNTAJE'], errors='coerce')
else:
    st.warning("No hay columna de puntaje en las evaluaciones.")
    st.stop()

st.subheader("Evolución de Desempeño por Cargo")
st.line_chart(df_eval.groupby('CARGO')['PUNTAJE'].mean())

st.subheader("Ranking de Desempeño por Cargo")
ranking = df_eval.groupby('CARGO')['PUNTAJE'].mean().sort_values(ascending=False)
st.dataframe(ranking)

st.markdown("---")
st.subheader("🔎 Análisis IA por Cargo y Planes de Capacitación")

for cargo, grupo in df_eval.groupby('CARGO'):
    st.markdown(f"### {cargo}")
    # Analizar todas las evaluaciones de este cargo
    respuestas = grupo.to_dict(orient='records')
    # Puedes concatenar respuestas o pasar una muestra
    analisis = analyze_results(respuestas)
    st.markdown(analisis, unsafe_allow_html=True)
    # Alertas
    if grupo['PUNTAJE'].min() < 60:
        st.error("⚠️ Hay empleados con desempeño bajo en este cargo. Prioriza capacitación y seguimiento.")
    else:
        st.success("Desempeño adecuado en este grupo.")

st.markdown("---")
st.caption("Dashboard generado automáticamente por IA y RRHH • SERVINET")