import streamlit as st
import pandas as pd
import datetime
import textwrap
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

# --- ESTILOS CSS PROFESIONALES ---
st.markdown("""
    <style>
    .block-container {padding-top: 1rem; padding-bottom: 2rem;}
    h1, h2, h3 {color: #0f172a; font-family: 'Helvetica Neue', sans-serif;}
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px; white-space: pre-wrap; background-color: #f8fafc;
        border-radius: 8px 8px 0 0; border: 1px solid #e2e8f0; border-bottom: none;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff; border-top: 3px solid #3b82f6;
        color: #1e3a8a; font-weight: bold; box-shadow: 0 -4px 6px -1px rgba(0,0,0,0.05);
    }
    div[data-testid="stForm"] { background-color: #f8fafc; padding: 20px; border-radius: 10px; border: 1px solid #e2e8f0; }
    </style>
""", unsafe_allow_html=True)

# --- FUNCIONES GLOBALES ---
def wrap_text_node(text, width=20):
    if not isinstance(text, str): return ""
    return "\n".join(textwrap.wrap(text, width=width))

def color_por_departamento(depto):
    colores = {
        "ADMINISTRATIVO": "#fef9c3", "OPERATIVO": "#dcfce7", "FINANZAS": "#fee2e2",
        "COMERCIAL": "#dbeafe", "RRHH": "#fce7f3", "TECNOLOGÍA": "#f3e8ff",
        "LOGÍSTICA": "#d1fae5", "DIRECCIÓN": "#fef08a", "JURÍDICO": "#fbcfe8",
        "MARKETING": "#ffedd5", "OTROS": "#f1f5f9"
    }
    return colores.get(str(depto).strip().upper(), "#f1f5f9")

# --- ENCABEZADO ---
col_logo, col_title = st.columns([1, 6])
with col_logo:
    st.image("logo_servinet.jpg", width=110)
with col_title:
    st.title("Gestión de Talento y Estructura Organizacional")
    now = datetime.datetime.now()
    st.markdown(f"**Vigencia:** Enero {now.year} - Diciembre {now.year} | **Actualizado:** {now.strftime('%d/%m/%Y')}")

# --- CARGA DE DATOS ---
df = get_employees()
if df.empty:
    st.error("❌ No se pudieron cargar los datos de empleados. Verifica la conexión a Google Sheets.")
    st.stop()

manuals_folder_id = get_or_create_manuals_folder()
tab1, tab2 = st.tabs(["🌳 Organigrama por Cargos", "👤 Ficha Técnica & Edición"])

# ======================================================================
# TAB 1: ORGANIGRAMA "SUPER PROFESIONAL"
# ======================================================================
with tab1:
    st.markdown("### 🔹 Mapa Estructural por Cargos")
    st.info("💡 **Interacción:** El organigrama muestra la jerarquía real de **CARGOS**. Haz clic o pasa el mouse sobre un cargo para ver la lista de empleados.")

    # 1. Agrupar empleados por cargo y determinar el jefe del cargo (por mayoría)
    df_cargos = (
        df.groupby(["CARGO", "DEPARTAMENTO"], as_index=False)
        .agg(
            NOMBRE_COMPLETO=("NOMBRE COMPLETO", list),
            CORREO=("CORREO", list),
            CELULAR=("CELULAR", list),
            JEFE_DIRECTO_CARGO=("JEFE_DIRECTO", lambda x: x.mode()[0] if not x.mode().empty else None)
        )
    )

    # 2. Mapear el nombre del jefe (persona) al cargo del jefe
    nombre_a_cargo = df.set_index('NOMBRE COMPLETO')['CARGO'].to_dict()
    df_cargos['PARENT_CARGO'] = df_cargos['JEFE_DIRECTO_CARGO'].map(nombre_a_cargo)

    # 3. Construir el árbol jerárquico
    nodes = {row['CARGO']: {"name": row['CARGO'], "data": row.to_dict(), "children": []} for _, row in df_cargos.iterrows()}
    forest = []
    for cargo, node in nodes.items():
        parent_cargo = node['data'].get('PARENT_CARGO')
        if parent_cargo and parent_cargo in nodes and parent_cargo != cargo:
            nodes[parent_cargo]['children'].append(node)
        else:
            forest.append(node)
    
    tree_data = {"name": "SERVINET", "data": {"CARGO": "SERVINET", "DEPARTAMENTO": "DIRECCIÓN", "NOMBRE_COMPLETO": []}, "children": forest} if len(forest) > 1 else (forest[0] if forest else {})

    # 4. Función recursiva para dar formato Echarts
    def format_node_for_echarts(node):
        data = node['data']
        cargo, depto, empleados = data.get('CARGO', 'N/A'), data.get('DEPARTAMENTO', 'OTROS'), data.get('NOMBRE_COMPLETO', [])
        formatted_label = f"{{title|{wrap_text_node(cargo, 18)}}}\n{{hr|}}\n{{subtitle|{len(empleados)} Personas}}"
        
        return {
            "name": formatted_label, "value": len(empleados),
            "itemStyle": {"color": color_por_departamento(depto), "borderColor": "#3b82f6", "borderWidth": 1.5, "borderRadius": 12, "shadowBlur": 10, "shadowColor": "rgba(0,0,0,0.08)"},
            "tooltip_info": {
                "cargo": cargo, "departamento": depto,
                "empleados": [{"nombre": n, "correo": c, "celular": cel} for n, c, cel in zip(empleados, data.get('CORREO', []), data.get('CELULAR', []))]
            },
            "children": [format_node_for_echarts(child) for child in node.get('children', [])]
        }

    if tree_data:
        echarts_tree_data = format_node_for_echarts(tree_data)
        option = {
            "tooltip": {
                "trigger": 'item', "triggerOn": 'mousemove|click', "enterable": True,
                "formatter": """
                    function(params) {
                        var info = params.data.tooltip_info; if (!info) return '';
                        var html = `<div style="font-family: sans-serif; min-width: 280px; max-height: 350px; overflow-y: auto; padding: 12px; border-radius: 8px; background: white; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
                                    <h4 style="margin:0 0 8px 0; color: #1e3a8a; border-bottom: 2px solid #3b82f6; padding-bottom: 6px;">${info.cargo}</h4>
                                    <div style="font-size: 12px; color: #475569; margin-bottom: 10px;"><b>Departamento:</b> ${info.departamento} | <b>Total:</b> ${info.empleados.length}</div>
                                    <table style="width: 100%; border-collapse: collapse; font-size: 12px;">`;
                        info.empleados.forEach(function(emp) { html += `<tr style="border-bottom: 1px solid #e2e8f0;"><td style="padding: 6px 4px; color: #334155;"><b>${emp.nombre}</b></td></tr>`; });
                        html += `</table></div>`; return html;
                    }
                """
            },
            "series": [{"type": "tree", "data": [echarts_tree_data], "left": '2%', "right": '2%', "top": '8%', "bottom": '8%', "orient": 'TB', "layout": 'orthogonal', "symbol": 'rect', "symbolSize": [220, 65], "roam": True, "initialTreeDepth": 3, "expandAndCollapse": True, "edgeShape": "polyline", "edgeForkPosition": "50%", "lineStyle": {"color": "#94a3b8", "width": 1.5},
                "label": {"show": True, "position": 'inside', "color": '#1e293b', "fontSize": 14, "rich": {
                        "title": {"color": "#003d6e", "fontSize": 15, "fontWeight": "bold", "align": "center", "lineHeight": 18},
                        "hr": {"borderColor": "#cbd5e1", "width": "100%", "borderWidth": 0.5, "height": 0, "margin": [4, 0, 4, 0]},
                        "subtitle": {"color": "#475569", "fontSize": 11, "align": "center", "lineHeight": 12}
                }}, "animationDurationUpdate": 600
            }]
        }
        st_echarts(options=option, height="950px")
    else:
        st.error("No se pudo construir la jerarquía del organigrama.")

    st.markdown("---")
    st.markdown("### 📂 Gestión del Organigrama en PDF")
    
    col_pdf1, col_pdf2 = st.columns(2)

    with col_pdf1:
        st.markdown("#### Generar y Guardar Nueva Versión")
        if st.button("📄 Crear PDF con IA y Subir a Drive"):
            with st.spinner("Generando descripciones con IA y creando PDF..."):
                # 1. Preparar datos para la IA y el PDF
                cargos_info = []
                for _, row in df_cargos.iterrows():
                    desc_cargo = "Descripción no generada."
                    if openai_client:
                        try:
                            prompt_cargo = f"Describe brevemente en una línea el propósito del cargo '{row['CARGO']}' en el departamento '{row['DEPARTAMENTO']}' para una empresa de telecomunicaciones."
                            resp = openai_client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt_cargo}], temperature=0.2)
                            desc_cargo = resp.choices[0].message.content.strip()
                        except Exception as e:
                            desc_cargo = f"Error IA: {e}"
                    cargos_info.append({"cargo": row['CARGO'], "departamento": row['DEPARTAMENTO'], "descripcion": desc_cargo, "empleados": row['NOMBRE_COMPLETO']})

                # 2. Generar descripción general con IA
                descripcion_general = "Análisis no disponible."
                if openai_client:
                    try:
                        prompt_general = f"Eres consultor senior en RRHH. Resume el organigrama de SERVINET en un párrafo ejecutivo (máximo 7 líneas), basado en estos cargos: {[c['cargo'] for c in cargos_info]}. Resalta la estructura y distribución de roles."
                        resp_gen = openai_client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt_general}], temperature=0.2)
                        descripcion_general = resp_gen.choices[0].message.content.strip()
                    except Exception as e:
                        descripcion_general = f"Error IA: {e}"

                # 3. Generar y subir el PDF
                pdf_filename = export_organigrama_pdf(cargos_info=cargos_info, descripcion_general=descripcion_general)
                upload_organigrama_to_drive(pdf_filename, manuals_folder_id)
                st.success("✅ PDF generado y guardado en Drive exitosamente.")
                st.rerun()

    with col_pdf2:
        st.markdown("#### Descargar Versión Guardada")
        organigrama_file_id = find_organigrama_in_drive(manuals_folder_id)
        if organigrama_file_id:
            pdf_bytes = download_organigrama_from_drive(organigrama_file_id)
            st.download_button(label="📥 Descargar Organigrama PDF de Drive", data=pdf_bytes, file_name="Organigrama_Cargos_SERVINET.pdf", mime="application/pdf", use_container_width=True)
        else:
            st.warning("No hay un organigrama guardado en Drive. Genéralo primero.")

# ======================================================================
# TAB 2: FICHA DE EMPLEADO & EDICIÓN (CORREGIDO Y MEJORADO)
# ======================================================================
with tab2:
    def actualizar_empleado_google_sheets(cedula, updates_dict):
        try:
            client = connect_to_drive()
            spreadsheet = client.open_by_key(SPREADSHEET_ID)
            sheet = spreadsheet.worksheet("BD EMPLEADOS")
            cell = sheet.find(str(cedula))
            if not cell: return False
            
            headers = sheet.row_values(1)
            col_map = {header.strip().upper(): i + 1 for i, header in enumerate(headers)}
            
            for key, value in updates_dict.items():
                col_idx = col_map.get(key.strip().upper())
                if col_idx: sheet.update_cell(cell.row, col_idx, value)
            return True
        except Exception as e:
            st.error(f"Error técnico al guardar: {e}"); return False

    st.markdown("##### 🔍 Filtros de Búsqueda")
    c1, c2, c3, c4 = st.columns(4)
    df_filt = df.copy()
    f_sede_val = c1.selectbox("Sede", ["Todas"] + sorted(df['SEDE'].dropna().unique()), key="f_sede_tab2")
    if f_sede_val != "Todas": df_filt = df_filt[df_filt['SEDE'] == f_sede_val]
    f_dep_val = c2.selectbox("Depto", ["Todos"] + sorted(df['DEPARTAMENTO'].dropna().unique()), key="f_dep_tab2")
    if f_dep_val != "Todos": df_filt = df_filt[df_filt['DEPARTAMENTO'] == f_dep_val]
    f_cargo_val = c3.selectbox("Cargo", ["Todos"] + sorted(df['CARGO'].dropna().unique()), key="f_cargo_tab2")
    if f_cargo_val != "Todos": df_filt = df_filt[df_filt['CARGO'] == f_cargo_val]
    f_estado_val = c4.selectbox("Estado", ["Todos"] + sorted(df['ESTADO'].dropna().unique()), key="f_estado_tab2")
    if f_estado_val != "Todos": df_filt = df_filt[df_filt['ESTADO'] == f_estado_val]

    empleados_disponibles = sorted(df_filt['NOMBRE COMPLETO'].unique())
    if empleados_disponibles:
        seleccion = st.selectbox("Seleccionar Empleado", empleados_disponibles, key="sel_emp_tab2")
        datos = df_filt[df_filt['NOMBRE COMPLETO'] == seleccion].iloc[0]
        st.markdown("---")
        col_card_izq, col_card_der = st.columns([1, 2])

        with col_card_izq:
            st.markdown(f"""<div style="background-color: white; padding: 28px; border-radius: 14px; border: 1.5px solid #e2e8f0; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.07);">
                <div style="font-size: 64px; margin-bottom: 10px;">👤</div>
                <h3 style="margin:0; color: #1e293b; font-size: 24px;">{seleccion}</h3>
                <p style="color: #3b82f6; font-weight: 600; font-size: 16px; margin-bottom: 20px;">{datos.get('CARGO', 'N/A')}</p>
                <div style="text-align: left; font-size: 15px; color: #475569; padding-top: 18px; border-top: 1px solid #f1f5f9;">
                    <p style="margin: 8px 0;"><b>📧 Email:</b> {datos.get('CORREO', '--')}</p>
                    <p style="margin: 8px 0;"><b>📱 Celular:</b> {datos.get('CELULAR', '--')}</p>
                    <p style="margin: 8px 0;"><b>📍 Sede:</b> {datos.get('SEDE', '--')}</p>
                    <p style="margin: 8px 0;"><b>🎯 Jefe:</b> {datos.get('JEFE_DIRECTO', 'N/A')}</p>
                </div></div>""", unsafe_allow_html=True)
            st.write(" "); st.markdown("##### 📄 Manual de Funciones")
            with st.spinner("Buscando manual..."):
                manual_file_id = find_manual_in_drive(datos.get("CARGO", ""), manuals_folder_id)
            if manual_file_id:
                pdf_bytes = download_manual_from_drive(manual_file_id)
                st.download_button("📥 Descargar Manual PDF", pdf_bytes, f"Manual_{datos.get('CARGO', '').replace(' ', '_')}.pdf", "application/pdf")
                
                # --- NUEVO: Botón para enviar por WhatsApp ---
                import urllib.parse
                # Genera un enlace de visualización de Google Drive (en vez de descarga directa)
                drive_url = f"https://drive.google.com/file/d/{manual_file_id}/view"
                nombre_empleado = datos.get("NOMBRE COMPLETO", "")
                cargo_empleado = datos.get("CARGO", "")
                mensaje = (
                    f"Hola {nombre_empleado},%0A%0A"
                    f"Te compartimos tu Manual de Funciones para el cargo de *{cargo_empleado}* en SERVINET.%0A"
                    "Este documento es clave para tu desarrollo profesional y para que tengas claridad sobre tus responsabilidades y oportunidades de crecimiento.%0A%0A"
                    f"Puedes consultarlo aquí:%0A{drive_url}%0A%0A"
                    "Si tienes dudas o sugerencias, no dudes en comunicarte.%0A%0A"
                    "Un saludo cordial,%0A"
                    "Psicóloga Carolina Perez%0A"
                    "Gestión Humana SERVINET"
                )
                mensaje_encoded = urllib.parse.quote(mensaje)
                celular = datos.get("CELULAR", "")
                st.markdown(f"""
                    <a href="https://web.whatsapp.com/send?phone={celular}&text={mensaje_encoded}" target="_blank">
                        <button style="
                            background-color:#25D366; 
                            color:white; 
                            border:none; 
                            padding:8px 18px; 
                            border-radius:5px; 
                            font-size:15px; 
                            cursor:pointer;
                            margin-top:8px;">
                            📲 Enviar Manual por WhatsApp
                        </button>
                    </a>
                """, unsafe_allow_html=True)
                st.success("Manual disponible y listo para socializar por WhatsApp.")
            else:
                st.warning("No hay manual para este cargo.")

        with col_card_der:
            st.subheader("📝 Edición de Información")
            with st.form("form_edicion"):
                updates = {}
                c_a, c_b = st.columns(2)
                updates["NOMBRE COMPLETO"] = c_a.text_input("Nombre Completo", value=datos.get("NOMBRE COMPLETO", ""))
                cedula_disabled = c_b.text_input("Cédula (ID Único)", value=datos.get("CEDULA", ""), disabled=True)
                updates["CARGO"] = c_a.text_input("Cargo", value=datos.get("CARGO", ""))
                updates["DEPARTAMENTO"] = c_b.text_input("Departamento", value=datos.get("DEPARTAMENTO", ""))
                updates["JEFE_DIRECTO"] = c_a.text_input("Jefe Directo", value=datos.get("JEFE_DIRECTO", ""))
                updates["SEDE"] = c_b.text_input("Sede", value=datos.get("SEDE", ""))
                updates["CORREO"] = c_a.text_input("Correo", value=datos.get("CORREO", ""))
                updates["CELULAR"] = c_b.text_input("Celular", value=str(datos.get("CELULAR", "")))
                updates["ESTADO"] = c_a.selectbox("Estado", ["Activo", "Inactivo"], index=0 if datos.get("ESTADO", "Activo") == "Activo" else 1)
                updates["SALARIO APORTES"] = c_b.text_input("Salario", value=str(datos.get("SALARIO APORTES", "")))
                updates["DIRECCIÓN DE RESIDENCIA"] = c_a.text_input("Dirección", value=datos.get("DIRECCIÓN DE RESIDENCIA", ""))
                updates["BANCO"] = c_b.text_input("Banco", value=datos.get("BANCO", ""))
                updates["ESTADO_CONTRATO"] = c_a.text_input("Estado Contrato", value=datos.get("ESTADO_CONTRATO", ""))
                
                if st.form_submit_button("💾 Guardar Cambios", use_container_width=True):
                    with st.spinner("Guardando en Google Sheets..."):
                        if actualizar_empleado_google_sheets(datos.get("CEDULA"), updates):
                            st.success("✅ ¡Datos actualizados exitosamente!"); st.cache_data.clear(); st.rerun()
                        else:
                            st.error("❌ Error al actualizar. No se encontró al empleado por cédula.")
    else:
        st.warning("⚠️ No se encontraron empleados con los filtros seleccionados.")