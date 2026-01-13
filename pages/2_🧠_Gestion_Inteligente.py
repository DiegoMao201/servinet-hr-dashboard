import streamlit as st
from modules.database import get_employees
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
import io
from fpdf import FPDF
import datetime

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
                    perfil_html = generate_role_profile_by_sections(cargo, st.session_state["company_context"])
                    logo_path = os.path.abspath("logo_servinet.jpg")
                    now = datetime.datetime.now()
                    anio_actual = now.year
                    vigencia = f"Enero {anio_actual} - Diciembre {anio_actual}"
                    fecha_emision = now.strftime("%d/%m/%Y")

                    datos_manual = {
                        "empresa": "GRUPO SERVINET",
                        "logo_url": logo_path,
                        "codigo_doc": f"DOC-MF-{str(datos.get('CEDULA', '001'))}",
                        "departamento": datos.get("DEPARTAMENTO", ""),
                        "titulo": f"Manual de Funciones: {cargo}",
                        "descripcion": f"Manual profesional para el cargo {cargo} en {datos.get('SEDE', '')}.",
                        "version": "1.0",
                        "vigencia": vigencia,
                        "fecha_emision": fecha_emision,
                        "empleado": seleccion if 'seleccion' in locals() else empleado,
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
    st.info("La IA genera una evaluación extensa y profesional con preguntas de selección.")

    # 1. Genera la super evaluación con IA
    eval_form = generate_evaluation(cargo, st.session_state["company_context"])
    respuestas = {}
    with st.form("form_eval"):
        for idx, pregunta in enumerate(eval_form.get("preguntas", [])):
            texto = pregunta.get("texto", f"Pregunta {idx+1}")
            tipo = pregunta.get("tipo", "likert")
            opciones = pregunta.get("opciones", ["1", "2", "3", "4", "5"])
            respuestas[f"preg_{idx}"] = st.radio(f"{idx+1}. {texto}", opciones, key=f"preg_{idx}")
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

        st.markdown("---")
        st.success("¡Evaluación completa y lista para análisis avanzado!")

with tab3:
    st.subheader("Resultados Globales")
    st.info("Pronto podrás ver el desempeño y progreso de todos los colaboradores aquí.")

    # --- Definir sheet correctamente ---
    from modules.database import connect_to_drive, SPREADSHEET_ID
    client = connect_to_drive()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    try:
        sheet = spreadsheet.worksheet("7_respuestas_evaluacion")
        df_resp = pd.DataFrame(sheet.get_all_records())
        if not df_resp.empty:
            st.subheader("📊 Resultados por Pregunta")
            pregunta_sel = st.selectbox("Selecciona una pregunta", df_resp["PREGUNTA"].unique())
            df_preg = df_resp[df_resp["PREGUNTA"] == pregunta_sel]
            st.bar_chart(df_preg["RESPUESTA"].value_counts().sort_index())

            import io
            excel_bytes = io.BytesIO()
            df_resp.to_excel(excel_bytes, index=False)
            st.download_button("📥 Exportar a Excel", data=excel_bytes.getvalue(), file_name="respuestas_evaluacion.xlsx")

            from fpdf import FPDF
            def export_pdf(df):
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", "B", 14)
                pdf.cell(0, 10, "Resultados Evaluación", ln=True, align="C")
                pdf.set_font("Arial", "", 10)
                for idx, row in df.iterrows():
                    pdf.cell(0, 8, f"{row['NOMBRE']} | {row['CARGO']} | {row['PREGUNTA']} | {row['RESPUESTA']}", ln=True)
                pdf_bytes = io.BytesIO()
                pdf.output(pdf_bytes)
                pdf_bytes.seek(0)
                return pdf_bytes

            st.download_button("📄 Exportar a PDF", data=export_pdf(df_resp), file_name="respuestas_evaluacion.pdf", mime="application/pdf")
        else:
            st.info("No hay respuestas de evaluación registradas aún.")
    except Exception as e:
        st.warning(f"No se pudo acceder a los resultados globales: {e}")