# pages/5_📅_Capacitaciones.py
import streamlit as st
import pandas as pd
from modules.database import connect_to_drive, SPREADSHEET_ID, get_evaluaciones, get_employees
from modules.ai_brain import analyze_results, analyze_clima_laboral

st.set_page_config(page_title="Capacitaciones", page_icon="📅", layout="wide")
st.title("📅 Plan y Cronograma de Capacitaciones")

client = connect_to_drive()
spreadsheet = client.open_by_key(SPREADSHEET_ID)
sheet = spreadsheet.worksheet("3_capacitaciones")
data = sheet.get_all_records()
df = pd.DataFrame(data)

tab1, tab2 = st.tabs(["🎯 Reforzar Desempeño", "🌤️ Mejorar Clima Laboral"])

# --- PESTAÑA 1: DESEMPEÑO ---
with tab1:
    st.header("Plan de Capacitación por Desempeño")
    df_eval = get_evaluaciones()
    if df_eval.empty:
        st.warning("No hay datos de evaluaciones registrados.")
    else:
        # Análisis IA global y por cargo
        st.subheader("Análisis IA Global")
        analisis_global = analyze_results(df_eval.to_dict(orient='records'))
        st.markdown(analisis_global, unsafe_allow_html=True)

        st.subheader("Planes de Capacitación por Cargo")
        for cargo, grupo in df_eval.groupby("CARGO"):
            st.markdown(f"**{cargo}**")
            analisis = analyze_results(grupo.to_dict(orient='records'))
            st.markdown(analisis, unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("Cronograma Actual de Capacitaciones")
        if df.empty or "NOMBRE" not in df.columns:
            st.info("No hay cronograma registrado.")
        else:
            st.dataframe(df)

        # Botón para actualizar el plan (solo si tú lo decides)
        if st.button("🔄 Generar/Actualizar Plan de Capacitación por Desempeño"):
            # Aquí puedes guardar el nuevo plan en la hoja de Google Sheets
            # Ejemplo: agregar una fila por cada recomendación IA
            import datetime
            for cargo, grupo in df_eval.groupby("CARGO"):
                analisis = analyze_results(grupo.to_dict(orient='records'))
                # Extrae temas sugeridos del análisis IA (puedes mejorar el parsing)
                temas = []
                for line in analisis.splitlines():
                    if "🎓" in line or "Tema" in line:
                        temas.append(line.replace("🎓", "").replace("-", "").strip())
                for tema in temas:
                    sheet.append_row([
                        f"CAPACITACIÓN {cargo}", cargo, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        tema, "Pendiente", ""
                    ])
            st.success("Plan de capacitación actualizado. Refresca la página para ver los cambios.")

# --- PESTAÑA 2: CLIMA LABORAL ---
with tab2:
    st.header("Plan de Capacitación por Clima Laboral")
    # Carga datos de clima laboral
    sheet_clima = spreadsheet.worksheet("4_clima_laboral")
    data_clima = sheet_clima.get_all_records()
    df_clima = pd.DataFrame(data_clima)
    if df_clima.empty:
        st.warning("No hay datos de clima laboral registrados.")
    else:
        st.subheader("Análisis IA Global de Clima Laboral")
        analisis_clima = analyze_clima_laboral(df_clima.to_dict(orient='records'))
        st.markdown(analisis_clima, unsafe_allow_html=True)

        st.subheader("Planes de Capacitación por Cargo (Clima)")
        for cargo, grupo in df_clima.groupby("CARGO"):
            st.markdown(f"**{cargo}**")
            analisis = analyze_clima_laboral(grupo.to_dict(orient='records'))
            st.markdown(analisis, unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("Cronograma Actual de Capacitaciones")
        if df.empty or "NOMBRE" not in df.columns:
            st.info("No hay cronograma registrado.")
        else:
            st.dataframe(df)

        # Botón para actualizar el plan (solo si tú lo decides)
        if st.button("🔄 Generar/Actualizar Plan de Capacitación por Clima Laboral"):
            import datetime
            for cargo, grupo in df_clima.groupby("CARGO"):
                analisis = analyze_clima_laboral(grupo.to_dict(orient='records'))
                temas = []
                for line in analisis.splitlines():
                    if "🏆" in line or "Tema" in line or "Capacitación" in line:
                        temas.append(line.replace("🏆", "").replace("-", "").strip())
                for tema in temas:
                    sheet.append_row([
                        f"CAPACITACIÓN CLIMA {cargo}", cargo, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        tema, "Pendiente", ""
                    ])
            st.success("Plan de capacitación por clima laboral actualizado. Refresca la página para ver los cambios.")