import streamlit as st
from modules.database import get_employees
from modules.document_reader import get_company_context
from modules.ai_brain import generate_role_profile, generate_evaluation, analyze_results
from modules.drive_manager import (
    get_or_create_manuals_folder,
    find_manual_in_drive,
    download_manual_from_drive,
    upload_manual_to_drive
)
from modules.pdf_generator import create_manual_pdf
import plotly.figure_factory as ff
import os

st.set_page_config(page_title="Gestión IA", page_icon="🧠", layout="wide")

st.title("🧠 Talent AI - SERVINET")
st.markdown("Generación de perfiles, evaluaciones y planes de carrera basados en tus Manuales de Funciones.")

# 1. Cargar contexto (Leemos los PDFs y Words solo una vez)
if "company_context" not in st.session_state:
    with st.spinner("🤖 La IA está leyendo tus manuales y PDFs... (Esto toma unos segundos)"):
        try:
            st.session_state["company_context"] = get_company_context()
            st.success("¡Contexto cargado! La IA ya conoce a Servinet.")
        except Exception as e:
            st.error(f"Error leyendo manuales: {e}")
            st.stop()

# 2. Seleccionar Empleado
df = get_employees()
empleados = df['NOMBRE COMPLETO'].unique()
seleccion = st.selectbox("Seleccionar Colaborador:", empleados)

if seleccion:
    # Obtener datos del empleado
    datos = df[df['NOMBRE COMPLETO'] == seleccion].iloc[0]
    cargo = datos['CARGO']
    
    st.info(f"Analizando perfil para: **{seleccion}** - Cargo: **{cargo}**")
    
    tab1, tab2, tab3 = st.tabs(["📄 Hoja de Vida de Funciones", "📝 Evaluación IA", "📈 Resultados y Capacitación"])
    

    # --- TAB 1: PERFIL DE CARGO ---
    with tab1:
        st.write("Manual de Funciones generado por IA y almacenado en Drive.")
        manuals_folder_id = get_or_create_manuals_folder()
        manual_file_id = find_manual_in_drive(cargo, manuals_folder_id)
        force_regen = st.checkbox("Forzar nueva generación de manual (sobrescribe el anterior)", value=False)
        perfil_html = None

        if manual_file_id and not force_regen:
            st.success("Manual ya generado y guardado en Drive. Mostrando versión almacenada.")
            pdf_bytes = download_manual_from_drive(manual_file_id)
            st.download_button(
                label="📥 Descargar Manual PDF",
                data=pdf_bytes,
                file_name=f"Manual_{cargo.replace(' ', '_').upper()}.pdf",
                mime="application/pdf"
            )
        else:
            if st.button("✨ Generar Manual de Funciones Personalizado") or force_regen:
                with st.spinner("Redactando documento oficial..."):
                    perfil_html = generate_role_profile(cargo, st.session_state["company_context"], force=force_regen)
                    pdf_filename = create_manual_pdf(cargo, perfil_html, empleado=seleccion)
                    upload_manual_to_drive(pdf_filename, manuals_folder_id)
                    with open(pdf_filename, "rb") as f:
                        st.download_button(
                            label="📥 Descargar Manual PDF",
                            data=f.read(),
                            file_name=os.path.basename(pdf_filename),
                            mime="application/pdf"
                        )
                    st.success("Manual generado y guardado en Drive.")
                    # Limpia el archivo temporal
                    try:
                        os.remove(pdf_filename)
                    except Exception:
                        pass
                
    # --- TAB 2: EVALUACIÓN ---
    with tab2:
        st.write("Esta evaluación se genera en tiempo real según el manual de procesos.")
        if st.button("🚀 Iniciar Evaluación de Desempeño"):
            with st.spinner("Diseñando preguntas estratégicas..."):
                evaluacion = generate_evaluation(cargo, st.session_state["company_context"])
                st.session_state[f"eval_{seleccion}"] = evaluacion
        
        # Si ya generamos la evaluación, mostrar el formulario
        if f"eval_{seleccion}" in st.session_state:
            data_eval = st.session_state[f"eval_{seleccion}"]
            
            with st.form("form_evaluacion"):
                st.subheader("Competencias Técnicas")
                respuestas_tec = {}
                for p in data_eval["preguntas_tecnicas"]:
                    respuestas_tec[p] = st.text_area(p)
                
                st.subheader("Competencias Blandas")
                respuestas_soft = {}
                for p in data_eval["preguntas_blandas"]:
                    respuestas_soft[p] = st.text_area(p)
                
                submitted = st.form_submit_button("✅ Finalizar y Analizar")
                
                if submitted:
                    # Guardamos todo en un objeto para que la IA lo analice
                    st.session_state["respuestas_finales"] = {
                        "empleado": seleccion,
                        "cargo": cargo,
                        "tecnicas": respuestas_tec,
                        "blandas": respuestas_soft
                    }
                    st.success("Respuestas guardadas. Ve a la pestaña de Resultados.")

    # --- TAB 3: ANÁLISIS ---
    with tab3:
        if "respuestas_finales" in st.session_state:
            if st.button("🧠 Analizar con IA (Nivel Experto)"):
                with st.spinner("La IA está diagnosticando estrés, competencias y creando plan de formación..."):
                    analisis = analyze_results(st.session_state["respuestas_finales"])
                    st.markdown(analisis)
                    
                    # Ejemplo de tareas de capacitación
                    tasks = [
                        dict(Task="Curso de Atención al Cliente", Start='2024-07-01', Finish='2024-07-05', Resource='Capacitación'),
                        dict(Task="Certificación Técnica", Start='2024-07-10', Finish='2024-07-15', Resource='Técnico'),
                        dict(Task="Evaluación Final", Start='2024-07-20', Finish='2024-07-21', Resource='Evaluación')
                    ]

                    fig = ff.create_gantt(tasks, index_col='Resource', show_colorbar=True, group_tasks=True)
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Primero debes completar la evaluación en la pestaña anterior.")
