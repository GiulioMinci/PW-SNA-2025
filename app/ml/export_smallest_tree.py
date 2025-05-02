import os
import joblib
from sklearn.tree import plot_tree
import matplotlib.pyplot as plt

# === Impostazioni
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
MODEL_PATH = os.path.join(BASE_DIR, "app", "ml", "model.pkl")
OUTPUT_DIR = os.path.join(BASE_DIR, "app", "ml", "tree_visualization")
os.makedirs(OUTPUT_DIR, exist_ok=True)
TREE_IMAGE_PATH = os.path.join(OUTPUT_DIR, "smallest_decision_tree.png")

# === Carica il modello Random Forest
clf = joblib.load(MODEL_PATH)

# === Trova l'albero più piccolo (meno nodi) nella foresta
smallest_tree = min(clf.estimators_, key=lambda est: est.tree_.node_count)

# === Disegna e salva il Decision Tree più piccolo
plt.figure(figsize=(20, 10))
plot_tree(smallest_tree,
          filled=True,
          rounded=True,
          fontsize=8)
plt.tight_layout()
plt.savefig(TREE_IMAGE_PATH, dpi=300)
plt.close()

print(f"[OK] Albero più piccolo salvato in {TREE_IMAGE_PATH}")
