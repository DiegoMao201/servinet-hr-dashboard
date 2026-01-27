import streamlit as st
import pandas as pd
from modules.database import get_employees, get_evaluaciones, init_memory
from modules.ai_brain import analyze_results
import json
import datetime
from modules.database import connect_to_drive, SPREADSHEET_ID

st.set_page_config(page_title="Desempeño Global", page_icon="📊", layout="wide")
st.image("logo_servinet.jpg", width=120)
st.title("📊 Desempeño Global del Talento")

# --- DATOS ---
df_emp = get_employees()
df_eval = get_evaluaciones()

if df_eval.empty or df_emp.empty:
    st.warning("No hay datos de evaluaciones o empleados.")
    st.stop()

# --- CARGA MEMORIA IA ---
memoria_df = pd.DataFrame()
try:
    worksheet = init_memory()
    if worksheet:
        memoria = worksheet.get_all_records()
        memoria_df = pd.DataFrame(memoria)
except Exception as e:
    st.warning(f"No se pudo cargar la memoria IA: {e}")

# --- ANÁLISIS GLOBAL CON IA ---
st.header("🧠 Análisis Ejecutivo Global con IA")
contexto_memoria = ""
if not memoria_df.empty:
    contexto_memoria = "\n".join([str(row["CONTENIDO"]) for _, row in memoria_df.iterrows() if row.get("TIPO_DOC") == "EVALUACION"])
    st.info(f"Se usaron {len(memoria_df)} registros históricos de memoria IA para el análisis.")

# Analiza todas las evaluaciones históricas
try:
    analisis_global = analyze_results(json.dumps(df_eval.to_dict(orient='records')) + "\n" + contexto_memoria)
    st.markdown(analisis_global, unsafe_allow_html=True)
except Exception as e:
    st.error(f"Error en análisis global: {e}")

st.markdown("---")
st.header("🔎 Análisis por Cargo y Plan de Acción")

temas_capacitacion = []
for cargo, grupo in df_eval.groupby('CARGO'):
    st.subheader(f"Cargo: {cargo}")
    respuestas = grupo.to_dict(orient='records')
    try:
        analisis = analyze_results(json.dumps(respuestas) + "\n" + contexto_memoria)
        st.markdown(analisis, unsafe_allow_html=True)
        # Extrae temas de capacitación sugeridos por la IA
        for line in analisis.splitlines():
            if "🎓" in line or "Tema" in line or "Capacitación" in line:
                temas_capacitacion.append({"CARGO": cargo, "TEMA": line.strip("🎓-• ")})
    except Exception as e:
        st.error(f"Error en análisis IA para {cargo}: {e}")

st.markdown("---")
st.subheader("🔎 Análisis IA por Cargo y Planes de Capacitación")

temas_capacitacion = []
for cargo, grupo in df_eval.groupby('CARGO'):
    st.markdown(f"### {cargo}")
    respuestas = grupo.to_dict(orient='records')
    analisis = analyze_results(respuestas)
    st.markdown(analisis, unsafe_allow_html=True)
    # Extrae temas sugeridos del análisis IA
    for line in analisis.splitlines():
        if "🎓" in line or "Tema" in line:
            tema = line.replace("🎓", "").replace("-", "").strip()
            if tema:
                temas_capacitacion.append({"CARGO": cargo, "TEMA": tema})
    if grupo['PUNTAJE'].min() < 60:
        st.error("⚠️ Hay empleados con desempeño bajo en este cargo. Prioriza capacitación y seguimiento.")
    else:
        st.success("Desempeño adecuado en este grupo.")

st.markdown("---")
st.subheader("📤 Guardar/Actualizar Plan de Capacitación Global")

if temas_capacitacion:
    df_temas = pd.DataFrame(temas_capacitacion).drop_duplicates()
    st.dataframe(df_temas, use_container_width=True)
    if st.button("💾 Guardar Plan de Capacitación en Google Sheets"):
        try:
            client = connect_to_drive()
            spreadsheet = client.open_by_key(SPREADSHEET_ID)
            sheet = spreadsheet.worksheet("3_capacitaciones")
            # Opcional: limpiar hoja antes de guardar para evitar duplicados
            # sheet.clear()
            for _, row in df_temas.iterrows():
                sheet.append_row([
                    f"CAPACITACIÓN {row['CARGO']}", row['CARGO'], datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    row['TEMA'], "Pendiente", ""
                ])
            st.success("Plan de capacitación actualizado y guardado. Consulta la pestaña de Capacitaciones.")
        except Exception as e:
            st.error(f"No se pudo guardar el plan: {e}")
else:
    st.info("No hay temas sugeridos por IA para capacitación.")

st.caption("Página integrada con IA, memoria histórica y plan de acción. SERVINET 2024.")