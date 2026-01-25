import streamlit as st
import base64
import datetime
from modules.database import get_employees, connect_to_drive, SPREADSHEET_ID

def render_clima_page(cedula, token):
    # --- OCULTAR MENÚ Y ENCABEZADO ---
    st.markdown("""
        <style>
            [data-testid="stSidebar"], [data-testid="main-menu"], [data-testid="stHeader"] { display: none; }
            .main .block-container { max-width: 600px; margin: auto; padding-top: 2rem; }
            body { background: linear-gradient(135deg, #e0e7ff 0%, #f0fdf4 100%); }
        </style>
    """, unsafe_allow_html=True)

    # --- VALIDACIÓN DEL ENLACE ---
    try:
        expected_token = base64.b64encode(str(cedula).encode()).decode()
        if token != expected_token:
            st.error("❌ Token de seguridad inválido. El enlace puede haber expirado o sido alterado.")
            st.stop()
    except Exception:
        st.error("❌ Error al validar el enlace.")
        st.stop()

    # --- DATOS DEL EMPLEADO ---
    df = get_employees()
    if df.empty:
        st.error("No se pudo conectar con la base de datos de empleados."); st.stop()

    empleado_data = df[df['CEDULA'].astype(str) == str(cedula)]
    if empleado_data.empty:
        st.error("Empleado no encontrado."); st.stop()

    datos = empleado_data.iloc[0]
    st.image("logo_servinet.jpg", width=120)
    st.title("🌤️ Encuesta de Clima Laboral")
    st.markdown(f"""
    <div style="background: #fff; border-radius: 12px; padding: 18px 28px; margin-bottom: 18px; box-shadow: 0 4px 24px rgba(60,60,120,0.08);">
        <h3 style="margin-bottom: 0.5em;">👤 {datos['NOMBRE COMPLETO']}</h3>
        <p style="margin:0; color:#3b82f6;"><b>Cargo:</b> {datos.get('CARGO','')}</p>
        <p style="margin:0; color:#64748b;"><b>Departamento:</b> {datos.get('DEPARTAMENTO','')}</p>
    </div>
    """, unsafe_allow_html=True)

    preguntas = [
        "¿Te sientes valorado en tu equipo?",
        "¿Recomendarías Servinet como lugar de trabajo?",
        "¿Sientes pertenencia con la empresa?",
        "¿Cómo calificarías el ambiente laboral?",
        "¿Sientes que tu opinión es escuchada?",
        "¿Te sientes motivado para dar lo mejor de ti?",
        "¿Consideras que tienes oportunidades de crecimiento?",
        "¿Cómo calificarías la comunicación interna?",
        "¿Te sientes apoyado por tus líderes?",
        "¿Qué mejorarías en el ambiente laboral? (opcional)"
    ]
    respuestas = {}
    with st.form("clima_form"):
        for p in preguntas[:-1]:
            respuestas[p] = st.slider(p, 0, 10, 5, key=p)
        respuestas[preguntas[-1]] = st.text_area(preguntas[-1], key="mejora")
        enviado = st.form_submit_button("Enviar encuesta", use_container_width=True)
    if enviado:
        client = connect_to_drive()
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        sheet = spreadsheet.worksheet("4_clima_laboral")
        sheet.append_row([
            datos['NOMBRE COMPLETO'],
            datos.get('CEDULA', ''),
            datos.get('CARGO', ''),
            datos.get('DEPARTAMENTO', ''),
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            *[respuestas[p] for p in preguntas]
        ])
        st.success("¡Encuesta registrada! Gracias por tu honestidad y participación.")
        st.balloons()