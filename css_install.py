import zipfile
import os
import shutil

# Percorso locale allo ZIP
zip_path = "bootstrap-italia.zip"

# Percorsi static
static_dir = "app/static"
subfolder_map = {
    "css": os.path.join(static_dir, "css"),
    "js": os.path.join(static_dir, "js"),
    "font": os.path.join(static_dir, "fonts"),
    "assets": os.path.join(static_dir, "img"),
}

# Crea le cartelle se non esistono
for path in subfolder_map.values():
    os.makedirs(path, exist_ok=True)

# Estrai e copia i file
with zipfile.ZipFile(zip_path, "r") as zip_ref:
    zip_ref.extractall("temp_bootstrap_italia")

    for internal, target in subfolder_map.items():
        src_path = os.path.join("temp_bootstrap_italia", internal)
        if os.path.exists(src_path):
            for item in os.listdir(src_path):
                src_item = os.path.join(src_path, item)
                dst_item = os.path.join(target, item)
                if os.path.isdir(src_item):
                    shutil.copytree(src_item, dst_item, dirs_exist_ok=True)
                else:
                    shutil.copy2(src_item, dst_item)

# Pulizia
shutil.rmtree("temp_bootstrap_italia")

print("✅ Bootstrap Italia installato correttamente in app/static/")
