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
    Crea el Manual de Funciones personalizado, ahora mucho más completo y analítico.
    """
    if not client:
        return "⚠️ Error: Falta configurar OPENAI_API_KEY."

    prompt = f"""
    Eres consultor senior en Recursos Humanos, experto en Normas ISO, gestión de talento, análisis organizacional y transformación digital en empresas de telecomunicaciones como SERVINET.
    CONTEXTO DE LA EMPRESA (Manuales, cultura, procesos, informes, estructura, diagnósticos, etc.):
    {company_context[:10000]}
    TAREA:
    Redacta un manual de funciones empresarial, profesional y EXTREMADAMENTE COMPLETO para el cargo: "{cargo}".
    El resultado debe ser HTML limpio, visualmente atractivo y corporativo, usando colores azul, gris y amarillo, tablas, listas, iconos y títulos claros.
    Estructura el documento en las siguientes secciones (usa emojis y títulos grandes):

    1. 🎯 Objetivo del Cargo (estratégico, 2-3 líneas, resaltado).
    2. 📜 Funciones Principales (lista con viñetas y subtítulos si aplica).
    3. 🔄 Procesos Clave (tabla o lista, con breve descripción de cada proceso).
    4. 🗺️ Mapa de Procesos (diagrama textual o tabla de relaciones entre procesos y áreas).
    5. 🧩 Matriz de Competencias (tabla con competencias técnicas y blandas, nivel requerido y nivel actual promedio en la empresa).
    6. 💡 Habilidades Blandas Requeridas (lista con ejemplos y casos prácticos).
    7. 🏆 Habilidades Técnicas Requeridas (lista y tabla con certificaciones, herramientas y tecnologías).
    8. 📊 KPIs Sugeridos (tabla con nombre del KPI, objetivo, frecuencia de medición y responsable).
    9. 🏅 Perfil Ideal (formación, experiencia, competencias, en tabla o lista).
    10. 🧠 Análisis de Riesgos (identifica riesgos operativos, humanos y tecnológicos asociados al cargo).
    11. 🚦 Alertas y Recomendaciones (resalta sugerencias de mejora, puntos críticos y alertas de gestión).
    12. 🔍 Diagnóstico Comparativo (compara el cargo con roles similares en el sector, identifica brechas y oportunidades).
    13. 📝 Observaciones y recomendaciones finales (resalta sugerencias de mejora y puntos críticos).
    14. 📚 Referencias y fuentes (lista de documentos, manuales y políticas internas usadas como base).

    - Usa títulos grandes, separadores visuales, y resalta los puntos clave con colores corporativos.
    - No incluyas encabezados HTML ni etiquetas <html>, <head> o <body>, solo el contenido de las secciones.
    - Si tienes datos de la empresa, personaliza el manual con ejemplos reales, cifras, y recomendaciones específicas para SERVINET.
    - Sé exhaustivo, analítico y profesional. El manual debe servir para onboarding, auditoría, capacitación y gestión estratégica.
    NO omitas ninguna sección. Si no tienes información suficiente, crea algo corto pero empresarial dependiendo del cargo.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
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
