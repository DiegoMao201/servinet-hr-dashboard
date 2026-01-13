import streamlit as st
import pandas as pd
from modules.database import get_employees
from modules.drive_manager import get_or_create_manuals_folder, find_manual_in_drive, download_manual_from_drive, upload_manual_to_drive
from modules.ai_brain import generate_role_profile
from modules.pdf_generator import create_manual_pdf_from_template
from modules.document_reader import get_company_context
import os
import re

st.set_page_config(page_title="Ficha de Empleado", page_icon="👤", layout="wide")
st.image("logo_servinet.jpg", width=120)
st.title("👤 Ficha de Empleado y Gestión")

df = get_employees()
if df.empty:
    st.warning("No hay datos disponibles o falló la conexión. Verifica que el archivo en Drive tenga datos.")
    st.stop()

# Filtros avanzados
areas = sorted(df['AREA'].dropna().unique()) if 'AREA' in df.columns else []
sedes = sorted(df['SEDE'].dropna().unique()) if 'SEDE' in df.columns else []
departamentos = sorted(df['DEPARTAMENTO'].dropna().unique()) if 'DEPARTAMENTO' in df.columns else []
cargos = sorted(df['CARGO'].dropna().unique()) if 'CARGO' in df.columns else []

col1, col2, col3, col4 = st.columns(4)
filtro_area = col1.selectbox("Filtrar por área", ["Todas"] + areas)
filtro_sede = col2.selectbox("Filtrar por sede", ["Todas"] + sedes)
filtro_dep = col3.selectbox("Filtrar por departamento", ["Todos"] + departamentos)
filtro_cargo = col4.selectbox("Filtrar por cargo", ["Todos"] + cargos)

df_filtrado = df.copy()
if filtro_area != "Todas" and 'AREA' in df_filtrado.columns:
    df_filtrado = df_filtrado[df_filtrado['AREA'] == filtro_area]
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

st.markdown(f"""
<div style='background:#f8f9fa;border-radius:24px;padding:40px;box-shadow:0 4px 24px #eee;max-width:900px;margin:auto;'>
  <div style='display:flex;align-items:center;gap:32px;'>
    <div style='font-size:5em;color:#0056b3;'>👤</div>
    <div>
      <h1 style='color:#003d6e;margin-bottom:0;'>{empleado}</h1>
      <div style='font-size:1.5em;color:#0056b3;font-weight:bold;'>{cargo}</div>
      <div style='margin-top:12px;'>
        <span style='background:#e6f7ff;color:#0056b3;padding:6px 16px;border-radius:12px;margin-right:12px;'>Sede: {datos.get('SEDE','--')}</span>
        <span style='background:#fffbe6;color:#856404;padding:6px 16px;border-radius:12px;'>Departamento: {datos.get('DEPARTAMENTO','--')}</span>
      </div>
    </div>
  </div>
  <hr style='margin:32px 0;'>
""", unsafe_allow_html=True)

# --- Ficha editable ---
with st.form("editar_empleado"):
    col1, col2 = st.columns(2)
    nombre = col1.text_input("Nombre Completo", value=datos.get("NOMBRE COMPLETO", ""))
    cedula = col2.text_input("Cédula", value=datos.get("CEDULA", ""))
    cargo_edit = col1.text_input("Cargo", value=datos.get("CARGO", ""))
    area = col2.text_input("Área", value=datos.get("AREA", ""))
    departamento = col1.text_input("Departamento", value=datos.get("DEPARTAMENTO", ""))
    sede = col2.text_input("Sede", value=datos.get("SEDE", ""))
    jefe = col1.text_input("Jefe Inmediato", value=datos.get("JEFE INMEDIATO", ""))
    correo = col2.text_input("Correo", value=datos.get("CORREO", ""))
    celular = col1.text_input("Celular", value=datos.get("CELULAR", ""))
    centro_trabajo = col2.text_input("Centro de Trabajo", value=datos.get("CENTRO TRABAJO", ""))
    # Agrega más campos según tu base de datos...
    actualizar = st.form_submit_button("Actualizar datos")
    if actualizar:
        ok = actualizar_empleado_google_sheets(
            nombre, cedula, cargo_edit, area, departamento, sede, jefe, correo, celular, centro_trabajo
        )
        if ok:
            st.success("Datos actualizados correctamente en Google Sheets.")
            st.experimental_rerun()  # <-- Esto recarga toda la app y actualiza los datos en pantalla
        else:
            st.error("No se encontró el empleado para actualizar. Verifica nombre y cédula.")

st.markdown("<hr>", unsafe_allow_html=True)

# --- Manual de funciones ---
st.markdown("### 📄 Manual de Funciones")
manual_file_id = find_manual_in_drive(cargo, manuals_folder_id)
if manual_file_id:
    pdf_bytes = download_manual_from_drive(manual_file_id)
    st.download_button(
        label="📥 Descargar Manual PDF",
        data=pdf_bytes,
        file_name=f"Manual_{cargo.replace(' ', '_').upper()}.pdf",
        mime="application/pdf"
    )
else:
    st.warning("Sin manual de funciones. Puedes generarlo desde Gestión Inteligente.")

st.markdown("</div>", unsafe_allow_html=True)

def actualizar_empleado_google_sheets(nombre, cedula, cargo, area, departamento, sede, jefe, correo, celular, centro_trabajo):
    from modules.database import connect_to_drive, SPREADSHEET_ID
    client = connect_to_drive()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    sheet = spreadsheet.worksheet("BD EMPLEADOS")
    # Busca la fila del empleado por nombre y cédula
    data = sheet.get_all_records()
    for idx, row in enumerate(data):
        if str(row.get("NOMBRE COMPLETO", "")).strip().upper() == nombre.strip().upper() and str(row.get("CEDULA", "")).strip() == str(cedula).strip():
            # Actualiza los campos (idx+2 porque get_all_records salta el header y Sheets es 1-based)
            fila = idx + 2
            sheet.update_cell(fila, sheet.find("NOMBRE COMPLETO").col, nombre)
            sheet.update_cell(fila, sheet.find("CEDULA").col, cedula)
            sheet.update_cell(fila, sheet.find("CARGO").col, cargo)
            sheet.update_cell(fila, sheet.find("AREA").col, area)
            sheet.update_cell(fila, sheet.find("DEPARTAMENTO").col, departamento)
            sheet.update_cell(fila, sheet.find("SEDE").col, sede)
            sheet.update_cell(fila, sheet.find("JEFE INMEDIATO").col, jefe)
            sheet.update_cell(fila, sheet.find("CORREO").col, correo)
            sheet.update_cell(fila, sheet.find("CELULAR").col, celular)
            sheet.update_cell(fila, sheet.find("CENTRO TRABAJO").col, centro_trabajo)
            return True
    return False