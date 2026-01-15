import streamlit as st
import os

def get_secret(key, section=None):
    """
    Busca un secreto primero en st.secrets (Local)
    y si no existe, busca en Variables de Entorno (Servidor/Coolify).
    """
    try:
        if section:
            return st.secrets[section][key]
        return st.secrets[key]
    except (FileNotFoundError, KeyError):
        env_key = f"{section.upper()}_{key.upper()}" if section else key.upper()
        return os.environ.get(env_key)

def check_password():
    """
    Muestra el formulario de login y retorna True si la contraseña es correcta.
    Esta función ya NO se preocupa por los enlaces de evaluación.
    """
    if st.session_state.get("password_correct", False):
        return True

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
