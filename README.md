# Servinet HR Dashboard

Aplicación de gestión de recursos humanos con Streamlit, integración con Google Drive y Google Sheets, generación de PDFs y uso de OpenAI.

## Características principales
- Visualización de organigrama y gestión inteligente de RRHH.
- Almacenamiento y consulta de manuales en Google Drive (cuenta personal).
- Escritura y lectura de datos en Google Sheets.
- Generación de PDFs personalizados.
- Integración con OpenAI para IA.

## Requisitos
- Python 3.8+
- Cuenta personal de Google Drive (no requiere unidad compartida).
- Archivo de credenciales de Google (service account o OAuth2).

## Instalación
1. Clona el repositorio:
   ```
   git clone https://github.com/tu-usuario/servinet-hr-dashboard.git
   cd servinet-hr-dashboard
   ```
2. Instala las dependencias:
   ```
   pip install -r requirements.txt
   ```
3. Agrega tu archivo de credenciales de Google (`service_account.json` o `client_secret.json`) en la raíz del proyecto. **No lo subas a GitHub.**
4. Comparte la carpeta destino de Drive con el correo de la cuenta de servicio y dale permisos de editor.

## Uso
1. Activa el entorno virtual:
   ```
   venv\Scripts\activate
   ```
2. Ejecuta la aplicación:
   ```
   streamlit run app.py
   ```

## Seguridad
- No subas tus credenciales ni archivos sensibles a GitHub.
- Revisa el archivo `.gitignore` para asegurar que los archivos privados estén excluidos.

## Estructura del proyecto
```
servinet-hr-dashboard/
├── app.py
├── requirements.txt
├── Dockerfile
├── modules/
│   ├── ai_brain.py
│   ├── auth.py
│   ├── database.py
│   ├── document_reader.py
│   ├── drive_manager.py
│   ├── pdf_generator.py
│   └── fonts/
├── pages/
│   ├── 1_📊_Organigrama.py
│   ├── 2_🧠_Gestion_Inteligente.py
│   └── pages/
│       └── 2_📝_Evaluaciones.py
```

## Licencia
MIT
