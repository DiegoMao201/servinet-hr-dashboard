import streamlit as st
import pandas as pd
# Asumo que estos módulos existen en tu carpeta local como indicaste en tu código original
from modules.database import get_employees, connect_to_drive, SPREADSHEET_ID
from modules.drive_manager import get_or_create_manuals_folder, find_manual_in_drive, download_manual_from_drive
import datetime
from streamlit_echarts import st_echarts 
import textwrap # Nueva librería estándar para ajustar texto largo

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Organigrama Corporativo", page_icon="🏢", layout="wide")

# --- ESTILOS CSS MEJORADOS ---
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
    </style>
""", unsafe_allow_html=True)

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

# --- PROCESAMIENTO DE DATOS ---
# Filtro base: Solo activos (excluye retirados)
df_org_base = df.copy()
if "ESTADO" in df_org_base.columns:
    df_org_base = df_org_base[~df_org_base["ESTADO"].str.upper().str.contains("RETIRADO", na=False)]

# Listas para filtros (Tab 2)
areas = sorted(df['AREA'].dropna().unique()) if 'AREA' in df.columns else []
sedes = sorted(df['SEDE'].dropna().unique()) if 'SEDE' in df.columns else []
departamentos = sorted(df['DEPARTAMENTO'].dropna().unique()) if 'DEPARTAMENTO' in df.columns else []
cargos = sorted(df['CARGO'].dropna().unique()) if 'CARGO' in df.columns else []

# --- TABS ---
tab1, tab2 = st.tabs(["🌳 Organigrama Interactivo", "👤 Ficha Técnica & Edición"])

# ==============================================================================
# TAB 1: ORGANIGRAMA MEJORADO (DISEÑO PROFESIONAL)
# ==============================================================================
with tab1:
    st.markdown("### 🔹 Mapa Estructural de la Compañía")
    st.info("💡 **Instrucciones:** Usa la rueda del mouse para hacer Zoom. Arrastra el lienzo para moverte. Haz clic en los nodos para ver detalles.")

    def wrap_text_node(text, width=20):
        """Función auxiliar para romper líneas de texto largo automáticamente"""
        if not isinstance(text, str): return ""
        return "\n".join(textwrap.wrap(text, width=width))

    def build_hierarchy_json_v2(df_in):
        """
        Versión optimizada para layouts verticales.
        Estructura los datos para ECharts Tree.
        """
        df_in = df_in.fillna("")
        
        # Mapeo de Nombre a Cédula (Normalizamos a string para evitar errores de tipo)
        nombre_to_id = {row['NOMBRE COMPLETO'].strip(): str(row['CEDULA']).strip() for _, row in df_in.iterrows()}
        
        nodes = {}
        
        # 1. Crear Nodos
        for _, row in df_in.iterrows():
            emp_id = str(row['CEDULA']).strip()
            
            # Buscar ID del Jefe
            jefe_nombre = (row.get('JEFE_DIRECTO', '') or row.get('JEFE INMEDIATO', '')).strip()
            parent_id = nombre_to_id.get(jefe_nombre, None)
            
            # Formateo visual del texto (Rich Text)
            nombre_display = wrap_text_node(row['NOMBRE COMPLETO'], width=18)
            cargo_display = wrap_text_node(row['CARGO'], width=22)
            
            # Formato ECharts Rich Text: {styleName|Text}
            formatted_label = f"{{name|{nombre_display}}}\n{{hr|}}\n{{role|{cargo_display}}}"
            
            # Nueva línea: Obtener departamento para el color
            depto = row.get('DEPARTAMENTO', 'OTROS')
            nodes[emp_id] = {
                "name": formatted_label,
                "value": row['CARGO'],
                "children": [],
                "tooltip_info": {
                    "nombre_real": row['NOMBRE COMPLETO'],
                    "area": row.get('AREA', 'N/A'),
                    "sede": row.get('SEDE', 'N/A'),
                    "email": row.get('CORREO', ''),
                    "celular": row.get('CELULAR', '')
                },
                "itemStyle": {"color": color_por_departamento(depto)},
                # IDs internos para lógica
                "_id": emp_id,
                "_parent_id": parent_id
            }

        # 2. Construir Árbol (Forest)
        forest = []
        for emp_id, node in nodes.items():
            parent_id = node.pop("_parent_id")
            
            # Evitar auto-referencia (si alguien se puso a sí mismo de jefe por error)
            if parent_id == emp_id:
                parent_id = None

            if parent_id and parent_id in nodes:
                nodes[parent_id]["children"].append(node)
            else:
                forest.append(node)
        
        # 3. Retornar Raíz Única
        if len(forest) == 1:
            return forest[0]
        else:
            # Si hay múltiples raíces (islas), creamos un nodo padre ficticio
            return {
                "name": "{name|DIRECCIÓN GENERAL}\n{hr|}\n{role|SERVINET}",
                "children": forest,
                "tooltip_info": {"nombre_real": "SERVINET", "area": "Global", "sede": "-", "email": "", "celular": ""},
                "itemStyle": {"color": "#0f172a", "borderColor": "#0f172a"}
            }

    try:
        tree_data = build_hierarchy_json_v2(df_org_base)
        
        # --- CONFIGURACIÓN ECHARTS (EL DISEÑO) ---
        option = {
            "tooltip": {
                "trigger": 'item',
                "triggerOn": 'mousemove',
                "padding": 0,
                "formatter": """
                    function(params) {
                        var info = params.data.tooltip_info;
                        if (!info) return '';
                        return `
                            <div style="font-family: 'Segoe UI', sans-serif; width: 220px; border-radius: 6px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.15); background: white;">
                                <div style="background: #3b82f6; color: white; padding: 10px 15px; font-weight: bold; font-size: 14px;">
                                    ${info.nombre_real}
                                </div>
                                <div style="padding: 15px; color: #334155; font-size: 12px; line-height: 1.6;">
                                    <strong style="color: #1e293b;">Cargo:</strong> ${params.value}<br>
                                    <strong style="color: #1e293b;">Área:</strong> ${info.area}<br>
                                    <strong style="color: #1e293b;">Sede:</strong> ${info.sede}<br>
                                    <div style="margin-top: 8px; border-top: 1px solid #e2e8f0; padding-top: 8px;">
                                        ${info.email ? `📧 ${info.email}<br>` : ''}
                                        ${info.celular ? `📱 ${info.celular}` : ''}
                                    </div>
                                </div>
                            </div>
                        `;
                    }
                """
            },
            "series": [
                {
                    "type": "tree",
                    "data": [tree_data],
                    "left": '5%', 
                    "right": '5%', 
                    "top": '5%', 
                    "bottom": '5%',
                    "orient": 'TB',  # TB = Top to Bottom (Organigrama Vertical Clásico)
                    
                    "symbol": 'rect', # Nodos rectangulares
                    "symbolSize": [160, 75], # [Ancho, Alto] - Ajustado para que quepa el texto
                    
                    "roam": True, # Permite zoom y mover
                    "initialTreeDepth": 2, # Niveles abiertos al iniciar
                    
                    "itemStyle": {
                        "color": "#ffffff", # Fondo blanco del nodo
                        "borderColor": "#3b82f6", # Borde azul
                        "borderWidth": 2,
                        "borderRadius": 6,
                        "shadowBlur": 5,
                        "shadowColor": "rgba(0,0,0,0.1)"
                    },
                    
                    "lineStyle": {
                        "color": "#94a3b8",
                        "width": 1.5,
                        "curveness": 0.5 # Líneas curvas suaves. Cambia a 0 para rectas ortogonales
                        # Para líneas ortogonales (rectas 90 grados), usa edgeShape: 'polyline'
                    },
                    
                    "label": {
                        "show": True,
                        "position": 'inside',
                        "color": '#333',
                        "rich": {
                            "name": {
                                "color": "#1e293b",
                                "fontSize": 12,
                                "fontWeight": "bold",
                                "align": "center",
                                "lineHeight": 14,
                                "padding": [0, 0, 4, 0]
                            },
                            "hr": {
                                "borderColor": "#e2e8f0",
                                "width": "100%",
                                "borderWidth": 0.5,
                                "height": 0,
                                "align": "center"
                            },
                            "role": {
                                "color": "#64748b",
                                "fontSize": 10,
                                "align": "center",
                                "lineHeight": 12,
                                "padding": [4, 0, 0, 0]
                            }
                        }
                    },
                    
                    "leaves": {
                        "label": {
                            "position": 'inside',
                            "verticalAlign": 'middle',
                            "align": 'center'
                        },
                        "itemStyle": {
                             "color": "#f0f9ff", # Azul muy claro para empleados base
                             "borderColor": "#60a5fa"
                        }
                    },
                    
                    "emphasis": {
                        "focus": 'descendant', # Al pasar mouse, resalta la rama completa
                        "itemStyle": {
                            "shadowBlur": 10,
                            "shadowColor": "rgba(59, 130, 246, 0.5)"
                        }
                    },
                    
                    "expandAndCollapse": True,
                    "animationDuration": 550,
                    "animationDurationUpdate": 750
                }
            ]
        }
        
        # Renderizar gráfico con altura suficiente para organigramas verticales
        st_echarts(options=option, height="850px")

    except Exception as e:
        st.error(f"Error al generar la estructura del organigrama: {e}")
        st.warning("Verifica datos huérfanos o ciclos infinitos (Jefe A es jefe de B, y B es jefe de A).")

# --- ADVERTENCIA DE HUÉRFANOS ---
if "JEFE_DIRECTO" in df_org_base.columns:
    empleados_con_jefe = df_org_base["JEFE_DIRECTO"].dropna().unique()
    nombres_empleados = df_org_base["NOMBRE COMPLETO"].unique()
    huerfanos = []
    for jefe in empleados_con_jefe:
        if jefe and jefe not in nombres_empleados:
            huerfanos.append(jefe)
    empleados_sin_jefe = df_org_base[df_org_base["JEFE_DIRECTO"].isna() | (df_org_base["JEFE_DIRECTO"] == "")]
    if not empleados_sin_jefe.empty:
        st.warning(f"👀 Empleados sin jefe asignado: {', '.join(empleados_sin_jefe['NOMBRE COMPLETO'])}")
    if huerfanos:
        st.error(f"⚠️ Jefes asignados que no existen en la base: {', '.join(huerfanos)}")

# ==============================================================================
# TAB 2: FICHA DE EMPLEADO & EDICIÓN (MANTENIDA EXACTA Y FUNCIONAL)
# ==============================================================================
with tab2:
    def actualizar_empleado_google_sheets(nombre, cedula, cargo, area, departamento, sede, jefe, correo, celular, centro_trabajo):
        try:
            client = connect_to_drive()
            spreadsheet = client.open_by_key(SPREADSHEET_ID)
            sheet = spreadsheet.worksheet("BD EMPLEADOS")
            data_gs = sheet.get_all_records()
            
            # Búsqueda robusta convirtiendo a string
            fila_encontrada = -1
            cedula_str = str(cedula).strip()
            
            for idx, row in enumerate(data_gs):
                if str(row.get("CEDULA", "")).strip() == cedula_str:
                    fila_encontrada = idx + 2
                    break
            
            if fila_encontrada > 0:
                # Mapeo exacto de columnas
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
            <div style="background-color: white; padding: 25px; border-radius: 12px; border: 1px solid #e2e8f0; text-align: center;">
                <div style="font-size: 64px; margin-bottom: 10px;">👤</div>
                <h3 style="margin:0; color: #1e293b; font-size: 20px;">{seleccion}</h3>
                <p style="color: #3b82f6; font-weight: 600; font-size: 14px; margin-bottom: 20px;">{datos.get('CARGO', 'Sin Cargo')}</p>
                <div style="text-align: left; font-size: 13px; color: #475569; padding-top: 15px; border-top: 1px solid #f1f5f9;">
                    <p style="margin: 5px 0;"><b>📧 Email:</b> {datos.get('CORREO', '--')}</p>
                    <p style="margin: 5px 0;"><b>📱 Celular:</b> {datos.get('CELULAR', '--')}</p>
                    <p style="margin: 5px 0;"><b>📍 Sede:</b> {datos.get('SEDE', '--')}</p>
                    <p style="margin: 5px 0;"><b>🏢 Área:</b> {datos.get('AREA', '--')}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Sección de Manuales
            st.write(" ")
            st.markdown("##### 📄 Documentación Asociada")
            
            with st.spinner("Buscando manuales..."):
                manuals_folder_id = get_or_create_manuals_folder()
                manual_file_id = find_manual_in_drive(datos.get("CARGO", ""), manuals_folder_id)
            
            if manual_file_id:
                pdf_bytes = download_manual_from_drive(manual_file_id)
                if pdf_bytes:
                    st.download_button(
                        label="📥 Descargar Manual de Funciones (PDF)",
                        data=pdf_bytes,
                        file_name=f"Manual_{datos.get('CARGO','').replace(' ','_')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
            else:
                st.info(f"No se encontró manual PDF para el cargo: '{datos.get('CARGO')}'")

        # COLUMNA DERECHA: FORMULARIO DE EDICIÓN
        with col_card_der:
            st.subheader("📝 Edición de Información")
            with st.form("form_edicion"):
                c_a, c_b = st.columns(2)
                
                # Campos editables
                nuevo_nombre = c_a.text_input("Nombre Completo", value=datos.get("NOMBRE COMPLETO", ""))
                # Cédula deshabilitada para evitar romper IDs
                nuevo_cedula = c_b.text_input("Cédula (ID Único)", value=datos.get("CEDULA", ""), disabled=True)
                
                nuevo_cargo = c_a.text_input("Cargo", value=datos.get("CARGO", ""))
                nuevo_area = c_b.text_input("Área", value=datos.get("AREA", ""))
                
                nuevo_depto = c_a.text_input("Departamento", value=datos.get("DEPARTAMENTO", ""))
                nueva_sede = c_b.text_input("Sede", value=datos.get("SEDE", ""))
                
                # Recuperar jefe (puede venir con nombres distintos de columna)
                jefe_actual = datos.get("JEFE_DIRECTO", "") or datos.get("JEFE INMEDIATO", "")
                nuevo_jefe = c_a.text_input("Jefe Inmediato (Nombre Exacto)", value=jefe_actual)
                
                nuevo_correo = c_b.text_input("Correo Electrónico", value=datos.get("CORREO", ""))
                nuevo_cel = c_a.text_input("Celular", value=datos.get("CELULAR", ""))
                nuevo_centro = c_b.text_input("Centro de Trabajo", value=datos.get("CENTRO TRABAJO", ""))
                
                # Hidden ID real para el update
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
                            st.cache_data.clear() # Obliga a recargar los datos
                            import time
                            time.sleep(1.5)
                            st.rerun()
                        else:
                            st.error("❌ Error al actualizar. Verifica que la cédula no haya cambiado en la BD externa.")

    else:
        st.warning("⚠️ No se encontraron empleados con los filtros seleccionados.")
        
    def color_por_departamento(depto):
        colores = {
            "ADMINISTRATIVO": "#fde68a",
            "OPERATIVO": "#a7f3d0",
            "FINANZAS": "#fca5a5",
            "COMERCIAL": "#93c5fd",
            "RRHH": "#fbcfe8",
            "TECNOLOGÍA": "#ddd6fe",
            "LOGÍSTICA": "#bbf7d0",
            "DIRECCIÓN": "#fef08a",
            "JURÍDICO": "#f9a8d4",
            "MARKETING": "#fdba74",
            "OTROS": "#e0e7ef"
        }
        if not depto:
            return "#e0e7ef"
        depto = depto.upper()
        return colores.get(depto, "#e0e7ef")
    
    st.markdown("#### 🎨 Leyenda de colores por departamento")
    leyenda_colores = {
        "ADMINISTRATIVO": "#fde68a",
        "OPERATIVO": "#a7f3d0",
        "FINANZAS": "#fca5a5",
        "COMERCIAL": "#93c5fd",
        "RRHH": "#fbcfe8",
        "TECNOLOGÍA": "#ddd6fe",
        "LOGÍSTICA": "#bbf7d0",
        "DIRECCIÓN": "#fef08a",
        "JURÍDICO": "#f9a8d4",
        "MARKETING": "#fdba74",
        "OTROS": "#e0e7ef"
    }
    st.markdown(
        "".join(
            f"<span style='display:inline-block;width:18px;height:18px;background:{color};border-radius:4px;margin-right:6px;'></span> {depto} &nbsp;&nbsp;"
            for depto, color in leyenda_colores.items()
        ),
        unsafe_allow_html=True
    )