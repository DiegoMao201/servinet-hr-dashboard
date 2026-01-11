import streamlit as st
import graphviz
import pandas as pd
from modules.database import get_employees

st.set_page_config(page_title="Ecosistema SERVINET", page_icon="🌐", layout="wide")

st.markdown("""
<style>
.metric-card {background: #f8f9fa; border-radius: 8px; padding: 10px; margin: 5px;}
.metric-title {color: #0056b3; font-weight: bold;}
.metric-value {font-size: 1.5em;}
.org-label {font-size: 1.1em; color: #0056b3; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

with st.spinner("Sincronizando con Base de Datos Maestra..."):
    df = get_employees()

if df.empty:
    st.warning("⚠️ No hay datos disponibles o falló la conexión. Verifica que el archivo en Drive tenga datos.")
    st.stop()

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
total_visible = len(df)
sedes_activas = df['SEDE'].nunique() if "SEDE" in df.columns else 0
cargos_unicos = df['CARGO'].nunique() if "CARGO" in df.columns else 0

with kpi1:
    st.markdown('<div class="metric-card"><span class="metric-title">Talento Visible</span><br><span class="metric-value">{}</span></div>'.format(total_visible), unsafe_allow_html=True)
with kpi2:
    st.markdown('<div class="metric-card"><span class="metric-title">Sedes Operativas</span><br><span class="metric-value">{}</span></div>'.format(sedes_activas), unsafe_allow_html=True)
with kpi3:
    st.markdown('<div class="metric-card"><span class="metric-title">Roles Distintos</span><br><span class="metric-value">{}</span></div>'.format(cargos_unicos), unsafe_allow_html=True)
with kpi4:
    st.markdown('<div class="metric-card"><span class="metric-title">Estado</span><br><span class="metric-value">Activo</span></div>', unsafe_allow_html=True)

st.markdown("---")

tab_graph, tab_data = st.tabs(["📊 Mapa Jerárquico (Organigrama)", "📋 Ficha de Empleado"])

with tab_graph:
    graph = graphviz.Digraph()
    graph.attr(rankdir='TB', splines='ortho', bgcolor='transparent')
    graph.attr('node', shape='box', style='filled', fontname='DejaVu', fontsize='10', penwidth='0')
    graph.attr('edge', color='#888888', arrowhead='vee')

    sedes = df['SEDE'].unique() if "SEDE" in df.columns else []
    for sede in sedes:
        with graph.subgraph(name=f'cluster_{sede}') as s:
            s.attr(label=f"Sede: {sede}", color="#0056b3")
            sede_df = df[df['SEDE'] == sede]
            for index, row in sede_df.iterrows():
                nombre = str(row['NOMBRE COMPLETO']).strip()
                cargo = str(row['CARGO']).strip()
                jefe = str(row['JEFE_DIRECTO']).strip()
                bg_color = "#f0f2f6"
                font_color = "#333333"
                cargo_upper = cargo.upper()
                if "GERENTE" in cargo_upper:
                    bg_color = "#004085"
                    font_color = "white"
                elif "DIRECTOR" in cargo_upper:
                    bg_color = "#0056b3"
                    font_color = "white"
                elif "COORDINADOR" in cargo_upper or "LIDER" in cargo_upper:
                    bg_color = "#cce5ff"
                    font_color = "#004085"
                label = f'''<
                <TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="4">
                <TR><TD><B>{nombre}</B></TD></TR>
                <TR><TD><FONT POINT-SIZE="9">{cargo}</FONT></TD></TR>
                <TR><TD><FONT POINT-SIZE="8" COLOR="#555555">📍 {sede}</FONT></TD></TR>
                </TABLE>
                >'''
                s.node(nombre, label=label, fillcolor=bg_color, fontcolor=font_color)
                if jefe and jefe in sede_df['NOMBRE COMPLETO'].values and jefe != nombre:
                    s.edge(jefe, nombre)
    st.graphviz_chart(graph, use_container_width=True)

with tab_data:
    col_sel, col_det = st.columns([1, 2])
    with col_sel:
        st.subheader("Buscador")
        persona = st.selectbox("Seleccionar Empleado", df['NOMBRE COMPLETO'].unique())
    with col_det:
        if persona:
            datos = df[df['NOMBRE COMPLETO'] == persona].iloc[0]
            st.markdown(f"### 👤 {datos['NOMBRE COMPLETO']}")
            st.caption(f"Cédula: {datos.get('CEDULA', '---')}")
            c1, c2 = st.columns(2)
            c1.info(f"**Cargo:** {datos.get('CARGO', '--')}")
            c2.success(f"**Sede:** {datos.get('SEDE', '--')}")
            st.markdown("#### Información de Contacto")
            st.write(f"📧 **Correo:** {datos.get('CORREO', 'No registrado')}")
            st.write(f"📱 **Celular:** {datos.get('CELULAR', 'No registrado')}")
            st.write(f"🏢 **Centro de Trabajo:** {datos.get('CENTRO TRABAJO', '--')}")
            # Manual de funciones
            with st.expander("📄 Manual de Funciones (PDF)"):
                from modules.drive_manager import (
                    get_or_create_manuals_folder,
                    find_manual_in_drive,
                    download_manual_from_drive
                )
                manuals_folder_id = get_or_create_manuals_folder()
                manual_file_id = find_manual_in_drive(datos.get('CARGO', ''), manuals_folder_id)
                if manual_file_id:
                    pdf_bytes = download_manual_from_drive(manual_file_id)
                    st.download_button(
                        label="📥 Descargar Manual PDF",
                        data=pdf_bytes,
                        file_name=f"Manual_{datos.get('CARGO', '').replace(' ', '_').upper()}.pdf",
                        mime="application/pdf"
                    )
                else:
                    st.info("No hay manual de funciones generado para este cargo aún.")
            # Evaluación y cronograma
            with st.expander("📝 Evaluación y Cronograma de Capacitación"):
                # Aquí puedes mostrar la última evaluación y el plan generado por IA
                st.write("Aquí se mostrarán los resultados de la última evaluación y el cronograma de capacitación generado por IA.")
