import streamlit as st
import os
import pandas as pd
import datetime
import json
import base64
import urllib.parse
import time
from modules.database import get_employees, save_content_to_memory, get_saved_content, connect_to_drive, SPREADSHEET_ID
from modules.document_reader import get_company_context
from modules.ai_brain import generate_role_profile_by_sections, generate_evaluation, analyze_results
from modules.drive_manager import (
    get_or_create_manuals_folder,
    find_manual_in_drive,
    download_manual_from_drive,
    upload_manual_to_drive,
    set_file_public
)
from modules.pdf_generator import (
    create_manual_pdf_from_template, 
    extraer_mision, extraer_funciones, extraer_educacion, extraer_experiencia,
    extraer_conocimientos, extraer_idiomas, extraer_competencias, extraer_kpis
)
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

# --- CONFIGURACIÓN INICIAL DE LA PÁGINA ---
st.set_page_config(
    page_title="Gestión IA - SERVINET", 
    page_icon="🧠", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILOS CSS PERSONALIZADOS ---
st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #f0f2f6; border-radius: 4px 4px 0px 0px; gap: 1px; padding-top: 10px; padding-bottom: 10px; }
    .stTabs [aria-selected="true"] { background-color: #FFFFFF; border-bottom: 2px solid #4B8BBE; }
    </style>
""", unsafe_allow_html=True)

# --- GESTIÓN DE ESTADO (SESSION STATE) ---
if "user_session" not in st.session_state:
    st.session_state.user_session = {
        "cedula": None,
        "nombre": None,
        "cargo": None,
        "departamento": None
    }

def reset_employee_state():
    """Limpia variables específicas del empleado anterior para evitar mezcla de datos."""
    keys_to_clear = [key for key in st.session_state.keys() if any(x in key for x in ["eval_form_", "analisis_", "manual_view_"])]
    for key in keys_to_clear:
        del st.session_state[key]

# --- BARRA LATERAL: CONFIGURACIÓN Y CONTEXTO ---
with st.sidebar:
    if os.path.exists("logo_servinet.jpg"):
        st.image("logo_servinet.jpg", width=180)
    
    st.title("⚙️ Panel de Control")
    st.markdown("---")
    st.subheader("📚 Base de Conocimiento (Drive)")
    manuals_folder_id = get_or_create_manuals_folder()
    if st.button("🔄 Recargar Manuales de Drive", help="Lee nuevamente todos los archivos en la carpeta de Drive"):
        with st.status("Releyendo archivos de Drive...", expanded=True) as status:
            st.write("Conectando a Drive...")
            st.session_state["company_context"] = get_company_context(manuals_folder_id)
            status.update(label="¡Contexto actualizado!", state="complete", expanded=False)
            st.toast("Base de conocimiento actualizada correctamente.", icon="✅")
    if "company_context" not in st.session_state:
        with st.spinner("Inicializando cerebro de IA..."):
            st.session_state["company_context"] = get_company_context(manuals_folder_id)
    context_preview = st.session_state.get("company_context", "")
    if context_preview:
        st.success(f"Contexto cargado: {len(context_preview)} caracteres.")
        with st.expander("Ver qué sabe la IA hoy"):
            st.text_area("Extracto del contexto", context_preview[:1000] + "...", height=150, disabled=True)
    else:
        st.error("⚠️ No se pudo cargar el contexto. Verifique la conexión a Drive.")

# --- LÓGICA DE ENLACES COMPARTIDOS (QUERY PARAMS) ---
params = st.query_params
link_cedula = params.get("cedula")
link_token = params.get("token")
link_employee_name = None

df = get_employees()
if df.empty:
    st.error("🚨 Error Crítico: No se pudo conectar a la base de datos de empleados.")
    st.stop()

if link_cedula and link_token:
    try:
        expected_token = base64.b64encode(str(link_cedula).encode()).decode()
        if link_token == expected_token:
            empleado_encontrado = df[df['CEDULA'].astype(str) == str(link_cedula)]
            if not empleado_encontrado.empty:
                link_employee_name = empleado_encontrado.iloc[0]['NOMBRE COMPLETO']
    except Exception as e:
        st.toast(f"Error en enlace compartido: {e}", icon="⚠️")

# --- CABECERA PRINCIPAL ---
st.title("🧠 Talent AI - SERVINET")
st.markdown("Plataforma inteligente para la gestión de **Perfiles, Evaluaciones y Planes de Carrera**.")

# --- SELECCIÓN DE COLABORADOR ---
st.markdown("### 👤 Selección de Colaborador")
lista_nombres = sorted(df['NOMBRE COMPLETO'].unique())
index_seleccion = 0
if link_employee_name and link_employee_name in lista_nombres:
    index_seleccion = lista_nombres.index(link_employee_name)
    st.info(f"🔗 Accediendo vía enlace directo para: **{link_employee_name}**")

seleccion_nombre = st.selectbox(
    "Busque o seleccione un colaborador:",
    options=lista_nombres,
    index=index_seleccion,
    key="selector_empleado",
    on_change=reset_employee_state,
    help="Escribe para buscar..."
)

if seleccion_nombre:
    datos_empleado = df[df['NOMBRE COMPLETO'] == seleccion_nombre].iloc[0]
    cedula_actual = str(datos_empleado['CEDULA']).strip()
    cargo_actual = datos_empleado['CARGO']
    depto_actual = datos_empleado.get('DEPARTAMENTO', 'General')
    empleado = {
        "nombre": seleccion_nombre,
        "cedula": cedula_actual,
        "cargo": cargo_actual,
        "departamento": depto_actual
    }
else:
    st.warning("Por favor seleccione un empleado para comenzar.")
    st.stop()

st.markdown("---")

# --- PESTAÑAS DE FUNCIONALIDAD ---
if link_employee_name:
    tabs = st.tabs(["📝 Evaluación 360°"])
    tab_manual, tab_eval, tab_resultados, tab_share = (None, tabs[0], None, None)
else:
    tabs = st.tabs(["📄 Manual de Funciones", "📝 Evaluación de Desempeño", "📈 Resultados y Análisis", "🔗 Compartir"])
    tab_manual, tab_eval, tab_resultados, tab_share = tabs

# ========== PESTAÑA 1: MANUAL DE FUNCIONES ==========
if tab_manual:
    with tab_manual:
        col_info, col_actions = st.columns([2, 1])
        with col_info:
            st.subheader(f"Manual: {empleado['cargo']}")
            st.caption(f"Departamento: {empleado['departamento']} | Cédula: {empleado['cedula']}")
        manual_id = find_manual_in_drive(empleado['cargo'], manuals_folder_id)
        if manual_id:
            st.success("✅ Documento existente en Drive")
            col_view, col_regen = st.columns(2)
            with col_view:
                if st.button("👁️ Ver / Descargar Manual Actual", key=f"btn_ver_{empleado['cedula']}"):
                    pdf_bytes = download_manual_from_drive(manual_id)
                    if pdf_bytes:
                        base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
                        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="500" type="application/pdf"></iframe>'
                        st.markdown(pdf_display, unsafe_allow_html=True)
                        st.download_button(
                            label="📥 Descargar PDF",
                            data=pdf_bytes,
                            file_name=f"Manual_{empleado['cargo']}.pdf",
                            mime="application/pdf"
                        )
        else:
            st.info("ℹ️ Aún no existe un manual para este cargo.")

        st.markdown("#### 🤖 Generador con IA")
        with st.expander("🛠️ Configuración avanzada del Prompt (Instrucciones a la IA)", expanded=True):
            prompt_adicional = st.text_area(
                "Instrucciones específicas antes de generar:",
                value="",
                placeholder="Ejemplo: 'Asegúrate de incluir funciones específicas sobre manejo de maquinaria pesada' o 'Usa un tono formal y enfócate en habilidades blandas'.",
                help="Lo que escribas aquí se enviará a la IA junto con los manuales de la empresa para personalizar este documento."
            )
        col_gen_btn, col_empty = st.columns([1, 2])
        with col_gen_btn:
            modo_regenerar = "Regenerar Manual (Sobreescribir)" if manual_id else "✨ Generar Manual con IA"
            if st.button(modo_regenerar, type="primary", key=f"gen_btn_{empleado['cedula']}"):
                progress_text = "Iniciando motor de IA..."
                my_bar = st.progress(0, text=progress_text)
                try:
                    contexto_total = st.session_state["company_context"]
                    if prompt_adicional:
                        contexto_total += f"\n\n[INSTRUCCIÓN ADICIONAL DEL USUARIO]: {prompt_adicional}"
                    my_bar.progress(25, text="Analizando manuales y estructura...")
                    perfil_html = generate_role_profile_by_sections(empleado['cargo'], contexto_total)
                    my_bar.progress(60, text="Maquetando documento PDF...")
                    logo_path = os.path.abspath("logo_servinet.jpg") if os.path.exists("logo_servinet.jpg") else None
                    now = datetime.datetime.now()
                    datos_pdf = {
                        "empresa": "GRUPO SERVINET",
                        "logo_url": logo_path,
                        "codigo_doc": f"MF-{empleado['cedula']}-{now.year}",
                        "departamento": empleado['departamento'],
                        "version": "1.0 IA",
                        "vigencia": str(now.year),
                        "fecha_emision": now.strftime("%d/%m/%Y"),
                        "cargo": empleado['cargo'],
                        "perfil_html": perfil_html
                    }
                    cargo_dict = {
                        "nombre": empleado['cargo'],
                        "area": empleado['departamento'],
                        "jefe_inmediato": empleado.get('jefe_directo', ''),
                        "subordinados": empleado.get('subordinados', ''),
                        "modalidad": empleado.get('modalidad', ''),
                        "sede": empleado.get('sede', ''),
                        "mision": extraer_mision(perfil_html),  # Puedes extraerlo del HTML generado
                        "funciones": extraer_funciones(perfil_html),  # idem
                        "educacion": extraer_educacion(perfil_html),
                        "experiencia": extraer_experiencia(perfil_html),
                        "conocimientos": extraer_conocimientos(perfil_html),
                        "idiomas": extraer_idiomas(perfil_html),
                        "competencias": extraer_competencias(perfil_html),
                        "kpis": extraer_kpis(perfil_html)
                    }
                    doc_dict = {
                        "codigo": f"MF-{empleado['cedula']}-{now.year}",
                        "version": "1.0 IA",
                        "fecha": now.strftime("%d/%m/%Y"),
                    }
                    template_dir = os.path.join(os.path.dirname(__file__), "../modules")
                    env = Environment(loader=FileSystemLoader(template_dir))
                    template = env.get_template("manual_template.html")

                    html_content = template.render(
                        cargo=cargo_dict,
                        doc=doc_dict,
                        logo_url="logo_servinet.jpg",
                        perfil_html=perfil_html  # <-- Asegúrate de pasar esto
                    )
                    pdf_filename = f"Manual_{cargo_dict['nombre'].replace(' ', '_')}.pdf"
                    HTML(string=html_content, base_url=template_dir).write_pdf(pdf_filename)

                    my_bar.progress(85, text="Subiendo a Google Drive...")
                    folder_id = get_or_create_manuals_folder()
                    file_id = upload_manual_to_drive(pdf_filename, folder_id)
                    set_file_public(file_id)
                    my_bar.progress(100, text="¡Completado!")
                    time.sleep(1)
                    my_bar.empty()
                    st.success(f"Manual generado correctamente para {empleado['cargo']}.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error durante la generación: {e}")

# ========== PESTAÑA 2: EVALUACIÓN ==========
if tab_eval:
    with tab_eval:
        st.header(f"Evaluación: {empleado['nombre']}")
        eval_key = f"eval_form_{empleado['cedula']}"
        id_db_eval = f"EVAL_FORM_{empleado['cedula']}"
        col_refresh, col_space = st.columns([1, 4])
        with col_refresh:
            if st.button("🔄 Generar Nuevo Cuestionario", help="Olvida el formulario actual y crea uno nuevo con IA"):
                if eval_key in st.session_state:
                    del st.session_state[eval_key]
                st.rerun()
        if eval_key not in st.session_state:
            saved_json = get_saved_content(id_db_eval, "EVAL_FORM")
            if saved_json:
                try:
                    st.session_state[eval_key] = json.loads(saved_json)
                    st.toast("Formulario cargado de memoria.", icon="📂")
                except:
                    st.session_state[eval_key] = None
            if not st.session_state.get(eval_key):
                with st.spinner(f"🧠 La IA está diseñando preguntas específicas para {empleado['cargo']}..."):
                    try:
                        nueva_eval = generate_evaluation(empleado['cargo'], st.session_state["company_context"])
                        if nueva_eval:
                            st.session_state[eval_key] = nueva_eval
                            save_content_to_memory(id_db_eval, "EVAL_FORM", json.dumps(nueva_eval, ensure_ascii=False))
                    except Exception as e:
                        st.error(f"Error generando evaluación: {e}")
        datos_eval = st.session_state.get(eval_key)
        if datos_eval and "preguntas" in datos_eval:
            with st.form(key=f"form_eval_render_{empleado['cedula']}"):
                st.markdown("### 📋 Cuestionario de Desempeño")
                respuestas_usuario = {}
                for i, p in enumerate(datos_eval["preguntas"]):
                    st.markdown(f"**{i+1}. {p.get('texto', 'Pregunta sin texto')}**")
                    opciones = p.get('opciones', ["1", "2", "3", "4", "5"])
                    respuestas_usuario[f"p_{i}"] = st.radio(
                        "Seleccione una opción:",
                        options=opciones,
                        key=f"radio_{empleado['cedula']}_{i}",
                        horizontal=True,
                        label_visibility="collapsed"
                    )
                    st.divider()
                comentarios = st.text_area("💬 Observaciones finales del evaluador:", height=100)
                enviado = st.form_submit_button("💾 Guardar Evaluación Completa", use_container_width=True, type="primary")

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
                        import json
                        save_content_to_memory(id_unico, "EVALUACION", json.dumps(contenido, ensure_ascii=False))

                        # --- GUARDAR EN 2_evaluaciones ---
                        try:
                            from modules._evaluar import calcular_puntaje
                            from modules.database import connect_to_drive, SPREADSHEET_ID
                            client = connect_to_drive()
                            spreadsheet = client.open_by_key(SPREADSHEET_ID)
                            sheet = spreadsheet.worksheet("2_evaluaciones")
                            # Extrae los datos principales
                            nombre = empleado.get("NOMBRE COMPLETO", "") or empleado.get("nombre", "")
                            cargo = empleado.get("CARGO", "") or empleado.get("cargo", "")
                            fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            tipo_evaluador = "Jefe"  # O el tipo que corresponda
                            puntaje = calcular_puntaje(respuestas_usuario)
                            respuestas_json = json.dumps(respuestas_usuario, ensure_ascii=False)
                            sheet.append_row([
                                nombre, cargo, fecha, tipo_evaluador, puntaje, respuestas_json, comentarios
                            ])
                            st.success("🎉 ¡Evaluación registrada con éxito!")
                            st.balloons()
                        except Exception as e:
                            st.error(f"Error guardando en hoja de evaluaciones: {e}")
                else:
                        st.warning("No se pudo cargar el formulario de evaluación. Intente regenerarlo.")

# ========== PESTAÑA 3: RESULTADOS ==========
if tab_resultados:
    with tab_resultados:
        st.header(f"Resultados: {empleado['nombre']}")
        id_resp = f"EVAL_RESP_{empleado['cedula']}"
        raw_eval = get_saved_content(id_resp, "EVALUACION")
        if raw_eval:
            col_kpi1, col_kpi2 = st.columns(2)
            eval_data = json.loads(raw_eval)
            fecha_eval = eval_data.get("fecha_registro", "")[:10]
            with col_kpi1:
                st.info(f"📅 Última evaluación: {fecha_eval}")
            analysis_key = f"analisis_{empleado['cedula']}"
            if st.button("🔄 Actualizar Análisis IA"):
                if analysis_key in st.session_state:
                    del st.session_state[analysis_key]
                st.rerun()
            if analysis_key not in st.session_state:
                with st.chat_message("assistant"):
                    with st.spinner("Analizando fortalezas y debilidades..."):
                        resultado_analisis = analyze_results(raw_eval)
                        st.session_state[analysis_key] = resultado_analisis
            st.markdown("---")
            st.markdown(st.session_state[analysis_key], unsafe_allow_html=True)
        else:
            st.warning("⚠️ Aún no se ha realizado ninguna evaluación para este colaborador.")
            st.markdown("Vaya a la pestaña **'Evaluación de Desempeño'** para completar una.")

# ========== PESTAÑA 4: COMPARTIR ==========
if tab_share:
    with tab_share:
        st.header("📲 Enviar Evaluación Remota")
        st.markdown("Genere un enlace seguro para que el jefe realice la evaluación de desempeño de su colaborador.")

        col_link, col_qr = st.columns([2, 1])
        with col_link:
            import urllib.parse
            token_seguro = base64.b64encode(str(empleado['cedula']).encode()).decode()
            base_url = "https://servinet.datovatenexuspro.com"
            link_final = f"{base_url}/?cedula={empleado['cedula']}&token={token_seguro}"
            link_final_encoded = urllib.parse.quote(link_final, safe='')

            nombre_subordinado = empleado['nombre']
            nombre_jefe = df[df['NOMBRE COMPLETO'] == nombre_subordinado].iloc[0].get('JEFE_DIRECTO', 'Jefe no asignado')

            mensaje_ws = (
                f"👋 Hola {nombre_jefe},%0A%0A"
                f"Te invitamos cordialmente a realizar la evaluación de desempeño de tu colaborador *{nombre_subordinado}* en SERVINET.%0A"
                "Tu retroalimentación es fundamental para el crecimiento y desarrollo del equipo.%0A%0A"
                "Por favor ingresa al siguiente enlace seguro y completa el formulario de evaluación:%0A"
                f"{link_final}%0A%0A"
                "¡Gracias por tu compromiso y liderazgo! 🌟"
            )
            mensaje_encoded = urllib.parse.quote(mensaje_ws)

            st.markdown(f"""
                <a href="https://web.whatsapp.com/send?text={mensaje_encoded}" target="_blank">
                    <button style="
                        background-color:#25D366; 
                        color:white; 
                        border:none; 
                        padding:10px 20px; 
                        border-radius:5px; 
                        font-size:16px; 
                        cursor:pointer;
                        display: flex;
                        align-items: center;
                        gap: 10px;">
                        <span style="font-size: 20px;">📱</span> Enviar por WhatsApp al jefe
                    </button>
                </a>
            """, unsafe_allow_html=True)
        with col_qr:
            st.info("💡 Tip: Copia el enlace y envíalo por correo si prefieres.")

if enviado:
    with st.spinner("Guardando respuestas..."):
        # Guardar en MEMORIA_IA
        save_content_to_memory(
            id_respuestas, 
            "EVALUACION", 
            json.dumps(contenido_evaluacion, ensure_ascii=False)
        )
        # Guardar en 2_evaluaciones
        try:
            from modules._evaluar import calcular_puntaje
            from modules.database import connect_to_drive, SPREADSHEET_ID
            client = connect_to_drive()
            spreadsheet = client.open_by_key(SPREADSHEET_ID)
            sheet = spreadsheet.worksheet("2_evaluaciones")
            # Extrae los datos principales
            nombre = datos_empleado.get("NOMBRE COMPLETO", "") or datos_empleado.get("nombre", "")
            cargo = datos_empleado.get("CARGO", "") or datos_empleado.get("cargo", "")
            fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            tipo_evaluador = "Jefe"  # O el tipo que corresponda
            puntaje = calcular_puntaje(respuestas)
            respuestas_json = json.dumps(respuestas, ensure_ascii=False)
            comentarios = comentarios_evaluador
            sheet.append_row([
                nombre, cargo, fecha, tipo_evaluador, puntaje, respuestas_json, comentarios
            ])
        except Exception as e:
            st.error(f"Error guardando en hoja de evaluaciones: {e}")
        st.success("🎉 ¡Evaluación registrada con éxito!")
        st.balloons()

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