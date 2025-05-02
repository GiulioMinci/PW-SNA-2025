import os
import sqlite3
from datetime import datetime

# === Percorsi ===
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
DB_PATH = os.path.join(BASE_DIR, "instance", "classificazioni.db")
IMG_DIR = os.path.join(BASE_DIR, "data", "raw", "screenshots")

# === Carica immagini presenti nella cartella ===
immagini_file = [f for f in os.listdir(IMG_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png"))]

# === Connetti al DB ===
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Verifica quali immagini sono già presenti
cur.execute("SELECT nome_file FROM immagini")
gia_presenti = set(row[0] for row in cur.fetchall())

aggiunte = 0
for nome_file in immagini_file:
    if nome_file not in gia_presenti:
        path = os.path.relpath(os.path.join("data/raw/screenshots", nome_file))
        cur.execute('''
            INSERT INTO immagini (nome_file, path, timestamp)
            VALUES (?, ?, ?)
        ''', (nome_file, path, datetime.now().isoformat()))
        aggiunte += 1

conn.commit()
conn.close()

print(f" {aggiunte} nuove immagini aggiunte al database.")
