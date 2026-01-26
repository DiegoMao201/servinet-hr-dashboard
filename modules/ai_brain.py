import streamlit as st
import openai
import json
import os

# Configuración de la API Key
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key and "openai" in st.secrets:
    api_key = st.secrets["openai"]["api_key"]

client = openai.OpenAI(api_key=api_key) if api_key else None

def generate_role_profile_by_sections(cargo, company_context):
    """
    Genera el manual de funciones por secciones, garantizando que no falte ninguna.
    CORREGIDO: Se toma control de la generación del título para evitar que el prompt se filtre.
    """
    if not client:
        return "⚠️ Error: Falta configurar OPENAI_API_KEY."

    secciones = [
        ("🎯 Objetivo del Cargo", "Redacta el objetivo estratégico del cargo en 2-3 líneas, resaltando su importancia para la empresa."),
        ("📜 Funciones Principales", "Lista las funciones principales del cargo, usando viñetas y subtítulos si aplica."),
        ("🔄 Procesos Clave", "Describe los procesos clave del cargo en una tabla o lista, con breve descripción de cada proceso."),
        ("🗺️ Mapa de Procesos", "Crea un diagrama textual o tabla que muestre las relaciones entre procesos y áreas para este cargo."),
        ("🧩 Matriz de Competencias", "Genera una tabla con competencias técnicas y blandas, nivel requerido y nivel actual promedio en la empresa."),
        ("💡 Habilidades Blandas Requeridas", "Lista las habilidades blandas requeridas, con ejemplos y casos prácticos."),
        ("🏆 Habilidades Técnicas Requeridas", "Lista y tabla con certificaciones, herramientas y tecnologías necesarias."),
        ("📊 KPIs Sugeridos", "Crea una tabla HTML con las columnas: KPI, Fórmula/Descripción, Meta, Frecuencia."),
        ("🏅 Perfil Ideal", "Describe el perfil ideal: formación, experiencia, competencias, en tabla o lista."),
        ("🧠 Análisis de Riesgos", "Identifica riesgos operativos, humanos y tecnológicos asociados al cargo."),
        ("🚦 Alertas y Recomendaciones", "Resalta sugerencias de mejora, puntos críticos y alertas de gestión."),
        ("🔍 Diagnóstico Comparativo", "Compara el cargo con roles similares en el sector, identifica brechas y oportunidades."),
        ("📝 Observaciones y recomendaciones finales", "Resalta sugerencias de mejora y puntos críticos."),
        ("📚 Referencias y fuentes", "Lista de documentos, manuales y políticas internas usadas como base."),
    ]

    contexto_limitado = company_context[:4000]
    manual_html = ""

    for titulo_seccion, instruccion in secciones:
        prompt = f"""
Eres un consultor experto en RRHH para Servinet, una empresa de telecomunicaciones.
Contexto de la empresa: {contexto_limitado}
Cargo a analizar: "{cargo}"

TAREA:
Genera únicamente el contenido para la sección "{titulo_seccion}".
Instrucción específica: {instruccion}

REGLAS ESTRICTAS:
- Tu respuesta debe ser solo el contenido HTML (listas, tablas, párrafos).
- NO incluyas el título de la sección en tu respuesta.
- NO incluyas las etiquetas ```html, <html>, <body>.
- Si no tienes información, genera contenido genérico y profesional para el cargo.
"""
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )
            content = response.choices[0].message.content.strip()
            if not content or len(content) < 10:
                content = "<p>Información no disponible. Se requiere completar esta sección.</p>"
        except Exception as e:
            content = f"<p>Error al generar contenido: {e}</p>"
        manual_html += f'<div class="section">\n'
        manual_html += f'  <div class="section-title">{titulo_seccion}</div>\n'
        manual_html += f'  {content}\n'
        manual_html += f'</div>\n'

    return manual_html

# --- El resto de las funciones se mantienen intactas ---

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

def analyze_clima_laboral(respuestas_list):
    """
    Analiza los resultados de clima laboral de un grupo de empleados.
    Usa GPT para generar un reporte ejecutivo, fortalezas, debilidades y plan de acción.
    """
    if not client:
        return "Error de configuración de IA."

    prompt = f"""
Eres consultor experto en clima laboral y bienestar organizacional. Analiza los siguientes resultados de encuesta de clima laboral (formato JSON, cada elemento es una respuesta individual):

{json.dumps(respuestas_list, ensure_ascii=False)}

Genera un reporte ejecutivo en Markdown que incluya:
1. 📊 Resumen general del clima laboral (nivel de satisfacción, ambiente, motivación, comunicación, liderazgo, etc.).
2. 💪 Fortalezas detectadas en la empresa.
3. 🚩 Debilidades y alertas principales.
4. 🎯 Recomendaciones y plan de acción para RRHH.
5. 🏆 Sugerencias de capacitaciones o intervenciones grupales.
Sé claro, profesional y orientado a la mejora continua.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error analizando clima laboral: {e}"

# La función generate_role_profile original ya no es necesaria si usas la de secciones,
# pero la dejamos por si la usas en otro lado.
def generate_role_profile(cargo, company_context, force=False):
    """
    Crea el Manual de Funciones personalizado, ahora mucho más completo y analítico.
    """
    if not client:
        return "⚠️ Error: Falta configurar OPENAI_API_KEY."

    prompt = f"""
    Eres consultor senior en Recursos Humanos, experto en Normas ISO, gestión de talento, análisis organizacional y transformación digital en empresas de telecomunicaciones como SERVINET.
    CONTEXTO DE LA EMPRESA (Manuales, cultura, procesos, informes, estructura, diagnósticos, etc.):
    {company_context[:4000]}
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
