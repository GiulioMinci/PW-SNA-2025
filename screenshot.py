import os
import time
import csv
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image  # Per comprimere e ritagliare le immagini

# Percorsi
screenshot_folder = "C:\\Users\\giuli\\Desktop\\Scraping comuni\\Screenshots"
os.makedirs(screenshot_folder, exist_ok=True)
dataset_path = "C:\\Users\\giuli\\Desktop\\Scraping comuni\\dataset.csv"
dataset_source_path = "C:\\Users\\giuli\\Desktop\\Scraping comuni\\web_comuni_join.csv"  # Percorso del dataset fornito

# Configurazione Selenium
options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")
options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36")

# Avvia il driver
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

# Carica il dataset dei comuni da file CSV
df_comuni = pd.read_csv(dataset_source_path)

def capture_screenshot(nome_comune, url):
    try:
        screenshot_name = f"{nome_comune.replace(' ', '_')}.jpg"
        screenshot_path = os.path.join(screenshot_folder, screenshot_name)
        
        # Controlla se lo screenshot esiste già
        if os.path.exists(screenshot_path):
            print(f"Screenshot già presente per {nome_comune}, skip...")
            return screenshot_path, "No"
        
        driver.get(url)
        time.sleep(3)  # Attendi il caricamento
        temp_screenshot = os.path.join(screenshot_folder, "temp.png")
        driver.save_screenshot(temp_screenshot)

        # Carica l'immagine con PIL e la comprime + ritaglia
        with Image.open(temp_screenshot) as img:
            width, height = img.size
            new_height = int(height * 0.25)  # Mantiene solo il 25% superiore
            img_cropped = img.crop((0, 0, width, new_height))  # Ritaglia la parte superiore
            
            # Converte in JPEG con compressione
            img_cropped.save(screenshot_path, "JPEG", quality=85)
            os.remove(temp_screenshot)  # Elimina il file temporaneo

        print(f"Screenshot salvato e compresso: {screenshot_path}")
        return screenshot_path, "No"
    
    except Exception as e:
        print(f"Errore durante la cattura dello screenshot per {nome_comune}: {e}")
        return None, "Sì"

# Specifica da quale riga partire e quanti comuni processare per eseguire il codice in più sessioni
start_index = 2100  # Cambia questo valore per iniziare da una riga diversa
batch_size = 100  # Numero di comuni da processare alla volta

df_comuni_batch = df_comuni.iloc[start_index:start_index+batch_size]

# Scrittura nel CSV
with open(dataset_path, mode='a', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    
    # Scrive l'intestazione solo se il file non esiste
    if not os.path.exists(dataset_path) or os.stat(dataset_path).st_size == 0:
        writer.writerow(["Nome Comune", "URL", "Percorso Screenshot", "Conforme", "Bloccato"])
    
    for _, row in df_comuni_batch.iterrows():
        nome_comune, url = row['comune'], row['sito_web']
        screenshot_path, bloccato = capture_screenshot(nome_comune, url)
        conforme = "Unknown"  # Da definire successivamente
        writer.writerow([nome_comune, url, screenshot_path, conforme, bloccato])
        print(f"Dati aggiornati per {nome_comune}.")

# Chiudi il browser
driver.quit()
print(f"Dataset aggiornato e salvato in {dataset_path}")