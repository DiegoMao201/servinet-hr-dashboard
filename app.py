import streamlit as st

# Configuración de página
st.set_page_config(
    page_title="SERVINET HR Dashboard",
    page_icon="📡",
    layout="wide"
)

# --- BIENVENIDA (Página principal) ---
st.title("📡 Panel de Control RRHH - SERVINET")
st.image("logo_servinet.jpg", width=180)
st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    st.info("👋 **Bienvenido al sistema centralizado.**")
    st.markdown("""
    Seleccione una opción del menú de la izquierda para comenzar.
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
