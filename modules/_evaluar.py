import streamlit as st
import pandas as pd
import json
import base64
from modules.database import get_employees, save_content_to_memory
from modules.ai_brain import generate_evaluation

def render_evaluation_page(cedula_empleado, token):
    """
    Esta función dibuja la página de evaluación completa.
    """
    # --- OCULTAR LA INTERFAZ DE STREAMLIT ---
    st.markdown("""
        <style>
            [data-testid="stSidebar"], [data-testid="main-menu"] { display: none; }
            .main .block-container { padding-top: 2rem; }
        </style>
    """, unsafe_allow_html=True)

    st.image("logo_servinet.jpg", width=120)
    st.title("Evaluación de Desempeño - SERVINET")

    # --- VALIDACIÓN DEL ENLACE ---
    try:
        expected_token = base64.b64encode(str(cedula_empleado).encode()).decode()
        if token != expected_token:
            st.error("❌ Token de seguridad inválido. El enlace puede haber expirado o sido alterado.")
            st.stop()
    except Exception:
        st.error("❌ Error al validar el enlace.")
        st.stop()

    # --- OBTENER DATOS Y MOSTRAR FORMULARIO ---
    df = get_employees()
    if df.empty:
        st.error("No se pudo conectar con la base de datos de empleados."); st.stop()

    empleado_data = df[df['CEDULA'].astype(str) == str(cedula_empleado)]
    if empleado_data.empty:
        st.error("Empleado no encontrado."); st.stop()

    datos_empleado = empleado_data.iloc[0]
    st.header(f"Evaluando a: {datos_empleado['NOMBRE COMPLETO']}")
    st.subheader(f"Cargo: {datos_empleado['CARGO']}")
    st.info("Por favor, complete todas las preguntas y guarde los cambios al finalizar.")
    st.markdown("---")

    with st.spinner("🧠 Generando formulario de evaluación..."):
        eval_form_data = generate_evaluation(datos_empleado['CARGO'], "")

    if not eval_form_data.get("preguntas"):
        st.error("La IA no pudo generar el formulario. Recargue la página."); st.stop()

    with st.form(f"form_eval_externa_{cedula_empleado}"):
        respuestas = {}
        for idx, pregunta in enumerate(eval_form_data.get("preguntas", [])):
            respuestas[f"preg_{idx}"] = st.radio(f"{idx+1}. {pregunta.get('texto')}", pregunta.get("opciones"), horizontal=True)
        
        comentarios_evaluador = st.text_area("Comentarios del Evaluador (Fortalezas y Áreas de Mejora):")
        enviado = st.form_submit_button("✅ Finalizar y Guardar Evaluación", use_container_width=True)

    if enviado:
        with st.spinner("Guardando respuestas..."):
            contenido_evaluacion = {"respuestas": respuestas, "comentarios": comentarios_evaluador}
            save_content_to_memory(str(cedula_empleado), "EVALUACION", json.dumps(contenido_evaluacion, ensure_ascii=False))
            st.success("🎉 ¡Evaluación registrada con éxito! Gracias. Ya puede cerrar esta ventana.")
            st.balloons()