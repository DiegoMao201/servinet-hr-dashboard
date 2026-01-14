import streamlit as st
import pandas as pd
from modules.database import get_employees, connect_to_drive, SPREADSHEET_ID
from modules.drive_manager import get_or_create_manuals_folder, find_manual_in_drive, download_manual_from_drive
import datetime
from streamlit_echarts import st_echarts # NECESITAS: pip install streamlit-echarts

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Organigrama Corporativo", page_icon="🏢", layout="wide")

# Estilos CSS personalizados para "tunear" la interfaz de Streamlit
st.markdown("""
    <style>
    .block-container {padding-top: 1rem; padding-bottom: 2rem;}
    h1 {color: #0f172a;}
    .stTabs [data-baseweb="tab-list"] {gap: 20px;}
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f1f5f9;
        border-radius: 10px 10px 0 0;
        gap: 10px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff;
        border-bottom: 2px solid #3b82f6;
        color: #3b82f6;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# --- ENCABEZADO ---
col_logo, col_title = st.columns([1, 6])
with col_logo:
    # Si no tienes la imagen, esto no fallará, solo mostrará un icono roto o nada
    try:
        st.image("logo_servinet.jpg", width=100)
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
# 1. Filtro base: Solo activos
df_org_base = df.copy()
if "ESTADO" in df_org_base.columns:
    df_org_base = df_org_base[~df_org_base["ESTADO"].str.upper().str.contains("RETIRADO", na=False)]

# Listas para filtros
areas = sorted(df['AREA'].dropna().unique()) if 'AREA' in df.columns else []
sedes = sorted(df['SEDE'].dropna().unique()) if 'SEDE' in df.columns else []
departamentos = sorted(df['DEPARTAMENTO'].dropna().unique()) if 'DEPARTAMENTO' in df.columns else []
cargos = sorted(df['CARGO'].dropna().unique()) if 'CARGO' in df.columns else []

# --- TABS ---
tab1, tab2 = st.tabs(["🌳 Organigrama Interactivo", "👤 Ficha Técnica & Edición"])

# ==============================================================================
# TAB 1: ORGANIGRAMA ESPECTACULAR (ECHARTS)
# ==============================================================================
with tab1:
    st.markdown("### 🔹 Visualización Jerárquica")
    st.info("💡 Usa la rueda del mouse para hacer Zoom y arrastra para moverte. Haz clic en los nodos para expandir/colapsar ramas.")

    def build_hierarchy_json(df_in):
        """
        Convierte el DataFrame plano en una estructura anidada (JSON/Dict) 
        que entiende ECharts.
        """
        # 1. Preparar un diccionario de nodos
        # Normalizamos nombres y IDs
        df_in = df_in.fillna("")
        
        # Mapeo de Nombre a Cédula para buscar IDs de jefes
        nombre_to_id = dict(zip(df_in['NOMBRE COMPLETO'], df_in['CEDULA'].astype(str)))
        
        nodes = {}
        
        # Crear todos los nodos primero
        for _, row in df_in.iterrows():
            emp_id = str(row['CEDULA'])
            jefe_nombre = row.get('JEFE_DIRECTO', '') or row.get('JEFE INMEDIATO', '')
            parent_id = nombre_to_id.get(jefe_nombre, None)
            
            # Formateo visual del nodo
            # Usamos Rich Text de ECharts: {name|NOMBRE}\n{title|Cargo}
            formatted_name = f"{{val|{row['NOMBRE COMPLETO']}}}\n{{sub|{row['CARGO']}}}"
            
            nodes[emp_id] = {
                "name": formatted_name,
                "value": row['CARGO'], # Valor auxiliar
                "children": [],
                "tooltip_info": { # Datos extra para el tooltip
                    "area": row.get('AREA', ''),
                    "sede": row.get('SEDE', ''),
                    "email": row.get('CORREO', ''),
                    "celular": row.get('CELULAR', '')
                },
                # Estilo específico si es necesario por nivel
                "itemStyle": {
                    "color": "#3b82f6" if parent_id else "#1e3a8a", # Jefe supremo más oscuro
                    "borderColor": "#fff",
                    "borderWidth": 2
                }
            }
            # Guardamos el parent_id temporalmente en el dict para armar el árbol
            nodes[emp_id]["_parent_id"] = parent_id

        # 2. Armar el árbol conectando hijos a padres
        forest = [] # Lista de raíces (puede haber más de un árbol si hay islas)
        
        for emp_id, node in nodes.items():
            parent_id = node.pop("_parent_id") # Removemos auxiliar
            
            if parent_id and parent_id in nodes:
                # Si tiene padre y el padre existe, lo agregamos a los hijos del padre
                nodes[parent_id]["children"].append(node)
            else:
                # Si no tiene padre o el padre no está en la lista (es el CEO o raíz)
                forest.append(node)
        
        # Si el bosque tiene múltiples raíces, creamos un nodo "Organización" ficticio o devolvemos el primero
        if len(forest) == 1:
            return forest[0]
        else:
            return {
                "name": "{val|DIRECCIÓN GENERAL}\n{sub|Servinet}",
                "children": forest,
                "itemStyle": {"color": "#0f172a"},
                "tooltip_info": {"area": "Global", "sede": "Todas", "email": "", "celular": ""}
            }

    # Construir datos
    try:
        tree_data = build_hierarchy_json(df_org_base)
        
        # Configuración de ECharts (El "Secreto" del diseño espectacular)
        option = {
            "tooltip": {
                "trigger": 'item',
                "triggerOn": 'mousemove',
                "formatter": """
                    function(params) {
                        var info = params.data.tooltip_info;
                        if (!info) return '';
                        return `
                            <div style="font-family: sans-serif; padding: 10px; border-radius: 5px; background: white; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                                <div style="font-weight: bold; color: #1e293b; margin-bottom: 5px; border-bottom: 1px solid #e2e8f0; padding-bottom: 5px;">
                                    ${params.name.split('\n')[0].replace('{val|','').replace('}','')}
                                </div>
                                <div style="color: #64748b; font-size: 12px;">Cargo: <b>${params.value}</b></div>
                                <div style="color: #64748b; font-size: 12px;">Área: ${info.area}</div>
                                <div style="color: #64748b; font-size: 12px;">Sede: ${info.sede}</div>
                                ${info.email ? `<div style="margin-top:5px; color:#3b82f6; font-size:11px;">📧 ${info.email}</div>` : ''}
                            </div>
                        `;
                    }
                """
            },
            "series": [
                {
                    "type": "tree",
                    "data": [tree_data],
                    "top": "5%",
                    "left": "2%",
                    "bottom": "5%",
                    "right": "2%",
                    "symbolSize": [180, 50], # Tamaño del "rectángulo" (ancho, alto)
                    "symbol": "rect", # Forma del nodo
                    "edgeShape": "polyline", # Líneas rectas con ángulos (estilo org chart clásico)
                    "edgeForkPosition": "63%",
                    "initialTreeDepth": 2, # Cuantos niveles mostrar expandidos al inicio
                    "lineStyle": {
                        "width": 2,
                        "color": "#cbd5e1",
                        "curveness": 0.5 # Curvatura suave si usas 'curve', para polyline no aplica tanto pero suaviza
                    },
                    "label": {
                        "show": True,
                        "position": "inside",
                        "color": "#fff",
                        "rich": { # AQUÍ ESTÁ LA MAGIA DEL TEXTO
                            "val": {
                                "fontSize": 14,
                                "fontWeight": "bold",
                                "lineHeight": 20,
                                "color": "#ffffff",
                                "align": "center"
                            },
                            "sub": {
                                "fontSize": 11,
                                "color": "#bfdbfe",
                                "lineHeight": 16,
                                "align": "center"
                            }
                        }
                    },
                    "leaves": {
                        "label": {
                            "position": "inside",
                            "verticalAlign": "middle",
                            "align": "center"
                        },
                        "itemStyle": {
                            "color": "#60a5fa" # Color diferente para nodos hoja
                        }
                    },
                    "emphasis": {
                        "focus": "descendant"
                    },
                    "expandAndCollapse": True,
                    "animationDuration": 550,
                    "animationDurationUpdate": 750
                }
            ]
        }
        
        # Renderizar gráfico con altura suficiente
        st_echarts(options=option, height="800px")
        
    except Exception as e:
        st.error(f"Error al generar el organigrama: {e}")
        st.warning("Verifica que las columnas 'CEDULA', 'NOMBRE COMPLETO', 'JEFE_DIRECTO' y 'CARGO' existan y estén escritas correctamente.")


# ==============================================================================
# TAB 2: FICHA DE EMPLEADO (Lógica Original Mejorada)
# ==============================================================================
with tab2:
    def actualizar_empleado_google_sheets(nombre, cedula, cargo, area, departamento, sede, jefe, correo, celular, centro_trabajo):
        try:
            client = connect_to_drive()
            spreadsheet = client.open_by_key(SPREADSHEET_ID)
            sheet = spreadsheet.worksheet("BD EMPLEADOS")
            data_gs = sheet.get_all_records()
            
            # Buscamos la fila correcta (Sheets es index 1, header es row 1, datos empiezan row 2)
            fila_encontrada = -1
            for idx, row in enumerate(data_gs):
                # Comparamos como string y quitamos espacios
                if str(row.get("CEDULA", "")).strip() == str(cedula).strip():
                    fila_encontrada = idx + 2
                    break
            
            if fila_encontrada > 0:
                # Mapeo de columnas a actualizar
                updates = [
                    (sheet.find("NOMBRE COMPLETO").col, nombre),
                    (sheet.find("CEDULA").col, cedula),
                    (sheet.find("CARGO").col, cargo),
                    (sheet.find("AREA").col, area),
                    (sheet.find("DEPARTAMENTO").col, departamento),
                    (sheet.find("SEDE").col, sede),
                    (sheet.find("JEFE INMEDIATO").col, jefe), # Ojo con el nombre exacto de columna en Sheets
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

    # Filtros
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

    empleados_disponibles = df_filt['NOMBRE COMPLETO'].unique()
    
    if len(empleados_disponibles) > 0:
        seleccion = st.selectbox("🔍 Buscar Empleado", empleados_disponibles)
        datos = df_filt[df_filt['NOMBRE COMPLETO'] == seleccion].iloc[0]
        
        # --- UI DE LA TARJETA ---
        st.markdown("---")
        col_card_izq, col_card_der = st.columns([1, 2])
        
        with col_card_izq:
            st.markdown(f"""
            <div style="background-color: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); text-align: center;">
                <div style="font-size: 60px; margin-bottom: 10px;">👤</div>
                <h3 style="margin:0; color: #1e293b;">{seleccion}</h3>
                <p style="color: #64748b; font-weight: 500;">{datos.get('CARGO', 'Sin Cargo')}</p>
                <div style="margin-top: 15px; text-align: left; font-size: 14px; color: #475569;">
                    <p>📧 {datos.get('CORREO', '--')}</p>
                    <p>📱 {datos.get('CELULAR', '--')}</p>
                    <p>📍 {datos.get('SEDE', '--')}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Botón Manual de Funciones
            st.write(" ")
            st.markdown("##### 📄 Documentación")
            manuals_folder_id = get_or_create_manuals_folder()
            manual_file_id = find_manual_in_drive(datos.get("CARGO", ""), manuals_folder_id)
            
            if manual_file_id:
                pdf_bytes = download_manual_from_drive(manual_file_id)
                if pdf_bytes:
                    st.download_button(
                        label="📥 Descargar Manual de Funciones",
                        data=pdf_bytes,
                        file_name=f"Manual_{datos.get('CARGO','').replace(' ','_')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
            else:
                st.info("No hay manual asociado a este cargo.")

        with col_card_der:
            st.subheader("📝 Edición de Datos")
            with st.form("form_edicion"):
                c_a, c_b = st.columns(2)
                nuevo_nombre = c_a.text_input("Nombre Completo", value=datos.get("NOMBRE COMPLETO", ""))
                nuevo_cedula = c_b.text_input("Cédula (No editable para ID)", value=datos.get("CEDULA", ""), disabled=True)
                nuevo_cargo = c_a.text_input("Cargo", value=datos.get("CARGO", ""))
                nuevo_area = c_b.text_input("Área", value=datos.get("AREA", ""))
                nuevo_depto = c_a.text_input("Departamento", value=datos.get("DEPARTAMENTO", ""))
                nueva_sede = c_b.text_input("Sede", value=datos.get("SEDE", ""))
                nuevo_jefe = c_a.text_input("Jefe Inmediato", value=datos.get("JEFE_DIRECTO", "") or datos.get("JEFE INMEDIATO", ""))
                nuevo_correo = c_b.text_input("Correo", value=datos.get("CORREO", ""))
                nuevo_cel = c_a.text_input("Celular", value=datos.get("CELULAR", ""))
                nuevo_centro = c_b.text_input("Centro de Trabajo", value=datos.get("CENTRO TRABAJO", ""))
                
                # Hidden ID real para el update
                real_cedula_for_update = datos.get("CEDULA", "")
                
                submitted = st.form_submit_button("💾 Guardar Cambios", use_container_width=True)
                
                if submitted:
                    with st.spinner("Actualizando en Google Sheets..."):
                        exito = actualizar_empleado_google_sheets(
                            nuevo_nombre, real_cedula_for_update, nuevo_cargo, nuevo_area, 
                            nuevo_depto, nueva_sede, nuevo_jefe, nuevo_correo, 
                            nuevo_cel, nuevo_centro
                        )
                        if exito:
                            st.success("¡Datos actualizados correctamente!")
                            st.cache_data.clear() # Limpiar caché para recargar datos nuevos
                            import time
                            time.sleep(1)
                            st.rerun() # Reinicia la app para ver cambios
                        else:
                            st.error("No se pudo actualizar. Verifica que la cédula exista en la BD.")

    else:
        st.warning("No hay empleados que coincidan con los filtros seleccionados.")