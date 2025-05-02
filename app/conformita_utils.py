import os
import cv2
import numpy as np
import sqlite3
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import traceback

# Percorso corretto al database condiviso
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "instance", "classificazioni.db")
STATIC_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "app", "static"))
SCREENSHOTS_DIR = os.path.join(STATIC_DIR, "screenshots")

# Cartella in cui salvare le immagini confrontate
matches_folder = os.path.join(STATIC_DIR, "matches")
os.makedirs(matches_folder, exist_ok=True)

log_errori_path = os.path.join(BASE_DIR, "..", "instance", "log_errori_sift.txt")

def logga_errore(messaggio):
    with open(log_errori_path, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat()}] {messaggio}\n")

def resolve_absolute_path(rel_path):
    filename = os.path.basename(rel_path.replace("\\", "/"))
    return os.path.join(SCREENSHOTS_DIR, filename)

def carica_etichette():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT etichetta_utente FROM immagini WHERE etichetta_utente IS NOT NULL")
    etichette = sorted([row[0] for row in cursor.fetchall()])
    conn.close()
    return etichette

def carica_immagini_da_analizzare(limit):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT comune, sito_web, path FROM immagini LIMIT ?", (limit,))
    dati = cursor.fetchall()
    conn.close()
    return dati

def carica_template_paths(etichetta_riferimento):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT path FROM immagini WHERE etichetta_utente = ?", (etichetta_riferimento,))
    paths = [row[0] for row in cursor.fetchall()]
    conn.close()
    return paths

def filtra_matches_geom(matches, kp1, kp2, threshold=5.0):
    if len(matches) < 4:
        return []
    src_pts = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
    M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, threshold)
    if M is None:
        return []
    return [m for i, m in enumerate(matches) if mask[i]]

def normalizza_dim(template, image):
    h, w = image.shape[:2]
    return cv2.resize(template, (w, h), interpolation=cv2.INTER_AREA)

def aggiorna_record_conformita(image_path, conforme, accuratezza, etichetta, threshold, match_img_path, template_path):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE immagini
        SET conforme_sift = ?,
            match_sift = ?,
            etichetta_sift = ?,
            threshold_sift = ?,
            timestamp_sift = ?,
            match_img_path_sift = ?,
            template_path_sift = ?
        WHERE path = ?
    """, (int(conforme), accuratezza, etichetta, threshold, datetime.utcnow().isoformat(), match_img_path, template_path, image_path))
    conn.commit()
    conn.close()

def check_design_conformity(image_path, template_paths, threshold, etichetta):
    try:
        image_path_abs = resolve_absolute_path(image_path)
        image = cv2.imread(image_path_abs, cv2.IMREAD_GRAYSCALE)
        if image is None:
            logga_errore(f"Errore nel caricamento immagine: {image_path_abs}")
            return 0, 0, image_path, ""

        sift = cv2.SIFT_create()
        best_matches = 0
        best_template_path = ""
        best_template = None
        best_kp1, best_kp2, best_match_list = None, None, None

        for template_path in template_paths:
            template_path_abs = resolve_absolute_path(template_path)
            template = cv2.imread(template_path_abs, cv2.IMREAD_GRAYSCALE)
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
            matches_filtrati = filtra_matches_geom(matches, kp1, kp2, threshold=8.0)
            if len(matches_filtrati) > best_matches:
                best_matches = len(matches_filtrati)
                best_template_path = template_path
                best_template = template
                best_kp1, best_kp2, best_match_list = kp1, kp2, matches_filtrati

        conforme = best_matches > threshold

        aggiorna_record_conformita(image_path, conforme, best_matches, etichetta, threshold, image_path, best_template_path)
        return conforme, best_matches, image_path, best_template_path

    except Exception as e:
        logga_errore(f"Errore durante check_design_conformity su {image_path}: {e}\n{traceback.format_exc()}")
        return 0, 0, image_path, ""

def confronta_tutti(etichetta, threshold, limit):
    immagini = carica_immagini_da_analizzare(limit)
    template_paths = carica_template_paths(etichetta)
    risultati = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        def processa(r):
            nome_comune, url, image_path = r
            conforme, match, path1, path2 = check_design_conformity(image_path, template_paths, threshold, etichetta)
            return [nome_comune, url, path1, conforme, match, path2, etichetta, threshold]
        risultati = list(executor.map(processa, immagini))
    return risultati
