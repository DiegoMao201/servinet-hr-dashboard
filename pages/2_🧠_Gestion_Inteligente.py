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
from modules.pdf_generator import create_manual_pdf_from_template
import os
import pandas as pd

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

force_regen = st.checkbox("Forzar nueva generación de manual (sobrescribe el anterior)", value=False)

tab1, tab2 = st.tabs(["📄 Manual de Funciones", "📝 Evaluación de Desempeño"])

with tab1:
    if seleccion:
        datos = df[df['NOMBRE COMPLETO'] == seleccion].iloc[0]
        cargo = datos['CARGO']
        manuals_folder_id = get_or_create_manuals_folder()
        manual_file_id = find_manual_in_drive(cargo, manuals_folder_id)

        st.subheader(f"Manual de Funciones para: {cargo}")
        st.markdown(f"**Colaborador:** {seleccion}  \n**Sede:** {datos.get('SEDE', '--')}  \n**Departamento:** {datos.get('SEDE', '--')}")

        if manual_file_id and not force_regen:
            st.success("✅ Manual encontrado en Drive para este cargo.")
            pdf_bytes = download_manual_from_drive(manual_file_id)
            st.download_button(
                label="📥 Descargar Manual PDF",
                data=pdf_bytes,
                file_name=f"Manual_{cargo.replace(' ', '_').upper()}.pdf",
                mime="application/pdf"
            )
            st.info("Si deseas actualizar el manual, activa la opción de regeneración.")
        else:
            st.warning("⚠️ No existe un manual para este cargo o se va a regenerar.")
            if st.button("✨ Generar Manual de Funciones Personalizado"):
                with st.spinner("Redactando documento oficial..."):
                    datos_manual = {
                        "empresa": "GRUPO SERVINET",
                        "logo_url": "https://gruposervinet.com.co/wp-content/uploads/2023/07/logo-servinet.png",
                        "codigo_doc": f"DOC-MF-{str(datos.get('CEDULA', '001'))}",
                        "departamento": datos.get("SEDE", ""),
                        "titulo": f"Manual de Funciones: {cargo}",
                        "descripcion": f"Manual profesional para el cargo {cargo} en {datos.get('SEDE', '')}.",
                        "version": "1.0",
                        "vigencia": "Enero 2025 - Diciembre 2025",
                        "fecha_emision": pd.Timestamp.now().strftime("%d/%m/%Y"),
                        "perfil_html": generate_role_profile(cargo, st.session_state["company_context"], force=force_regen),
                        "primary_color": "#003d6e",
                        "secondary_color": "#00a8e1",
                        "accent_color": "#ffb81c",
                        "empleado": seleccion,
                        "cargo": cargo,
                    }
                    pdf_filename = create_manual_pdf_from_template(datos_manual, cargo, empleado=seleccion)
                    upload_manual_to_drive(pdf_filename, folder_id=manuals_folder_id)
                    with open(pdf_filename, "rb") as f:
                        st.download_button(
                            label="📥 Descargar Manual PDF",
                            data=f.read(),
                            file_name=os.path.basename(pdf_filename),
                            mime="application/pdf"
                        )
                    st.success("Manual generado y guardado en Drive.")
                    try:
                        os.remove(pdf_filename)
                    except Exception:
                        pass

with tab2:
    st.write("Aquí podrás realizar la evaluación de desempeño y ver el plan de capacitación generado por IA.")
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
