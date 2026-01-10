import streamlit as st
import openai # O google.generativeai

st.title("Evaluación de Desempeño 360")

empleado = st.selectbox("Seleccionar Empleado", ["Juan", "Maria", "Pedro"])
cargo = "Técnico Instalador" # Esto deberías jalarlo de la DB automáticamente

st.subheader(f"Evaluando a: {empleado} ({cargo})")

# Formulario basado en los KPIs que definiste en el prompt anterior
kpi_1 = st.slider("Calidad de Instalación (Reincidencias)", 0, 100)
kpi_2 = st.slider("Satisfacción Cliente (NPS)", 0, 10)
comentarios = st.text_area("Observaciones cualitativas del supervisor")

if st.button("Generar Plan de Capacitación con IA"):
    # Prompt para la IA
    prompt = f"""
    Actúa como experto en RRHH de la empresa de telecomunicaciones SERVINET.
    Analiza al empleado {empleado}, cargo {cargo}.
    Resultados:
    - Calidad técnica: {kpi_1}/100
    - Satisfacción cliente: {kpi_2}/10
    - Notas: {comentarios}
    
    1. Danos una conclusión del desempeño.
    2. Crea un plan de capacitación específico para mejorar sus puntos débiles.
    """
    
    # Llamada simulada a IA (Aquí conectas tu API Key)
    st.info("La IA está analizando los datos...")
    # response = openai.ChatCompletion.create(...) 
    st.success("Plan Generado:")
    st.write("Basado en el bajo NPS, sugiero un curso de 'Protocolos de Atención en Casa del Cliente'...")
