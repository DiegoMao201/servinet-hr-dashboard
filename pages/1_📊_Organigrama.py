import streamlit as st
import pandas as pd
from modules.database import get_employees, get_saved_content
from modules.drive_manager import get_or_create_manuals_folder, find_manual_in_drive, download_manual_from_drive
from modules.ai_brain import analyze_results

st.set_page_config(page_title="Organigrama", page_icon="📊", layout="wide")
st.image("logo_servinet.jpg", width=120)
st.title("📊 Organigrama y Ficha de Empleado")

df = get_employees()
if df.empty:
    st.warning("No hay datos disponibles o falló la conexión. Verifica que el archivo en Drive tenga datos.")
    st.stop()

sedes = sorted(df['SEDE'].dropna().unique())
departamentos = sorted(df['DEPARTAMENTO'].dropna().unique())
cargos = sorted(df['CARGO'].dropna().unique())

col1, col2, col3 = st.columns(3)
filtro_sede = col1.selectbox("Filtrar por sede", ["Todas"] + sedes)
filtro_dep = col2.selectbox("Filtrar por departamento", ["Todos"] + departamentos)
filtro_cargo = col3.selectbox("Filtrar por cargo", ["Todos"] + cargos)

df_filtrado = df.copy()
if filtro_sede != "Todas":
    df_filtrado = df_filtrado[df_filtrado['SEDE'] == filtro_sede]
if filtro_dep != "Todos":
    df_filtrado = df_filtrado[df_filtrado['DEPARTAMENTO'] == filtro_dep]
if filtro_cargo != "Todos":
    df_filtrado = df_filtrado[df_filtrado['CARGO'] == filtro_cargo]

empleado = st.selectbox("Seleccionar Empleado", df_filtrado['NOMBRE COMPLETO'].unique())
datos = df_filtrado[df_filtrado['NOMBRE COMPLETO'] == empleado].iloc[0]
cargo = datos.get("CARGO", "")
manuals_folder_id = get_or_create_manuals_folder()

st.markdown(f"""
<div style='background:#f8f9fa;border-radius:12px;padding:24px;box-shadow:0 2px 8px #eee;'>
  <h2 style='color:#003d6e;'><span style='font-size:2em;'>👤</span> {empleado} <span style='font-size:0.7em;color:#888;'>({cargo})</span></h2>
  <p><b>Sede:</b> {datos.get('SEDE','--')} | <b>Departamento:</b> {datos.get('DEPARTAMENTO','--')}</p>
</div>
""", unsafe_allow_html=True)

# Manual de funciones
with st.expander("📄 Manual de Funciones"):
    manual_file_id = find_manual_in_drive(cargo, manuals_folder_id)
    eval_text = get_saved_content(cargo, "EVALUACION")
    badges = []
    if not manual_file_id:
        badges.append("<span style='background:#fff3cd;color:#856404;padding:4px 10px;border-radius:8px;'>Sin manual</span>")
    if not eval_text:
        badges.append("<span style='background:#f8d7da;color:#721c24;padding:4px 10px;border-radius:8px;'>Sin evaluación</span>")
    if badges:
        st.markdown(" ".join(badges), unsafe_allow_html=True)
    else:
        st.success("Empleado con documentación y evaluación al día.")
    if manual_file_id:
        pdf_bytes = download_manual_from_drive(manual_file_id)
        st.download_button(
            label="📥 Descargar Manual PDF",
            data=pdf_bytes,
            file_name=f"Manual_{cargo.replace(' ', '_').upper()}.pdf",
            mime="application/pdf"
        )
        st.success("Manual disponible.")
    else:
        st.warning("No hay manual de funciones para este cargo.")

# Evaluación y análisis IA
with st.expander("📝 Evaluación y Análisis IA"):
    evaluacion = get_saved_content(cargo, "EVALUACION")
    if evaluacion:
        st.markdown("**Última evaluación:**")
        st.markdown(evaluacion, unsafe_allow_html=True)
        analisis = analyze_results(evaluacion)
        st.markdown("**Análisis IA:**")
        st.markdown(analisis, unsafe_allow_html=True)
    else:
        st.warning("No hay evaluación registrada para este empleado.")

# Puedes agregar aquí más tabs o expanders para historial, desempeño, etc.