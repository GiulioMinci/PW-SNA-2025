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
from multiprocessing import cpu_count, freeze_support

# Percorsi
screenshot_folder = "C:\\Users\\giuli\\Desktop\\Scraping comuni\\Screenshots"
os.makedirs(screenshot_folder, exist_ok=True)
dataset_path = "C:\\Users\\giuli\\Desktop\\Scraping comuni\\dataset.csv"
dataset_source_path = "C:\\Users\\giuli\\Desktop\\Scraping comuni\\web_comuni_join.csv"

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

def capture_screenshot(row):
    """ Cattura e salva lo screenshot con compressione e ritaglio. """
    nome_comune = row['comune']
    url = row['sito_web']

    driver = setup_driver()  # Ogni processo usa il proprio driver

    try:
        screenshot_name = f"{nome_comune.replace(' ', '_')}.jpg"
        screenshot_path = os.path.join(screenshot_folder, screenshot_name)

        # Controlla se lo screenshot esiste già
        if os.path.exists(screenshot_path):
            print(f"Screenshot già presente per {nome_comune}, skip...")
            driver.quit()
            return nome_comune, url, screenshot_path, "No"

        driver.get(url)

        # Attendi dinamicamente il caricamento del body
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        except:
            print(f"Timeout su {nome_comune}, skip...")
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
        print(f"Screenshot salvato e compresso: {screenshot_path}")

        driver.quit()
        return nome_comune, url, screenshot_path, "No"

    except Exception as e:
        print(f"Errore durante la cattura dello screenshot per {nome_comune}: {e}")
        driver.quit()
        return nome_comune, url, None, "Sì"

if __name__ == '__main__':
    freeze_support()  # Necessario su Windows per multiprocessing

    # Carica il dataset
    df_comuni = pd.read_csv(dataset_source_path)

    # Specifica l'intervallo di righe da processare
    start_index = 7501  # Modifica questo valore per riprendere da un altro punto
    batch_size = 396  # Numero di comuni da processare

    # Seleziona il batch di comuni da processare
    df_comuni_batch = df_comuni.iloc[start_index:start_index+batch_size]

    # Parallelizzazione con ProcessPoolExecutor (ogni processo ha il proprio driver)
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
        results = list(executor.map(capture_screenshot, df_comuni_batch.to_dict(orient="records")))

    # Scrittura nel CSV
    with open(dataset_path, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)

        # Scrive l'intestazione solo se il file non esiste
        if not os.path.exists(dataset_path) or os.stat(dataset_path).st_size == 0:
            writer.writerow(["Nome Comune", "URL", "Percorso Screenshot", "Conforme", "Bloccato"])

        for nome_comune, url, screenshot_path, bloccato in results:
            conforme = "Unknown"  # Da definire successivamente
            writer.writerow([nome_comune, url, screenshot_path, conforme, bloccato])
            print(f"Dati aggiornati per {nome_comune}.")

    print(f"Dataset aggiornato e salvato in {dataset_path}")
