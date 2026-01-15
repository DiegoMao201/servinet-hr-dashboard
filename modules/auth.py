import streamlit as st
import os
import pickle
import base64
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets"
]

@st.cache_resource(show_spinner="Conectando a los servicios de Google...")
def get_google_creds():
    """
    Función centralizada para obtener credenciales de Google.
    Cacheada como un recurso para no repetir el proceso en la misma sesión.
    """
    creds = None
    # Prioriza las variables de entorno (producción)
    token_b64 = os.environ.get("GOOGLE_TOKEN_PICKLE_B64")
    if token_b64:
        creds = pickle.loads(base64.b64decode(token_b64))
    # Si no, busca el archivo local (desarrollo)
    elif os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # Valida y refresca el token si es necesario
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Flujo para generar un nuevo token si no existe
            secret_b64 = os.environ.get("GOOGLE_CLIENT_SECRET_JSON_B64")
            if secret_b64:
                secret_json = base64.b64decode(secret_b64).decode("utf-8")
                with open("client_secret.json", "w", encoding="utf-8") as f:
                    f.write(secret_json)
            
            if not os.path.exists("client_secret.json"):
                st.error("Falta el archivo 'client_secret.json' para la autenticación de Google.")
                return None

            flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
            # Idealmente, se usa generar_token.py para esto, pero es un fallback
            creds = flow.run_console()
        
        # Guarda el nuevo token para futuras ejecuciones
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
            
    return creds

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
