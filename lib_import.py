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
EXTENSIONS = {
    ".kicad_sym": "lib",
    ".kicad_mod": "lib/footprints",
    ".wrl": "lib/3dmodels",
    ".stp": "lib/3dmodels"
}

def load_configuration():
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_FILE):
        config["Paths"] = {
            "default_zip_folder": "default"
        }
        with open(CONFIG_FILE, "w") as f:
            config.write(f)
    else:
        config.read(CONFIG_FILE)
    return config

def move_and_rename_files(source_files, destination_base, component_name=None, is_ul=False):
    symbol_files = []
    mod_count = 0

    for original_file in source_files:
        ext = os.path.splitext(original_file)[1].lower()
        if ext in EXTENSIONS:
            destination_directory = os.path.join(destination_base, EXTENSIONS[ext])
            os.makedirs(destination_directory, exist_ok=True)

            if is_ul:
                if ext == ".kicad_sym":
                    new_filename = f"{component_name}.kicad_sym"
                elif ext == ".kicad_mod":
                    mod_count += 1
                    new_filename = f"{component_name}_{mod_count}.kicad_mod"
                else:
                    new_filename = f"{component_name}{ext}"
            else:
                new_filename = os.path.basename(original_file)

            destination_path = os.path.join(destination_directory, new_filename)

            if not os.path.exists(destination_path):
                shutil.move(original_file, destination_path)
                print(f"Moved: {original_file} → {destination_path}")
                if ext == ".kicad_sym":
                    symbol_files.append(os.path.abspath(destination_path))
            else:
                print(f"Exists: {destination_path}, don't move.")

    return symbol_files

def process_zip_files(zip_path, destination_base):
    zip_file_name = os.path.basename(zip_path)
    is_ul = zip_file_name.startswith("ul_")
    component_name = os.path.splitext(zip_file_name)[0].replace("ul_", "") if is_ul else None

    with tempfile.TemporaryDirectory() as tempdir:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(tempdir)

        files_to_move = []
        if is_ul and os.path.isdir(os.path.join(tempdir, "KiCADv6")):
            # Walk through the KiCADv6 directory for UL
            for root, _, files in os.walk(os.path.join(tempdir, "KiCADv6")):
                for file in files:
                    complete_file_path = os.path.join(root, file)
                    if os.path.splitext(file)[1].lower() in EXTENSIONS:
                        files_to_move.append(complete_file_path)
        else:
            # SnapEDA: search in the root directory
            for root, _, files in os.walk(tempdir):
                for file in files:
                    complete_file_path = os.path.join(root, file)
                    if os.path.splitext(file)[1].lower() in EXTENSIONS:
                        files_to_move.append(complete_file_path)

        symbol_files = move_and_rename_files(
            files_to_move,
            destination_base,
            component_name,
            is_ul=is_ul
        )

    os.remove(zip_path)
    print(f"ZIP removed: {zip_path}")
    return symbol_files

def update_symbol_library_table(project_path, symbol_files):
    symbol_library_table_path = os.path.join(os.path.dirname(project_path), "sym-lib-table")

    if not os.path.exists(symbol_library_table_path):
        with open(symbol_library_table_path, "w") as f:
            f.write("(sym_lib_table\n  (version 7)\n)\n")

    with open(symbol_library_table_path, "r") as f:
        symbol_library_lines = f.readlines()

    existing_symbols = set()
    for line in symbol_library_lines:
        match = re.search(r'\(lib\s+\(name\s+"([^"]+)"\)', line)
        if match:
            existing_symbols.add(match.group(1))

    new_symbol_entries = []
    for path in symbol_files:
        nombre = os.path.splitext(os.path.basename(path))[0]
        if nombre not in existing_symbols:
            uri = f"${{KIPRJMOD}}/lib/{os.path.basename(path)}"
            entrada = f'  (lib (name "{nombre}")(type "KiCad")(uri "{uri}")(options "")(descr ""))\n'
            new_symbol_entries.append(entrada)

    if new_symbol_entries:
        for i in range(len(symbol_library_lines) - 1, -1, -1):
            if symbol_library_lines[i].strip() == ")":
                symbol_library_lines[i:i] = new_symbol_entries
                break
        with open(symbol_library_table_path, "w") as f:
            f.writelines(symbol_library_lines)
        print(f"{len(new_symbol_entries)} new entries added to sym-lib-table.")
    else:
        print("No new symbols were added (they were already present).")

def update_fp_library_table(project_directory):
    fp_lib_table_path = os.path.join(os.path.dirname(project_directory), "fp-lib-table")
    entry = '  (lib (name "footprints")(type "KiCad")(uri "${KIPRJMOD}/lib/footprints")(options "")(descr ""))\n'

    if not os.path.exists(fp_lib_table_path):
        with open(fp_lib_table_path, "w") as f:
            f.write(f"(fp_lib_table\n  (version 7)\n{entry})\n")
        print("Archive fp-lib-table created with entry footprints.")
        return

    with open(fp_lib_table_path, "r") as f:
        file_contents = f.read()
        lines = f.readlines()

    if 'name "footprints"' in file_contents:
        print("Library 'footprints' exists in fp-lib-table.")
        return

    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip() == ")":
            lines[i:i] = [entry]
            break
    with open(fp_lib_table_path, "w") as f:
        f.writelines(lines)
    print("Entry 'footprints' added to fp-lib-table.")

def execute_import_routines(kicad_project_path, zip_folder):
    if not os.path.exists(zip_folder):
        messagebox.showerror("Error", f"Folder {zip_folder} not exists.")
        return

    if not kicad_project_path.endswith(".kicad_pro"):
        messagebox.showerror("Error", "Select valid archive .kicad_pro.")
        return

    zips = [f for f in os.listdir(zip_folder) if f.endswith(".zip")]
    if not zips:
        messagebox.showinfo("Nothing to do", ".zip don't found.")
        return

    base_dir = os.path.dirname(kicad_project_path)
    for carpeta in set(EXTENSIONS.values()):
        os.makedirs(os.path.join(base_dir, carpeta), exist_ok=True)

    new_symbol_list = []
    for zip_name in zips:
        news = process_zip_files(os.path.join(zip_folder, zip_name), base_dir)
        new_symbol_list.extend(news)

    if new_symbol_list:
        update_symbol_library_table(kicad_project_path, new_symbol_list)
    update_fp_library_table(kicad_project_path)

    messagebox.showinfo("Importation ended", f"{len(zips)} ZIPs processed.\n🔁 If you had KiCad open, restart the project to see the new libraries.")

def initialize_gui():
    config = load_configuration()

    def select_project():
        project_file_path = filedialog.askopenfilename(title="Select .kicad_pro", filetypes=[("KiCad Project", "*.kicad_pro")])
        if project_file_path:
            project_file_path_entry.delete(0, tk.END)
            project_file_path_entry.insert(0, project_file_path)

    def seleccionar_zip_folder():
        selected_directory = filedialog.askdirectory(title="Select folder with .zip")
        if selected_directory:
            zip_folder_entry.delete(0, tk.END)
            zip_folder_entry.insert(0, selected_directory)

    def execute_import():
        execute_import_routines(project_file_path_entry.get(), zip_folder_entry.get())

    window = tk.Tk()
    window.title("Local importer from SnapEDA & UL")

    tk.Label(window, text="Project path (.kicad_pro):").pack()
    project_file_path_entry = tk.Entry(window, width=60)
    project_file_path_entry.pack()
    tk.Button(window, text="Select project", command=select_project).pack(pady=5)

    tk.Label(window, text="Folder with .zip:").pack()
    zip_folder_entry = tk.Entry(window, width=60)
    zip_folder_entry.insert(0, config["Paths"]["default_zip_folder"])
    zip_folder_entry.pack()
    tk.Button(window, text="Select ZIPs folder", command=seleccionar_zip_folder).pack(pady=5)

    tk.Button(window, text="Start importation", command=execute_import).pack(pady=10)

    window.mainloop()

if __name__ == "__main__":
    initialize_gui()
