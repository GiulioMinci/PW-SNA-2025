import os
import sqlite3
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

# === CONFIG ===
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
DB_PATH = os.path.join(BASE_DIR, "instance", "classificazioni.db")
FEATURES_PATH = os.path.join(BASE_DIR, "instance", "resnet_features.npy")
IDS_PATH = os.path.join(BASE_DIR, "instance", "resnet_ids.npy")

def esegui_clusterizzazione(eps=2.5, min_samples=5):
    if not os.path.exists(FEATURES_PATH) or not os.path.exists(IDS_PATH):
        raise FileNotFoundError("Assicurati di aver eseguito prima estrai_resnet_embeddings.py")

    print("📦 Caricamento embedding ResNet101...")
    X = np.load(FEATURES_PATH)
    ids = np.load(IDS_PATH)

    print("📐 Standardizzazione feature...")
    X_scaled = StandardScaler().fit_transform(X)

    print("🧩 Avvio clusterizzazione DBSCAN...")
    dbscan = DBSCAN(eps=eps, min_samples=min_samples, n_jobs=-1)
    labels = dbscan.fit_predict(X_scaled)
    print("✅ Clustering completato.")

    print("💾 Salvataggio dei cluster nel database...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    for img_id, label in zip(ids, labels):
        is_outlier = 1 if label == -1 else 0
        cur.execute("""
            UPDATE immagini
            SET cluster_dbscan = ?, is_outlier = ?
            WHERE id = ?
        """, (int(label), is_outlier, int(img_id)))
    conn.commit()
    conn.close()

    print(f"✔️ Cluster trovati: {len(set(labels)) - (1 if -1 in labels else 0)}")
    print(f"📦 Outlier rilevati: {list(labels).count(-1)}")

    return labels

if __name__ == "__main__":
    esegui_clusterizzazione(eps=100, min_samples=1)

