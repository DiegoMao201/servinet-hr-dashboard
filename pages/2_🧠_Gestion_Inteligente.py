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
import time

# ==============================================================================
# 0. CONFIGURACIÓN Y ESTILOS
# ==============================================================================
st.set_page_config(page_title="Gestión IA", page_icon="🧠", layout="wide")

# CSS para limpiar la interfaz cuando entra un jefe externo
st.markdown("""
    <style>
    /* Oculta la barra lateral y el menú principal de Streamlit */
    [data-testid="stSidebar"], [data-testid="main-menu"] { display: none; }
    /* Ajusta el padding superior para que el contenido no quede pegado arriba */
    .main .block-container { padding-top: 2rem; }
    
    /* Estilo para la tarjeta del empleado en la vista externa */
    .employee-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #0056b3; /* Color primario del tema */
        margin-bottom: 20px;
    }
    .employee-name { font-size: 24px; font-weight: bold; color: #262730; }
    .employee-role { font-size: 18px; color: #555; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 1. FUNCIONES AUXILIARES
# ==============================================================================

def validar_acceso_externo():
    """Verifica si alguien entra con un link compartido válido."""
    params = st.query_params
    cedula_param = params.get("cedula", [None])[0]
    token_param = params.get("token", [None])[0]
    
    if cedula_param and token_param:
        try:
            # CORRECCIÓN: El token debe ser la cédula en bytes antes de codificar
            expected_token = base64.b64encode(str(cedula_param).encode('utf-8')).decode('utf-8')
            if token_param == expected_token:
                return str(cedula_param)
        except Exception:
            return None
    return None

def render_formulario_evaluacion(datos_empleado, context):
    """Renderiza el formulario de evaluación (Reutilizable para Admin y Jefe Externo)"""
    nombre = datos_empleado['NOMBRE COMPLETO']
    cargo = datos_empleado['CARGO']
    cedula = datos_empleado['CEDULA']

    st.markdown("### 📝 Formulario de Evaluación de Desempeño")
    st.info(f"Por favor, evalúa las competencias de **{nombre}** en su rol de **{cargo}**.")

    with st.spinner("🔄 Cargando dimensiones a evaluar..."):
        eval_form_data = generate_evaluation(cargo, context)

    if not eval_form_data.get("preguntas"):
        st.error("No se pudo cargar el formulario. Intenta recargar la página.")
        return

    with st.form(f"form_eval_{cedula}"):
        respuestas = {}
        st.markdown("---")
        
        for idx, pregunta in enumerate(eval_form_data.get("preguntas", [])):
            st.markdown(f"**{idx+1}. {pregunta.get('texto')}**")
            respuestas[f"preg_{idx}"] = st.radio(
                "Seleccione una opción:", 
                pregunta.get("opciones", []), 
                key=f"radio_{cedula}_{idx}", 
                label_visibility="collapsed",
                horizontal=True
            )
            st.markdown("<br>", unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("**Conclusiones Generales**")
        comentarios_evaluador = st.text_area(
            "Fortalezas y Áreas de Mejora:", 
            height=150,
            placeholder="Escribe aquí tus observaciones detalladas sobre el desempeño..."
        )
        
        enviado = st.form_submit_button("💾 GUARDAR Y FINALIZAR EVALUACIÓN", type="primary", use_container_width=True)

    if enviado:
        with st.spinner("Guardando evaluación en el sistema..."):
            contenido_evaluacion = {"respuestas": respuestas, "comentarios": comentarios_evaluador}
            save_content_to_memory(str(cedula), "EVALUACION", json.dumps(contenido_evaluacion, ensure_ascii=False))
            st.balloons()
            st.success("✅ ¡Excelente! La evaluación ha sido guardada correctamente. Ya puede cerrar esta ventana.")
            time.sleep(3)

# ==============================================================================
# 2. CARGA DE DATOS Y CONTEXTO
# ==============================================================================

@st.cache_data(ttl=600)
def load_initial_data():
    folder_id = get_or_create_manuals_folder()
    company_context = get_company_context(folder_id)
    return folder_id, company_context

manuals_folder_id, company_context = load_initial_data()
df = get_employees()

if df.empty:
    st.error("Error crítico: No se pudo conectar a la base de datos de empleados.")
    st.stop()

# ==============================================================================
# 3. ENRUTAMIENTO (ROUTER)
# ==============================================================================

cedula_externa = validar_acceso_externo()

if cedula_externa:
    # ---------------------------------------------------------
    # VISTA EXTERNA (JEFE / EVALUADOR) - SIN BARRAS LATERALES
    # ---------------------------------------------------------
    empleado_found = df[df['CEDULA'].astype(str) == cedula_externa]
    
    if not empleado_found.empty:
        datos_empleado = empleado_found.iloc[0]
        
        st.image("logo_servinet.jpg", width=100)
        st.markdown(f"""
            <div class="employee-card">
                <div class="employee-name">{datos_empleado['NOMBRE COMPLETO']}</div>
                <div class="employee-role">📌 Cargo: {datos_empleado['CARGO']}</div>
            </div>
        """, unsafe_allow_html=True)
        
        render_formulario_evaluacion(datos_empleado, company_context)
    else:
        st.error("❌ El enlace no es válido o el empleado ya no existe en la base de datos.")

else:
    # ---------------------------------------------------------
    # VISTA ADMINISTRADOR (RRHH) - CON INTERFAZ COMPLETA
    # ---------------------------------------------------------
    st.title("🧠 Gestión de Talento - SERVINET")
    st.markdown("Generación de perfiles, evaluaciones y planes de carrera.")

    empleados_lista = [""] + sorted(df['NOMBRE COMPLETO'].unique())
    seleccion = st.selectbox("👤 Seleccione un colaborador para gestionar:", empleados_lista)

    if seleccion:
        datos_empleado = df[df['NOMBRE COMPLETO'] == seleccion].iloc[0]
        cargo_empleado = datos_empleado['CARGO']
        cedula_empleado = datos_empleado['CEDULA']

        tab_manual, tab_eval, tab_resultados, tab_share = st.tabs(["📄 Manual de Funciones", "📝 Evaluación Interna", "📈 Resultados", "🔗 Link para WhatsApp"])

        with tab_manual:
            st.subheader(f"Manual de Funciones: {cargo_empleado}")
            force_regen = st.checkbox("Forzar nueva generación de manual", key=f"regen_{cedula_empleado}")
            manual_file_id = find_manual_in_drive(cargo_empleado, manuals_folder_id)

            if manual_file_id and not force_regen:
                st.success("✅ Manual encontrado en Drive.")
                pdf_bytes = download_manual_from_drive(manual_file_id)
                st.download_button("📥 Descargar Manual PDF", pdf_bytes, f"Manual_{cargo_empleado.replace(' ', '_')}.pdf", "application/pdf")
            else:
                if st.button("✨ Generar Manual con IA", key=f"gen_manual_{cedula_empleado}"):
                    with st.spinner("Generando documento..."):
                        perfil_html = generate_role_profile_by_sections(cargo_empleado, company_context)
                        
                        def get_section(html, keyword):
                            pattern = rf"{keyword}(.*?)(<div class=\"section-title\"|$)"
                            match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
                            return match.group(1).strip() if match else ""

                        now = datetime.datetime.now()
                        datos_plantilla = {
                            "empresa": "GRUPO SERVINET", "logo_url": os.path.abspath("logo_servinet.jpg"),
                            "codigo_doc": f"DOC-MF-{cedula_empleado}", "departamento": datos_empleado.get("DEPARTAMENTO", ""),
                            "version": "1.0", "vigencia": f"Año {now.year}", "fecha_emision": now.strftime("%d/%m/%Y"),
                            "empleado": seleccion, "cargo": cargo_empleado,
                            "objetivo_cargo": get_section(perfil_html, "🎯 Objetivo del Cargo"),
                            "funciones_principales": get_section(perfil_html, "📜 Funciones Principales"),
                            "procesos_clave": get_section(perfil_html, "🔄 Procesos Clave"),
                            "habilidades_blandas": get_section(perfil_html, "💡 Habilidades Blandas"),
                            "kpis_sugeridos": get_section(perfil_html, "📊 KPIs Sugeridos"),
                            "perfil_ideal": get_section(perfil_html, "🏅 Perfil Ideal"),
                            "observaciones": get_section(perfil_html, "📝 Observaciones"),
                        }
                        
                        pdf_filename = create_manual_pdf_from_template(datos_plantilla, cargo_empleado, empleado=seleccion)
                        upload_manual_to_drive(pdf_filename, folder_id=manuals_folder_id)
                        with open(pdf_filename, "rb") as f:
                            st.download_button("📥 Bajar Nuevo PDF", f.read(), os.path.basename(pdf_filename))
                        st.success("Manual generado y subido a Drive.")

        with tab_eval:
            st.warning("Estás en vista de Administrador. Si deseas enviar esto al jefe, usa la pestaña 'Link para WhatsApp'.")
            render_formulario_evaluacion(datos_empleado, company_context)

        with tab_resultados:
            st.header("Análisis de Resultados")
            contenido_guardado = get_saved_content(str(cedula_empleado), "EVALUACION")
            if contenido_guardado:
                if st.button("🧠 Analizar con IA", key=f"analizar_{cedula_empleado}"):
                    with st.spinner("Interpretando resultados..."):
                        analisis = analyze_results(contenido_guardado)
                        st.markdown(analisis, unsafe_allow_html=True)
            else:
                st.info("Aún no se ha completado la evaluación para este empleado.")

        with tab_share:
            st.header("📲 Enviar Evaluación Remota por WhatsApp")
            st.markdown("Genera un enlace seguro para que el Evaluador complete el formulario sin acceder al sistema completo.")

            token_seguro = base64.b64encode(str(cedula_empleado).encode('utf-8')).decode('utf-8')
            base_url = "https://servinet.datovatenexuspro.com" 
            
            # El enlace ahora apunta a esta misma página, que actuará como router
            url_evaluacion = f"{base_url}/2_🧠_Gestion_Inteligente?cedula={cedula_empleado}&token={token_seguro}"

            st.success("✅ ¡Enlace generado!")
            mensaje = (
                f"Hola, te envío el enlace para la Evaluación de Desempeño de *{seleccion}*.\n\n"
                f"Por favor ingresa al siguiente enlace para completarla (no requiere contraseña):\n"
                f"{url_evaluacion}\n\n"
                f"Gracias,\n*Gestión Humana - SERVINET*"
            )

            st.text_area("Mensaje a enviar:", value=mensaje, height=150)
            mensaje_encoded = urllib.parse.quote(mensaje)
            whatsapp_link = f"https://web.whatsapp.com/send?text={mensaje_encoded}"

            st.markdown(f'''
                <a href="{whatsapp_link}" target="_blank" style="
                    display: inline-block; text-align: center;
                    padding: 12px 20px; background-color: #25D366; color: white; 
                    text-decoration: none; border-radius: 8px; font-weight: bold;">
                    📤 Enviar por WhatsApp
                </a>
            ''', unsafe_allow_html=True)