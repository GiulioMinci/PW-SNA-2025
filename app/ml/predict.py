import os
import sqlite3
import numpy as np
from PIL import Image
import joblib

# === Percorsi ===
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
DB_PATH = os.path.join(BASE_DIR, "instance", "classificazioni.db")
IMG_DIR = os.path.join(BASE_DIR, "data", "raw", "screenshots")
MODEL_PATH = os.path.join(BASE_DIR, "app", "ml", "model.pkl")

# === Estrazione feature ===
def estrai_feature(path, size=(64, 64)):
    try:
        img = Image.open(path).convert("RGB").resize(size)
        return np.array(img).flatten() / 255.0
    except Exception as e:
        print(f"Errore con immagine {path}: {e}")
        return None

# === Carica modello ===
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError("Modello non trovato. Esegui prima train_model.py")

clf = joblib.load(MODEL_PATH)

# === Connessione al DB con timeout per evitare blocchi
conn = sqlite3.connect(DB_PATH, timeout=10)
cur = conn.cursor()

# === Recupera tutte le immagini
cur.execute("SELECT id, nome_file FROM immagini")
rows = cur.fetchall()

processate = 0

# === Predizioni e aggiornamento
for img_id, nome_file in rows:
    full_path = os.path.join(IMG_DIR, nome_file)
    features = estrai_feature(full_path)
    if features is not None:
        try:
            probs = clf.predict_proba([features])[0]
            predizione = clf.classes_[np.argmax(probs)]
            confidenza = float(np.max(probs))

            cur.execute("""
    UPDATE immagini
    SET etichetta_modello = ?,
        confidence = ?,
        etichetta_modello_originale = 
            CASE
                WHEN etichetta_modello_originale IS NULL THEN ?
                ELSE etichetta_modello_originale
            END,
        stato_validazione = 
            CASE
                WHEN stato_validazione IS NULL THEN 'solo_modello'
                ELSE stato_validazione
            END
    WHERE id = ?
""", (predizione, confidenza, predizione, img_id))

            processate += 1
        except Exception as e:
            print(f"Errore nella predizione per {nome_file}: {e}")

conn.commit()
conn.close()

print(f"[OK] Predizione aggiornata per {processate} immagini.")
