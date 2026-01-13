import streamlit as st
import pandas as pd
from modules.database import get_employees, get_saved_content
from modules.drive_manager import get_or_create_manuals_folder, find_manual_in_drive, download_manual_from_drive, upload_manual_to_drive
from modules.ai_brain import analyze_results, generate_role_profile
from modules.pdf_generator import create_manual_pdf_from_template
import os
import plotly.graph_objects as go
import io
from fpdf import FPDF

st.set_page_config(page_title="Organigrama", page_icon="📊", layout="wide")
st.image("logo_servinet.jpg", width=120)
st.title("📊 Organigrama y Ficha de Empleado")

if "df_empleados" not in st.session_state:
    st.session_state["df_empleados"] = get_employees()
df = st.session_state["df_empleados"]
if df.empty:
    st.warning("No hay datos disponibles o falló la conexión. Verifica que el archivo en Drive tenga datos.")
    st.stop()

sedes = sorted(df['SEDE'].dropna().unique()) if 'SEDE' in df.columns else []
departamentos = sorted(df['DEPARTAMENTO'].dropna().unique()) if 'DEPARTAMENTO' in df.columns else []
cargos = sorted(df['CARGO'].dropna().unique()) if 'CARGO' in df.columns else []

tab1, tab2 = st.tabs(["👥 Organigrama Visual", "👤 Ficha de Empleado"])

with tab1:
    st.subheader("Organigrama de la Empresa (Interactivo)")
    # Construir nodos y edges para plotly
    nodes = []
    edges = []
    color_map = {dep: f"rgba({50+idx*30},100,200,0.8)" for idx, dep in enumerate(departamentos)}
    for idx, row in df.iterrows():
        nombre = row.get("NOMBRE COMPLETO", "")
        cargo = row.get("CARGO", "")
        dep = row.get("DEPARTAMENTO", "")
        sede = row.get("SEDE", "")
        jefe = row.get("JEFE INMEDIATO", "")
        nodes.append(dict(
            id=nombre,
            label=f"{nombre}\n{cargo}\n{dep}\n{sede}",
            color=color_map.get(dep, "#0056b3"),
            title=f"<b>{nombre}</b><br>{cargo}<br>{dep}<br>{sede}"
        ))
        if jefe and jefe != nombre:
            edges.append((jefe, nombre))
    # Plotly Sankey para organigrama
    node_labels = [n['label'] for n in nodes]
    node_colors = [n['color'] for n in nodes]
    node_titles = [n['title'] for n in nodes]
    node_ids = [n['id'] for n in nodes]
    source = [node_ids.index(e[0]) for e in edges if e[0] in node_ids and e[1] in node_ids]
    target = [node_ids.index(e[1]) for e in edges if e[0] in node_ids and e[1] in node_ids]
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=node_labels,
            color=node_colors,
            customdata=node_titles,
            hovertemplate='%{customdata}<extra></extra>',
        ),
        link=dict(
            source=source,
            target=target,
            value=[1]*len(source)
        )
    )])
    fig.update_layout(title_text="Organigrama Interactivo", font_size=12, height=700)
    st.plotly_chart(fig, use_container_width=True)
    st.download_button("📥 Exportar Organigrama PNG", fig.to_image(format="png"), file_name="organigrama.png")

with tab2:
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
      <div style='display:flex;gap:40px;flex-wrap:wrap;'>
        <div style='flex:1;min-width:300px;'>
          <h3 style='color:#003d6e;'>📄 Manual de Funciones</h3>
    """, unsafe_allow_html=True)

    manual_file_id = find_manual_in_drive(cargo, manuals_folder_id)
    if manual_file_id:
        pdf_bytes = download_manual_from_drive(manual_file_id)
        st.markdown("""
        <span style='background:#d4edda;color:#155724;padding:6px 14px;border-radius:12px;'>Manual disponible</span>
        """, unsafe_allow_html=True)
        st.download_button(
            label="📥 Descargar Manual PDF",
            data=pdf_bytes,
            file_name=f"Manual_{cargo.replace(' ', '_').upper()}.pdf",
            mime="application/pdf"
        )
    else:
        st.markdown("""
        <span style='background:#f8d7da;color:#721c24;padding:6px 14px;border-radius:12px;'>Sin manual de funciones</span>
        """, unsafe_allow_html=True)
        if st.button("✨ Generar Manual con IA"):
            st.info("Generando manual...")
            from modules.document_reader import get_company_context
            company_context = get_company_context(manuals_folder_id)
            perfil_html = generate_role_profile(cargo, company_context)
            datos_manual = {
                "empresa": "GRUPO SERVINET",
                "logo_url": os.path.abspath("logo_servinet.jpg"),
                "codigo_doc": f"DOC-MF-{str(datos.get('CEDULA', '001'))}",
                "departamento": datos.get("SEDE", ""),
                "titulo": f"Manual de Funciones: {cargo}",
                "descripcion": f"Manual profesional para el cargo {cargo} en {datos.get('SEDE', '')}.",
                "version": "1.0",
                "vigencia": "Enero 2025 - Diciembre 2025",
                "fecha_emision": pd.Timestamp.now().strftime("%d/%m/%Y"),
                "empleado": empleado,
                "cargo": cargo,
                "objetivo_cargo": "",
                "funciones_principales": "",
                "procesos_clave": "",
                "habilidades_blandas": "",
                "kpis_sugeridos": "",
                "perfil_ideal": "",
                "observaciones": "",
            }
            pdf_filename = create_manual_pdf_from_template(datos_manual, cargo, empleado=empleado)
            upload_manual_to_drive(pdf_filename, folder_id=manuals_folder_id)
            with open(pdf_filename, "rb") as f:
                st.download_button(
                    label="📥 Descargar Manual PDF",
                    data=f.read(),
                    file_name=os.path.basename(pdf_filename),
                    mime="application/pdf"
                )
            st.success("Manual generado y guardado en Drive.")
            try:
                os.remove(pdf_filename)
            except Exception:
                pass

    st.markdown("""
        </div>
        <div style='flex:1;min-width:300px;'>
          <h3 style='color:#003d6e;'>📝 Evaluaciones</h3>
    """, unsafe_allow_html=True)

    eval_text = get_saved_content(cargo, "EVALUACION")
    if eval_text:
        st.markdown("""
        <span style='background:#d4edda;color:#155724;padding:6px 14px;border-radius:12px;'>Evaluación disponible</span>
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
        <span style='background:#f8d7da;color:#721c24;padding:6px 14px;border-radius:12px;'>Sin evaluación registrada</span>
        """, unsafe_allow_html=True)

    st.markdown("""
        </div>
      </div>
      <hr style='margin:32px 0;'>
      <div style='margin-top:20px;'>
        <b>Correo:</b> {correo} &nbsp; | &nbsp; <b>Celular:</b> {celular} &nbsp; | &nbsp; <b>Centro de Trabajo:</b> {centro_trabajo}
      </div>
    </div>
    """.format(
        correo=datos.get('CORREO', 'No registrado'),
        celular=datos.get('CELULAR', 'No registrado'),
        centro_trabajo=datos.get('CENTRO TRABAJO', '--')
    ), unsafe_allow_html=True)

def generate_org_pdf(df, analysis_text, conclusions_text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Organigrama Empresarial - SERVINET", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 8, "Análisis y Comentarios:")
    pdf.set_font("Arial", "I", 11)
    pdf.multi_cell(0, 8, analysis_text)
    pdf.ln(5)
    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 8, "Conclusiones:")
    pdf.set_font("Arial", "I", 11)
    pdf.multi_cell(0, 8, conclusions_text)
    pdf.ln(10)
    pdf.set_font("Arial", "B", 13)
    pdf.cell(0, 8, "Estructura Organizacional:", ln=True)
    pdf.set_font("Arial", "", 11)
    # Listado jerárquico simple
    for idx, row in df.iterrows():
        pdf.cell(0, 8, f"{row['NOMBRE COMPLETO']} - {row['CARGO']} ({row['DEPARTAMENTO']})", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", "I", 9)
    pdf.cell(0, 8, "Documento generado automáticamente por el sistema de RRHH SERVINET.", ln=True)
    pdf_bytes = io.BytesIO()
    pdf.output(pdf_bytes)
    pdf_bytes.seek(0)
    return pdf_bytes

# --- Análisis y conclusiones automáticos ---
def get_org_analysis(df):
    total = len(df)
    departamentos = df['DEPARTAMENTO'].value_counts().to_dict()
    sedes = df['SEDE'].value_counts().to_dict()
    managers = df[df['CARGO'].str.contains("Jefe|Gerente|Director", case=False, na=False)]
    analysis = f"- Total de empleados: {total}\n"
    analysis += f"- Departamentos: {', '.join([f'{k} ({v})' for k,v in departamentos.items()])}\n"
    analysis += f"- Sedes: {', '.join([f'{k} ({v})' for k,v in sedes.items()])}\n"
    analysis += f"- Managers detectados: {len(managers)}\n"
    return analysis

def get_org_conclusions(df):
    # Puedes usar IA aquí si quieres, pero aquí va un ejemplo simple:
    if len(df) < 10:
        return "La empresa tiene una estructura compacta. Se recomienda fortalecer los equipos clave y planificar el crecimiento."
    else:
        return "La estructura organizacional es robusta. Se recomienda revisar los flujos de reporte y fortalecer la comunicación entre departamentos."

# --- Botón para exportar PDF ---
if st.button("📄 Exportar Organigrama y Análisis en PDF"):
    analysis_text = get_org_analysis(df)
    conclusions_text = get_org_conclusions(df)
    pdf_bytes = generate_org_pdf(df, analysis_text, conclusions_text)
    st.download_button(
        label="Descargar PDF profesional",
        data=pdf_bytes,
        file_name="Organigrama_SERVINET.pdf",
        mime="application/pdf"
    )