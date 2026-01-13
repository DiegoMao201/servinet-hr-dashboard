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
    """
    if not client:
        return "⚠️ Error: Falta configurar OPENAI_API_KEY."

    prompt = f"""
    Eres consultor senior en Recursos Humanos, experto en Normas ISO y gestión de talento en empresas de telecomunicaciones como SERVINET.
    CONTEXTO DE LA EMPRESA (Manuales y cultura):
    {company_context[:20000]}
    TAREA:
    Redacta un manual de funciones empresarial y profesional para el cargo: "{cargo}".
    El resultado debe ser HTML limpio, visualmente atractivo y corporativo, usando colores azul, gris y amarillo, tablas, listas, iconos y títulos claros.
    Estructura el documento en las siguientes secciones (usa emojis y títulos grandes):
    1. 🎯 Objetivo del Cargo (estratégico, 2-3 líneas, resaltado).
    2. 📜 Funciones Principales (lista con viñetas y subtítulos si aplica).
    3. 🔄 Procesos Clave (tabla o lista, con breve descripción de cada proceso).
    4. 💡 Habilidades Blandas Requeridas (lista con ejemplos).
    5. 📊 KPIs Sugeridos (tabla con nombre del KPI, objetivo y frecuencia de medición).
    6. 🏅 Perfil Ideal (formación, experiencia, competencias, en tabla o lista).
    7. 📝 Observaciones y recomendaciones (resalta sugerencias de mejora y puntos críticos).
    Usa títulos grandes, separadores visuales, y resalta los puntos clave con colores corporativos.
    No incluyas encabezados HTML ni etiquetas <html>, <head> o <body>, solo el contenido de las secciones.
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
    Crea una super evaluación de desempeño (mínimo 30 preguntas, selección múltiple/Likert).
    """
    if not client: return {}

    prompt = f"""
Eres experto en psicometría y recursos humanos. Basado en los manuales y contexto de Servinet, diseña una evaluación de desempeño para el cargo "{cargo}".
REQUISITOS:
- Mínimo 30 preguntas (pueden ser más).
- Todas las preguntas deben ser de selección (NO abiertas), usando escala Likert de 1 a 5 o selección múltiple.
- Cubre: habilidades técnicas, blandas, clima laboral, liderazgo, KPIs, pertenencia, satisfacción, comunicación, innovación, cumplimiento, etc.
- Entrega un JSON con la siguiente estructura EXACTA:
{{
  "preguntas": [
    {{
      "texto": "Pregunta 1...",
      "tipo": "likert",  // o "multiple"
      "opciones": ["1 - Nunca", "2 - Rara vez", "3 - A veces", "4 - Frecuentemente", "5 - Siempre"]
    }},
    ...
  ]
}}
NO incluyas preguntas abiertas. Haz las preguntas claras, variadas y relevantes para el cargo.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        st.error(f"Error generando evaluación: {e}")
        return {"preguntas": []}

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
