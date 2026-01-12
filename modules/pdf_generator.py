from fpdf import FPDF
import os
import re
from weasyprint import HTML
from jinja2 import Environment, FileSystemLoader

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

def create_manual_pdf_from_template(data, cargo, empleado=None):
    template_dir = os.path.dirname(__file__)
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("manual_template.html")
    html_content = template.render(**data)
    filename = f"Manual_{cargo.replace(' ', '_').upper()}.pdf"
    abs_path = os.path.abspath(filename)
    HTML(string=html_content).write_pdf(abs_path)
    return abs_path
