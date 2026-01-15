import streamlit as st
import os
import base64

def get_secret(key, section=None):
    """
    Busca un secreto primero en st.secrets (Local)
    y si no existe, busca en Variables de Entorno (Servidor/Coolify).
    """
    # 1. Intenta leer desde secrets.toml (Local)
    try:
        if section:
            return st.secrets[section][key]
        return st.secrets[key]
    except (FileNotFoundError, KeyError):
        # 2. Si falla, busca en Variables de Entorno (Coolify)
        # Convertimos la clave a mayúsculas para seguir estándar (ej: admin -> ADMIN_PASSWORD)
        env_key = f"{section.upper()}_{key.upper()}" if section else key.upper()
        return os.environ.get(env_key)

def is_valid_evaluation_link():
    """Verifica si la URL actual es un enlace de evaluación válido."""
    try:
        params = st.query_params
        cedula = params.get("evaluar_cedula", [None])[0]
        token = params.get("token", [None])[0]

        if not cedula or not token:
            return False

        # Recreamos el token esperado para validarlo
        expected_token = base64.b64encode(str(cedula).encode()).decode()
        return token == expected_token
    except Exception:
        return False

def check_password():
    """
    Retorna True si el usuario está logueado o si accede mediante un enlace de evaluación válido.
    """
    # --- LÓGICA DE ACCESO INTELIGENTE ---
    # 1. Si el usuario ya está logueado en la sesión, permite el acceso.
    if st.session_state.get("password_correct", False):
        return True

    # 2. SI NO ESTÁ LOGUEADO, revisa si es un enlace de evaluación válido.
    if is_valid_evaluation_link():
        # Si es válido, le damos acceso para esta única vez y lo marcamos como logueado.
        st.session_state["password_correct"] = True
        return True

    # 3. Si no es ninguna de las anteriores, muestra el formulario de login normal.
    st.header("🔒 Acceso Restringido - SERVINET")
    password_input = st.text_input("Ingrese contraseña de acceso", type="password")

    if st.button("Ingresar"):
        correct_password = get_secret("admin", section="passwords")
        
        if correct_password and password_input == correct_password:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("❌ Contraseña incorrecta o error de configuración")
            
    return False
