import streamlit as st
from modules.database import get_employees, save_content_to_memory, get_saved_content
from modules.document_reader import get_company_context
from modules.ai_brain import generate_role_profile_by_sections, generate_evaluation, analyze_results
from modules.drive_manager import (
    get_or_create_manuals_folder,
    find_manual_in_drive,
    download_manual_from_drive,
    upload_manual_to_drive
)
from modules.pdf_generator import create_manual_pdf_from_template
import os
import pandas as pd
import datetime
import json
import base64
import urllib.parse

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Gestión IA", page_icon="🧠", layout="wide")

if os.path.exists("logo_servinet.jpg"):
    st.image("logo_servinet.jpg", width=120)

st.title("🧠 Talent AI - SERVINET")
st.markdown("Generación de perfiles, evaluaciones y planes de carrera basados en tus Manuales de Funciones.")

# --- CARGA DE DATOS Y CONTEXTO ---
manuals_folder_id = get_or_create_manuals_folder()

if "company_context" not in st.session_state:
    with st.spinner("🤖 La IA está leyendo tus manuales..."):
        st.session_state["company_context"] = get_company_context(manuals_folder_id)
        if st.session_state["company_context"]:
            st.success("¡Contexto cargado!")
        else:
            st.warning("No se encontraron manuales.")

df = get_employees()
if df.empty:
    st.error("No se pudieron cargar los datos de los empleados.")
    st.stop()

# --- LÓGICA PARA ENLACES COMPARTIDOS ---
params = st.query_params
empleado_cedula_link = params.get("cedula")
token_link = params.get("token")
empleado_seleccionado_por_link = None

if empleado_cedula_link and token_link:
    try:
        expected_token = base64.b64encode(str(empleado_cedula_link).encode()).decode()
        if token_link == expected_token:
            empleado_encontrado = df[df['CEDULA'].astype(str) == str(empleado_cedula_link)]
            if not empleado_encontrado.empty:
                empleado_seleccionado_por_link = empleado_encontrado.iloc[0]['NOMBRE COMPLETO']
    except Exception as e:
        st.error(f"Error validando el enlace: {e}")

# --- SELECCIÓN DE EMPLEADO CON DETECCIÓN DE CAMBIO ---
st.markdown("---")
st.subheader("Selección de Colaborador")

if empleado_seleccionado_por_link:
    st.info(f"Evaluando a: **{empleado_seleccionado_por_link}** (Link)")
    seleccion = empleado_seleccionado_por_link
else:
    empleados_lista = [""] + sorted(df['NOMBRE COMPLETO'].unique())
    seleccion = st.selectbox(
        "Seleccione un colaborador:", 
        empleados_lista,
        key="selector_empleado_principal"
    )

# --- MEJORA CLAVE: DETECTAR CAMBIO DE EMPLEADO Y LIMPIAR CACHÉ ---
if seleccion:
    # Obtener cédula del empleado seleccionado
    datos_empleado = df[df['NOMBRE COMPLETO'] == seleccion].iloc[0]
    cedula_empleado = str(datos_empleado['CEDULA']).strip()
    cargo_empleado = datos_empleado['CARGO']

    # Si el empleado cambió, limpiar todos los estados relacionados
    if "ultima_cedula_seleccionada" not in st.session_state or st.session_state["ultima_cedula_seleccionada"] != cedula_empleado:
        # Limpiar estados del empleado anterior
        keys_to_clear = [k for k in st.session_state.keys() if any(x in k for x in ["eval_form_", "analisis_", "manual_"])]
        for key in keys_to_clear:
            st.session_state.pop(key, None)
        
        # Actualizar el registro de último empleado
        st.session_state["ultima_cedula_seleccionada"] = cedula_empleado
        st.rerun()  # Forzar recarga para reflejar el cambio

    # --- PESTAÑAS ---
    if empleado_seleccionado_por_link:
        tabs = st.tabs(["📝 Evaluación"])
        tab_manual, tab_eval, tab_resultados, tab_share = (None, tabs[0], None, None)
    else:
        tabs = st.tabs(["📄 Manual de Funciones", "📝 Evaluación", "📈 Resultados y Plan de Acción", "🔗 Compartir por WhatsApp"])
        tab_manual, tab_eval, tab_resultados, tab_share = tabs

    # --- PESTAÑA 1: MANUAL DE FUNCIONES ---
    if tab_manual:
        with tab_manual:
            st.header(f"Manual de Funciones para: {cargo_empleado}")
            st.markdown(f"**Colaborador:** {seleccion} | **Departamento:** {datos_empleado.get('DEPARTAMENTO', '--')}")
            
            force_regen = st.checkbox("Forzar nueva generación", key=f"regen_{cedula_empleado}")
            manual_file_id = find_manual_in_drive(cargo_empleado, manuals_folder_id)

            if manual_file_id and not force_regen:
                st.success("✅ Manual encontrado en Drive")
                pdf_bytes = download_manual_from_drive(manual_file_id)
                st.download_button("📥 Descargar Manual PDF", pdf_bytes, f"Manual_{cargo_empleado.replace(' ', '_')}.pdf", "application/pdf")
            else:
                st.warning("⚠️ No existe manual o se forzará regeneración")
                if st.button("✨ Generar Manual con IA", key=f"gen_manual_{cedula_empleado}"):
                    with st.spinner("Redactando documento..."):
                        perfil_html_completo = generate_role_profile_by_sections(cargo_empleado, st.session_state["company_context"])
                        
                        now = datetime.datetime.now()
                        logo_path = os.path.abspath("logo_servinet.jpg") if os.path.exists("logo_servinet.jpg") else None
                        
                        datos_plantilla = {
                            "empresa": "GRUPO SERVINET", 
                            "logo_url": logo_path,
                            "codigo_doc": f"DOC-MF-{cedula_empleado}", 
                            "departamento": datos_empleado.get("DEPARTAMENTO", ""),
                            "version": "1.0", 
                            "vigencia": f"Año {now.year}", 
                            "fecha_emision": now.strftime("%d/%m/%Y"),
                            "cargo": cargo_empleado,
                            "empleado": seleccion,
                            "perfil_html": perfil_html_completo
                        }
                        
                        pdf_filename = create_manual_pdf_from_template(datos_plantilla, cargo_empleado, empleado=seleccion)
                        upload_manual_to_drive(pdf_filename, folder_id=manuals_folder_id)
                        
                        with open(pdf_filename, "rb") as f:
                            st.download_button("📥 Descargar Manual Generado", f.read(), os.path.basename(pdf_filename), "application/pdf")
                        st.success("Manual generado y guardado")

    # --- PESTAÑA 2: EVALUACIÓN ---
    if tab_eval:
        with tab_eval:
            st.header(f"Evaluación de Desempeño: {seleccion} ({cargo_empleado})")
            st.info("La IA genera una evaluación profesional.")

            id_evaluacion = f"EVAL_FORM_{cedula_empleado}"
            
            col_btn1, col_btn2 = st.columns([3, 1])
            with col_btn2:
                if st.button("🔄 Nueva Eval", help="Genera nuevo formulario"):
                    st.session_state.pop(f"eval_form_{cedula_empleado}", None)
                    st.rerun()
            
            # Buscar o generar formulario
            if f"eval_form_{cedula_empleado}" not in st.session_state:
                with st.spinner("🔍 Buscando formulario..."):
                    eval_form_json = get_saved_content(id_evaluacion, "EVAL_FORM")
                
                if eval_form_json:
                    try:
                        eval_form_data = json.loads(eval_form_json)
                        st.session_state[f"eval_form_{cedula_empleado}"] = eval_form_data
                        st.success("✅ Formulario cargado desde memoria")
                    except json.JSONDecodeError:
                        eval_form_data = None
                else:
                    with st.spinner("🧠 Generando formulario..."):
                        eval_form_data = generate_evaluation(cargo_empleado, st.session_state["company_context"])
                        if eval_form_data.get("preguntas"):
                            save_content_to_memory(id_evaluacion, "EVAL_FORM", json.dumps(eval_form_data, ensure_ascii=False))
                            st.session_state[f"eval_form_{cedula_empleado}"] = eval_form_data
                            st.success("✨ Formulario generado y guardado")
                        else:
                            st.error("Error generando formulario")
            
            eval_form_data = st.session_state.get(f"eval_form_{cedula_empleado}")
            
            if not eval_form_data or not eval_form_data.get("preguntas"):
                st.error("No se pudo cargar el formulario")
            else:
                with st.form(f"form_eval_{cedula_empleado}"):
                    respuestas = {}
                    st.markdown("#### Cuestionario de Evaluación")
                    for idx, pregunta in enumerate(eval_form_data.get("preguntas", [])):
                        respuestas[f"preg_{idx}"] = st.radio(
                            f"{idx+1}. {pregunta.get('texto')}", 
                            pregunta.get("opciones"), 
                            key=f"preg_{idx}_{cedula_empleado}", 
                            horizontal=True
                        )
                    
                    comentarios_evaluador = st.text_area(
                        "Comentarios del Evaluador:", 
                        key=f"comentarios_{cedula_empleado}"
                    )
                    enviado = st.form_submit_button("💾 Guardar Evaluación", use_container_width=True)

                if enviado:
                    with st.spinner("Guardando..."):
                        id_respuestas = f"EVAL_RESP_{cedula_empleado}"
                        contenido_evaluacion = {
                            "respuestas": respuestas, 
                            "comentarios": comentarios_evaluador,
                            "fecha": datetime.datetime.now().isoformat()
                        }
                        save_content_to_memory(
                            id_respuestas, 
                            "EVALUACION", 
                            json.dumps(contenido_evaluacion, ensure_ascii=False)
                        )
                        st.success("✅ Evaluación registrada")
                        st.balloons()

    # --- PESTAÑA 3: RESULTADOS ---
    if tab_resultados:
        with tab_resultados:
            st.header(f"Análisis de Desempeño: {seleccion}")
            id_respuestas = f"EVAL_RESP_{cedula_empleado}"
            contenido_guardado = get_saved_content(id_respuestas, "EVALUACION")
            
            if contenido_guardado:
                st.info("Mostrando análisis de la última evaluación")
                
                if st.button("🔄 Refrescar Análisis"):
                    st.session_state.pop(f"analisis_{cedula_empleado}", None)
                    st.rerun()

                if f"analisis_{cedula_empleado}" not in st.session_state:
                    with st.spinner("Analizando..."):
                         st.session_state[f"analisis_{cedula_empleado}"] = analyze_results(contenido_guardado)

                st.markdown(st.session_state[f"analisis_{cedula_empleado}"], unsafe_allow_html=True)
            else:
                st.warning("⚠️ No hay evaluación guardada para este empleado")

    # --- PESTAÑA 4: COMPARTIR ---
    if tab_share:
        with tab_share:
            st.header("📲 Compartir Evaluación por WhatsApp")
            st.info("Genera un enlace único para evaluación remota")

            token_seguro = base64.b64encode(str(cedula_empleado).encode()).decode()
            base_url = "https://servinet.datovatenexuspro.com"
            url_evaluacion = f"{base_url}/?cedula={cedula_empleado}&token={token_seguro}"

            mensaje = (
                f"Hola, soy CAROLINA PEREZ. Te envío el link para evaluar a *{seleccion}*.\n\n"
                f"Completa todos los campos y guarda al finalizar. ¡Gracias!\n\n"
                f"Enlace: {url_evaluacion}"
            )
            mensaje_encoded = urllib.parse.quote(mensaje)
            whatsapp_link = f"https://web.whatsapp.com/send?text={mensaje_encoded}"

            st.markdown(f"**Enlace para {seleccion}:**")
            st.code(url_evaluacion, language="text")
            st.markdown(f'''
                <a href="{whatsapp_link}" target="_blank" style="
                    display: inline-block;
                    padding: 12px 20px;
                    background-color: #25D366;
                    color: white;
                    text-decoration: none;
                    border-radius: 8px;
                    font-weight: bold;">
                    💬 Abrir en WhatsApp
                </a>
            ''', unsafe_allow_html=True)