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
import re
import datetime
import json
import base64
import urllib.parse

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Gestión IA", page_icon="🧠", layout="wide")

# Verificar si existe el logo antes de mostrarlo para evitar errores
if os.path.exists("logo_servinet.jpg"):
    st.image("logo_servinet.jpg", width=120)
else:
    st.warning("⚠️ No se encontró el archivo 'logo_servinet.jpg'.")

st.title("🧠 Talent AI - SERVINET")
st.markdown("Generación de perfiles, evaluaciones y planes de carrera basados en tus Manuales de Funciones.")

# --- CARGA DE DATOS Y CONTEXTO ---
manuals_folder_id = get_or_create_manuals_folder()

if "company_context" not in st.session_state:
    with st.spinner("🤖 La IA está leyendo tus manuales y PDFs... (Esto toma unos segundos)"):
        st.session_state["company_context"] = get_company_context(manuals_folder_id)
        if st.session_state["company_context"]:
            st.success("¡Contexto cargado! La IA ya conoce a Servinet.")
        else:
            st.warning("No se encontraron manuales para crear el contexto. La IA funcionará con conocimiento general.")

df = get_employees()
if df.empty:
    st.error("No se pudieron cargar los datos de los empleados.")
    st.stop()

# --- LÓGICA PARA ENLACES COMPARTIDOS ---
# Ajuste para compatibilidad con versiones recientes de Streamlit
params = st.query_params
empleado_cedula_link = params.get("cedula")  # Corregido para coincidir con el link generado
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

# --- SELECCIÓN DE EMPLEADO (INTERFAZ PRINCIPAL) ---
st.markdown("---")
st.subheader("Selección de Colaborador")

# Si se accedió por link, pre-seleccionamos al empleado
if empleado_seleccionado_por_link:
    st.info(f"Evaluando a: **{empleado_seleccionado_por_link}** (Iniciado por enlace compartido)")
    seleccion = empleado_seleccionado_por_link
else:
    empleados_lista = [""] + sorted(df['NOMBRE COMPLETO'].unique())
    seleccion = st.selectbox("Seleccione un colaborador para gestionar:", empleados_lista)

# --- FLUJO PRINCIPAL ---
if seleccion:
    # OBTENER DATOS DEL EMPLEADO
    datos_empleado = df[df['NOMBRE COMPLETO'] == seleccion].iloc[0]
    cargo_empleado = datos_empleado['CARGO']
    cedula_empleado = datos_empleado['CEDULA']

    # Definir pestañas
    tab_titles = ["📄 Manual de Funciones", "📝 Evaluación", "📈 Resultados y Plan de Acción", "🔗 Compartir por WhatsApp"]
    
    # Si se accedió por link, solo mostramos la pestaña de evaluación
    if empleado_seleccionado_por_link:
        tabs = st.tabs([tab_titles[1]]) # Solo mostrar pestaña de evaluación
        tab_manual, tab_eval, tab_resultados, tab_share = (None, tabs[0], None, None)
    else:
        tabs = st.tabs(tab_titles)
        tab_manual, tab_eval, tab_resultados, tab_share = tabs

    # --- PESTAÑA 1: MANUAL DE FUNCIONES ---
    if tab_manual:
        with tab_manual:
            st.header(f"Manual de Funciones para: {cargo_empleado}")
            st.markdown(f"**Colaborador:** {seleccion} | **Departamento:** {datos_empleado.get('DEPARTAMENTO', '--')}")
            
            force_regen = st.checkbox("Forzar nueva generación de manual (sobrescribe el anterior)", key=f"regen_{cedula_empleado}")
            manual_file_id = find_manual_in_drive(cargo_empleado, manuals_folder_id)

            if manual_file_id and not force_regen:
                st.success("✅ Manual encontrado en Drive para este cargo.")
                pdf_bytes = download_manual_from_drive(manual_file_id)
                st.download_button("📥 Descargar Manual PDF", pdf_bytes, f"Manual_{cargo_empleado.replace(' ', '_')}.pdf", "application/pdf")
            else:
                st.warning("⚠️ No existe un manual para este cargo o se forzará la regeneración.")
                if st.button("✨ Generar Manual de Funciones con IA", key=f"gen_manual_{cedula_empleado}"):
                    with st.spinner("Redactando documento oficial con IA... (Esto puede tardar un minuto)"):
                        # La IA ahora genera un bloque de HTML con todas las secciones
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
                            # MEJORA: Pasamos el bloque de HTML completo a la plantilla
                            "perfil_html": perfil_html_completo
                        }
                        
                        pdf_filename = create_manual_pdf_from_template(datos_plantilla, cargo_empleado, empleado=seleccion)
                        upload_manual_to_drive(pdf_filename, folder_id=manuals_folder_id)
                        
                        with open(pdf_filename, "rb") as f:
                            st.download_button("📥 Descargar Manual PDF Generado", f.read(), os.path.basename(pdf_filename), "application/pdf")
                        st.success("Manual generado y guardado en Drive.")

    # --- PESTAÑA 2: EVALUACIÓN DE DESEMPEÑO ---
    if tab_eval:
        with tab_eval:
            st.header(f"Evaluación de Desempeño para: {seleccion} ({cargo_empleado})")
            st.info("La IA genera una evaluación profesional. El jefe directo debe completarla y guardar los cambios.")

            # MEJORA CLAVE: Lógica de "Generar y Guardar" o "Cargar Existente"
            id_evaluacion = f"EVAL_FORM_{str(cedula_empleado).strip()}"
            
            # 1. Buscar si el formulario de evaluación ya existe en la memoria
            eval_form_json = get_saved_content(id_evaluacion, "EVAL_FORM")
            
            if eval_form_json:
                # Si existe, lo cargamos
                eval_form_data = json.loads(eval_form_json)
                st.success("✅ Formulario de evaluación cargado desde la memoria.")
            else:
                # Si no existe, lo generamos y lo guardamos inmediatamente
                with st.spinner("🧠 Creando y guardando un nuevo formulario de evaluación único..."):
                    eval_form_data = generate_evaluation(cargo_empleado, st.session_state["company_context"])
                    if eval_form_data.get("preguntas"):
                        save_content_to_memory(id_evaluacion, "EVAL_FORM", json.dumps(eval_form_data))
                        contenido_guardado = get_saved_content(id_evaluacion, "EVAL_FORM")
                        if contenido_guardado:
                            st.info("✅ Formulario guardado correctamente en memoria.")
                        else:
                            st.error("❌ No se pudo guardar el formulario en memoria.")
                        st.success("✨ Nuevo formulario de evaluación generado y guardado para este empleado.")
                    else:
                        st.error("La IA no pudo generar el formulario. Inténtalo de nuevo.")
            
            if not eval_form_data.get("preguntas"):
                st.error("No se pudo cargar o generar el formulario de evaluación.")
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
                    
                    comentarios_evaluador = st.text_area("Comentarios del Evaluador (Fortalezas y Áreas de Mejora):", key=f"comentarios_{cedula_empleado}")
                    enviado = st.form_submit_button("💾 Guardar Evaluación", use_container_width=True)

                if enviado:
                    with st.spinner("Guardando respuestas..."):
                        # Guardamos las RESPUESTAS con un ID diferente
                        id_respuestas = f"EVAL_RESP_{cedula_empleado}"
                        contenido_evaluacion = {"respuestas": respuestas, "comentarios": comentarios_evaluador}
                        save_content_to_memory(str(cedula_empleado), "EVALUACION", json.dumps(contenido_evaluacion, ensure_ascii=False))
                        st.success("✅ Evaluación registrada correctamente. Ahora puedes ver el análisis en la pestaña 'Resultados y Plan de Acción'.")
                        st.balloons()

    # --- PESTAÑA 3: RESULTADOS Y PLAN DE ACCIÓN ---
    if tab_resultados:
        with tab_resultados:
            st.header(f"Análisis de Desempeño: {seleccion}")
            contenido_guardado = get_saved_content(str(cedula_empleado), "EVALUACION")
            if contenido_guardado:
                st.info("Mostrando el análisis de la última evaluación guardada para este empleado.")
                
                # Botón para refrescar análisis
                if st.button("🔄 Refrescar Análisis con IA"):
                    st.session_state.pop(f"analisis_{cedula_empleado}", None)

                if f"analisis_{cedula_empleado}" not in st.session_state:
                    with st.spinner("La IA está analizando los resultados..."):
                         st.session_state[f"analisis_{cedula_empleado}"] = analyze_results(contenido_guardado)

                st.markdown(st.session_state[f"analisis_{cedula_empleado}"], unsafe_allow_html=True)
            else:
                st.warning("⚠️ No hay una evaluación guardada para este empleado. Por favor, completa y guarda una en la pestaña 'Evaluación'.")

    # --- PESTAÑA 4: COMPARTIR POR WHATSAPP ---
    if tab_share:
        with tab_share:
            st.header("📲 Compartir Evaluación por WhatsApp")
            st.info("Genera un enlace único y aislado para que el jefe directo complete la evaluación de forma remota.")

            # Token seguro basado en la cédula
            token_seguro = base64.b64encode(str(cedula_empleado).encode()).decode()
            base_url = "https://servinet.datovatenexuspro.com"  # Cambia por tu dominio real

            # El link apunta a la raíz con los parámetros
            url_evaluacion = f"{base_url}/?cedula={cedula_empleado}&token={token_seguro}"

            mensaje = (
                f"Hola, soy CAROLINA PEREZ. Te envío el link para realizar la evaluación de desempeño de *{seleccion}*.\n\n"
                f"Por favor, completa todos los campos y guarda los cambios al finalizar. ¡Gracias!\n\n"
                f"Enlace: {url_evaluacion}"
            )
            mensaje_encoded = urllib.parse.quote(mensaje)
            whatsapp_link = f"https://web.whatsapp.com/send?text={mensaje_encoded}"

            st.markdown(f"**Enlace de evaluación para {seleccion}:**")
            st.code(url_evaluacion, language="text")
            st.markdown(f'''
                <a href="{whatsapp_link}" target="_blank" style="
                    display: inline-block;
                    padding: 12px 20px;
                    background-color: #25D366;
                    color: white;
                    text-decoration: none;
                    border-radius: 8px;
                    font-weight: bold;
                    text-align: center;">
                    💬 Abrir en WhatsApp Web
                </a>
            ''', unsafe_allow_html=True)
            st.success("Haz clic en el botón para abrir WhatsApp Web con el mensaje y el enlace listos para ser enviados.")