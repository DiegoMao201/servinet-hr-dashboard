import streamlit as st
import pandas as pd
from modules.database import get_evaluaciones, get_employees, connect_to_drive, SPREADSHEET_ID
from modules.drive_manager import find_manual_in_drive, download_manual_from_drive, get_or_create_manuals_folder
from modules.ai_brain import analyze_results

st.set_page_config(page_title="Evaluaciones 360", page_icon="📝", layout="wide")
st.image("logo_servinet.jpg", width=120)
st.title("📝 Evaluaciones de Desempeño 360")

@st.cache_data(ttl=900)
def get_data():
    return get_evaluaciones(), get_employees()

df_eval, df_emp = get_data()

if df_eval.empty or df_emp.empty:
    st.warning("No hay datos de evaluaciones o empleados.")
    st.stop()

empleado = st.selectbox("Seleccionar Empleado", df_emp['NOMBRE COMPLETO'].unique())
datos = df_emp[df_emp['NOMBRE COMPLETO'] == empleado].iloc[0]
cargo = datos.get("CARGO", "")
manuals_folder_id = get_or_create_manuals_folder()

st.markdown(f"### 👤 {empleado} ({cargo})")
st.caption(f"Sede: {datos.get('SEDE', '--')} | Departamento: {datos.get('DEPARTAMENTO', '--')}")

with st.expander("📄 Manual de Funciones"):
    manual_file_id = find_manual_in_drive(cargo, manuals_folder_id)
    if manual_file_id:
        pdf_bytes = download_manual_from_drive(manual_file_id)
        st.download_button(
            label="📥 Descargar Manual PDF",
            data=pdf_bytes,
            file_name=f"Manual_{cargo.replace(' ', '_').upper()}.pdf",
            mime="application/pdf"
        )
        st.success("Manual disponible.")
    else:
        st.warning("No hay manual de funciones para este cargo.")

st.markdown("## 📊 Historial de Evaluaciones")
df_hist = df_eval[df_eval['NOMBRE'].str.upper() == empleado.upper()]
if not df_hist.empty:
    st.dataframe(df_hist.sort_values('FECHA', ascending=False), use_container_width=True)
    if "PUNTAJE" in df_hist.columns:
        st.line_chart(df_hist.set_index('FECHA')['PUNTAJE'])
    ultima_eval = df_hist.sort_values('FECHA', ascending=False).iloc[0]
    st.markdown("### 🧠 Análisis IA de la última evaluación")
    analisis = analyze_results(ultima_eval.to_dict())
    st.markdown(analisis, unsafe_allow_html=True)
else:
    st.info("Este empleado aún no tiene evaluaciones registradas.")

st.markdown("---")
st.subheader("🔔 Alertas y Recomendaciones")
if df_hist.empty:
    st.error("⚠️ Urgente: Este empleado no ha sido evaluado. Prioriza su evaluación.")
else:
    if "PUNTAJE" in df_hist.columns and df_hist['PUNTAJE'].min() < 60:
        st.warning("⚠️ Desempeño bajo detectado en alguna evaluación. Revisa el plan de capacitación.")
    else:
        st.success("Desempeño adecuado en las evaluaciones registradas.")

with st.expander("📈 Ver desempeño global"):
    st.info("Consulta el desempeño global en la pestaña correspondiente para comparar este empleado con el resto del equipo.")

with st.expander("📝 Nueva Evaluación 360°"):
    tipo_evaluador = st.selectbox("Tipo de Evaluador", ["Auto", "Jefe", "Par", "Subordinado"])
    puntaje = st.slider("Puntaje Global (%)", 0, 100, 50)
    comentarios = st.text_area("Comentarios adicionales")
    enviado = st.button("Registrar Evaluación")
    if enviado:
        import datetime
        client = connect_to_drive()
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        sheet = spreadsheet.worksheet("2_evaluaciones")
        sheet.append_row([
            empleado, cargo, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            tipo_evaluador, puntaje, "", comentarios
        ])
        st.success("Evaluación registrada.")

st.caption("Página integrada con IA, manuales y desempeño. SERVINET 2024.")

# Nueva sección para Capacitación
st.title("📅 Cronograma de Capacitaciones")

client = connect_to_drive()
spreadsheet = client.open_by_key(SPREADSHEET_ID)
sheet = spreadsheet.worksheet("3_capacitaciones")
data = sheet.get_all_records()
df_capacitaciones = pd.DataFrame(data)

st.dataframe(df_capacitaciones)
st.markdown("### Registrar nueva capacitación")
nombre = st.selectbox("Empleado", df_capacitaciones["NOMBRE"].unique())
tema = st.text_input("Tema")
estado = st.selectbox("Estado", ["Pendiente", "Realizada"])
if st.button("Registrar capacitación"):
    import datetime
    cargo = df_capacitaciones[df_capacitaciones["NOMBRE"] == nombre]["CARGO"].iloc[0]
    sheet.append_row([
        nombre, cargo, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        tema, estado, ""
    ])
    st.success("Capacitación registrada.")