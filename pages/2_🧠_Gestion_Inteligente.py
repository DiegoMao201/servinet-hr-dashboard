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
import re

st.set_page_config(page_title="Gestión IA", page_icon="🧠", layout="wide")

st.image("logo_servinet.jpg", width=120)
st.title("🧠 Talent AI - SERVINET")
st.markdown("Generación de perfiles, evaluaciones y planes de carrera basados en tus Manuales de Funciones.")

manuals_folder_id = "1nmKGvJusOG13cePPwTfrYSxrPwXgwEcZ"

if "company_context" not in st.session_state:
    with st.spinner("🤖 La IA está leyendo tus manuales y PDFs... (Esto toma unos segundos)"):
        try:
            st.session_state["company_context"] = get_company_context(manuals_folder_id)
            st.success("¡Contexto cargado! La IA ya conoce a Servinet.")
        except Exception as e:
            st.error(f"Error leyendo manuales: {e}")
            st.stop()

df = get_employees()
empleados = df['NOMBRE COMPLETO'].unique()
seleccion = st.selectbox("Seleccionar Colaborador:", empleados)

force_regen = st.checkbox("Forzar nueva generación de manual (sobrescribe el anterior)", value=False)

tab1, tab2, tab3 = st.tabs(["📄 Manual de Funciones", "📝 Evaluación de Desempeño", "📊 Resultados"])

def get_section(html, keyword):
    pattern = rf"{keyword}(.*?)(<h2|<div class=\"section-title\"|$)"
    match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else ""

with tab1:
    if seleccion:
        datos = df[df['NOMBRE COMPLETO'] == seleccion].iloc[0]
        cargo = datos['CARGO']
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
                    perfil_html = generate_role_profile(cargo, st.session_state["company_context"], force=force_regen)
                    datos_manual = {
                        "empresa": "GRUPO SERVINET",
                        "logo_url": os.path.abspath("logo_servinet.jpg"),
                        "codigo_doc": f"DOC-MF-{str(datos.get('CEDULA', '001'))}",
                        "departamento": datos.get("DEPARTAMENTO", ""),
                        "titulo": f"Manual de Funciones: {cargo}",
                        "descripcion": f"Manual profesional para el cargo {cargo} en {datos.get('SEDE', '')}.",
                        "version": "1.0",
                        "vigencia": "Enero 2025 - Diciembre 2025",
                        "fecha_emision": pd.Timestamp.now().strftime("%d/%m/%Y"),
                        "empleado": seleccion,
                        "cargo": cargo,
                        "objetivo_cargo": get_section(perfil_html, "🎯"),
                        "funciones_principales": get_section(perfil_html, "📜"),
                        "procesos_clave": get_section(perfil_html, "🔄"),
                        "habilidades_blandas": get_section(perfil_html, "💡"),
                        "kpis_sugeridos": get_section(perfil_html, "📊"),
                        "perfil_ideal": get_section(perfil_html, "🏅"),
                        "observaciones": get_section(perfil_html, "📝"),
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
    datos = df[df['NOMBRE COMPLETO'] == seleccion].iloc[0]
    cargo = datos['CARGO']
    st.subheader(f"Evaluación de Desempeño para: {seleccion} ({cargo})")
    st.info("La IA genera el formulario según el cargo y contexto empresarial.")

    # 1. Genera el formulario con IA
    eval_form = generate_evaluation(cargo, st.session_state["company_context"])
    respuestas = {}
    with st.form("form_eval"):
        st.markdown("### Preguntas Técnicas")
        for idx, pregunta in enumerate(eval_form.get("preguntas_tecnicas", [])):
            respuestas[f"tecnica_{idx}"] = st.text_area(f"🔧 {pregunta}", key=f"tecnica_{idx}")

        st.markdown("### Preguntas de Habilidades Blandas")
        for idx, pregunta in enumerate(eval_form.get("preguntas_blandas", [])):
            respuestas[f"blanda_{idx}"] = st.text_area(f"💡 {pregunta}", key=f"blanda_{idx}")

        st.markdown("### KPIs a Medir")
        for idx, kpi in enumerate(eval_form.get("kpis_a_medir", [])):
            respuestas[f"kpi_{idx}"] = st.slider(f"📊 {kpi}", min_value=0, max_value=100, value=50, key=f"kpi_{idx}")

        enviado = st.form_submit_button("Enviar Evaluación")

    # 2. Guarda las respuestas en Google Sheets
    if enviado:
        import json
        from modules.database import save_content_to_memory
        respuestas_json = json.dumps(respuestas, ensure_ascii=False)
        save_content_to_memory(cargo, "EVALUACION", respuestas_json)
        st.success("✅ Evaluación registrada correctamente.")

        # 3. Análisis IA y cronograma de capacitación
        analisis = analyze_results(respuestas_json)
        st.markdown("### 🧠 Análisis IA")
        st.markdown(analisis, unsafe_allow_html=True)

        # 4. Cronograma de capacitación (extraído del análisis)
        st.markdown("### 📅 Cronograma de Capacitación")
        # Puedes extraer los temas del análisis IA y mostrarlos como cronograma
        import re
        temas = re.findall(r'Plan de Capacitación.*?:\s*(.*)', analisis)
        if temas:
            for idx, tema in enumerate(temas[0].split('\n')):
                if tema.strip():
                    st.markdown(f"- {tema.strip()}")
        else:
            st.info("La IA no detectó temas urgentes de capacitación.")

        st.markdown("---")
        st.success("¡Todo el flujo está conectado! Puedes ver el historial y progreso en la pestaña de desempeño global.")

with tab3:
    st.subheader("Resultados Globales")
    st.info("Pronto podrás ver el desempeño y progreso de todos los colaboradores aquí.")