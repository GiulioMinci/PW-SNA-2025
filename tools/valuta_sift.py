import sqlite3
import pandas as pd
from sklearn.metrics import accuracy_score

def valuta_accuracy_sift(db_path='instance/classificazioni.db'):
    # Collegamento al database
    conn = sqlite3.connect(db_path)

    query = """
    SELECT conforme_sift, etichetta_utente
    FROM immagini
    WHERE conforme_sift IS NOT NULL AND etichetta_utente IS NOT NULL
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    # Costruisci la "vera" etichetta binaria (normalizza maiuscole/minuscole/spazi)
    df['vero_conforme'] = df['etichetta_utente'].apply(
        lambda x: 1 if x.strip().lower() == 'design system' else 0
    )

    # Calcola l'accuracy
    if not df.empty:
        accuracy_sift = accuracy_score(df['vero_conforme'], df['conforme_sift'])
        print(f"Accuracy SIFT: {accuracy_sift:.2%}")
        return accuracy_sift
    else:
        print("⚠️ Nessun dato disponibile per valutare l'Accuracy SIFT.")
        return None
