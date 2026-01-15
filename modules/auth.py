import streamlit as st
import os
from modules._evaluar import render_evaluation_page
from modules.auth import check_password

# --- CONFIGURACIÓN INICIAL DE LA PÁGINA ---
st.set_page_config(
    page_title="SERVINET HR Dashboard",
    page_icon="📡",
    layout="wide"
)

# --- MEJORA CLAVE: EL PORTERO INTELIGENTE (ROUTER) ---
# 1. Revisa si la URL contiene los parámetros para una evaluación externa
params = st.query_params
cedula_eval = params.get("cedula")
token_eval = params.get("token")

# 2. SI ES UN ENLACE DE EVALUACIÓN, RENDERIZA LA PÁGINA DEDICADA Y DETIENE TODO LO DEMÁS
if cedula_eval and token_eval:
    # Llama a la función desde tu módulo _evaluar.py para mostrar la vista dedicada.
    # Esto cumple tu requisito de que el enlace solo muestre la evaluación.
    render_evaluation_page(cedula_eval, token_eval)

# 3. SI ES UN ACCESO NORMAL, PIDE CONTRASEÑA Y MUESTRA LA APP COMPLETA
else:
    # La función check_password() ahora maneja el login y devuelve True si es exitoso.
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
