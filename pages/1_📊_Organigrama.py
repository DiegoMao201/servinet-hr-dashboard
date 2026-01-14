import streamlit as st
import pandas as pd
import datetime
import textwrap
from collections import Counter
from streamlit_echarts import st_echarts 

# --- IMPORTACIÓN DE MÓDULOS LOCALES ---
# Asegúrate de que estos archivos existen en tu carpeta modules/
try:
    from modules.database import get_employees, connect_to_drive, SPREADSHEET_ID
    from modules.drive_manager import (
        get_or_create_manuals_folder,
        upload_organigrama_to_drive,
        find_organigrama_in_drive,
        download_organigrama_from_drive,
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
    
    /* Estilo de Tabs */
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
    
    /* Mejoras generales de UI */
    div[data-testid="stForm"] {
        background-color: #f8fafc;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
    }
    
    /* Estilo para el tooltip de lista de empleados */
    .echarts-tooltip {
        max-height: 400px;
        overflow-y: auto;
    }
    </style>
""", unsafe_allow_html=True)

# --- FUNCIONES GLOBALES ---

def wrap_text_node(text, width=20):
    """Rompe líneas de texto largo automáticamente para ajustar a la tarjeta."""
    if not isinstance(text, str): return ""
    return "\n".join(textwrap.wrap(text, width=width))

def color_por_departamento(depto):
    """Asigna color corporativo pastel según el departamento."""
    colores = {
        "ADMINISTRATIVO": "#fef9c3", # Amarillo pastel
        "OPERATIVO": "#dcfce7",      # Verde pastel
        "FINANZAS": "#fee2e2",       # Rojo pastel
        "COMERCIAL": "#dbeafe",      # Azul pastel
        "RRHH": "#fce7f3",           # Rosa pastel
        "TECNOLOGÍA": "#f3e8ff",     # Morado pastel
        "LOGÍSTICA": "#d1fae5",      # Esmeralda
        "DIRECCIÓN": "#fef08a",      # Amarillo fuerte
        "JURÍDICO": "#fbcfe8",       # Rosa
        "MARKETING": "#ffedd5",      # Naranja
        "OTROS": "#f1f5f9"           # Gris
    }
    if not depto:
        return "#f1f5f9"
    # Normalizar a mayúsculas y quitar espacios extra
    depto_norm = str(depto).strip().upper()
    return colores.get(depto_norm, "#f1f5f9")

# --- ENCABEZADO ---
col_logo, col_title = st.columns([1, 6])
with col_logo:
    try:
        # Intenta cargar logo si existe, si no usa emoji
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

# --- PROCESAMIENTO Y LIMPIEZA DE DATOS ---
# 1. Copia base y exclusión de retirados
df_org_base = df.copy()
if "ESTADO" in df_org_base.columns:
    df_org_base = df_org_base[~df_org_base["ESTADO"].str.upper().str.contains("RETIRADO", na=False)]

# 2. Normalización de columnas clave
df_org_base['NOMBRE COMPLETO'] = df_org_base['NOMBRE COMPLETO'].astype(str).str.strip()
if 'JEFE_DIRECTO' in df_org_base.columns:
    df_org_base['JEFE_DIRECTO'] = df_org_base['JEFE_DIRECTO'].fillna("").astype(str).str.strip()
elif 'JEFE INMEDIATO' in df_org_base.columns:
    df_org_base['JEFE_DIRECTO'] = df_org_base['JEFE INMEDIATO'].fillna("").astype(str).str.strip()

# 3. ALGORITMO ANTI-BUCLES (Ciclos Infinitos en Personas)
# Esto es necesario para la edición en el Tab 2, aunque el Tab 1 use cargos.
employees_dict = dict(zip(df_org_base['NOMBRE COMPLETO'], df_org_base['JEFE_DIRECTO']))
ciclos_detectados = []

def detect_and_break_cycles(df_input):
    """Detecta y rompe ciclos jerárquicos para evitar crash."""
    df_clean = df_input.copy()
    
    # Mapeo temporal
    adj_list = dict(zip(df_clean['NOMBRE COMPLETO'], df_clean['JEFE_DIRECTO']))
    links_to_break = []

    def visit(node, path):
        if node in path:
            links_to_break.append(node)
            return
        if node not in adj_list or not adj_list[node]:
            return 
        path.add(node)
        visit(adj_list[node], path)
        path.remove(node)

    for emp in df_clean['NOMBRE COMPLETO']:
        visit(emp, set())

    if links_to_break:
        unique_breaks = list(set(links_to_break))
        st.warning(f"⚠️ **Alerta:** Se rompieron vínculos cíclicos de personas para visualizar: {', '.join(unique_breaks)}")
        for name in unique_breaks:
            df_clean.loc[df_clean['NOMBRE COMPLETO'] == name, 'JEFE_DIRECTO'] = ""
            
    return df_clean

df_org_final = detect_and_break_cycles(df_org_base)

# --- Normalización y aseguramiento de columnas clave ---
df_org_final.columns = [str(c).strip().upper() for c in df_org_final.columns]

# Renombra columnas si es necesario para compatibilidad
if "CARGO " in df_org_final.columns:
    df_org_final = df_org_final.rename(columns={"CARGO ": "CARGO"})
if "DEPARTAMENTO " in df_org_final.columns:
    df_org_final = df_org_final.rename(columns={"DEPARTAMENTO ": "DEPARTAMENTO"})
if "JEFE_DIRECTO" not in df_org_final.columns and "JEFE DIRECTO" in df_org_final.columns:
    df_org_final = df_org_final.rename(columns={"JEFE DIRECTO": "JEFE_DIRECTO"})
if "CORREO " in df_org_final.columns:
    df_org_final = df_org_final.rename(columns={"CORREO ": "CORREO"})
if "CELULAR " in df_org_final.columns:
    df_org_final = df_org_final.rename(columns={"CELULAR ": "CELULAR"})

# Si falta alguna columna, la agregamos vacía (¡incluye 'AREA' aunque no la uses!)
for col in ["CARGO", "DEPARTAMENTO", "JEFE_DIRECTO", "CORREO", "CELULAR", "AREA"]:
    if col not in df_org_final.columns:
        df_org_final[col] = ""

# Listas para filtros (Tab 2)
areas = sorted(df['AREA'].dropna().unique()) if 'AREA' in df.columns else []
sedes = sorted(df['SEDE'].dropna().unique()) if 'SEDE' in df.columns else []
departamentos = sorted(df['DEPARTAMENTO'].dropna().unique()) if 'DEPARTAMENTO' in df.columns else []
cargos = sorted(df['CARGO'].dropna().unique()) if 'CARGO' in df.columns else []

# --- PREPARACIÓN DE DATOS AGRUPADOS POR CARGO (Para Tab 1) ---
# Necesitamos saber qué cargo reporta a qué cargo.
# 1. Mapa: Persona -> Cargo
mapa_persona_cargo = dict(zip(df_org_final['NOMBRE COMPLETO'], df_org_final['CARGO']))

# 2. Agregar columna "Cargo del Jefe" a cada empleado
df_org_final['JEFE_CARGO_REAL'] = df_org_final['JEFE_DIRECTO'].map(mapa_persona_cargo).fillna("")

# 3. Agrupar por CARGO
# Estructura deseada: DataFrame donde el índice es el CARGO y tenemos una lista de empleados y el jefe (cargo) más común.
df_cargos_group = df_org_final.groupby('CARGO').agg({
    'NOMBRE COMPLETO': list,
    'CORREO': list,
    'CELULAR': list,
    'DEPARTAMENTO': 'first',
    'AREA': 'first',  # No importa si está vacía, ya no falla
    'JEFE_CARGO_REAL': lambda x: Counter(x).most_common(1)[0][0] if len(x) > 0 else ""
}).reset_index()

# 4. Anti-bucles para CARGOS (Porque Gerente puede reportar a Director y Director a Gerente por error)
def break_role_cycles(df_roles):
    df_clean = df_roles.copy()
    adj_list = dict(zip(df_clean['CARGO'], df_clean['JEFE_CARGO_REAL']))
    links_to_break = []

    def visit(node, path):
        if node in path:
            links_to_break.append(node)
            return
        # Si el jefe es el mismo cargo (auto-referencia), romperlo a menos que sea el único
        if node in adj_list and adj_list[node] == node:
             links_to_break.append(node)
             return
        if node not in adj_list or not adj_list[node]:
            return
        path.add(node)
        visit(adj_list[node], path)
        path.remove(node)

    for role in df_clean['CARGO']:
        visit(role, set())

    if links_to_break:
        unique = list(set(links_to_break))
        # st.warning(f"Ciclos de Cargos rotos: {unique}") # Debug opcional
        for role in unique:
             df_clean.loc[df_clean['CARGO'] == role, 'JEFE_CARGO_REAL'] = ""
    return df_clean

df_cargos_final = break_role_cycles(df_cargos_group)


# --- TABS ---
tab1, tab2 = st.tabs(["🌳 Organigrama por Cargos", "👤 Ficha Técnica & Edición"])

# ==============================================================================
# TAB 1: ORGANIGRAMA AGRUPADO POR CARGOS (SOLICITUD USUARIO)
# ==============================================================================
with tab1:
    st.markdown("### 🔹 Mapa Estructural por Cargos")
    st.info("💡 **Interacción:** El organigrama muestra **CARGOS**. Haz clic o pasa el mouse sobre un cargo para ver la lista de **TODOS** los empleados que lo ocupan.")

    def build_hierarchy_by_role_json(df_in):
        # Crear Nodos
        nodes = {}
        
        # Diccionario para buscar ID de Cargo padre
        # Usaremos el nombre del cargo como ID ya que es único tras el groupby
        
        for _, row in df_in.iterrows():
            cargo_id = row['CARGO'] # ID único es el nombre del cargo
            parent_id = row['JEFE_CARGO_REAL']
            
            # Si el parent es vacío o es el mismo cargo, es raíz (o error de ciclo ya limpiado)
            if parent_id == "" or parent_id == cargo_id:
                parent_id = None
            
            # Datos visuales del nodo (Solo mostramos el Cargo y conteo)
            count_emp = len(row['NOMBRE COMPLETO'])
            cargo_display = wrap_text_node(cargo_id, width=18)
            
            # Etiqueta visual
            formatted_label = f"{{title|{cargo_display}}}\n{{hr|}}\n{{subtitle|{count_emp} Personas}}"
            
            depto = row.get('DEPARTAMENTO', 'OTROS')
            bg_color = color_por_departamento(depto)
            
            # Preparar lista de empleados para el tooltip
            lista_empleados = []
            nombres = row['NOMBRE COMPLETO']
            correos = row['CORREO']
            celulares = row['CELULAR']

            for i in range(len(nombres)):
                lista_empleados.append({
                    "nombre": nombres[i],
                    "correo": correos[i] if i < len(correos) else "",
                    "celular": celulares[i] if i < len(celulares) else ""
                })

            nodes[cargo_id] = {
                "name": formatted_label,
                "value": count_emp, # Valor numérico para lógica interna
                "children": [],
                "tooltip_info": {
                    "cargo": cargo_id,
                    "departamento": depto,
                    "area": row.get('AREA', ''),
                    "empleados": lista_empleados
                },
                "itemStyle": {
                    "color": bg_color,
                    "borderColor": "#94a3b8",
                    "borderWidth": 1,
                    "borderRadius": 4,
                    "shadowBlur": 5,
                    "shadowColor": "rgba(0,0,0,0.1)"
                },
                "_id": cargo_id,
                "_parent_id": parent_id
            }

        # Armar el árbol recorriendo nodos y asignando hijos
        forest = []
        # Es necesario procesar los nodos que tienen padres existentes
        for cargo_id, node in nodes.items():
            parent_id = node.get("_parent_id")
            
            if parent_id and parent_id in nodes:
                nodes[parent_id]["children"].append(node)
            else:
                forest.append(node)
        
        # Manejo de Raíces Múltiples
        if len(forest) == 1:
            return forest[0]
        else:
            return {
                "name": "{title|DIRECCIÓN GENERAL}\n{hr|}\n{subtitle|ESTRUCTURA}",
                "children": forest,
                "tooltip_info": {"cargo": "Agrupador Raíz", "departamento": "-", "empleados": []},
                "itemStyle": {"color": "#1e293b", "borderColor": "#0f172a"},
                "label": {"color": "white"}
            }

    try:
        tree_data = build_hierarchy_by_role_json(df_cargos_final)
        
        # --- CONFIGURACIÓN ECHARTS PROFESIONAL ---
        option = {
            "tooltip": {
                "trigger": 'item',
                "triggerOn": 'mousemove|click', # Funciona con clic o mouse
                "enterable": True, # Permite entrar al tooltip para scrollear
                "formatter": """
    function(params) {
        var info = params.data.tooltip_info;
        if (!info) return '';
        
        // Encabezado del Tooltip
        let html = `<div style="font-family: sans-serif; min-width: 250px; max-height: 300px; overflow-y: auto; padding: 10px; border-radius: 4px; background: white; box-shadow: 0 2px 10px rgba(0,0,0,0.2);">
            <h4 style="margin:0 0 5px 0; color: #1e3a8a; border-bottom: 2px solid #3b82f6; padding-bottom: 5px;">${info.cargo}</h4>
            <div style="font-size: 11px; color: #64748b; margin-bottom: 8px;">
                <b>Depto:</b> ${info.departamento} | <b>Total:</b> ${info.empleados.length}
            </div>
            <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                <tr style="background: #f1f5f9; text-align: left;">
                    <th style="padding: 4px;">Empleado</th>
                    <th style="padding: 4px;">Contacto</th>
                </tr>`;
        
        // Iterar sobre los empleados del cargo
        info.empleados.forEach(function(emp) {
            html += `
                <tr style="border-bottom: 1px solid #e2e8f0;">
                    <td style="padding: 6px 4px; color: #334155;">
                        <b>${emp.nombre}</b>
                    </td>
                    <td style="padding: 6px 4px; color: #64748b;">
                        ${emp.celular}<br>
                        <span style="font-size: 10px; color: #94a3b8;">${emp.correo}</span>
                    </td>
                </tr>
            `;
        });
        
        html += `</table></div>`;
        return html;
    }
                """
            },
            "series": [
                {
                    "type": "tree",
                    "data": [tree_data],
                    "left": '1%',           # Antes: '5%'
                    "right": '1%',          # Antes: '5%'
                    "top": '5px',           # Antes: '30px'
                    "bottom": '5px',        # Antes: '30px'
                    "orient": 'TB',
                    "layout": 'orthogonal',
                    "symbol": 'rect',
                    "symbolSize": [260, 70],  # Antes: [120, 48] (¡mucho más grande!)
                    "roam": True,
                    "initialTreeDepth": 2,    # Un poco más expandido
                    "expandAndCollapse": True,
                    "edgeShape": "polyline",
                    "edgeForkPosition": "50%",  # Más compacto
                    "lineStyle": {
                        "color": "#3b82f6",
                        "width": 2,
                        "curveness": 0
                    },
                    "label": {
                        "show": True,
                        "position": 'inside',
                        "color": '#1e293b',
                        "fontSize": 16,  # Más grande
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
                        "borderRadius": 14,  # Más redondeado
                        "shadowBlur": 12,
                        "shadowColor": "rgba(59,130,246,0.10)"
                    },
                    "animationDuration": 350,
                    "animationDurationUpdate": 450
                }
            ]
        }
        
        st_echarts(options=option, height="900px")  # Menor altura, más compacto

    except Exception as e:
        st.error(f"Error crítico al generar organigrama por cargos: {e}")

    # Leyenda de colores eliminada para profesionalismo empresarial

# ==============================================================================
# TAB 2: FICHA DE EMPLEADO & EDICIÓN (SIN CAMBIOS, NECESARIO PARA FUNCIONALIDAD)
# ==============================================================================
with tab2:
    def actualizar_empleado_google_sheets(nombre, cedula, cargo, area, departamento, sede, jefe, correo, celular, centro_trabajo):
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
                    (sheet.find("NOMBRE COMPLETO").col, nombre),
                    (sheet.find("CEDULA").col, cedula),
                    (sheet.find("CARGO").col, cargo),
                    (sheet.find("AREA").col, area),
                    (sheet.find("DEPARTAMENTO").col, departamento),
                    (sheet.find("SEDE").col, sede),
                    (sheet.find("JEFE INMEDIATO").col, jefe), 
                    (sheet.find("CORREO").col, correo),
                    (sheet.find("CELULAR").col, celular),
                    (sheet.find("CENTRO TRABAJO").col, centro_trabajo)
                ]
                
                for col_idx, val in updates:
                    sheet.update_cell(fila_encontrada, col_idx, val)
                return True
            return False
        except Exception as e:
            st.error(f"Error técnico al guardar: {e}")
            return False

    # Filtros Superiores
    st.markdown("##### 🔍 Filtros de Búsqueda")
    c1, c2, c3, c4 = st.columns(4)
    f_area = c1.selectbox("Filtrar por Área", ["Todas"] + areas)
    f_sede = c2.selectbox("Filtrar por Sede", ["Todas"] + sedes)
    f_dep = c3.selectbox("Filtrar por Depto", ["Todos"] + departamentos)
    f_cargo = c4.selectbox("Filtrar por Cargo", ["Todos"] + cargos)

    df_filt = df.copy()
    if f_area != "Todas": df_filt = df_filt[df_filt['AREA'] == f_area]
    if f_sede != "Todas": df_filt = df_filt[df_filt['SEDE'] == f_sede]
    if f_dep != "Todos": df_filt = df_filt[df_filt['DEPARTAMENTO'] == f_dep]
    if f_cargo != "Todos": df_filt = df_filt[df_filt['CARGO'] == f_cargo]

    empleados_disponibles = sorted(df_filt['NOMBRE COMPLETO'].unique())
    
    if len(empleados_disponibles) > 0:
        seleccion = st.selectbox("Seleccionar Empleado para ver Detalle", empleados_disponibles)
        datos = df_filt[df_filt['NOMBRE COMPLETO'] == seleccion].iloc[0]
        
        st.markdown("---")
        
        # Diseño de Tarjeta y Formulario
        col_card_izq, col_card_der = st.columns([1, 2])
        
        # COLUMNA IZQUIERDA: TARJETA VISUAL
        with col_card_izq:
            st.markdown(f"""
            <div style="background-color: white; padding: 25px; border-radius: 12px; border: 1px solid #e2e8f0; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                <div style="font-size: 64px; margin-bottom: 10px;">👤</div>
                <h3 style="margin:0; color: #1e293b; font-size: 20px;">{seleccion}</h3>
                <p style="color: #3b82f6; font-weight: 600; font-size: 14px; margin-bottom: 20px;">{datos.get('CARGO', 'Sin Cargo')}</p>
                <div style="text-align: left; font-size: 13px; color: #475569; padding-top: 15px; border-top: 1px solid #f1f5f9;">
                    <p style="margin: 8px 0;"><b>📧 Email:</b> {datos.get('CORREO', '--')}</p>
                    <p style="margin: 8px 0;"><b>📱 Celular:</b> {datos.get('CELULAR', '--')}</p>
                    <p style="margin: 8px 0;"><b>📍 Sede:</b> {datos.get('SEDE', '--')}</p>
                    <p style="margin: 8px 0;"><b>🏢 Área:</b> {datos.get('AREA', '--')}</p>
                    <p style="margin: 8px 0;"><b>🎯 Jefe:</b> {datos.get('JEFE_DIRECTO', 'N/A')}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Sección de Manuales
            st.write(" ")
            st.markdown("##### 📄 Manual de Funciones")

            with st.spinner("Buscando manual de funciones..."):
                manuals_folder_id = get_or_create_manuals_folder()
                manual_file_id = find_manual_in_drive(datos.get("CARGO", ""), manuals_folder_id)

            if manual_file_id:
                pdf_bytes = download_manual_from_drive(manual_file_id)
                st.download_button(
                    label="📥 Descargar Manual de Funciones PDF",
                    data=pdf_bytes,
                    file_name=f"Manual_{datos.get('CARGO', '').replace(' ', '_').upper()}.pdf",
                    mime="application/pdf"
                )
                st.info("Manual de funciones disponible.")
            else:
                st.warning("No hay manual de funciones guardado para este cargo.")

        # COLUMNA DERECHA: FORMULARIO DE EDICIÓN
        with col_card_der:
            st.subheader("📝 Edición de Información")
            with st.form("form_edicion"):
                c_a, c_b = st.columns(2)
                
                # Campos editables
                nuevo_nombre = c_a.text_input("Nombre Completo", value=datos.get("NOMBRE COMPLETO", ""))
                # Cédula deshabilitada
                nuevo_cedula = c_b.text_input("Cédula (ID Único)", value=datos.get("CEDULA", ""), disabled=True)
                
                nuevo_cargo = c_a.text_input("Cargo", value=datos.get("CARGO", ""))
                nuevo_area = c_b.text_input("Área", value=datos.get("AREA", ""))
                
                nuevo_depto = c_a.text_input("Departamento", value=datos.get("DEPARTAMENTO", ""))
                nueva_sede = c_b.text_input("Sede", value=datos.get("SEDE", ""))
                
                # Recuperar jefe normalizado
                jefe_actual = datos.get("JEFE_DIRECTO", "") 
                nuevo_jefe = c_a.text_input("Jefe Inmediato (Nombre Exacto)", value=jefe_actual)
                
                nuevo_correo = c_b.text_input("Correo Electrónico", value=datos.get("CORREO", ""))
                nuevo_cel = c_a.text_input("Celular", value=datos.get("CELULAR", ""))
                nuevo_centro = c_b.text_input("Centro de Trabajo", value=datos.get("CENTRO TRABAJO", ""))
                
                # ID real para el update
                real_cedula_for_update = datos.get("CEDULA", "")
                
                st.markdown("---")
                submitted = st.form_submit_button("💾 Guardar Cambios en Base de Datos", use_container_width=True)
                
                if submitted:
                    with st.spinner("Conectando con Google Sheets..."):
                        exito = actualizar_empleado_google_sheets(
                            nuevo_nombre, real_cedula_for_update, nuevo_cargo, nuevo_area, 
                            nuevo_depto, nueva_sede, nuevo_jefe, nuevo_correo, 
                            nuevo_cel, nuevo_centro
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

# --- Genera la descripción general del organigrama con IA ---

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

# --- Construye la lista de cargos_info ---
# Reutilizamos df_cargos_final para optimizar, pero mantenemos estructura original para el PDF
cargos_info = []
for idx, row in df_cargos_final.iterrows():
    cargo = row['CARGO']
    departamento = row['DEPARTAMENTO']
    empleados = row['NOMBRE COMPLETO']
    
    # Descripción por IA para cada cargo
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

# --- Descripción general del organigrama ---
# Solo llamamos a la IA si hay cliente
descripcion_general = ""
if openai_client:
    try:
        descripcion_general = generar_descripcion_general_organigrama(cargos_info)
    except:
        descripcion_general = "No se pudo generar descripción."

# --- Botón para exportar PDF ---
if st.button("📄 Exportar Organigrama por Cargos a PDF"):
    with st.spinner("Generando PDF profesional..."):
        pdf_filename = export_organigrama_pdf(
            cargos_info=cargos_info,
            descripcion_general=descripcion_general,
            # leyenda_colores eliminado
            filename="Organigrama_Cargos.pdf"
        )
        # Subir a Drive
        upload_organigrama_to_drive(pdf_filename, manuals_folder_id)
        with open(pdf_filename, "rb") as f:
            st.download_button(
                label="📥 Descargar PDF Organigrama",
                data=f.read(),
                file_name=pdf_filename,
                mime="application/pdf"
            )
        st.success("PDF generado y guardado en Drive exitosamente.")