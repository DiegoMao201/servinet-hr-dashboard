import streamlit as st

def check_password():
    """Retorna True si el usuario está logueado correctamente."""
    
    # Si ya está validado, no pedir contraseña
    if st.session_state.get("password_correct", False):
        return True

    # Mostrar input de contraseña
    st.header("🔒 Acceso Restringido - SERVINET")
    password_input = st.text_input("Ingrese contraseña de acceso", type="password")

    if st.button("Ingresar"):
        # Verifica contra los secrets
        if password_input == st.secrets["passwords"]["admin"]:
            st.session_state["password_correct"] = True
            st.rerun() # Recarga la página
        else:
            st.error("❌ Contraseña incorrecta")
            
    return False
