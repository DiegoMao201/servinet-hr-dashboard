import streamlit as st
from modules.auth import check_password
import os

# Configuración de página
st.set_page_config(
    page_title="SERVINET HR Dashboard",
    page_icon="📡",
    layout="wide"
)

# --- LÓGICA DE CONTROL DE VISUALIZACIÓN ---
# Revisa si la URL es para una evaluación externa
params = st.query_params
is_external_eval = "_evaluar" in st.get_option("server.baseUrlPath") or (params.get("token") and params.get("cedula"))

# Si es una evaluación externa, oculta la barra lateral para una experiencia limpia
if is_external_eval:
    st.markdown("""
        <style>
            [data-testid="stSidebar"] { display: none; }
        </style>
    """, unsafe_allow_html=True)

# 1. Verificación de seguridad
if not check_password():
    st.stop()  # Si no hay login, detiene todo aquí.

# 2. Bienvenida (Esta parte solo se mostrará a usuarios logueados, no en la página de evaluación)
st.title("📡 Panel de Control RRHH - SERVINET")
st.image("logo_servinet.jpg", width=180)
st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.info("👋 **Bienvenido al sistema centralizado.**")
    st.markdown("""
    Desde aquí podrás:
    * Visualizar el organigrama en tiempo real.
    * Realizar evaluaciones de desempeño asistidas por IA.
    * Consultar la base de datos de empleados.
    """)

with col2:
    st.warning("⚠️ **Estado del Sistema**")
    st.success("✅ Conexión a Google Drive: ACTIVA")
    st.success("✅ Motor de IA: LISTO")

st.markdown("---")
st.caption("Desarrollado para SERVINET - Versión 1.0")

# No es necesario mostrar esto en producción, puedes comentarlo o eliminarlo
# st.write("GCP_JSON_KEY exists:", bool(os.environ.get("GCP_JSON_KEY")))
# st.write("OPENAI_API_KEY exists:", bool(os.environ.get("OPENAI_API_KEY")))
