import streamlit as st
import pandas as pd
from modules.database import get_employees
from modules.drive_manager import get_or_create_manuals_folder, find_manual_in_drive, download_manual_from_drive, upload_manual_to_drive
from modules.ai_brain import generate_role_profile
from modules.pdf_generator import create_manual_pdf_from_template
from modules.document_reader import get_company_context
import os
import re
import datetime

st.set_page_config(page_title="Organigrama y Ficha", page_icon="👤", layout="wide")
st.image("logo_servinet.jpg", width=120)
st.title("👤 Gestión de Empleados y Organigrama")

now = datetime.datetime.now()
anio_actual = now.year
vigencia = f"Enero {anio_actual} - Diciembre {anio_actual}"
fecha_emision = now.strftime("%d/%m/%Y")

df = get_employees()
if df.empty:
    st.warning("No hay datos disponibles o falló la conexión. Verifica que el archivo en Drive tenga datos.")
    st.stop()

# Filtros avanzados
areas = sorted(df['AREA'].dropna().unique()) if 'AREA' in df.columns else []
sedes = sorted(df['SEDE'].dropna().unique()) if 'SEDE' in df.columns else []
departamentos = sorted(df['DEPARTAMENTO'].dropna().unique()) if 'DEPARTAMENTO' in df.columns else []
cargos = sorted(df['CARGO'].dropna().unique()) if 'CARGO' in df.columns else []

tab1, tab2 = st.tabs(["🌳 Organigrama Visual", "👤 Ficha de Empleado"])

def preparar_df_organigrama(df):
    nombre_to_id = dict(zip(df['NOMBRE COMPLETO'], df['CEDULA'].astype(str)))
    df_org = pd.DataFrame({
        'id': df['CEDULA'].astype(str),
        'name': df['NOMBRE COMPLETO'],
        'position': df['CARGO'],
        'department': df['DEPARTAMENTO'],
        'parent_id': df['JEFE_DIRECTO'].map(nombre_to_id).fillna('') if 'JEFE_DIRECTO' in df.columns else ['']*len(df),
        'email': df.get('CORREO', pd.Series(['']*len(df))),
        'phone': df.get('CELULAR', pd.Series(['']*len(df))),
        'sede': df.get('SEDE', pd.Series(['']*len(df))),
        'estado': df.get('ESTADO', pd.Series(['']*len(df))),
        'tipo': df.get('PLANTA - COOPERATIVA', pd.Series(['']*len(df))),
    })
    return df_org

def render_organigrama(df_empleados):
    empleados_json = df_empleados.to_json(orient='records')
    html_code = f"""
    <!DOCTYPE html>
    <html lang="es" style="height: 100%;">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <script src="https://cdn.tailwindcss.com"></script>
      <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
      <style>
        body {{
          font-family: 'Plus Jakarta Sans', sans-serif;
          background: linear-gradient(to bottom right, #f8fafc, #e0e7ff, #ede9fe);
        }}
        .org-tree {{
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 0.5rem;
        }}
        .org-level {{
          display: flex;
          justify-content: center;
          gap: 0.5rem;
          position: relative;
          padding-top: 0.5rem;
          flex-wrap: wrap;
        }}
        .org-level::before {{
          content: '';
          position: absolute;
          top: 0;
          left: 50%;
          width: 2px;
          height: 0.8rem;
          background: linear-gradient(180deg, #6366f1 0%, #a5b4fc 100%);
        }}
        .org-level:first-child::before {{
          display: none;
        }}
        .org-level:first-child {{
          padding-top: 0;
        }}
        .org-node {{
          position: relative;
          min-width: 110px;
          max-width: 140px;
          background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
          border-radius: 10px;
          padding: 0.5rem 0.7rem;
          box-shadow: 0 2px 8px rgba(99, 102, 241, 0.10), 0 1px 4px rgba(0, 0, 0, 0.04);
          border: 1px solid rgba(99, 102, 241, 0.12);
          transition: all 0.2s ease;
          cursor: pointer;
          margin-bottom: 0.3rem;
        }}
        .org-node:hover {{
          transform: translateY(-2px) scale(1.04);
          box-shadow: 0 4px 12px rgba(99, 102, 241, 0.18), 0 2px 8px rgba(0, 0, 0, 0.08);
        }}
        .org-node.ceo {{
          background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
          color: white;
          min-width: 140px;
        }}
        .org-node.manager {{
          border-left: 2px solid #6366f1;
        }}
        .node-avatar {{
          width: 28px;
          height: 28px;
          border-radius: 6px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 700;
          font-size: 0.9rem;
          margin-bottom: 0.2rem;
          background: linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%);
          color: #4f46e5;
        }}
        .org-node.ceo .node-avatar {{
          background: rgba(255, 255, 255, 0.2);
          color: white;
        }}
        .node-name {{
          font-weight: 600;
          font-size: 0.8rem;
          margin-bottom: 0.1rem;
          white-space: normal;
        }}
        .node-position {{
          font-size: 0.7rem;
          color: #6b7280;
          margin-bottom: 0.1rem;
        }}
        .org-node.ceo .node-position {{
          color: rgba(255, 255, 255, 0.85);
        }}
        .node-dept {{
          display: inline-block;
          padding: 0.10rem 0.3rem;
          border-radius: 10px;
          font-size: 0.6rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          margin-top: 0.1rem;
          background: #fef3c7;
          color: #92400e;
        }}
        .node-sede {{
          font-size: 0.6rem;
          color: #2563eb;
          margin-top: 0.05rem;
        }}
        .node-estado {{
          font-size: 0.6rem;
          color: #059669;
          margin-top: 0.05rem;
        }}
        .node-tipo {{
          font-size: 0.6rem;
          color: #b91c1c;
          margin-top: 0.05rem;
        }}
        .node-contact {{
          font-size: 0.6rem;
          color: #64748b;
          margin-top: 0.05rem;
        }}
      </style>
    </head>
    <body>
      <div class="header" style="text-align:center;margin-bottom:0.5rem;">
        <h1 style="font-size:1.1rem;font-weight:700;color:#1e293b;">Organigrama Empresarial</h1>
        <p style="color:#64748b;margin:0;font-size:0.8rem;">Estructura Organizacional Compacta</p>
      </div>
      <div id="org-chart" class="org-tree"></div>
      <script>
        const employees = {empleados_json};
        function getInitials(name) {{
          return name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
        }}
        function buildTree() {{
          const map = new Map();
          const roots = [];
          employees.forEach(emp => {{
            map.set(emp.id, {{ ...emp, children: [] }});
          }});
          employees.forEach(emp => {{
            const node = map.get(emp.id);
            if (emp.parent_id && map.has(emp.parent_id)) {{
              map.get(emp.parent_id).children.push(node);
            }} else {{
              roots.push(node);
            }}
          }});
          return roots;
        }}
        function renderOrgChart() {{
          const tree = buildTree();
          const orgChart = document.getElementById('org-chart');
          orgChart.innerHTML = '';
          function renderLevel(nodes, level = 0) {{
            if (nodes.length === 0) return;
            const levelDiv = document.createElement('div');
            levelDiv.className = 'org-level';
            nodes.forEach(node => {{
              const nodeDiv = document.createElement('div');
              const isCEO = level === 0 && !node.parent_id;
              nodeDiv.className = `org-node ${{isCEO ? 'ceo' : node.children.length > 0 ? 'manager' : ''}}`;
              nodeDiv.innerHTML = `
                <div class="node-avatar">${{getInitials(node.name)}}</div>
                <div class="node-name">${{node.name}}</div>
                <div class="node-position">${{node.position}}</div>
                <span class="node-dept">${{node.department}}</span>
                <div class="node-sede">${{node.sede || ''}}</div>
                <div class="node-estado">${{node.estado || ''}}</div>
                <div class="node-tipo">${{node.tipo || ''}}</div>
                <div class="node-contact">${{node.email || ''}}</div>
                <div class="node-contact">${{node.phone || ''}}</div>
              `;
              levelDiv.appendChild(nodeDiv);
            }});
            orgChart.appendChild(levelDiv);
            const allChildren = nodes.flatMap(n => n.children);
            if (allChildren.length > 0) {{
              renderLevel(allChildren, level + 1);
            }}
          }}
          renderLevel(tree);
        }}
        renderOrgChart();
      </script>
    </body>
    </html>
    """
    st.components.v1.html(html_code, height=600, scrolling=True)

with tab1:
    st.subheader("🌳 Organigrama Visual Interactivo")
    df_org = preparar_df_organigrama(df)
    render_organigrama(df_org)

with tab2:
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
        actualizar = st.form_submit_button("Actualizar datos")
        if actualizar:
            ok = actualizar_empleado_google_sheets(
                nombre, cedula, cargo_edit, area, departamento, sede, jefe, correo, celular, centro_trabajo
            )
            if ok:
                st.success("Datos actualizados correctamente en Google Sheets.")
                st.experimental_rerun()
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