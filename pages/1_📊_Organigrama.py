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

empleado = st.selectbox("Seleccionar Empleado", df['NOMBRE COMPLETO'].unique())
datos = df[df['NOMBRE COMPLETO'] == empleado].iloc[0]
cargo = datos.get("CARGO", "")
manuals_folder_id = get_or_create_manuals_folder()

st.markdown(f"### 👤 {empleado} ({cargo})")
st.caption(f"Sede: {datos.get('SEDE', '--')} | Departamento: {datos.get('DEPARTAMENTO', '--')}")

# Manual de funciones
with st.expander("📄 Manual de Funciones"):
    manual_file_id = find_manual_in_drive(cargo, manuals_folder_id)
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