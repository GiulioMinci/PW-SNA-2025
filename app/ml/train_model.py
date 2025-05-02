import os
import sqlite3
import numpy as np
from PIL import Image
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
import joblib

# === Percorsi ===
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
DB_PATH = os.path.join(BASE_DIR, "instance", "classificazioni.db")
IMG_DIR = os.path.join(BASE_DIR, "data", "raw", "screenshots")
MODEL_PATH = os.path.join(BASE_DIR, "app", "ml", "model.pkl")
REPORT_PATH = os.path.join(BASE_DIR, "app", "ml", "training_report.txt")

# === Carica immagini etichettate dal DB ===
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("SELECT nome_file, etichetta_utente FROM immagini WHERE etichetta_utente IS NOT NULL")
rows = cur.fetchall()
conn.close()

# === Estrai feature ===
def estrai_feature(path, size=(64, 64)):
    try:
        img = Image.open(path).convert("RGB").resize(size)
        return np.array(img).flatten() / 255.0
    except Exception as e:
        print(f"Errore immagine {path}: {e}")
        return None

X, y = [], []
for nome_file, etichetta in rows:
    full_path = os.path.join(IMG_DIR, nome_file)
    features = estrai_feature(full_path)
    if features is not None:
        X.append(features)
        y.append(etichetta)

X = np.array(X)
y = np.array(y)

# === Addestra modello ===
clf = RandomForestClassifier(n_estimators=100, random_state=42)
clf.fit(X, y)

# === Valutazione ===
y_pred = clf.predict(X)
acc = accuracy_score(y, y_pred)
report = classification_report(y, y_pred)

# === Salva modello e report ===
os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
joblib.dump(clf, MODEL_PATH)

with open(REPORT_PATH, "w") as f:
    f.write(f"Accuracy: {acc:.4f}\n\n")
    f.write(report)

print(f" Modello salvato in: {MODEL_PATH}")
print(f" Report salvato in: {REPORT_PATH}")
print(f" Accuracy: {acc:.4f}")
