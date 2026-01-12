import streamlit as st
import pandas as pd
from modules.database import get_employees, init_memory

st.set_page_config(page_title="Desempeño Global", page_icon="📊", layout="wide")
st.image("logo_servinet.jpg", width=120)
st.title("📊 Desempeño Global del Talento")

df = get_employees()
worksheet = init_memory()
if worksheet:
    data = worksheet.get_all_records()
    df_eval = pd.DataFrame(data)
    df_eval = df_eval[df_eval['TIPO_DOC'] == "EVALUACION"]
    # Extrae puntaje
    import re
    def extraer_puntaje(texto):
        m = re.search(r"(\d{1,3})\s*%", texto)
        return int(m.group(1)) if m else None
    df_eval['PUNTAJE'] = df_eval['CONTENIDO'].apply(extraer_puntaje)
    df_eval = df_eval.dropna(subset=['PUNTAJE'])
    if not df_eval.empty:
        st.subheader("Evolución de Desempeño por Cargo")
        st.line_chart(df_eval.groupby('CARGO')['PUNTAJE'].mean())
        st.subheader("Ranking de Desempeño")
        ranking = df_eval.groupby('CARGO')['PUNTAJE'].mean().sort_values(ascending=False)
        st.dataframe(ranking)
    else:
        st.info("No hay datos de desempeño para graficar.")
else:
    st.warning("No se pudo acceder a la memoria de evaluaciones.")