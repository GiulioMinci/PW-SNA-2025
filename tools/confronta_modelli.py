import sqlite3
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Forza backend non interattivo per evitare errori con tkinter

import matplotlib.pyplot as plt
import seaborn as sns
import os
from datetime import datetime
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay, classification_report, accuracy_score

def carica_dati(db_path='instance/classificazioni.db'):
    conn = sqlite3.connect(db_path)
    query = """
    SELECT etichetta_utente, etichetta_modello_originale, conforme_sift
    FROM immagini
    WHERE etichetta_utente IS NOT NULL
      AND etichetta_modello_originale IS NOT NULL
      AND conforme_sift IS NOT NULL
      AND stato_validazione IN ('confermato', 'corretto')
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    df = df.apply(lambda col: col.str.lower().str.strip() if col.dtype == 'object' else col)
    df['etichetta_sift'] = df['conforme_sift'].apply(lambda x: 'design system' if x == 1 else 'altro')
    return df

def grafico_accuracy(df, output_dir):
    acc_rf = accuracy_score(df['etichetta_utente'], df['etichetta_modello_originale'])
    acc_sift = accuracy_score(df['etichetta_utente'], df['etichetta_sift'])

    modelli = ['Random Forest', 'SIFT']
    valori = [acc_rf * 100, acc_sift * 100]
    colors = ['blue', 'orange']

    plt.figure(figsize=(8, 5))
    bars = plt.bar(modelli, valori, color=colors)
    for i, val in enumerate(valori):
        plt.text(i, val + 2, f'{val:.1f}%', ha='center')
    plt.title("Confronto Modelli vs Etichetta Utente")
    plt.ylabel("Accuracy (%)")
    plt.ylim(0, 100)
    plt.grid(axis='y', linestyle='--', alpha=0.7)

    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f'confronto_modelli_{timestamp()}.png')
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
    return path

def grafico_confusion_rf(df, output_dir):
    y_true = df['etichetta_utente']
    y_pred = df['etichetta_modello_originale']
    labels = sorted(list(set(y_true) | set(y_pred)))

    cm = confusion_matrix(y_true, y_pred, labels=labels)
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=labels)

    fig, ax = plt.subplots(figsize=(8, 6))
    disp.plot(ax=ax, cmap='Blues', xticks_rotation=45)
    plt.title("Confusion Matrix - Random Forest")

    path = os.path.join(output_dir, f'confusion_rf_{timestamp()}.png')
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
    return path

def grafico_class_report_rf(df, output_dir):
    y_true = df['etichetta_utente']
    y_pred = df['etichetta_modello_originale']
    report = classification_report(y_true, y_pred, output_dict=True)
    df_report = pd.DataFrame(report).T.drop(['accuracy', 'macro avg', 'weighted avg'])

    fig, ax = plt.subplots(figsize=(10, 5))
    df_report[['precision', 'recall', 'f1-score']].plot(kind='bar', ax=ax)
    plt.title("Metriche per classe - Random Forest")
    plt.ylim(0, 1)
    plt.grid(axis='y', linestyle='--', alpha=0.5)

    path = os.path.join(output_dir, f'metriche_rf_{timestamp()}.png')
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
    return path

def grafico_confusion_sift(df, output_dir):
    df['vero_conforme'] = df['etichetta_utente'].apply(lambda x: 1 if x == 'design system' else 0)
    cm = confusion_matrix(df['vero_conforme'], df['conforme_sift'], labels=[1, 0])
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=["Design System", "Altro"])

    fig, ax = plt.subplots(figsize=(5, 4))
    disp.plot(ax=ax, cmap='Oranges')
    plt.title("Confusion Matrix - SIFT")

    path = os.path.join(output_dir, f'confusion_sift_{timestamp()}.png')
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
    return path

def timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def genera_grafico_confronto():
    output_dir = 'app/static/confronti/'
    df = carica_dati()

    paths = [
        grafico_accuracy(df, output_dir),
        grafico_confusion_rf(df, output_dir),
        grafico_class_report_rf(df, output_dir),
        grafico_confusion_sift(df, output_dir)
    ]
    return [p.replace('app/static/', '') for p in paths]
