# pages/6_🌤️_Clima_Laboral.py
import streamlit as st
from modules.database import connect_to_drive, SPREADSHEET_ID, get_employees
from modules.ai_brain import analyze_clima_laboral
import base64
import pandas as pd
import urllib.parse

st.set_page_config(page_title="Clima Laboral", page_icon="🌤️", layout="wide")
st.title("🌤️ Encuesta de Clima Laboral")

# --- CARGA DE DATOS ---
df = get_employees()
client = connect_to_drive()
spreadsheet = client.open_by_key(SPREADSHEET_ID)
sheet = spreadsheet.worksheet("4_clima_laboral")
data_clima = sheet.get_all_records()
df_clima = pd.DataFrame(data_clima)

# Convierte las columnas de preguntas a numéricas (ignora errores)
preguntas = [col for col in df_clima.columns if col.startswith("¿")]
for col in preguntas:
    df_clima[col] = pd.to_numeric(df_clima[col], errors='coerce')

# --- FILTRAR EMPLEADOS QUE NO HAN RESPONDIDO ---
respondieron = set(str(row['CEDULA']) for _, row in df_clima.iterrows() if 'CEDULA' in row and row['CEDULA'])
df['CEDULA'] = df['CEDULA'].astype(str)
df_pendientes = df[~df['CEDULA'].isin(respondieron)]

tab1, tab2, tab3 = st.tabs(["📨 Envío y Registro", "📊 Resultados Globales", "🧠 Análisis y Plan de Acción"])

with tab1:
    st.subheader("🔗 Enlaces personalizados para encuesta de clima laboral")
    if df_pendientes.empty:
        st.success("🎉 Todos los empleados han respondido la encuesta de clima laboral.")
    else:
        for _, row in df_pendientes.iterrows():
            token = base64.b64encode(str(row['CEDULA']).encode()).decode()
            url = f"https://servinet.datovatenexuspro.com/?clima={row['CEDULA']}&token={token}"
            url_encoded = urllib.parse.quote(url, safe='')
            mensaje_ws = (
                f"🌤️ Hola {row['NOMBRE COMPLETO']},%0A"
                "Te invitamos a diligenciar la Encuesta de Clima Laboral de SERVINET.%0A"
                "Tu opinión es muy importante para nosotros y nos ayuda a mejorar el ambiente de trabajo.%0A"
                "Por favor ingresa al siguiente enlace seguro y responde la encuesta: "
                f"{url_encoded}%0A"
                "¡Gracias por tu participación! 😊"
            )
            st.markdown(f"""
                <div style="background:#f8fafc; border-radius:10px; padding:16px; margin-bottom:12px; box-shadow:0 2px 8px #e0e7ef;">
                    <b>{row['NOMBRE COMPLETO']}</b> ({row.get('CARGO','')})<br>
                    <a href="{url}" target="_blank" style="color:#2563eb;">Abrir encuesta</a>
                    <br>
                    <a href="https://web.whatsapp.com/send?phone={row.get('CELULAR','')}&text={mensaje_ws}" target="_blank">
                        <button style="
                            background-color:#25D366; 
                            color:white; 
                            border:none; 
                            padding:8px 18px; 
                            border-radius:5px; 
                            font-size:15px; 
                            cursor:pointer;
                            margin-top:8px;">
                            📲 Enviar por WhatsApp
                        </button>
                    </a>
                </div>
            """, unsafe_allow_html=True)
    st.markdown("---")
    st.info("Solo aparecen los empleados que aún no han respondido la encuesta. Cuando respondan, desaparecerán de este listado automáticamente.")
    with st.expander("👀 Ver empleados que ya respondieron"):
        if not df_clima.empty and "NOMBRE COMPLETO" in df_clima.columns:
            st.dataframe(df_clima[["NOMBRE COMPLETO", "CEDULA", "CARGO", "DEPARTAMENTO"]])
        else:
            st.write("Aún no hay respuestas registradas.")

with tab2:
    st.header("📈 Resultados Globales de Clima Laboral")
    if not df_clima.empty:
        preguntas = [col for col in df_clima.columns if col.startswith("¿")]
        # --- Conversión a numérico ---
        for col in preguntas:
            df_clima[col] = pd.to_numeric(df_clima[col], errors='coerce')

        st.subheader("Promedio Global por Pregunta")
        promedios = df_clima[preguntas].mean().sort_values(ascending=False)
        st.bar_chart(promedios)

        st.subheader("Distribución de Respuestas por Pregunta")
        import plotly.express as px
        for col in preguntas:
            fig = px.histogram(df_clima, x=col, nbins=11, title=col, color_discrete_sequence=['#3b82f6'])
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Promedio de Clima por Cargo")
        clima_por_cargo = df_clima.groupby("CARGO")[preguntas].mean()
        st.dataframe(clima_por_cargo.style.background_gradient(cmap="Blues"), use_container_width=True)

        st.subheader("Mapa de Calor de Clima Laboral por Cargo")
        import plotly.figure_factory as ff
        z = clima_por_cargo.values
        x = clima_por_cargo.columns.tolist()
        y = clima_por_cargo.index.tolist()
        fig = ff.create_annotated_heatmap(z, x=x, y=y, colorscale='Blues', showscale=True)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.info("Haz clic en las pestañas para ver análisis IA y planes de acción por cargo.")
    else:
        st.info("Aún no hay respuestas de clima laboral registradas.")

with tab3:
    st.header("🧠 Análisis IA y Plan de Acción")
    if not df_clima.empty:
        preguntas = [col for col in df_clima.columns if col.startswith("¿")]
        # --- Conversión a numérico ---
        for col in preguntas:
            df_clima[col] = pd.to_numeric(df_clima[col], errors='coerce')

        st.subheader("Análisis Ejecutivo Global")
        respuestas_list = df_clima.to_dict(orient='records')
        analisis = analyze_clima_laboral(respuestas_list)
        st.markdown(analisis, unsafe_allow_html=True)

        st.subheader("Análisis y Plan de Acción por Cargo")
        cargos = df_clima["CARGO"].dropna().unique()
        for cargo in cargos:
            grupo = df_clima[df_clima["CARGO"] == cargo]
            if not grupo.empty:
                st.markdown(f"### {cargo}")
                respuestas_cargo = grupo.to_dict(orient='records')
                analisis_cargo = analyze_clima_laboral(respuestas_cargo)
                st.markdown(analisis_cargo, unsafe_allow_html=True)
                # Gráfico de barras para este cargo
                promedios_cargo = grupo[preguntas].mean().sort_values(ascending=False)
                st.bar_chart(promedios_cargo)
                st.markdown("---")
    else:
        st.info("Aún no hay suficientes datos para análisis.")