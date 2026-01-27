import streamlit as st
import pandas as pd
import json
import base64
from modules.database import get_employees, save_content_to_memory, get_saved_content
from modules.ai_brain import generate_evaluation
import datetime

def render_evaluation_page(cedula_empleado, token):
    """
    Vista dedicada y profesional para el jefe.
    """
    # --- OCULTAR MENÚ Y ENCABEZADO ---
    st.markdown("""
        <style>
            [data-testid="stSidebar"], [data-testid="main-menu"], [data-testid="stHeader"] { display: none; }
            .main .block-container { max-width: 700px; margin: auto; padding-top: 2rem; }
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

    # --- DATOS DEL EMPLEADO ---
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

    # --- CARGAR FORMULARIO DESDE MEMORIA ---
    # MEJORA: ID normalizado y consistente
    id_evaluacion = f"EVAL_FORM_{str(cedula_empleado).strip()}"
    
    with st.spinner("🔍 Cargando formulario de evaluación..."):
        eval_form_json = get_saved_content(id_evaluacion, "EVAL_FORM")
    
    if eval_form_json:
        try:
            eval_form_data = json.loads(eval_form_json)
            st.success("✅ Formulario cargado correctamente.")
        except json.JSONDecodeError:
            st.error("Error al decodificar el formulario.")
            eval_form_data = None
    else:
        # Fallback: generar uno nuevo
        st.warning("No se encontró un formulario pre-generado. Creando uno nuevo...")
        eval_form_data = generate_evaluation(datos_empleado['CARGO'], "")
        if eval_form_data.get("preguntas"):
            save_content_to_memory(id_evaluacion, "EVAL_FORM", json.dumps(eval_form_data, ensure_ascii=False))
        else:
            st.error("Error crítico: No se pudo generar el formulario.")
            st.stop()

    if not eval_form_data.get("preguntas"):
        st.error("La IA no pudo generar el formulario. Recargue la página."); st.stop()

    # --- FORMULARIO DE EVALUACIÓN ---
    with st.form(f"form_eval_externa_{cedula_empleado}"):
        respuestas = {}
        for idx, pregunta in enumerate(eval_form_data.get("preguntas", [])):
            respuestas[f"preg_{idx}"] = st.radio(f"{idx+1}. {pregunta.get('texto')}", pregunta.get("opciones"), horizontal=True)
        
        comentarios_evaluador = st.text_area("Comentarios del Evaluador (Fortalezas y Áreas de Mejora):")
        enviado = st.form_submit_button("✅ Finalizar y Guardar Evaluación", use_container_width=True, type="primary")

    if enviado:
        with st.spinner("Guardando respuestas y procesando..."):
            # --- GUARDAR EN MEMORIA_IA ---
            id_unico = f"EVAL_RESP_{empleado['cedula']}"
            contenido = {
                "metadata": empleado,
                "respuestas": respuestas_usuario,
                "comentarios": comentarios,
                "fecha_registro": datetime.datetime.now().isoformat()
            }
            from modules.database import save_content_to_memory
            save_content_to_memory(id_unico, "EVALUACION", json.dumps(contenido, ensure_ascii=False))

            # --- GUARDAR EN 2_evaluaciones ---
            try:
                from modules._evaluar import calcular_puntaje
                from modules.database import connect_to_drive, SPREADSHEET_ID
                client = connect_to_drive()
                spreadsheet = client.open_by_key(SPREADSHEET_ID)
                sheet = spreadsheet.worksheet("2_evaluaciones")
                nombre = empleado.get("NOMBRE COMPLETO", "") or empleado.get("nombre", "")
                cargo = empleado.get("CARGO", "") or empleado.get("cargo", "")
                fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                tipo_evaluador = "Jefe"
                puntaje = calcular_puntaje(respuestas_usuario)
                respuestas_json = json.dumps(respuestas_usuario, ensure_ascii=False)
                sheet.append_row([
                    nombre, cargo, fecha, tipo_evaluador, puntaje, respuestas_json, comentarios
                ])
                st.success("🎉 ¡Evaluación registrada con éxito!")
                st.balloons()
            except Exception as e:
                st.error(f"Error guardando en hoja de evaluaciones: {e}")

    # --- ANÁLISIS DE ERRORES ---
    if not eval_form_json:
        st.warning(f"No se encontró un formulario pre-generado para ID: {id_evaluacion} y tipo_doc: EVAL_FORM")
        # Opcional: muestra todos los IDs existentes para depuración
        worksheet = init_memory()
        if worksheet:
            data = worksheet.get_all_records()
            ids = [row['ID_UNICO'] for row in data if row.get('TIPO_DOC') == "EVAL_FORM"]
            st.info(f"Formularios existentes en memoria: {ids}")

def calcular_puntaje(respuestas):
    """
    Calcula el puntaje global de la evaluación.
    Asume que las respuestas son valores numéricos (Likert 1-5).
    Retorna el promedio en porcentaje (0-100).
    """
    valores = []
    for v in respuestas.values():
        try:
            val = int(str(v)[0])  # Si la opción es "5 - Siempre", toma el número
            valores.append(val)
        except Exception:
            continue
    if not valores:
        return 0
    return round(sum(valores) / (len(valores) * 5) * 100, 2)