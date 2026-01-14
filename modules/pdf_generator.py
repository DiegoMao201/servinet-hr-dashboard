from fpdf import FPDF
from weasyprint import HTML
from jinja2 import Environment, FileSystemLoader
import os
import re

class PDF(FPDF):
    def header(self):
        self.set_font('DejaVu', 'B', 15)
        self.cell(80)
        self.cell(30, 10, 'SERVINET - Manual de Funciones', 0, 0, 'C')
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font('DejaVu', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def clean_html_to_text(html):
    # Elimina imágenes externas y etiquetas <img>
    html = re.sub(r'<img[^>]*>', '', html)
    # Elimina todas las etiquetas HTML pero deja los emojis y texto
    text = re.sub('<[^<]+?>', '', html)
    # Opcional: reemplaza múltiples saltos de línea por uno solo
    text = re.sub(r'\n+', '\n', text)
    return text.strip()

def create_manual_pdf(cargo, perfil_html, empleado=None):
    """Genera un PDF profesional del manual de funciones."""
    pdf = PDF()
    # Ruta absoluta para la fuente
    font_path = os.path.join(os.path.dirname(__file__), 'fonts', 'DejaVuSans.ttf')
    pdf.add_font('DejaVu', '', font_path, uni=True)
    pdf.add_font('DejaVu', 'B', font_path, uni=True)
    pdf.add_font('DejaVu', 'I', font_path, uni=True)
    pdf.set_font("DejaVu", "B", 14)
    pdf.add_page()
    title = f"Manual de Funciones: {cargo}"
    if empleado:
        title += f" - {empleado}"
    pdf.cell(0, 10, title, ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("DejaVu", "", 11)
    text = clean_html_to_text(perfil_html)
    pdf.multi_cell(0, 10, text)
    # Guarda el PDF en una ruta absoluta temporal
    filename = f"Manual_{cargo.replace(' ', '_').upper()}.pdf"
    abs_path = os.path.abspath(filename)
    pdf.output(abs_path)
    return abs_path

def create_manual_pdf_from_html(html_content, cargo, empleado=None):
    filename = f"Manual_{cargo.replace(' ', '_').upper()}.pdf"
    abs_path = os.path.abspath(filename)
    HTML(string=html_content).write_pdf(abs_path)
    return abs_path

def extract_section(html, section_title):
    # Busca el bloque por título (ejemplo simple, mejora según tu IA)
    pattern = rf"<h2.*?>.*?{section_title}.*?</h2>(.*?)<h2"
    match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""

def create_manual_pdf_from_template(data, cargo, empleado=None):
    template_dir = os.path.dirname(__file__)
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("manual_template.html")
    html_content = template.render(**data)
    filename = f"Manual_{cargo.replace(' ', '_').upper()}.pdf"
    abs_path = os.path.abspath(filename)
    HTML(string=html_content).write_pdf(abs_path)
    return abs_path

def export_organigrama_pdf(cargos_info, descripcion_general, leyenda_colores, filename="Organigrama_Cargos.pdf"):
    """
    cargos_info: lista de dicts con keys: cargo, departamento, descripcion, empleados (lista)
    descripcion_general: texto generado por IA
    leyenda_colores: dict departamento -> color
    """
    template_html = """
    <!doctype html>
    <html lang=\"es\">
    <head>
      <meta charset=\"UTF-8\">
      <title>Organigrama Corporativo por Cargos</title>
      <style>
        @page { size: A4; margin: 25mm 20mm 25mm 20mm; }
        body { font-family: 'Inter', Arial, sans-serif; color: #222; background: #fff; }
        .header { text-align: center; margin-bottom: 40px; }
        .logo { height: 80px; margin-bottom: 10px; }
        .title { font-size: 2.5em; color: #003d6e; font-weight: bold; margin-bottom: 8px; }
        .subtitle { font-size: 1.2em; color: #00a8e1; margin-bottom: 18px; }
        .executive-summary { background: #f0f2f6; border-left: 5px solid #003d6e; padding: 18px; margin-bottom: 30px; font-size: 1.1em; }
        .cargo-grid { display: flex; flex-wrap: wrap; gap: 18px; justify-content: flex-start; }
        .cargo-card {
          flex: 1 1 320px;
          min-width: 320px;
          max-width: 370px;
          background: #fff;
          border-radius: 14px;
          border: 1.5px solid #e2e8f0;
          box-shadow: 0 2px 8px rgba(0,0,0,0.04);
          padding: 22px 18px 18px 18px;
          margin-bottom: 18px;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
        }
        .cargo-title { font-size: 1.3em; color: #003d6e; font-weight: bold; margin-bottom: 6px; }
        .cargo-depto { font-size: 1em; font-weight: 600; color: #00a8e1; margin-bottom: 8px; }
        .cargo-desc { font-size: 1.05em; color: #475569; margin-bottom: 10px; }
        .cargo-empleados { font-size: 1em; color: #222; margin-bottom: 4px; }
        .cargo-empleados ul { margin: 0 0 0 18px; }
        .cargo-empleados li { margin-bottom: 2px; }
        .footer { margin-top: 40px; text-align: right; font-size: 0.9em; color: #888; }
        .page-break { page-break-after: always; }
      </style>
    </head>
    <body>
      <div class=\"header\">
        <img src=\"https://i.imgur.com/9Qe5p7R.png\" class=\"logo\" alt=\"Logo Servinet\">
        <div class=\"title\">Organigrama Corporativo por Cargos</div>
        <div class=\"subtitle\">SERVINET - RRHH</div>
      </div>
      <div class=\"executive-summary\">
        <b>Resumen Ejecutivo:</b><br>
        {{ descripcion_general }}
      </div>
      <div class=\"cargo-grid\">
        {% for cargo in cargos_info %}
          <div class=\"cargo-card\">
            <div class=\"cargo-title\">{{ cargo.cargo }}</div>
            <div class=\"cargo-depto\">{{ cargo.departamento }}</div>
            <div class=\"cargo-desc\">{{ cargo.descripcion }}</div>
            <div class=\"cargo-empleados\">
              <b>Empleados:</b>
              <ul>
                {% for emp in cargo.empleados %}
                  <li>{{ emp }}</li>
                {% endfor %}
              </ul>
            </div>
          </div>
        {% endfor %}
      </div>
      <div class=\"footer\">
        Documento generado automáticamente por IA y RRHH. SERVINET 2024.
      </div>
    </body>
    </html>
    """
    env = Environment(loader=FileSystemLoader("."))
    template = env.from_string(template_html)
    html_content = template.render(
        cargos_info=cargos_info,
        descripcion_general=descripcion_general,
        leyenda_colores=None
    )
    HTML(string=html_content).write_pdf(filename)
    return filename

# En manual_template.html, después de la portada
"""
<div class="pdf-page shadow-2xl mb-10 animate-fade-in">
  <div class="absolute inset-0 geometric-pattern"></div>
  <div class="content-wrapper h-full flex flex-col">
    <h2 class="font-display text-2xl font-bold text-gray-900 mb-4">Datos del Empleado</h2>
    <ul>
      <li><b>Nombre:</b> {{ empleado }}</li>
      <li><b>Cargo:</b> {{ cargo }}</li>
      <li><b>Departamento:</b> {{ departamento }}</li>
      <li><b>Fecha de Emisión:</b> {{ fecha_emision }}</li>
    </ul>
    <hr>
    {{ perfil_html | safe }}
  </div>
</div>
"""

st.markdown(f"""
<div class="empleado-card" style="background-color: white; padding: 32px; border-radius: 16px; border: 1.5px solid #e2e8f0; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.07);">
    <div style="font-size: 64px; margin-bottom: 10px;">👤</div>
    <h3 style="margin:0; color: #1e293b; font-size: 24px;">{seleccion}</h3>
    <p style="color: #3b82f6; font-weight: 600; font-size: 16px; margin-bottom: 20px;">{datos.get('CARGO', 'Sin Cargo')}</p>
    <div style="text-align: left; font-size: 15px; color: #475569; padding-top: 18px; border-top: 1px solid #f1f5f9;">
        <p style="margin: 8px 0;"><b>📧 Email:</b> {datos.get('CORREO', '--')}</p>
        <p style="margin: 8px 0;"><b>📱 Celular:</b> {datos.get('CELULAR', '--')}</p>
        <p style="margin: 8px 0;"><b>📍 Sede:</b> {datos.get('SEDE', '--')}</p>
        <p style="margin: 8px 0;"><b>🏢 Área:</b> {datos.get('AREA', '--')}</p>
        <p style="margin: 8px 0;"><b>🎯 Jefe:</b> {datos.get('JEFE_DIRECTO', 'N/A')}</p>
    </div>
</div>
""", unsafe_allow_html=True)
