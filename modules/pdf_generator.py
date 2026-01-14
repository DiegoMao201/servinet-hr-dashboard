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
    <html lang="es">
    <head>
      <meta charset="UTF-8">
      <title>Organigrama por Cargos</title>
      <style>
        body { font-family: 'Inter', Arial, sans-serif; color: #222; background: #fff; }
        .header { text-align: center; margin-bottom: 30px; }
        .title { font-size: 2.2em; color: #003d6e; font-weight: bold; margin-bottom: 10px; }
        .subtitle { font-size: 1.1em; color: #00a8e1; margin-bottom: 20px; }
        .leyenda { margin-bottom: 20px; }
        .leyenda span { display: inline-block; width: 18px; height: 18px; border-radius: 4px; margin-right: 6px; vertical-align: middle; }
        .descripcion { background: #e6f7ff; border-left: 4px solid #00a8e1; padding: 10px; margin-bottom: 25px; font-size: 1.1em; }
        .cargo-card { border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 28px; padding: 22px; background: #f8fafc; }
        .cargo-title { font-size: 1.5em; color: #003d6e; font-weight: bold; margin-bottom: 6px; }
        .cargo-depto { font-size: 1em; font-weight: bold; padding: 3px 12px; border-radius: 10px; margin-bottom: 8px; display: inline-block; }
        .cargo-desc { font-size: 1.08em; color: #475569; margin-bottom: 12px; }
        .cargo-empleados { font-size: 1.05em; color: #222; margin-bottom: 4px; }
        .cargo-empleados ul { margin: 0 0 0 18px; }
        .cargo-empleados li { margin-bottom: 2px; }
        .divider { border-top: 2px solid #e2e8f0; margin: 18px 0 18px 0; }
        .footer { margin-top: 40px; text-align: right; font-size: 0.9em; color: #888; }
      </style>
    </head>
    <body>
      <div class="header">
        <div class="title">Organigrama Corporativo por Cargos</div>
        <div class="subtitle">SERVINET - RRHH</div>
      </div>
      <div class="leyenda">
        <b>Leyenda de Departamentos:</b><br>
        {% for dept, color in leyenda_colores.items() %}
          <span style="background:{{ color }};"></span> {{ dept }} &nbsp;
        {% endfor %}
      </div>
      <div class="descripcion">
        <b>Descripción General:</b><br>
        {{ descripcion_general }}
      </div>
      {% for cargo in cargos_info %}
        <div class="cargo-card">
          <div class="cargo-title">{{ cargo.cargo }}</div>
          <div class="cargo-depto" style="background:{{ leyenda_colores.get(cargo.departamento, '#f1f5f9') }};">
            {{ cargo.departamento }}
          </div>
          <div class="cargo-desc"><b>Descripción del Cargo:</b><br>{{ cargo.descripcion }}</div>
          <div class="cargo-empleados">
            <b>Empleados en este cargo:</b>
            <ul>
              {% for emp in cargo.empleados %}
                <li>👤 {{ emp }}</li>
              {% endfor %}
            </ul>
          </div>
        </div>
        <div class="divider"></div>
      {% endfor %}
      <div class="footer">
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
        leyenda_colores=leyenda_colores
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
