import streamlit as st
import pandas as pd
import datetime
import textwrap
from collections import Counter
from streamlit_echarts import st_echarts 

# --- IMPORTACIÓN DE MÓDULOS LOCALES ---
try:
    from modules.database import get_employees, connect_to_drive, SPREADSHEET_ID
    from modules.drive_manager import (
        get_or_create_manuals_folder,
        upload_organigrama_to_drive,
        find_organigrama_in_drive,
        download_organigrama_from_drive,
        find_manual_in_drive,
        download_manual_from_drive
    )
    from modules.ai_brain import client as openai_client
    from modules.pdf_generator import export_organigrama_pdf
except ImportError as e:
    st.error(f"Error al importar módulos locales: {e}. Verifica que la carpeta 'modules' y los archivos existan.")
    st.stop()

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Organigrama Corporativo Pro", page_icon="🏢", layout="wide")

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .block-container {padding-top: 1rem; padding-bottom: 2rem;}
    h1 {color: #0f172a; font-family: 'Helvetica Neue', sans-serif;}
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f8fafc;
        border-radius: 8px 8px 0 0;
        gap: 10px;
        padding-top: 10px;
        padding-bottom: 10px;
        border: 1px solid #e2e8f0;
        border-bottom: none;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff;
        border-top: 3px solid #3b82f6;
        color: #1e3a8a;
        font-weight: bold;
        box-shadow: 0 -4px 6px -1px rgba(0,0,0,0.05);
    }
    div[data-testid="stForm"] {
        background-color: #f8fafc;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
    }
    .echarts-tooltip {
        max-height: 400px;
        overflow-y: auto;
    }
    </style>
""", unsafe_allow_html=True)

# --- FUNCIONES GLOBALES ---
def wrap_text_node(text, width=20):
    if not isinstance(text, str): return ""
    return "\n".join(textwrap.wrap(text, width=width))

def color_por_departamento(depto):
    colores = {
        "ADMINISTRATIVO": "#fef9c3",
        "OPERATIVO": "#dcfce7",
        "FINANZAS": "#fee2e2",
        "COMERCIAL": "#dbeafe",
        "RRHH": "#fce7f3",
        "TECNOLOGÍA": "#f3e8ff",
        "LOGÍSTICA": "#d1fae5",
        "DIRECCIÓN": "#fef08a",
        "JURÍDICO": "#fbcfe8",
        "MARKETING": "#ffedd5",
        "OTROS": "#f1f5f9"
    }
    if not depto:
        return "#f1f5f9"
    depto_norm = str(depto).strip().upper()
    return colores.get(depto_norm, "#f1f5f9")

# --- ENCABEZADO ---
col_logo, col_title = st.columns([1, 6])
with col_logo:
    try:
        st.image("logo_servinet.jpg", width=110)
    except:
        st.write("🏢")
with col_title:
    st.title("Gestión de Talento y Estructura Organizacional")
    now = datetime.datetime.now()
    st.markdown(f"**Vigencia:** Enero {now.year} - Diciembre {now.year} | **Actualizado:** {now.strftime('%d/%m/%Y')}")

# --- CARGA DE DATOS ---
df = get_employees()
if df.empty:
    st.error("❌ No se pudieron cargar los datos de empleados. Verifica la conexión a Google Sheets y el módulo database.")
    st.stop()

# --- CARGA DE CARPETA DE MANUALES/ORGANIGRAMA EN DRIVE ---
manuals_folder_id = get_or_create_manuals_folder()

tab1, tab2 = st.tabs(["🌳 Organigrama por Cargos", "👤 Ficha Técnica & Edición"])

# ======================================================================
# TAB 1: ORGANIGRAMA AGRUPADO POR CARGOS
# ======================================================================
with tab1:
    st.markdown("### 🔹 Mapa Estructural por Cargos")
    st.info("💡 **Interacción:** El organigrama muestra **CARGOS**. Haz clic o pasa el mouse sobre un cargo para ver la lista de **TODOS** los empleados que lo ocupan.")

    # --- Agrupación por cargo y jefe ---
    df_cargos = (
        df.groupby(["CARGO", "DEPARTAMENTO"], as_index=False)
        .agg({
            "NOMBRE COMPLETO": list,
            "CORREO": list,
            "CELULAR": list,
            "JEFE_DIRECTO": lambda x: x.mode()[0] if not x.mode().empty else "",
        })
    )

    # Determina el jefe de cada cargo (por mayoría)
    cargo_to_jefe = {}
    for _, row in df_cargos.iterrows():
        cargo = row["CARGO"]
        jefe = row["JEFE_DIRECTO"]
        cargo_to_jefe[cargo] = jefe

    # Encuentra el cargo raíz (el que no es jefe de nadie más)
    todos_cargos = set(df_cargos["CARGO"])
    todos_jefes = set(j for j in df_cargos["JEFE_DIRECTO"] if j)
    raices = list(todos_cargos - todos_jefes)
    # Si hay más de una raíz, elige "DIRECCIÓN GENERAL" si existe, si no, el primero
    root_cargo = "DIRECCIÓN GENERAL" if "DIRECCIÓN GENERAL" in raices else (raices[0] if raices else df_cargos["CARGO"].iloc[0])

    # Construye el árbol de cargos
    def build_tree(cargo, df_cargos, cargo_to_jefe):
        node_row = df_cargos[df_cargos["CARGO"] == cargo].iloc[0]
        hijos = [c for c, j in cargo_to_jefe.items() if j == cargo and c != cargo]
        children = [build_tree(h, df_cargos, cargo_to_jefe) for h in hijos]
        count_emp = len(node_row["NOMBRE COMPLETO"])
        cargo_display = wrap_text_node(cargo, width=18)
        formatted_label = f"{{title|{cargo_display}}}\n{{hr|}}\n{{subtitle|{count_emp} Personas}}"
        depto = node_row.get('DEPARTAMENTO', 'OTROS')
        bg_color = color_por_departamento(depto)
        lista_empleados = []
        nombres = node_row['NOMBRE COMPLETO']
        correos = node_row['CORREO']
        celulares = node_row['CELULAR']
        for i in range(len(nombres)):
            lista_empleados.append({
                "nombre": nombres[i],
                "correo": correos[i] if i < len(correos) else "",
                "celular": celulares[i] if i < len(celulares) else ""
            })
        return {
            "name": formatted_label,
            "value": count_emp,
            "children": children,
            "tooltip_info": {
                "cargo": cargo,
                "departamento": depto,
                "area": "",
                "empleados": lista_empleados
            },
            "itemStyle": {
                "color": bg_color,
                "borderColor": "#94a3b8",
                "borderWidth": 1,
                "borderRadius": 4,
                "shadowBlur": 5,
                "shadowColor": "rgba(0,0,0,0.1)"
            }
        }

    try:
        tree_data = build_tree(root_cargo, df_cargos, cargo_to_jefe)
        option = {
            "tooltip": {
                "trigger": 'item',
                "triggerOn": 'mousemove|click',
                "enterable": True,
                "formatter": """
        function(params) {
            var info = params.data.tooltip_info;
            if (!info) return '';
            var sDiv = 'font-family: sans-serif; min-width: 250px; max-height: 300px; overflow-y: auto; padding: 10px; border-radius: 4px; background: white; box-shadow: 0 2px 10px rgba(0,0,0,0.2); text-align: left;';
            var sH4 = 'margin:0 0 5px 0; color: #1e3a8a; border-bottom: 2px solid #3b82f6; padding-bottom: 5px;';
            var sInfo = 'font-size: 11px; color: #64748b; margin-bottom: 8px;';
            var sTable = 'width: 100%; border-collapse: collapse; font-size: 12px;';
            var sTh = 'padding: 4px; background: #f1f5f9; text-align: left; color: #333;';
            var sTd = 'padding: 6px 4px; border-bottom: 1px solid #e2e8f0;';
            var html = '<div style="' + sDiv + '">';
            html += '<h4 style="' + sH4 + '">' + info.cargo + '</h4>';
            html += '<div style="' + sInfo + '">';
            html += '<b>Depto:</b> ' + info.departamento + ' | <b>Total:</b> ' + info.empleados.length;
            html += '</div>';
            html += '<table style="' + sTable + '">';
            html += '<tr><th style="' + sTh + '">Empleado</th><th style="' + sTh + '">Contacto</th></tr>';
            for (var i = 0; i < info.empleados.length; i++) {
                var emp = info.empleados[i];
                var correoShow = emp.correo ? emp.correo : '';
                var celShow = emp.celular ? emp.celular : '';
                html += '<tr>';
                html += '<td style="' + sTd + ' color: #334155;"><b>' + emp.nombre + '</b></td>';
                html += '<td style="' + sTd + ' color: #64748b;">' + celShow + '<br><span style="font-size: 10px; color: #94a3b8;">' + correoShow + '</span></td>';
                html += '</tr>';
            }
            html += '</table></div>';
            return html;
        }
    """
            },
            "series": [
                {
                    "type": "tree",
                    "data": [tree_data],
                    "left": '1%',
                    "right": '1%',
                    "top": '5px',
                    "bottom": '5px',
                    "orient": 'TB',
                    "layout": 'orthogonal',
                    "symbol": 'rect',
                    "symbolSize": [260, 70],
                    "roam": True,
                    "initialTreeDepth": 2,
                    "expandAndCollapse": True,
                    "edgeShape": "polyline",
                    "edgeForkPosition": "50%",
                    "lineStyle": {
                        "color": "#3b82f6",
                        "width": 2,
                        "curveness": 0
                    },
                    "label": {
                        "show": True,
                        "position": 'inside',
                        "color": '#1e293b',
                        "fontSize": 16,
                        "rich": {
                            "title": {"color": "#003d6e", "fontSize": 18, "fontWeight": "bold", "align": "center", "lineHeight": 22, "padding": [0, 5, 0, 5]},
                            "hr": {"borderColor": "#cbd5e1", "width": "100%", "borderWidth": 0.5, "height": 0, "margin": [5, 0, 5, 0]},
                            "subtitle": {"color": "#475569", "fontSize": 13, "align": "center", "lineHeight": 14, "padding": [2, 0, 0, 0]}
                        }
                    },
                    "itemStyle": {
                        "color": "#f8fafc",
                        "borderColor": "#3b82f6",
                        "borderWidth": 2,
                        "borderRadius": 14,
                        "shadowBlur": 12,
                        "shadowColor": "rgba(59,130,246,0.10)"
                    },
                    "animationDuration": 350,
                    "animationDurationUpdate": 450
                }
            ]
        }
        st_echarts(options=option, height="900px")
    except Exception as e:
        st.error(f"Error crítico al generar organigrama por cargos: {e}")

    st.markdown("### 📂 Organigrama PDF Guardado")
    organigrama_file_id = find_organigrama_in_drive(manuals_folder_id)
    if organigrama_file_id:
        pdf_bytes = download_organigrama_from_drive(organigrama_file_id)
        st.download_button(
            label="📥 Descargar Organigrama PDF Guardado",
            data=pdf_bytes,
            file_name="Organigrama_Cargos.pdf",
            mime="application/pdf"
        )
        st.info("Mostrando organigrama guardado. Si deseas actualizarlo, usa el botón de arriba.")
    else:
        st.warning("No hay organigrama guardado. Genera uno para almacenarlo en Drive.")

    # --- Construye la lista de cargos_info ---
    cargos_info = []
    for idx, row in df_cargos_final.iterrows():
        cargo = row['CARGO']
        departamento = row['DEPARTAMENTO']
        empleados = row['NOMBRE COMPLETO']
        prompt_cargo = f"Describe brevemente el cargo '{cargo}' en el departamento '{departamento}' para una empresa de telecomunicaciones."
        desc_cargo = ""
        if openai_client:
            try:
                resp = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt_cargo}],
                    temperature=0.2
                )
                desc_cargo = resp.choices[0].message.content.strip()
            except:
                desc_cargo = "Sin descripción IA."
        cargos_info.append({
            "cargo": cargo,
            "departamento": departamento,
            "descripcion": desc_cargo,
            "empleados": empleados
        })

    def generar_descripcion_general_organigrama(cargos_info):
        if not openai_client:
            return "Descripción no disponible (falta API KEY de OpenAI)."
        prompt = f"""
Eres consultor senior en RRHH. Resume y describe el organigrama de la empresa SERVINET, en un párrafo ejecutivo (máximo 7 líneas), resaltando estructura, fortalezas y oportunidades, basado en los siguientes cargos y departamentos:
{[ (c['cargo'], c['departamento'], len(c['empleados'])) for c in cargos_info ]}
Organiza la información con títulos claros, una estructura profesional. Usa listas para los cargos y empleados, y resalta los puntos clave. Incluye una visión estratégica, fortalezas y oportunidades de mejora.
El resultado debe estar en formato Markdown o HTML simple, con títulos, subtítulos y listas ordenadas o con viñetas.
"""
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        return response.choices[0].message.content.strip()

    descripcion_general = ""
    if openai_client:
        try:
            descripcion_general = generar_descripcion_general_organigrama(cargos_info)
        except:
            descripcion_general = "No se pudo generar descripción."

    if st.button("📄 Exportar Organigrama por Cargos a PDF"):
        with st.spinner("Generando PDF profesional..."):
            pdf_filename = export_organigrama_pdf(
                cargos_info=cargos_info,
                descripcion_general=descripcion_general,
                filename="Organigrama_Cargos.pdf"
            )
            upload_organigrama_to_drive(pdf_filename, manuals_folder_id)
            with open(pdf_filename, "rb") as f:
                st.download_button(
                    label="📥 Descargar PDF Organigrama",
                    data=f.read(),
                    file_name=pdf_filename,
                    mime="application/pdf"
                )
            st.success("PDF generado y guardado en Drive exitosamente.")

# ======================================================================
# TAB 2: FICHA DE EMPLEADO & EDICIÓN
# ======================================================================
with tab2:
    def get_col_index(sheet, col_name):
        headers = sheet.row_values(1)
        for idx, header in enumerate(headers, start=1):
            if header.strip().upper() == col_name.strip().upper():
                return idx
        return None

    def actualizar_empleado_google_sheets(
        nombre, cedula, cargo, departamento, jefe, sede, correo, celular, estado, salario, direccion, banco, estado_contrato
    ):
        try:
            client = connect_to_drive()
            spreadsheet = client.open_by_key(SPREADSHEET_ID)
            sheet = spreadsheet.worksheet("BD EMPLEADOS")
            data_gs = sheet.get_all_records()
            fila_encontrada = -1
            cedula_str = str(cedula).strip()
            for idx, row in enumerate(data_gs):
                if str(row.get("CEDULA", "")).strip() == cedula_str:
                    fila_encontrada = idx + 2
                    break
            if fila_encontrada > 0:
                updates = [
                    (get_col_index(sheet, "NOMBRE COMPLETO"), nombre),
                    (get_col_index(sheet, "CEDULA"), cedula),
                    (get_col_index(sheet, "CARGO"), cargo),
                    (get_col_index(sheet, "DEPARTAMENTO"), departamento),
                    (get_col_index(sheet, "JEFE_DIRECTO"), jefe),
                    (get_col_index(sheet, "SEDE"), sede),
                    (get_col_index(sheet, "CORREO"), correo),
                    (get_col_index(sheet, "CELULAR"), celular),
                    (get_col_index(sheet, "ESTADO"), estado),
                    (get_col_index(sheet, "SALARIO APORTES"), salario),
                    (get_col_index(sheet, "DIRECCIÓN DE RESIDENCIA"), direccion),
                    (get_col_index(sheet, "BANCO"), banco),
                    (get_col_index(sheet, "ESTADO_CONTRATO"), estado_contrato),
                ]
                for col_idx, val in updates:
                    if col_idx:
                        sheet.update_cell(fila_encontrada, col_idx, val)
                return True
            return False
        except Exception as e:
            st.error(f"Error técnico al guardar: {e}")
            return False

    st.markdown("##### 🔍 Filtros de Búsqueda")
    c1, c2, c3, c4 = st.columns(4)
    f_sede = c1.selectbox("Filtrar por Sede", ["Todas"] + sorted(df['SEDE'].dropna().unique()))
    f_dep = c2.selectbox("Filtrar por Depto", ["Todos"] + sorted(df['DEPARTAMENTO'].dropna().unique()))
    f_cargo = c3.selectbox("Filtrar por Cargo", ["Todos"] + sorted(df['CARGO'].dropna().unique()))
    f_estado = c4.selectbox("Filtrar por Estado", ["Todos"] + sorted(df['ESTADO'].dropna().unique()))

    df_filt = df.copy()
    if f_sede != "Todas": df_filt = df_filt[df_filt['SEDE'] == f_sede]
    if f_dep != "Todos": df_filt = df_filt[df_filt['DEPARTAMENTO'] == f_dep]
    if f_cargo != "Todos": df_filt = df_filt[df_filt['CARGO'] == f_cargo]
    if f_estado != "Todos": df_filt = df_filt[df_filt['ESTADO'] == f_estado]

    empleados_disponibles = sorted(df_filt['NOMBRE COMPLETO'].unique())
    if empleados_disponibles:
        seleccion = st.selectbox("Seleccionar Empleado para ver Detalle", empleados_disponibles)
        datos = df_filt[df_filt['NOMBRE COMPLETO'] == seleccion].iloc[0]
        st.markdown("---")
        col_card_izq, col_card_der = st.columns([1, 2])

        with col_card_izq:
            st.markdown(f"""
            <div style="background-color: white; padding: 28px; border-radius: 14px; border: 1.5px solid #e2e8f0; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.07);">
                <div style="font-size: 64px; margin-bottom: 10px;">👤</div>
                <h3 style="margin:0; color: #1e293b; font-size: 24px;">{seleccion}</h3>
                <p style="color: #3b82f6; font-weight: 600; font-size: 16px; margin-bottom: 20px;">{datos.get('CARGO', 'Sin Cargo')}</p>
                <div style="text-align: left; font-size: 15px; color: #475569; padding-top: 18px; border-top: 1px solid #f1f5f9;">
                    <p style="margin: 8px 0;"><b>📧 Email:</b> {datos.get('CORREO', '--')}</p>
                    <p style="margin: 8px 0;"><b>📱 Celular:</b> {datos.get('CELULAR', '--')}</p>
                    <p style="margin: 8px 0;"><b>📍 Sede:</b> {datos.get('SEDE', '--')}</p>
                    <p style="margin: 8px 0;"><b>🏢 Departamento:</b> {datos.get('DEPARTAMENTO', '--')}</p>
                    <p style="margin: 8px 0;"><b>🎯 Jefe:</b> {datos.get('JEFE_DIRECTO', 'N/A')}</p>
                    <p style="margin: 8px 0;"><b>💰 Salario:</b> {datos.get('SALARIO APORTES', '--')}</p>
                    <p style="margin: 8px 0;"><b>🏦 Banco:</b> {datos.get('BANCO', '--')}</p>
                    <p style="margin: 8px 0;"><b>🏠 Dirección:</b> {datos.get('DIRECCIÓN DE RESIDENCIA', '--')}</p>
                    <p style="margin: 8px 0;"><b>📄 Estado Contrato:</b> {datos.get('ESTADO_CONTRATO', '--')}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.write(" ")
            st.markdown("##### 📄 Manual de Funciones")
            with st.spinner("Buscando manual de funciones..."):
                cargo_actual = datos.get("CARGO", "")
                manual_file_id = find_manual_in_drive(cargo_actual, manuals_folder_id)
            if manual_file_id:
                pdf_bytes = download_manual_from_drive(manual_file_id)
                st.download_button(
                    label="📥 Descargar Manual de Funciones PDF",
                    data=pdf_bytes,
                    file_name=f"Manual_{cargo_actual.replace(' ', '_').upper()}.pdf",
                    mime="application/pdf"
                )
                st.info("Manual de funciones disponible.")
            else:
                st.warning("No hay manual de funciones guardado para este cargo.")

        with col_card_der:
            st.subheader("📝 Edición de Información")
            with st.form("form_edicion"):
                c_a, c_b = st.columns(2)
                nuevo_nombre = c_a.text_input("Nombre Completo", value=datos.get("NOMBRE COMPLETO", ""))
                nuevo_cedula = c_b.text_input("Cédula (ID Único)", value=datos.get("CEDULA", ""), disabled=True)
                nuevo_cargo = c_a.text_input("Cargo", value=datos.get("CARGO", ""))
                nuevo_departamento = c_b.text_input("Departamento", value=datos.get("DEPARTAMENTO", ""))
                nuevo_jefe = c_a.text_input("Jefe Directo", value=datos.get("JEFE_DIRECTO", ""))
                nueva_sede = c_b.text_input("Sede", value=datos.get("SEDE", ""))
                nuevo_correo = c_a.text_input("Correo Electrónico", value=datos.get("CORREO", ""))
                nuevo_cel = c_b.text_input("Celular", value=datos.get("CELULAR", ""))
                nuevo_estado = c_a.text_input("Estado", value=datos.get("ESTADO", ""))
                nuevo_salario = c_b.text_input("Salario", value=datos.get("SALARIO APORTES", ""))
                nuevo_direccion = c_a.text_input("Dirección de Residencia", value=datos.get("DIRECCIÓN DE RESIDENCIA", ""))
                nuevo_banco = c_b.text_input("Banco", value=datos.get("BANCO", ""))
                nuevo_estado_contrato = c_a.text_input("Estado Contrato", value=datos.get("ESTADO_CONTRATO", ""))

                st.markdown("---")
                submitted = st.form_submit_button("💾 Guardar Cambios en Base de Datos", use_container_width=True)
                if submitted:
                    with st.spinner("Conectando con Google Sheets..."):
                        exito = actualizar_empleado_google_sheets(
                            nuevo_nombre, nuevo_cedula, nuevo_cargo, nuevo_departamento, nuevo_jefe,
                            nueva_sede, nuevo_correo, nuevo_cel, nuevo_estado, nuevo_salario,
                            nuevo_direccion, nuevo_banco, nuevo_estado_contrato
                        )
                        if exito:
                            st.success("✅ ¡Datos actualizados exitosamente!")
                            st.cache_data.clear()
                            import time
                            time.sleep(1.5)
                            st.rerun()
                        else:
                            st.error("❌ Error al actualizar. Verifica que la cédula no haya cambiado.")
    else:
        st.warning("⚠️ No se encontraron empleados con los filtros seleccionados.")