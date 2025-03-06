import os
import csv
import cv2
import numpy as np
import logging
from concurrent.futures import ThreadPoolExecutor

# Cartelle
dataset_path = "C:\\Users\\giuli\\Desktop\\Scraping comuni\\dataset.csv"
output_csv_path = "C:\\Users\\giuli\\Desktop\\Scraping comuni\\risultati_scraping.csv"
matches_folder = "C:\\Users\\giuli\\Desktop\\Scraping comuni\\Matches"
template_folder = "C:\\Users\\giuli\\Desktop\\Scraping comuni\\Esempi"
log_path = "C:\\Users\\giuli\\Desktop\\Scraping comuni\\scraping_log.txt"

# Creazione cartelle se non esistono
os.makedirs(matches_folder, exist_ok=True)

# Configurazione del logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler(log_path), logging.StreamHandler()])

# Carica tutti i template disponibili (sia PNG che JPG)
template_paths = [os.path.join(template_folder, f) for f in os.listdir(template_folder) if f.endswith((".png", ".jpg"))]

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

def aggiungi_overlay(img, conforme, num_matches):
    """
    Aggiunge un bollino rosso/verde e il numero di punti in comune sull'immagine in bianco e nero.
    """
    overlay = img.copy()
    height, width = img.shape[:2]
    
    colore = (255) if conforme == "Sì" else (0)  # Bianco se conforme, nero se non conforme
    bollino_radius = 30
    posizione_bollino = (50, 50)
    posizione_testo = (95, 60)  # Spostato per evitare sovrapposizione

    # Disegna il bollino
    cv2.circle(overlay, posizione_bollino, bollino_radius, colore, -1)

    # Testo con il numero di match
    font = cv2.FONT_HERSHEY_SIMPLEX
    spessore_testo = 2

    # Bordo nero intorno al testo per renderlo più leggibile
    cv2.putText(overlay, f"{num_matches} match", posizione_testo, font, 1, (0, 0, 0), spessore_testo + 2, cv2.LINE_AA)
    cv2.putText(overlay, f"{num_matches} match", posizione_testo, font, 1, (255), spessore_testo, cv2.LINE_AA)

    return overlay

def check_design_conformity(image_path):
    match_img_path = os.path.join(matches_folder, os.path.basename(image_path).replace(".png", ".jpg"))

    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)  # Carica immagine in bianco e nero
    if image is None:
        logging.error(f"Errore nel caricamento dell'immagine: {image_path}")
        return "Errore", 0, "", ""

    sift = cv2.SIFT_create()
    best_matches = 0
    best_template = None
    best_kp1 = None
    best_kp2 = None
    best_match_list = None

    for template_path in template_paths:
        template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)  # Carica template in bianco e nero
        if template is None:
            continue
        template = normalizza_dim(template, image)
        kp1, des1 = sift.detectAndCompute(template, None)
        kp2, des2 = sift.detectAndCompute(image, None)
        if des1 is None or des2 is None:
            continue
        bf = cv2.BFMatcher(cv2.NORM_L2, crossCheck=True)
        matches = bf.match(des1, des2)
        matches_filtrati = filtra_matches_geom(matches, kp1, kp2, threshold=8.0)
        num_matches = len(matches_filtrati)
        if num_matches > best_matches:
            best_matches = num_matches
            best_template = template
            best_kp1 = kp1
            best_kp2 = kp2
            best_match_list = matches_filtrati

    conforme = "Sì" if best_matches > 35 else "No"

    if best_template is not None and best_kp1 is not None and best_kp2 is not None and best_match_list is not None:
        match_img = cv2.drawMatches(best_template, best_kp1, image, best_kp2, best_match_list[:50], None,
                                    flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)

        match_img = aggiungi_overlay(match_img, conforme, best_matches)  # Aggiunta overlay con bollino e testo
        cv2.imwrite(match_img_path, match_img, [int(cv2.IMWRITE_JPEG_QUALITY), 95])

    logging.info(f"{image_path}: {best_matches} matches trovati. Conformità: {conforme}")
    return conforme, best_matches, match_img_path

def process_row(row):
    nome_comune, url, image_path = row[0], row[1], row[2]
    conforme, avg_matches, match_img_path = check_design_conformity(image_path)
    return [nome_comune, url, image_path, conforme, avg_matches, match_img_path]

table_rows = [["Nome Comune", "URL", "Percorso Screenshot", "Conforme", "Media Matches", "Percorso Matches"]]
with open(dataset_path, mode='r', newline='', encoding='utf-8') as file:
    reader = csv.reader(file)
    next(reader)
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = executor.map(process_row, reader)
        table_rows.extend(results)

with open(output_csv_path, mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerows(table_rows)

logging.info(f"Analisi completata, risultati salvati in: {output_csv_path}")
