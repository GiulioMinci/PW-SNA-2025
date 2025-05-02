import os
import cv2
import numpy as np
import sqlite3
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import traceback

# Percorsi
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "instance", "classificazioni.db")
MATCHES_DIR = os.path.join(BASE_DIR, "..", "app", "static", "matches")
os.makedirs(MATCHES_DIR, exist_ok=True)

# Log
log_errori_path = os.path.join(BASE_DIR, "..", "instance", "log_errori_sift.txt")
progress_log_path = os.path.join(BASE_DIR, "..", "instance", "progress_sift.txt")

# Funzioni di log
def logga_errore(messaggio):
    with open(log_errori_path, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat()}] {messaggio}\n")

def logga_progress(messaggio):
    with open(progress_log_path, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat()}] {messaggio}\n")

# Funzione per costruire il path assoluto delle immagini
def resolve_absolute_path(rel_path):
    rel_path = rel_path.replace("\\", "/")  # Normalizza gli slash
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base_dir, rel_path)

# Funzione per leggere le immagini che hanno caratteri speciali nei nomi
def leggi_immagine_unicode(path, flags=cv2.IMREAD_GRAYSCALE):
    try:
        stream = np.fromfile(path, dtype=np.uint8)
        image = cv2.imdecode(stream, flags)
        return image
    except Exception as e:
        logga_errore(f"Errore lettura immagine: {path} - {e}")
        return None

# Carica immagini dal DB
def carica_immagini_da_analizzare(limit):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT comune, sito_web, path
        FROM immagini
        WHERE match_sift IS NULL
        LIMIT ?
    """, (limit,))
    dati = cursor.fetchall()
    conn.close()
    return dati

# Carica template da confrontare
def carica_template_paths():
    templates_dir = os.path.join(BASE_DIR, "..", "app", "static", "templates_conformi")
    templates = []
    for filename in os.listdir(templates_dir):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
            templates.append(os.path.join(templates_dir, filename))
    return templates

# Filtra i match geometricamente
def filtra_matches_geom(matches, kp1, kp2, threshold=3.0):
    if len(matches) < 4:
        return []
    src_pts = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
    M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, threshold)
    if M is None:
        return []
    return [m for i, m in enumerate(matches) if mask[i]]

# Normalizza la dimensione del template
def normalizza_dim(template, image):
    h, w = image.shape[:2]
    return cv2.resize(template, (w, h), interpolation=cv2.INTER_AREA)

# Salva i risultati nel DB
def salva_match_db(image_path, best_matches, best_template_filename):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE immagini
        SET match_sift = ?,
            match_img_path_sift = ?,
            timestamp_sift = ?
        WHERE path = ?
    """, (
        best_matches,
        best_template_filename,
        datetime.utcnow().isoformat(),
        image_path
    ))
    conn.commit()
    conn.close()

# Analizza una singola immagine
def analizza_immagine(record):
    try:
        nome_comune, url, image_path = record
        logga_progress(f"Analizzo {image_path}...")

        image_path_abs = resolve_absolute_path(image_path)
        image = leggi_immagine_unicode(image_path_abs)

        if image is None:
            logga_errore(f"Errore nel caricamento immagine: {image_path_abs}")
            return

        sift = cv2.SIFT_create()
        best_matches = 0
        best_template_filename = ""

        template_paths = carica_template_paths()

        for template_path_abs in template_paths:
            template = leggi_immagine_unicode(template_path_abs)
            if template is None:
                logga_errore(f"Errore nel caricamento template: {template_path_abs}")
                continue

            template = normalizza_dim(template, image)
            kp1, des1 = sift.detectAndCompute(template, None)
            kp2, des2 = sift.detectAndCompute(image, None)
            if des1 is None or des2 is None:
                continue

            bf = cv2.BFMatcher(cv2.NORM_L2, crossCheck=True)
            matches = bf.match(des1, des2)
            matches_filtrati = filtra_matches_geom(matches, kp1, kp2, threshold=3.0)

            if len(matches_filtrati) > best_matches:
                best_matches = len(matches_filtrati)
                best_template_filename = os.path.basename(template_path_abs)

        salva_match_db(image_path, best_matches, best_template_filename)
        logga_progress(f"→ {image_path} → {best_matches} match")

    except Exception as e:
        logga_errore(f"Errore durante analisi immagine {record}: {e}\n{traceback.format_exc()}")

# Analizza tutte le immagini
def confronta_tutti(limit=1000):
    immagini = carica_immagini_da_analizzare(limit)
    if not immagini:
        print("✅ Nessuna immagine nuova da analizzare.")
        return

    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(analizza_immagine, immagini)

    print(f"✔️ Analisi completata su {len(immagini)} immagini.")
