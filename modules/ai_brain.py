import streamlit as st
import openai
import json
import os

# Configura la API Key desde Coolify (Variable: OPENAI_API_KEY)
# Si no está en Coolify, intenta buscar en secrets locales
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key and "openai" in st.secrets:
    api_key = st.secrets["openai"]["api_key"]

client = openai.OpenAI(api_key=api_key)

def generate_role_profile(cargo, company_context):
    """
    Crea la 'Hoja de Vida de Funciones' personalizada.
    """
    prompt = f"""
    Actúa como un Director de RRHH experto en normas ISO y gestión por competencias.
    
    CONTEXTO DE LA EMPRESA (Manuales y Estructura):
    {company_context[:15000]}  # Limitamos caracteres por seguridad
    
    TAREA:
    Genera un perfil de cargo detallado y profesional para el cargo: "{cargo}".
    
    El formato debe ser HTML limpio para mostrar en web, con estas secciones:
    1. 🎯 Objetivo del Cargo (Alineado a la estrategia de Servinet).
    2. 📜 Funciones Principales (Extraídas del manual).
    3. 🔄 Procesos Clave (Qué hace día a día).
    4. 💡 Habilidades Blandas Requeridas.
    5. 📊 KPIs Sugeridos (Indicadores de éxito).
    
    Responde SOLO con el código HTML (sin ```html). Usa iconos y diseño moderno.
    """
    
    response = client.chat.completions.create(
        model="gpt-4o", # O gpt-3.5-turbo si quieres ahorrar
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return response.choices[0].message.content

def generate_evaluation(cargo, company_context):
    """
    Crea una evaluación de desempeño dinámica en formato JSON.
    """
    prompt = f"""
    Eres un experto en psicometría y evaluación de desempeño.
    Basado en los manuales de Servinet, crea una evaluación para: "{cargo}".
    
    La salida debe ser estrictamente un JSON con esta estructura:
    {{
        "preguntas_tecnicas": ["pregunta 1", "pregunta 2", "pregunta 3"],
        "preguntas_blandas": ["pregunta 1", "pregunta 2"],
        "kpis_a_medir": ["kpi 1", "kpi 2"]
    }}
    
    Las preguntas deben ser situacionales ("¿Qué harías si...?") o de verificación de proceso.
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

def analyze_results(respuestas_json):
    """
    Analiza las respuestas del empleado y saca conclusiones.
    """
    prompt = f"""
    Analiza estos resultados de evaluación de desempeño:
    {respuestas_json}
    
    Genera un reporte que incluya:
    1. Nivel de competencia (0-100).
    2. Nivel de estrés detectado (Bajo/Medio/Alto) basado en el tono.
    3. Compromiso organizacional.
    4. Plan de Capacitación sugerido (3 temas clave).
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content
