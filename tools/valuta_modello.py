import sqlite3
from sklearn.metrics import classification_report, accuracy_score

def valuta_modello(db_path="instance/classificazioni.db", report_path="app/ml/training_report_reale.txt"):
    # Connessione al DB
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Estrazione solo dei casi con valutazione utente
    cur.execute("""
        SELECT etichetta_utente, etichetta_modello_originale
        FROM immagini
        WHERE etichetta_utente IS NOT NULL
          AND etichetta_modello_originale IS NOT NULL
          AND stato_validazione IN ('confermato', 'corretto')
    """)

    rows = cur.fetchall()
    conn.close()

    if rows:
        y_true = [row[0] for row in rows]
        y_pred = [row[1] for row in rows]

        acc = accuracy_score(y_true, y_pred)
        report = classification_report(y_true, y_pred)

        with open(report_path, "w") as f:
            f.write(f"Accuracy (su immagini validate): {acc:.4f}\n\n")
            f.write(report)

        print("✅ Report generato in", report_path)
        print(f"Accuracy: {acc:.4f}")

        return acc, report
    else:
        print("⚠️ Nessuna immagine validata trovata per la valutazione.")
        return None, None
