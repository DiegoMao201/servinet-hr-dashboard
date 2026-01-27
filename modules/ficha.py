import streamlit as st
import base64
from modules.database import get_employees, connect_to_drive, SPREADSHEET_ID

def render_ficha_page(cedula, token):
    # --- OCULTAR MENÚ Y ENCABEZADO ---
    st.markdown("""
        <style>
            [data-testid="stSidebar"], [data-testid="main-menu"], [data-testid="stHeader"] { display: none; }
            .main .block-container { max-width: 700px; margin: auto; padding-top: 2rem; }
        </style>
    """, unsafe_allow_html=True)

    st.image("logo_servinet.jpg", width=120)
    st.title("📝 Actualización de Ficha de Empleado")

    # --- VALIDACIÓN DEL ENLACE ---
    try:
        expected_token = base64.b64encode(str(cedula).encode()).decode()
        if token != expected_token:
            st.error("❌ Token de seguridad inválido. El enlace puede haber expirado o sido alterado.")
            st.stop()
    except Exception:
        st.error("❌ Error al validar el enlace.")
        st.stop()

    # --- DATOS DEL EMPLEADO ---
    df = get_employees()
    if df.empty:
        st.error("No se pudo conectar con la base de datos de empleados."); st.stop()

    empleado_data = df[df['CEDULA'].astype(str) == str(cedula)]
    if empleado_data.empty:
        st.error("Empleado no encontrado."); st.stop()

    datos = empleado_data.iloc[0]

    st.markdown(f"""
    <div style="background: #fff; border-radius: 12px; padding: 18px 28px; margin-bottom: 18px; box-shadow: 0 4px 24px rgba(60,60,120,0.08);">
        <h3 style="margin-bottom: 0.5em;">👤 {datos['NOMBRE COMPLETO']}</h3>
        <p style="margin:0; color:#3b82f6;"><b>Cargo:</b> {datos.get('CARGO','')}</p>
        <p style="margin:0; color:#64748b;"><b>Departamento:</b> {datos.get('DEPARTAMENTO','')}</p>
    </div>
    """, unsafe_allow_html=True)

    st.info("Por favor revisa y actualiza tus datos personales. Tu información es confidencial y solo será usada para fines internos de SERVINET.")

    with st.form("form_actualiza_ficha"):
        col1, col2 = st.columns(2)
        nombre = col1.text_input("Nombre Completo", value=datos.get("NOMBRE COMPLETO", ""))
        cedula_val = col2.text_input("Cédula", value=datos.get("CEDULA", ""), disabled=True)
        cargo = col1.text_input("Cargo", value=datos.get("CARGO", ""))
        departamento = col2.text_input("Departamento", value=datos.get("DEPARTAMENTO", ""))
        jefe = col1.text_input("Jefe Directo", value=datos.get("JEFE_DIRECTO", ""))
        sede = col2.text_input("Sede", value=datos.get("SEDE", ""))
        correo = col1.text_input("Correo", value=datos.get("CORREO", ""))
        celular = col2.text_input("Celular", value=str(datos.get("CELULAR", "")))
        direccion_residencia = col1.text_input("Dirección de Residencia", value=datos.get("DIRECCIÓN DE RESIDENCIA", ""))
        banco = col2.text_input("Banco", value=datos.get("BANCO", ""))
        fecha_ingreso = col1.text_input("Fecha de Ingreso", value=datos.get("FECHA_INGRESO", ""))
        fecha_nacimiento = col2.text_input("Fecha de Nacimiento", value=datos.get("FECHA_NACIMIENTO", ""))
        estado_civil = col1.text_input("Estado Civil", value=datos.get("ESTADO_CIVIL", ""))
        hijos = col2.text_input("Hijos", value=datos.get("HIJOS", ""))
        direccion = col1.text_input("Dirección", value=datos.get("DIRECCION", ""))

        enviado = st.form_submit_button("💾 Actualizar Datos", use_container_width=True, type="primary")

    if enviado:
        try:
            client = connect_to_drive()
            spreadsheet = client.open_by_key(SPREADSHEET_ID)
            sheet = spreadsheet.worksheet("BD EMPLEADOS")
            cell = sheet.find(str(cedula))
            if not cell:
                st.error("No se encontró tu registro en la base de datos."); st.stop()
            headers = sheet.row_values(1)
            col_map = {header.strip().upper(): i + 1 for i, header in enumerate(headers)}
            updates = {
                "NOMBRE COMPLETO": nombre,
                "CARGO": cargo,
                "DEPARTAMENTO": departamento,
                "JEFE_DIRECTO": jefe,
                "SEDE": sede,
                "CORREO": correo,
                "CELULAR": celular,
                "DIRECCIÓN DE RESIDENCIA": direccion_residencia,
                "BANCO": banco,
                "FECHA_INGRESO": fecha_ingreso,
                "FECHA_NACIMIENTO": fecha_nacimiento,
                "ESTADO_CIVIL": estado_civil,
                "HIJOS": hijos,
            }
            for key, value in updates.items():
                col_idx = col_map.get(key.strip().upper())
                if col_idx: sheet.update_cell(cell.row, col_idx, value)
            st.success("✅ ¡Tus datos han sido actualizados exitosamente!")
            st.balloons()
        except Exception as e:
            st.error(f"Error técnico al guardar: {e}")