import streamlit as st
import graphviz
import pandas as pd
from modules.database import get_employees

st.set_page_config(page_title="Estructura Organizacional", page_icon="🏢", layout="wide")

# --- ESTILOS CSS PERSONALIZADOS ---
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        border-left: 5px solid #0056b3;
        padding: 15px;
        border-radius: 5px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    .stGraphVizChart > svg {
        width: 100%;
        height: auto;
    }
</style>
""", unsafe_allow_html=True)

# --- CABECERA ---
col_head_1, col_head_2 = st.columns([3, 1])
with col_head_1:
    st.title("🏢 Ecosistema Organizacional SERVINET")
    st.markdown("**Visualización interactiva de talento humano y estructura de mando.**")
with col_head_2:
    if st.button("🔄 Actualizar Datos"):
        st.cache_data.clear()
        st.rerun()

# --- CARGA DE DATOS ---
with st.spinner("Conectando con la base de datos maestra..."):
    df = get_employees()

if df.empty:
    st.warning("⚠️ No se pudo cargar la base de datos. Verifica la conexión.")
    st.stop()

# --- FILTROS SIDEBAR ---
with st.sidebar:
    st.header("🔍 Filtros de Visualización")
    
    # Filtro Estado (Por defecto solo ACTIVO)
    estados_disponibles = list(df['ESTADO'].unique())
    estado_default = ["ACTIVO"] if "ACTIVO" in estados_disponibles else estados_disponibles
    filtro_estado = st.multiselect("Estado del empleado", estados_disponibles, default=estado_default)
    
    # Filtro Sede
    sedes = ["Todas"] + list(df['SEDE'].unique())
    filtro_sede = st.selectbox("Sede Operativa", sedes)

    st.markdown("---")
    st.info("💡 Usa estos filtros para enfocar el organigrama en áreas específicas.")

# --- APLICAR FILTROS ---
df_filtered = df[df['ESTADO'].isin(filtro_estado)]
if filtro_sede != "Todas":
    df_filtered = df_filtered[df_filtered['SEDE'] == filtro_sede]

# --- DASHBOARD DE MÉTRICAS (KPIs) ---
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

total_emp = len(df_filtered)
sedes_activas = df_filtered['SEDE'].nunique()
cargos_unicos = df_filtered['CARGO'].nunique()
# Calculo simple de promedio de edad si hay datos, sino 0
promedio_edad = 0 
# (Aquí podrías agregar lógica para calcular edad si tienes fecha nacimiento)

with kpi1:
    st.markdown(f"""<div class="metric-card"><h3>👥 {total_emp}</h3><p>Colaboradores Listados</p></div>""", unsafe_allow_html=True)
with kpi2:
    st.markdown(f"""<div class="metric-card"><h3>📍 {sedes_activas}</h3><p>Sedes Activas</p></div>""", unsafe_allow_html=True)
with kpi3:
    st.markdown(f"""<div class="metric-card"><h3>🛠️ {cargos_unicos}</h3><p>Cargos Distintos</p></div>""", unsafe_allow_html=True)
with kpi4:
    st.markdown(f"""<div class="metric-card"><h3>📅 {filtro_estado[0] if len(filtro_estado)==1 else "Mixto"}</h3><p>Estado Visualizado</p></div>""", unsafe_allow_html=True)

st.markdown("---")

# --- VISUALIZACIÓN DUAL (GRÁFICO + DETALLE) ---
tab1, tab2 = st.tabs(["📊 Vista Gráfica (Árbol)", "📋 Directorio Detallado"])

with tab1:
    # --- CONSTRUCCIÓN DEL GRAFO CON GRAPHVIZ ---
    graph = graphviz.Digraph()
    graph.attr(bgcolor='transparent')
    graph.attr(rankdir='TB', splines='ortho') # TB = Top to Bottom, Ortho = Lineas rectas
    graph.attr('node', shape='box', style='filled', fontname='Helvetica', penwidth='0')
    graph.attr('edge', color='#555555', arrowhead='vee')

    # Crear nodos
    for index, row in df_filtered.iterrows():
        nombre = str(row['NOMBRE COMPLETO'])
        cargo = str(row['CARGO'])
        sede = str(row['SEDE'])
        
        # Diseño del nodo (HTML-like labels para mejor estilo)
        # Diferenciamos colores según el nivel (Jefes vs Operativos)
        if "GERENTE" in cargo.upper() or "DIRECTOR" in cargo.upper():
            color = "#1f77b4" # Azul oscuro
            font_color = "white"
        elif "COORDINADOR" in cargo.upper() or "LIDER" in cargo.upper():
            color = "#aec7e8" # Azul claro
            font_color = "black"
        else:
            color = "#f0f2f6" # Gris claro
            font_color = "#31333F"

        label = f'''<
        <TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0">
        <TR><TD><B>{nombre}</B></TD></TR>
        <TR><TD><FONT POINT-SIZE="10">{cargo}</FONT></TD></TR>
        <TR><TD><FONT POINT-SIZE="8" COLOR="gray">{sede}</FONT></TD></TR>
        </TABLE>
        >'''
        
        graph.node(nombre, label=label, fillcolor=color, fontcolor=font_color)

        # Conexiones
        jefe = str(row['Jefe_Directo']).strip()
        # Solo dibujamos la línea si el jefe existe en la lista FILTRADA
        if jefe and jefe in df_filtered['NOMBRE COMPLETO'].values:
            graph.edge(jefe, nombre)

    st.graphviz_chart(graph, use_container_width=True)

with tab2:
    # --- BUSCADOR Y FICHA TÉCNICA ---
    col_search, col_card = st.columns([1, 2])
    
    with col_search:
        st.subheader("👤 Buscador de Talento")
        seleccionado = st.selectbox("Seleccione un colaborador para ver detalles:", df_filtered['NOMBRE COMPLETO'].unique())
    
    with col_card:
        if seleccionado:
            datos = df[df['NOMBRE COMPLETO'] == seleccionado].iloc[0]
            
            st.markdown(f"### Ficha Técnica: {datos['NOMBRE COMPLETO']}")
            st.caption(f"ID Ref: {datos['CEDULA']}")
            
            # Tarjeta de Datos
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"**🏢 Cargo:** {datos['CARGO']}")
                st.write(f"**📍 Sede:** {datos['SEDE']}")
                st.write(f"**🎯 Centro de Trabajo:** {datos['Centro Trabajo']}")
            with c2:
                st.write(f"**📧 Email:** {datos['CORREO']}")
                st.write(f"**📱 Celular:** {datos['CELULAR']}")
                st.write(f"**📅 Ingreso:** {datos['Fecha Inicio laboral/dd/mm/aaa']}")

            with st.expander("🔒 Ver Información Privada (RRHH)"):
                st.warning("Información Confidencial")
                st.write(f"**Dirección:** {datos['DIRECCIÓN DE RESIDENCIA']}")
                st.write(f"**Banco:** {datos['BANCO']} - {datos['CUENTA BANCOLOMBIA']}")
                st.write(f"**EPS:** {datos['Salud']} | **AFP:** {datos['Pensión']}")
                st.write(f"**Novedades Recientes:** {datos['NOVEDADES']}")
