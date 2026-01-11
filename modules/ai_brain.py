import streamlit as st
import openai
import json
import os

# Configuración de la API Key
# Prioridad: 1. Coolify (Env Var) -> 2. Local (secrets.toml)
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key and "openai" in st.secrets:
    api_key = st.secrets["openai"]["api_key"]

# Inicializamos el cliente si hay llave
if api_key:
    client = openai.OpenAI(api_key=api_key)
else:
    client = None

def generate_role_profile(cargo, company_context, force=False):
    """
    Crea el Manual de Funciones personalizado.
    Si force=False, solo genera si no existe (la lógica de chequeo se maneja fuera de esta función).
    """
    if not client:
        return "⚠️ Error: Falta configurar OPENAI_API_KEY."

    prompt = f"""
    Actúa como un Director de RRHH experto en normas ISO.
    CONTEXTO DE LA EMPRESA (Manuales):
    {company_context[:20000]}
    TAREA:
    Genera un perfil de cargo profesional para: "{cargo}".
    El formato debe ser HTML limpio (sin ```html ni markdown) para mostrar en web.
    Usa iconos y un diseño corporativo moderno (Azul/Gris).
    SECCIONES OBLIGATORIAS:
    1. 🎯 Objetivo del Cargo (Estratégico).
    2. 📜 Funciones Principales (Lista con viñetas).
    3. 🔄 Procesos Clave (Día a día).
    4. 💡 Habilidades Blandas Requeridas.
    5. 📊 KPIs Sugeridos.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        content = response.choices[0].message.content
        return content.replace("```html", "").replace("```", "")
    except Exception as e:
        return f"Error generando perfil: {e}"

def generate_evaluation(cargo, company_context):
    """
    Crea la evaluación de desempeño en formato JSON.
    Modelo: gpt-4o-mini
    """
    if not client: return {}

    prompt = f"""
    Eres experto en psicometría. Basado en los manuales de Servinet, crea una evaluación para: "{cargo}".
    
    SALIDA: Un JSON válido con esta estructura exacta:
    {{
        "preguntas_tecnicas": ["pregunta situacional 1", "pregunta 2", "pregunta 3"],
        "preguntas_blandas": ["pregunta 1", "pregunta 2"],
        "kpis_a_medir": ["kpi 1", "kpi 2"]
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", # <--- MODELO ECONÓMICO
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        st.error(f"Error generando evaluación: {e}")
        return {"preguntas_tecnicas": ["Error generando preguntas"], "preguntas_blandas": []}

def analyze_results(respuestas_json):
    """
    Analiza las respuestas del empleado.
    Modelo: gpt-4o-mini
    """
    if not client: return "Error de configuración."

    prompt = f"""
    Analiza estos resultados de evaluación de desempeño de un empleado de Servinet:
    {respuestas_json}
    
    Genera un reporte ejecutivo en formato Markdown que incluya:
    1. 🏆 Nivel de competencia (0-100%).
    2. 🧠 Estado emocional y nivel de estrés percibido.
    3. 🎓 Plan de Capacitación (3 temas urgentes y prácticos).
    4. ⚠️ Alerta de Retención (¿Riesgo de renuncia? Bajo/Medio/Alto).
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", # <--- MODELO ECONÓMICO
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error analizando resultados: {e}"
