import streamlit as st
import graphviz
import pandas as pd
from modules.database import get_employees

# Configuración de la página
st.set_page_config(page_title="Ecosistema SERVINET", page_icon="🌐", layout="wide")

# --- CSS PARA ESTILO PROFESIONAL ---
st.markdown("""
<style>
    /* Tarjetas de Métricas */
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #dedede;
        padding: 10px;
        border-radius: 8px;
        border-left: 5px solid #0056b3;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    /* Títulos */
    h1 { color: #004085; }
    h3 { color: #333333; }
</style>
""", unsafe_allow_html=True)

# --- ENCABEZADO ---
col_logo, col_title = st.columns([1, 5])
with col_title:
    st.title("🌐 Ecosistema Organizacional SERVINET")
    st.markdown("Plataforma de visualización de talento y estructura jerárquica en tiempo real.")

# --- CARGA DE DATOS ---
with st.spinner("Sincronizando con Base de Datos Maestra..."):
    df = get_employees()

if df.empty:
    st.warning("⚠️ No hay datos disponibles o falló la conexión. Verifica que el archivo en Drive tenga datos.")
    st.stop()

# --- BARRA LATERAL DE FILTROS ---
with st.sidebar:
    st.header("🔍 Control de Visualización")
    if "ESTADO" in df.columns:
        estados = list(df['ESTADO'].unique())
        default_estado = ["ACTIVO"] if "ACTIVO" in estados else estados
        filtro_estado = st.multiselect("Estado Contractual", estados, default=default_estado)
        df_filtered = df[df['ESTADO'].isin(filtro_estado)]
    else:
        st.error("No se encontró la columna 'ESTADO'.")
        df_filtered = df

    if "SEDE" in df.columns:
        opciones_sede = ["Todas las Sedes"] + list(df_filtered['SEDE'].unique())
        sede_sel = st.selectbox("Filtrar por Sede", opciones_sede)
        if sede_sel != "Todas las Sedes":
            df_filtered = df_filtered[df_filtered['SEDE'] == sede_sel]

# --- DASHBOARD DE KPIS (Métricas Arriba) ---
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

total_visible = len(df_filtered)
sedes_activas = df_filtered['SEDE'].nunique() if "SEDE" in df_filtered.columns else 0
cargos_unicos = df_filtered['CARGO'].nunique() if "CARGO" in df_filtered.columns else 0

kpi1.metric("Talento Visible", total_visible, help="Total de empleados según filtros")
kpi2.metric("Sedes Operativas", sedes_activas)
kpi3.metric("Roles Distintos", cargos_unicos)
kpi4.metric("Estado", "Filtro Activo" if len(filtro_estado) < len(estados) else "Total")

st.markdown("---")

# --- VISUALIZACIÓN ---
tab_graph, tab_data = st.tabs(["📊 Mapa Jerárquico (Organigrama)", "📋 Ficha de Empleado"])

with tab_graph:
    # Lógica de Graphviz
    graph = graphviz.Digraph()
    graph.attr(rankdir='TB', splines='ortho', bgcolor='transparent')
    graph.attr('node', shape='box', style='filled', fontname='Arial', fontsize='10', penwidth='0')
    graph.attr('edge', color='#888888', arrowhead='vee')

    # Validamos que existan las columnas clave
    if 'NOMBRE COMPLETO' in df_filtered.columns and 'CARGO' in df_filtered.columns and 'JEFE_DIRECTO' in df_filtered.columns:
        
        for index, row in df_filtered.iterrows():
            nombre = str(row['NOMBRE COMPLETO']).strip()
            cargo = str(row['CARGO']).strip()
            sede = str(row.get('SEDE', 'N/A')).strip()
            
            # Estilo condicional según jerarquía
            bg_color = "#f0f2f6" # Gris por defecto
            font_color = "#333333"
            
            cargo_upper = cargo.upper()
            if "GERENTE" in cargo_upper:
                bg_color = "#004085" # Azul Oscuro
                font_color = "white"
            elif "DIRECTOR" in cargo_upper:
                bg_color = "#0056b3" # Azul Servinet
                font_color = "white"
            elif "COORDINADOR" in cargo_upper or "LIDER" in cargo_upper:
                bg_color = "#cce5ff" # Azul clarito
                font_color = "#004085"
            
            # Nodo HTML para diseño bonito
            label = f'''<
            <TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="4">
            <TR><TD><B>{nombre}</B></TD></TR>
            <TR><TD><FONT POINT-SIZE="9">{cargo}</FONT></TD></TR>
            <TR><TD><FONT POINT-SIZE="8" COLOR="#555555">📍 {sede}</FONT></TD></TR>
            </TABLE>
            >'''
            
            graph.node(nombre, label=label, fillcolor=bg_color, fontcolor=font_color)
            
            # Conexión con Jefe
            jefe = str(row['JEFE_DIRECTO']).strip()
            # Solo conectamos si el jefe está en la lista visible
            if jefe and jefe in df_filtered['NOMBRE COMPLETO'].values and jefe != nombre:
                graph.edge(jefe, nombre)
        
        st.graphviz_chart(graph, use_container_width=True)
    else:
        st.error("Error: Faltan columnas clave (NOMBRE COMPLETO, CARGO, JEFE_DIRECTO) en el Excel.")

with tab_data:
    col_sel, col_det = st.columns([1, 2])
    
    with col_sel:
        st.subheader("Buscador")
        persona = st.selectbox("Seleccionar Empleado", df_filtered['NOMBRE COMPLETO'].unique())
    
    with col_det:
        if persona:
            # Obtener datos de la fila
            datos = df_filtered[df_filtered['NOMBRE COMPLETO'] == persona].iloc[0]
            
            st.markdown(f"### 👤 {datos['NOMBRE COMPLETO']}")
            st.caption(f"Cédula: {datos.get('CEDULA', '---')}")
            
            c1, c2 = st.columns(2)
            c1.info(f"**Cargo:** {datos.get('CARGO', '--')}")
            c2.success(f"**Sede:** {datos.get('SEDE', '--')}")
            
            st.markdown("#### Información de Contacto")
            st.write(f"📧 **Correo:** {datos.get('CORREO', 'No registrado')}")
            st.write(f"📱 **Celular:** {datos.get('CELULAR', 'No registrado')}")
            st.write(f"🏢 **Centro de Trabajo:** {datos.get('CENTRO TRABAJO', '--')}")
            

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
