from PIL import Image
import os

file_path = "C:\\Users\\giuli\\Desktop\\Scraping comuni\\Screenshots\\Agliè.jpg"
new_file_path = "C:\\Users\\giuli\\Desktop\\Scraping comuni\\Screenshots\\Agliè_converted.jpg"

if os.path.exists(file_path):
    try:
        img = Image.open(file_path)
        img.convert("RGB").save(new_file_path, "JPEG", quality=95)
        print(f"Conversione riuscita: {new_file_path}")
    except Exception as e:
        print(f"Errore nella conversione di {file_path}: {e}")
else:
    print(f"File non trovato: {file_path}")
