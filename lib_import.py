# [IMPORTS Y CONFIG INICIALES]
import os
import zipfile
import shutil
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox
import configparser
import re

CONFIG_FILE = "config.ini"
EXTENSIONES = {
    ".kicad_sym": "lib",
    ".kicad_mod": "lib/footprints",
    ".wrl": "lib/3dmodels",
    ".stp": "lib/3dmodels"
}

def cargar_configuracion():
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_FILE):
        config["Paths"] = {
            "default_zip_folder": "por_defecto"
        }
        with open(CONFIG_FILE, "w") as f:
            config.write(f)
    else:
        config.read(CONFIG_FILE)
    return config

def mover_y_renombrar_archivos(origenes, destino_base, nombre_componente=None, is_ul=False):
    archivos_sym = []
    mod_count = 0

    for archivo_original in origenes:
        ext = os.path.splitext(archivo_original)[1].lower()
        if ext in EXTENSIONES:
            carpeta_destino = os.path.join(destino_base, EXTENSIONES[ext])
            os.makedirs(carpeta_destino, exist_ok=True)

            if is_ul:
                if ext == ".kicad_sym":
                    nuevo_nombre = f"{nombre_componente}.kicad_sym"
                elif ext == ".kicad_mod":
                    mod_count += 1
                    nuevo_nombre = f"{nombre_componente}_{mod_count}.kicad_mod"
                else:
                    nuevo_nombre = f"{nombre_componente}{ext}"
            else:
                nuevo_nombre = os.path.basename(archivo_original)

            destino = os.path.join(carpeta_destino, nuevo_nombre)

            if not os.path.exists(destino):
                shutil.move(archivo_original, destino)
                print(f"Movido: {archivo_original} → {destino}")
                if ext == ".kicad_sym":
                    archivos_sym.append(os.path.abspath(destino))
            else:
                print(f"Ya existe: {destino}, no se mueve.")

    return archivos_sym

def procesar_zip(zip_path, destino_base):
    nombre_zip = os.path.basename(zip_path)
    es_ul = nombre_zip.startswith("ul_")
    nombre_componente = os.path.splitext(nombre_zip)[0].replace("ul_", "") if es_ul else None

    with tempfile.TemporaryDirectory() as tempdir:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(tempdir)

        archivos_a_mover = []
        if es_ul and os.path.isdir(os.path.join(tempdir, "KiCADv6")):
            # Recorrer recursivamente dentro de KiCADv6
            for root, _, files in os.walk(os.path.join(tempdir, "KiCADv6")):
                for archivo in files:
                    path_completo = os.path.join(root, archivo)
                    if os.path.splitext(archivo)[1].lower() in EXTENSIONES:
                        archivos_a_mover.append(path_completo)
        else:
            # SnapEDA: buscar todo en el zip
            for root, _, files in os.walk(tempdir):
                for archivo in files:
                    path_completo = os.path.join(root, archivo)
                    if os.path.splitext(archivo)[1].lower() in EXTENSIONES:
                        archivos_a_mover.append(path_completo)

        archivos_sym = mover_y_renombrar_archivos(
            archivos_a_mover,
            destino_base,
            nombre_componente,
            is_ul=es_ul
        )

    os.remove(zip_path)
    print(f"ZIP eliminado: {zip_path}")
    return archivos_sym

def actualizar_sym_lib_table(proyecto_path, archivos_sym):
    tabla_path = os.path.join(os.path.dirname(proyecto_path), "sym-lib-table")

    if not os.path.exists(tabla_path):
        with open(tabla_path, "w") as f:
            f.write("(sym_lib_table\n  (version 7)\n)\n")

    with open(tabla_path, "r") as f:
        lineas = f.readlines()

    existentes = set()
    for linea in lineas:
        match = re.search(r'\(lib\s+\(name\s+"([^"]+)"\)', linea)
        if match:
            existentes.add(match.group(1))

    nuevas_entradas = []
    for path in archivos_sym:
        nombre = os.path.splitext(os.path.basename(path))[0]
        if nombre not in existentes:
            uri = f"${{KIPRJMOD}}/lib/{os.path.basename(path)}"
            entrada = f'  (lib (name "{nombre}")(type "KiCad")(uri "{uri}")(options "")(descr ""))\n'
            nuevas_entradas.append(entrada)

    if nuevas_entradas:
        for i in range(len(lineas) - 1, -1, -1):
            if lineas[i].strip() == ")":
                lineas[i:i] = nuevas_entradas
                break
        with open(tabla_path, "w") as f:
            f.writelines(lineas)
        print(f"{len(nuevas_entradas)} nuevas entradas añadidas a sym-lib-table.")
    else:
        print("No se añadieron nuevos símbolos (ya estaban presentes).")

def actualizar_fp_lib_table(proyecto_path):
    tabla_path = os.path.join(os.path.dirname(proyecto_path), "fp-lib-table")
    entrada = '  (lib (name "footprints")(type "KiCad")(uri "${KIPRJMOD}/lib/footprints")(options "")(descr ""))\n'

    if not os.path.exists(tabla_path):
        with open(tabla_path, "w") as f:
            f.write(f"(fp_lib_table\n  (version 7)\n{entrada})\n")
        print("Archivo fp-lib-table creado con entrada de footprints.")
        return

    with open(tabla_path, "r") as f:
        contenido = f.read()
        lineas = f.readlines()

    if 'name "footprints"' in contenido:
        print("La librería 'footprints' ya existe en fp-lib-table.")
        return

    for i in range(len(lineas) - 1, -1, -1):
        if lineas[i].strip() == ")":
            lineas[i:i] = [entrada]
            break
    with open(tabla_path, "w") as f:
        f.writelines(lineas)
    print("Entrada 'footprints' añadida a fp-lib-table.")

def ejecutar_importacion(proyecto_path, zip_folder):
    if not os.path.exists(zip_folder):
        messagebox.showerror("Error", f"La carpeta {zip_folder} no existe.")
        return

    if not proyecto_path.endswith(".kicad_pro"):
        messagebox.showerror("Error", "Selecciona un archivo .kicad_pro válido.")
        return

    zips = [f for f in os.listdir(zip_folder) if f.endswith(".zip")]
    if not zips:
        messagebox.showinfo("Nada que hacer", "No se encontraron archivos .zip.")
        return

    base_dir = os.path.dirname(proyecto_path)
    for carpeta in set(EXTENSIONES.values()):
        os.makedirs(os.path.join(base_dir, carpeta), exist_ok=True)

    nuevos_sym = []
    for zip_name in zips:
        nuevos = procesar_zip(os.path.join(zip_folder, zip_name), base_dir)
        nuevos_sym.extend(nuevos)

    if nuevos_sym:
        actualizar_sym_lib_table(proyecto_path, nuevos_sym)
    actualizar_fp_lib_table(proyecto_path)

    messagebox.showinfo("Importación completada", f"{len(zips)} ZIPs procesados.\n🔁 Si tenías KiCad abierto, reinicia el proyecto para ver las nuevas librerías.")

def iniciar_gui():
    config = cargar_configuracion()

    def seleccionar_proyecto():
        ruta = filedialog.askopenfilename(title="Selecciona .kicad_pro", filetypes=[("KiCad Project", "*.kicad_pro")])
        if ruta:
            entrada_proyecto.delete(0, tk.END)
            entrada_proyecto.insert(0, ruta)

    def seleccionar_zip_folder():
        ruta = filedialog.askdirectory(title="Selecciona carpeta con .zip")
        if ruta:
            entrada_zip.delete(0, tk.END)
            entrada_zip.insert(0, ruta)

    def ejecutar():
        ejecutar_importacion(entrada_proyecto.get(), entrada_zip.get())

    ventana = tk.Tk()
    ventana.title("Importador SnapEDA + UL (solo local)")

    tk.Label(ventana, text="Ruta del proyecto (.kicad_pro):").pack()
    entrada_proyecto = tk.Entry(ventana, width=60)
    entrada_proyecto.pack()
    tk.Button(ventana, text="Seleccionar proyecto", command=seleccionar_proyecto).pack(pady=5)

    tk.Label(ventana, text="Carpeta con archivos .zip:").pack()
    entrada_zip = tk.Entry(ventana, width=60)
    entrada_zip.insert(0, config["Paths"]["default_zip_folder"])
    entrada_zip.pack()
    tk.Button(ventana, text="Seleccionar carpeta ZIPs", command=seleccionar_zip_folder).pack(pady=5)

    tk.Button(ventana, text="Iniciar Importación", command=ejecutar).pack(pady=10)

    ventana.mainloop()

if __name__ == "__main__":
    iniciar_gui()
