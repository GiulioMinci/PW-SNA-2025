import os
import time
import csv
import pandas as pd
import concurrent.futures
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image  # Per comprimere e ritagliare le immagini
from urllib.parse import urlparse  # Per estrarre il dominio puro
from multiprocessing import cpu_count, freeze_support

# Percorsi
screenshot_folder = "C:\\Users\\giuli\\Desktop\\Scraping comuni\\Screenshots\\seconda_iterazione"
os.makedirs(screenshot_folder, exist_ok=True)
dataset_path = "C:\\Users\\giuli\\Desktop\\Scraping comuni\\dataset_seconda_iterazione.csv"
input_path = "C:\\Users\\giuli\\Desktop\\Scraping comuni\\comuni_senza_screenshot.csv"

# Numero massimo di processi da avviare
num_workers = min(cpu_count(), 5)  # Evita di saturare la CPU

def setup_driver():
    """ Crea un'istanza separata di Selenium per ogni processo. """
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def check_url(url):
    """ Verifica se un URL è accessibile, restituisce True se funziona. """
    try:
        response = requests.get(url, timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def normalize_url(url):
    """ Prova diverse varianti dell'URL per trovare una versione funzionante. """
    if not url or pd.isna(url) or url.strip() == "":  # Se il sito non esiste, ritorna None
        return None

    url = url.strip()  # Rimuove spazi extra

    # 1️⃣ Prova con https://
    if url.startswith("http://"):
        url = url.replace("http://", "https://", 1)
    if check_url(url):
        print(f"✅ {url} è accessibile.")
        return url

    # 2️⃣ Se non funziona, prova con https://www.
    if "www." not in url:
        url_with_www = url.replace("https://", "https://www.", 1)
        if check_url(url_with_www):
            print(f"✅ {url_with_www} è accessibile (aggiunto www).")
            return url_with_www

    # 3️⃣ Se entrambe falliscono, estrai solo il dominio e riprova con https://
    parsed_url = urlparse(url)
    domain_only = parsed_url.netloc or parsed_url.path  # Estrai solo dominio
    if domain_only:
        url_domain_only = f"https://{domain_only}"
        if check_url(url_domain_only):
            print(f"✅ {url_domain_only} è accessibile (usando solo dominio).")
            return url_domain_only

    print(f"❌ Nessuna versione dell'URL è accessibile: {url}")
    return None  # Se nessuna versione funziona, ritorna None

def capture_screenshot(row):
    """ Cattura e salva lo screenshot con compressione e ritaglio. """
    nome_comune = row['Nome Comune']
    url = normalize_url(row['URL'])  # Corregge l'URL prima di procedere

    if not url:  # Se il comune non ha un sito, lo saltiamo
        print(f"❌ {nome_comune}: Nessun sito web valido trovato, skip...")
        return nome_comune, None, None, "Sì"

    print(f"🌍 {nome_comune}: visitando {url}")

    # Controlla se il sito risponde prima di usare Selenium
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            print(f"⚠️ {nome_comune}: il sito non risponde (HTTP {response.status_code}), skip...")
            return nome_comune, url, None, "Sì"
    except requests.exceptions.RequestException as e:
        print(f"⚠️ {nome_comune}: errore di connessione ({e}), skip...")
        return nome_comune, url, None, "Sì"

    driver = setup_driver()  # Ogni processo usa il proprio driver

    try:
        screenshot_name = f"{nome_comune.replace(' ', '_')}.jpg"
        screenshot_path = os.path.join(screenshot_folder, screenshot_name)

        # Controlla se lo screenshot esiste già
        if os.path.exists(screenshot_path):
            print(f"📸 {nome_comune}: Screenshot già presente, skip...")
            driver.quit()
            return nome_comune, url, screenshot_path, "No"

        driver.get(url)

        # Attendi dinamicamente il caricamento del body
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        except:
            print(f"⏳ {nome_comune}: Timeout nel caricamento della pagina, skip...")
            driver.quit()
            return nome_comune, url, None, "Sì"

        # Cattura lo screenshot
        temp_screenshot = os.path.join(screenshot_folder, f"temp_{nome_comune}.png")
        driver.save_screenshot(temp_screenshot)

        # Comprime e ritaglia con PIL senza salvare un file intermedio
        with Image.open(temp_screenshot) as img:
            width, height = img.size
            new_height = int(height * 0.25)  # Mantiene solo il 25% superiore
            img_cropped = img.crop((0, 0, width, new_height))
            img_cropped.save(screenshot_path, "JPEG", quality=85)
        
        os.remove(temp_screenshot)  # Rimuove il file temporaneo
        print(f"✅ {nome_comune}: Screenshot salvato e compresso: {screenshot_path}")

        driver.quit()
        return nome_comune, url, screenshot_path, "No"

    except Exception as e:
        print(f"❌ {nome_comune}: Errore durante la cattura dello screenshot: {e}")
        driver.quit()
        return nome_comune, url, None, "Sì"

if __name__ == '__main__':
    freeze_support()  # Necessario su Windows per multiprocessing

    # Carica il dataset **solo con i comuni senza screenshot**
    df_comuni = pd.read_csv(input_path)

    # Parallelizzazione con ProcessPoolExecutor (ogni processo ha il proprio driver)
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
        results = list(executor.map(capture_screenshot, df_comuni.to_dict(orient="records")))

    # Scrittura nel CSV
    with open(dataset_path, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)

        if not os.path.exists(dataset_path) or os.stat(dataset_path).st_size == 0:
            writer.writerow(["Nome Comune", "URL", "Percorso Screenshot", "Conforme", "Bloccato"])

        for nome_comune, url, screenshot_path, bloccato in results:
            conforme = "Unknown"
            writer.writerow([nome_comune, url, screenshot_path, conforme, bloccato])
            print(f"📝 Dati aggiornati per {nome_comune}.")

    print(f"📊 Dataset aggiornato e salvato in {dataset_path}")
