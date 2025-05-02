import os
import sqlite3
import numpy as np
from PIL import Image
import torch
from torchvision import models, transforms

# === Percorsi
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
DB_PATH = os.path.join(BASE_DIR, "instance", "classificazioni.db")
IMG_DIR = os.path.join(BASE_DIR, "data", "raw", "screenshots")
FEATURES_PATH = os.path.join(BASE_DIR, "instance", "resnet_features.npy")
IDS_PATH = os.path.join(BASE_DIR, "instance", "resnet_ids.npy")

# === Caricamento modello ResNet101 senza classificatore finale
model = models.resnet101(weights=models.ResNet101_Weights.DEFAULT)
model.eval()
model = torch.nn.Sequential(*list(model.children())[:-1])

# === Preprocessing: bianco e nero replicato su 3 canali
preprocess = transforms.Compose([
    transforms.Grayscale(num_output_channels=3),
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225])
])

# === Carica immagini dal DB
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("SELECT id, nome_file FROM immagini")
rows = cur.fetchall()
conn.close()

# === Carica embedding esistenti se presenti
if os.path.exists(FEATURES_PATH) and os.path.exists(IDS_PATH):
    features = list(np.load(FEATURES_PATH))
    ids = list(np.load(IDS_PATH))
    print(f"📦 Caricati {len(ids)} embedding esistenti.")
else:
    features = []
    ids = []

# === Per evitare duplicati
ids_esistenti = set(ids)

BATCH_SAVE = 500
nuove = 0

for idx, (img_id, nome_file) in enumerate(rows, 1):
    if img_id in ids_esistenti:
        continue

    path = os.path.join(IMG_DIR, nome_file)
    try:
        image = Image.open(path).convert("L")  # Grayscale
        input_tensor = preprocess(image).unsqueeze(0)

        with torch.no_grad():
            output = model(input_tensor).squeeze().numpy()

        features.append(output)
        ids.append(img_id)
        nuove += 1

    except Exception as e:
        print(f"❌ Errore su {nome_file}: {e}")

    # Salvataggio parziale
    if nuove > 0 and nuove % BATCH_SAVE == 0:
        print(f"💾 Salvataggio parziale: {len(ids)} embedding totali.")
        np.save(FEATURES_PATH, np.array(features))
        np.save(IDS_PATH, np.array(ids))

# === Salvataggio finale
np.save(FEATURES_PATH, np.array(features))
np.save(IDS_PATH, np.array(ids))
print(f"✅ Totale embedding salvati: {len(ids)}")
