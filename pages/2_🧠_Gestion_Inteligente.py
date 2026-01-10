import streamlit as st
from modules.database import get_employees
from modules.document_reader import get_company_context
from modules.ai_brain import generate_role_profile, generate_evaluation, analyze_results

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
        if st.button("✨ Generar Manual de Funciones Personalizado"):
            with st.spinner("Redactando documento oficial..."):
                perfil_html = generate_role_profile(cargo, st.session_state["company_context"])
                st.markdown(perfil_html, unsafe_allow_html=True)
                # Aquí podrías agregar un botón para descargar en PDF
                
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
        else:
            st.info("Primero debes completar la evaluación en la pestaña anterior.")
