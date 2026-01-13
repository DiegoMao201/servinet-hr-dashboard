import streamlit as st
import pandas as pd
from modules.database import get_employees, get_saved_content
from modules.drive_manager import get_or_create_manuals_folder, find_manual_in_drive, download_manual_from_drive
from modules.ai_brain import analyze_results

st.set_page_config(page_title="Organigrama", page_icon="📊", layout="wide")
st.image("logo_servinet.jpg", width=120)
st.title("📊 Organigrama y Ficha de Empleado")

if "df_empleados" not in st.session_state:
    st.session_state["df_empleados"] = get_employees()
df = st.session_state["df_empleados"]  # Ahora usa la versión cacheada
if df.empty:
    st.warning("No hay datos disponibles o falló la conexión. Verifica que el archivo en Drive tenga datos.")
    st.stop()

# Filtros avanzados (robustos)
sedes = sorted(df['SEDE'].dropna().unique()) if 'SEDE' in df.columns else []
departamentos = sorted(df['DEPARTAMENTO'].dropna().unique()) if 'DEPARTAMENTO' in df.columns else []
cargos = sorted(df['CARGO'].dropna().unique()) if 'CARGO' in df.columns else []

col1, col2, col3 = st.columns(3)
filtro_sede = col1.selectbox("Filtrar por sede", ["Todas"] + sedes)
filtro_dep = col2.selectbox("Filtrar por departamento", ["Todos"] + departamentos)
filtro_cargo = col3.selectbox("Filtrar por cargo", ["Todos"] + cargos)

df_filtrado = df.copy()
if filtro_sede != "Todas" and 'SEDE' in df_filtrado.columns:
    df_filtrado = df_filtrado[df_filtrado['SEDE'] == filtro_sede]
if filtro_dep != "Todos" and 'DEPARTAMENTO' in df_filtrado.columns:
    df_filtrado = df_filtrado[df_filtrado['DEPARTAMENTO'] == filtro_dep]
if filtro_cargo != "Todos" and 'CARGO' in df_filtrado.columns:
    df_filtrado = df_filtrado[df_filtrado['CARGO'] == filtro_cargo]

empleado = st.selectbox("Seleccionar empleado", df_filtrado['NOMBRE COMPLETO'].unique())
datos = df_filtrado[df_filtrado['NOMBRE COMPLETO'] == empleado].iloc[0]
cargo = datos.get("CARGO", "")
manuals_folder_id = get_or_create_manuals_folder()

# Ficha tipo hoja de vida
st.markdown(f"""
<div style='background:#f8f9fa;border-radius:16px;padding:32px;box-shadow:0 2px 12px #eee;max-width:900px;margin:auto;'>
  <div style='display:flex;align-items:center;gap:24px;'>
    <div style='font-size:4em;color:#003d6e;'>👤</div>
    <div>
      <h2 style='color:#003d6e;margin-bottom:0;'>{empleado}</h2>
      <div style='font-size:1.2em;color:#0056b3;font-weight:bold;'>{cargo}</div>
      <div style='margin-top:8px;'>
        <span style='background:#e6f7ff;color:#0056b3;padding:4px 12px;border-radius:8px;margin-right:8px;'>Sede: {datos.get('SEDE','--')}</span>
        <span style='background:#fffbe6;color:#856404;padding:4px 12px;border-radius:8px;'>Departamento: {datos.get('DEPARTAMENTO','--')}</span>
      </div>
    </div>
  </div>
  <hr style='margin:24px 0;'>
  <div style='display:flex;gap:32px;flex-wrap:wrap;'>
    <div style='flex:1;min-width:250px;'>
      <h4 style='color:#003d6e;'>📄 Manual de Funciones</h4>
""", unsafe_allow_html=True)

manual_file_id = find_manual_in_drive(cargo, manuals_folder_id)
if manual_file_id:
    pdf_bytes = download_manual_from_drive(manual_file_id)
    st.markdown("""
    <span style='background:#d4edda;color:#155724;padding:4px 10px;border-radius:8px;'>Manual disponible</span>
    """, unsafe_allow_html=True)
    st.download_button(
        label="📥 Descargar Manual PDF",
        data=pdf_bytes,
        file_name=f"Manual_{cargo.replace(' ', '_').upper()}.pdf",
        mime="application/pdf"
    )
else:
    st.markdown("""
    <span style='background:#f8d7da;color:#721c24;padding:4px 10px;border-radius:8px;'>Sin manual de funciones</span>
    """, unsafe_allow_html=True)

st.markdown("""
    </div>
    <div style='flex:1;min-width:250px;'>
      <h4 style='color:#003d6e;'>📝 Evaluaciones</h4>
""", unsafe_allow_html=True)

eval_text = get_saved_content(cargo, "EVALUACION")
if eval_text:
    st.markdown("""
    <span style='background:#d4edda;color:#155724;padding:4px 10px;border-radius:8px;'>Evaluación disponible</span>
    """, unsafe_allow_html=True)
    st.download_button(
        label="📥 Descargar Evaluación (PDF/Texto)",
        data=eval_text.encode("utf-8"),
        file_name=f"Evaluacion_{cargo.replace(' ', '_').upper()}.txt",
        mime="text/plain"
    )
    analisis = analyze_results(eval_text)
    st.markdown("**Análisis IA:**")
    st.markdown(analisis, unsafe_allow_html=True)
else:
    st.markdown("""
    <span style='background:#f8d7da;color:#721c24;padding:4px 10px;border-radius:8px;'>Sin evaluación registrada</span>
    """, unsafe_allow_html=True)

st.markdown("""
    </div>
  </div>
  <hr style='margin:24px 0;'>
  <div style='margin-top:16px;'>
    <b>Correo:</b> {correo} &nbsp; | &nbsp; <b>Celular:</b> {celular} &nbsp; | &nbsp; <b>Centro de Trabajo:</b> {centro_trabajo}
  </div>
</div>
""".format(
    correo=datos.get('CORREO', 'No registrado'),
    celular=datos.get('CELULAR', 'No registrado'),
    centro_trabajo=datos.get('CENTRO TRABAJO', '--')
), unsafe_allow_html=True)