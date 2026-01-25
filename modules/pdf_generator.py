from fpdf import FPDF
from weasyprint import HTML
from jinja2 import Environment, FileSystemLoader
import os
import re
import datetime

class PDF(FPDF):
    def header(self):
        # Asegúrate de que la fuente DejaVu está registrada
        if 'dejavu' not in self.font_families:
            # La ruta puede necesitar ajuste dependiendo de dónde guardes la fuente
            font_path = os.path.join(os.path.dirname(__file__), 'fonts', 'DejaVuSans.ttf')
            if os.path.exists(font_path):
                self.add_font('DejaVu', '', font_path, uni=True)
        
        logo_path = 'logo_servinet.jpg'
        if os.path.exists(logo_path):
            self.image(logo_path, 10, 8, 33)
        
        self.set_font('DejaVu', 'B', 15)
        self.cell(80)
        self.cell(30, 10, 'Manual de Funciones', 0, 0, 'C')
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font('DejaVu', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def clean_html_to_text(html):
    text = re.sub(r'<.*?>', '', html)
    text = text.replace('&nbsp;', ' ')
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n+', '\n', text)
    return text.strip()

def create_manual_pdf(cargo, perfil_html, empleado=None):
    pdf = PDF()
    font_path = os.path.join(os.path.dirname(__file__), 'fonts', 'DejaVuSans.ttf')
    if os.path.exists(font_path):
        pdf.add_font('DejaVu', '', font_path, uni=True)
    pdf.set_font('DejaVu', '', 12)
    pdf.add_page()
    
    clean_text = clean_html_to_text(perfil_html)
    pdf.multi_cell(0, 10, clean_text)
    
    filename = f"Manual_{cargo.replace(' ', '_')}"
    if empleado:
        filename += f"_{empleado.replace(' ', '_')}"
    filename += ".pdf"
    
    abs_path = os.path.abspath(filename)
    pdf.output(abs_path)
    return abs_path

def create_manual_pdf_from_html(html_content, cargo, empleado=None):
    filename = f"Manual_{cargo.replace(' ', '_')}"
    if empleado:
        filename += f"_{empleado.replace(' ', '_')}"
    filename += ".pdf"
    abs_path = os.path.abspath(filename)
    HTML(string=html_content).write_pdf(abs_path)
    return abs_path

def extract_section(html, section_title):
    pattern = re.compile(f'<h3[^>]*>{re.escape(section_title)}</h3>\s*<ul[^>]*>(.*?)</ul>', re.DOTALL | re.IGNORECASE)
    match = pattern.search(html)
    if match:
        return match.group(1).strip()
    return ""

def create_manual_pdf_from_template(data, cargo, empleado=None):
    template_dir = os.path.dirname(__file__)
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("manual_template.html")
    
    html_content = template.render(data)
    
    filename = f"Manual_{cargo.replace(' ', '_').upper()}.pdf"
    abs_path = os.path.abspath(filename)
    
    HTML(string=html_content, base_url=template_dir).write_pdf(abs_path)
    
    return abs_path

# --- MEJORA 2: FUNCIÓN COMPLETA Y CONECTADA PARA EL PDF DEL ORGANIGRAMA ---
def export_organigrama_pdf(cargos_info, descripcion_general, empresa_nombre="SERVINET", filename="Organigrama_Cargos.pdf"):
    """
    Genera un PDF profesional del organigrama usando la nueva plantilla unificada y corregida.
    """
    template_dir = os.path.dirname(__file__)
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("organigrama_template.html")
    logo_path = os.path.abspath("logo_servinet.jpg") if os.path.exists("logo_servinet.jpg") else None

    # MEJORA: Paleta de colores para los departamentos, unificada y profesional
    colores_departamento = {
        "ADMINISTRATIVO": "#facc15", # Amarillo
        "OPERATIVO": "#4ade80",      # Verde
        "FINANZAS": "#f87171",       # Rojo
        "COMERCIAL": "#60a5fa",      # Azul
        "RRHH": "#f472b6",           # Rosa
        "TECNOLOGÍA": "#a78bfa",     # Púrpura
        "LOGÍSTICA": "#34d399",      # Esmeralda
        "DIRECCIÓN": "#fbbf24",      # Ámbar
        "JURÍDICO": "#e879f9",       # Fucsia
        "MARKETING": "#fb923c",      # Naranja
        "OTROS": "#9ca3af"           # Gris
    }

    html_content = template.render(
        cargos_info=cargos_info,
        descripcion_general=descripcion_general,
        empresa=empresa_nombre,
        colores_depto=colores_departamento, # Pasamos la paleta de colores
        logo_url=logo_path,
        now=datetime.datetime.now()
    )
    HTML(string=html_content, base_url=template_dir).write_pdf(filename)
    return filename

def export_organigrama_pdf_master(df_empleados, descripcion_general, empresa_nombre="SERVINET", filename="Organigrama_Cargos.pdf"):
    """
    Genera un PDF profesional del organigrama usando la plantilla master.
    """
    from jinja2 import Environment, FileSystemLoader
    from weasyprint import HTML
    import datetime
    import os

    template_dir = os.path.dirname(__file__)
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("organigrama_template.html")
    logo_path = os.path.abspath("logo_servinet.jpg") if os.path.exists("logo_servinet.jpg") else None

    # Agrupa empleados por departamento y cargo
    data_grouped = {}
    for _, row in df_empleados.iterrows():
        depto = row.get("DEPARTAMENTO", "OTROS")
        cargo = row.get("CARGO", "Sin Cargo")
        if depto not in data_grouped:
            data_grouped[depto] = []
        # Busca si ya existe el cargo en el departamento
        cargo_entry = next((c for c in data_grouped[depto] if c["cargo"] == cargo), None)
        emp_dict = {
            "nombre": row.get("NOMBRE COMPLETO", ""),
            "email": row.get("CORREO", ""),
            "telefono": row.get("CELULAR", ""),
            "ubicacion": row.get("SEDE", ""),
            "modalidad": row.get("MODALIDAD", "Oficina"),
            "foto_url": row.get("FOTO_URL", ""),
        }
        if cargo_entry:
            cargo_entry["empleados"].append(emp_dict)
        else:
            cargo_entry = {
                "cargo": cargo,
                "descripcion": row.get("DESCRIPCION_CARGO", ""),  # O usa IA si quieres
                "empleados": [emp_dict]
            }
            data_grouped[depto].append(cargo_entry)

    # KPIs
    total_empleados = len(df_empleados)
    total_departamentos = len(data_grouped)
    fecha_actual = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

    html_content = template.render(
        empresa=empresa_nombre,
        logo_url=logo_path,
        now=datetime.datetime.now(),
        descripcion_general=descripcion_general,
        data_grouped=data_grouped,
        total_empleados=total_empleados,
        total_departamentos=total_departamentos,
        fecha_actual=fecha_actual
    )
    HTML(string=html_content, base_url=template_dir).write_pdf(filename)
    return filename

# --- BLOQUE DE EJEMPLO, AHORA CORRECTAMENTE COMENTADO PARA NO CAUSAR ERRORES ---
"""
El siguiente bloque es solo un ejemplo de cómo usar las funciones en tus páginas.
No debe ejecutarse directamente en este módulo.

# En manual_template.html, después de la portada
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

# EJEMPLO DE USO (colócalo en tu página, no aquí):

cargos_info = []
for _, row in df_cargos.iterrows():
    desc_cargo = "Descripción no generada."
    # La variable 'openai_client' debe estar definida en la página que usa este código.
    if 'openai_client' in locals() and openai_client:
        try:
            prompt_cargo = f"Describe brevemente en una línea el propósito del cargo '{row['CARGO']}' en el departamento '{row['DEPARTAMENTO']}' para una empresa de telecomunicaciones."
            resp = openai_client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt_cargo}], temperature=0.2)
            desc_cargo = resp.choices[0].message.content.strip()
        except Exception as e:
            desc_cargo = f"Error IA: {e}"
    cargos_info.append({
        "cargo": row['CARGO'],
        "departamento": row['DEPARTAMENTO'],
        "descripcion": desc_cargo,
        "empleados": row['NOMBRE_COMPLETO']  # Esto debe ser una lista, no string
    })
"""

