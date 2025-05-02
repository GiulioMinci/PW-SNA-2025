import os
import cv2
import numpy as np
import sqlite3
import time

# === CONFIGURAZIONI =====
DB_PATH = "instance/classificazioni.db"
SCREENSHOTS_DIR = "app/static/screenshots"
TEMPLATES_DIR = "app/static/templates_conformi"
MATCHES_SIFT_DIR = "app/static/matches_sift"
os.makedirs(MATCHES_SIFT_DIR, exist_ok=True)
# =========================

def filtra_matches_geom(matches, kp1, kp2, threshold=5.0):
    if len(matches) < 4:
        return []
    src_pts = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
    M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, threshold)
    if M is None:
        return []
    return [m for i, m in enumerate(matches) if mask[i]]

def carica_immagini(limit):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT path, nome_file
        FROM immagini
        LIMIT ?
    """, (limit,))
    immagini = cur.fetchall()
    conn.close()
    return immagini

def carica_template_paths():
    return [
        os.path.join(TEMPLATES_DIR, f)
        for f in os.listdir(TEMPLATES_DIR)
        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))
    ]

def trova_miglior_template(img_path, template_paths):
    sift = cv2.SIFT_create(nfeatures=500)
    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return None, None, None, None

    kp_img, des_img = sift.detectAndCompute(img, None)
    if des_img is None:
        return None, None, None, None

    best_matches = 0
    best_template_path = None
    best_matches_filtrati = None
    best_kp_template = None

    bf = cv2.BFMatcher(cv2.NORM_L2, crossCheck=True)

    for template_path in template_paths:
        template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
        if template is None:
            continue

        kp_template, des_template = sift.detectAndCompute(template, None)
        if des_template is None:
            continue

        matches = bf.match(des_template, des_img)
        matches_filtrati = filtra_matches_geom(matches, kp_template, kp_img, threshold=5.0)

        if len(matches_filtrati) > best_matches:
            best_matches = len(matches_filtrati)
            best_template_path = template_path
            best_matches_filtrati = matches_filtrati
            best_kp_template = kp_template

    return best_template_path, best_kp_template, kp_img, best_matches_filtrati

def salva_match(img_path, template_path, kp_template, kp_img, matches_filtrati, nome_output):
    img_template = cv2.imread(template_path, cv2.IMREAD_COLOR)
    img = cv2.imread(img_path, cv2.IMREAD_COLOR)

    if img_template is None or img is None:
        print(f"❌ Errore nel caricamento immagini {img_path} o {template_path}")
        return

    img_template = cv2.cvtColor(img_template, cv2.COLOR_BGR2RGB)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    img_matches = cv2.drawMatches(
        img_template, kp_template,
        img, kp_img,
        matches_filtrati, None,
        flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS
    )

    # 🔵 Scrive sopra il numero di match trovati
    num_match = len(matches_filtrati)
    testo = f"Match trovati: {num_match}"
    posizione = (50, 50)
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 2.0
    colore = (0, 255, 0) if num_match >= 30 else (0, 0, 255)  # Verde se molti match, rosso se pochi
    spessore = 4

    img_matches = cv2.cvtColor(img_matches, cv2.COLOR_RGB2BGR)
    cv2.putText(img_matches, testo, posizione, font, font_scale, colore, spessore, cv2.LINE_AA)

    output_path = os.path.join(MATCHES_SIFT_DIR, nome_output)
    cv2.imwrite(output_path, img_matches)

def main():
    print("🚀 Batch Visualizzazione Match SIFT")

    try:
        limit = int(input("Quante immagini vuoi analizzare? (default 1000): ") or "1000")
    except ValueError:
        limit = 1000

    immagini = carica_immagini(limit)
    templates = carica_template_paths()

    start_time = time.time()

    for idx, (path_db, nome_file) in enumerate(immagini, start=1):
        print(f"[{idx}/{limit}] Analizzo {nome_file}...")

        screenshot_path = os.path.join(SCREENSHOTS_DIR, os.path.basename(path_db.replace("\\", "/")))

        best_template_path, best_kp_template, best_kp_img, best_matches_filtrati = trova_miglior_template(
            screenshot_path, templates
        )

        if best_template_path and best_matches_filtrati:
            nome_output = f"match_{nome_file}".replace(" ", "_")
            salva_match(
                screenshot_path,
                best_template_path,
                best_kp_template,
                best_kp_img,
                best_matches_filtrati,
                nome_output
            )
            print(f"✅ Salvato: {nome_output} ({len(best_matches_filtrati)} match)")
        else:
            print(f"⚠️ Nessun match trovato per {nome_file}")

    elapsed = time.time() - start_time
    print(f"⏱️ Tempo totale: {elapsed:.2f} secondi")

if __name__ == "__main__":
    main()
