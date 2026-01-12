# to_base64.py
import base64

# Valores por defecto
default_input = "token.pickle"
default_output = "token.pickle.b64"

input_file = input(f"Nombre del archivo a codificar (ej: {default_input}): ").strip()
if not input_file:
    input_file = default_input

output_file = input(f"Nombre del archivo de salida (ej: {default_output}): ").strip()
if not output_file:
    output_file = default_output

try:
    with open(input_file, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    with open(output_file, "w") as f:
        f.write(encoded)
    print(f"Archivo codificado guardado en {output_file}")
except FileNotFoundError:
    print(f"❌ No se encontró el archivo '{input_file}'. Asegúrate de que existe en la carpeta actual.")