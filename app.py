import streamlit as st
import os
from modules._evaluar import render_evaluation_page
from modules.clima import render_clima_page  # <--- Importa tu función de clima
from modules.auth import check_password

# --- CONFIGURACIÓN INICIAL DE LA PÁGINA ---
st.set_page_config(
    page_title="SERVINET HR Dashboard",
    page_icon="📡",
    layout="wide"
)

# --- ROUTER INTELIGENTE ---
params = st.query_params
cedula_eval = params.get("cedula")
token_eval = params.get("token")
cedula_clima = params.get("clima")
token_clima = params.get("token")

# 1. Si es enlace de clima laboral, muestra solo la encuesta de clima
if cedula_clima and token_clima:
    render_clima_page(cedula_clima, token_clima)

# 2. Si es enlace de evaluación, muestra solo la evaluación
elif cedula_eval and token_eval:
    render_evaluation_page(cedula_eval, token_eval)

# 3. Si es acceso normal, pide contraseña y muestra la app completa
else:
    if check_password():
        # --- PÁGINA DE BIENVENIDA (Solo se muestra si la contraseña es correcta) ---
        st.title("📡 Panel de Control RRHH - SERVINET")
        
        if os.path.exists("logo_servinet.jpg"):
            st.image("logo_servinet.jpg", width=180)
        
        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            st.info("👋 **Bienvenido al sistema centralizado.**")
            st.markdown("""
            Seleccione una opción del menú de la izquierda para comenzar.
            *   Visualizar el organigrama en tiempo real.
            *   Realizar evaluaciones de desempeño asistidas por IA.
            *   Consultar la base de datos de empleados.
            """)
        with col2:
            st.warning("⚠️ **Estado del Sistema**")
            st.success("✅ Conexión a Google Drive: ACTIVA")
            st.success("✅ Motor de IA: LISTO")

        st.markdown("---")
        st.caption("Desarrollado para SERVINET - Versión 1.0")
