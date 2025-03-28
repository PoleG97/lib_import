# KiCad Library Importer (SnapEDA & Ultra Librarian)

This is a simple and efficient graphical tool to import component libraries from **SnapEDA** and **Ultra Librarian** into a local KiCad project.  
It supports both `.zip` formats and handles symbol, footprint, and 3D model files automatically.

---

## ✅ Features

- 🧩 Compatible with **SnapEDA** and **Ultra Librarian**
- 📦 Batch import of multiple `.zip` files at once
- 🔍 Recursive extraction of relevant files (`.kicad_sym`, `.kicad_mod`, `.wrl`, `.stp`)
- ✍️ Automatic editing of:
  - `sym-lib-table`
  - `fp-lib-table`
- 📁 Correct file placement inside the KiCad project structure
- ✨ Ultra Librarian ZIPs are automatically renamed using the component name (based on the zip filename)
- ❌ Duplicate entries are not added
- 🧹 ZIP files are deleted after being processed

---

## 📦 Ultra Librarian Support

A `.zip` is detected as **Ultra Librarian** if:
- Its name starts with `ul_`, and
- It contains a folder named `KiCADv6` inside the archive

In this case:
- Files are renamed using the component name (from the zip filename)
  - e.g., `ul_LM358.zip` → `LM358.kicad_sym`, `LM358_1.kicad_mod`, `LM358.stp`
- Multiple `.kicad_mod` files are handled with suffixes to avoid overwriting: `COMPONENT_1.kicad_mod`, `COMPONENT_2.kicad_mod`, etc.

---

## 📁 Project Folder Structure (Default)

The script assumes the following default structure in your KiCad project:

```
your_project/ 
├── your_project.kicad_pro ← KiCad project main file
├── sym-lib-table ← Automatically updated with new symbols 
├── fp-lib-table ← Automatically updated with footprints 
└── lib/ 
    ├── *.kicad_sym ← Symbols (format .kicad_sym) 
├── footprints/ 
│   └── *.kicad_mod ← Footprints (format .kicad_mod) 
    └── 3dmodels/ 
        └── *.wrl / *.stp ← 3D (.wrl o .stp)
```

> 🛠️ **You can customize this structure** by editing the `EXTENSIONES` dictionary in the Python script.  
> For example, to use `symbols/` instead of `lib/`, simply change:
> ```python
> EXTENSIONES = {
>     ".kicad_sym": "symbols",
>     ...
> }
> ```

---

## 🖥️ How to Use

1. Run the script with Python 3:
   ```bash
   python importador_snapeda_local.py
   ```
2. Select your .kicad_pro project file

3. Select the folder containing your .zip files (SnapEDA or UL)

4. Click Start Import

>[!WARNING]
After importing new libraries, you must restart KiCad or reopen your project.
This is because KiCad loads the symbol and footprint tables only once, when the project is opened.
Any changes made to sym-lib-table or fp-lib-table while KiCad is open won’t be detected until the next launch.

## 🛠 Requirements

- **Python 3.11+** (or later)(could works in previous version, but NOT TESTED).
- **Standard libraries**: `tkinter`, `configparser`, `json`, `os`, `sys`.
- **Pyperclip**: For copying text to the clipboard. You can install it with `pip install pyperclip`:
- **Tkinter**: For the graphical interface. On Linux systems, you may need to install the `python3-tk` package.

You can install **tkinter** on Debian based images using the following command:

```bash
sudo apt-get install python3-tk
```

You can install the required dependencies (pip) with:

```bash
pip install -r requirements.txt
```

>[!TIP]
> To run it in the background without showing errors:
>
>`nohup python3 /path/lib_import.py > /dev/null 2>&1 &`