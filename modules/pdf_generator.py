from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        # self.image('assets/logo.png', 10, 8, 33) # Descomentar si tienes logo
        self.set_font('Arial', 'B', 15)
        self.cell(80)
        self.cell(30, 10, 'SERVINET - Reporte de Desempeño', 0, 0, 'C')
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

def create_evaluation_pdf(empleado, cargo, puntaje, conclusiones, plan):
    pdf = PDF()
    pdf.add_page()
    
    # Titulo Empleado
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"Evaluación de: {empleado}", ln=True)
    pdf.cell(0, 10, f"Cargo: {cargo} | Puntaje Global: {puntaje}/100", ln=True)
    pdf.ln(10)
    
    # Conclusiones
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "1. Análisis de Desempeño:", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 10, conclusiones)
    pdf.ln(5)
    
    # Plan
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "2. Plan de Capacitación Sugerido:", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 10, plan)
    
    filename = f"Evaluacion_{empleado.replace(' ', '_')}.pdf"
    pdf.output(filename)
    return filename
