import os
import time
import csv
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image
from multiprocessing import Pool, cpu_count

# Percorsi
screenshot_folder = "C:\\Users\\giuli\\Desktop\\Scraping comuni\\Screenshots"
dataset_path = "C:\\Users\\giuli\\Desktop\\Scraping comuni\\dataset.csv"
dataset_source_path = "C:\\Users\\giuli\\Desktop\\Scraping comuni\\web_comuni_join.csv"
os.makedirs(screenshot_folder, exist_ok=True)

# Configurazione Selenium
def create_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

# Funzione per catturare screenshot
def capture_screenshot(row):
    nome_comune, url = row['comune'], row['sito_web']
    driver = create_driver()
    
    try:
        screenshot_name = f"{nome_comune.replace(' ', '_')}.jpg"
        screenshot_path = os.path.join(screenshot_folder, screenshot_name)
        
        if os.path.exists(screenshot_path):
            print(f"Screenshot già presente per {nome_comune}, skip...")
            driver.quit()
            return [nome_comune, url, screenshot_path, "No", "No"]
        
        driver.get(url)
        time.sleep(3)  # Attendi caricamento
        temp_screenshot = os.path.join(screenshot_folder, "temp.png")
        driver.save_screenshot(temp_screenshot)
        
        with Image.open(temp_screenshot) as img:
            width, height = img.size
            new_height = int(height * 0.25)
            img_cropped = img.crop((0, 0, width, new_height))
            img_cropped.save(screenshot_path, "JPEG", quality=85)
            os.remove(temp_screenshot)
        
        print(f"Screenshot salvato per {nome_comune}")
        driver.quit()
        return [nome_comune, url, screenshot_path, "Unknown", "No"]
    except Exception as e:
        print(f"Errore per {nome_comune}: {e}")
        driver.quit()
        return [nome_comune, url, None, "Unknown", "Sì"]

# Carica il dataset
df_comuni = pd.read_csv(dataset_source_path)
start_index = 1044
batch_size = 50
num_processes = 6  # Numero di istanze parallele

df_comuni_batch = df_comuni.iloc[start_index:start_index+batch_size]

# Esegui il multiprocessing
if __name__ == "__main__":
    with Pool(num_processes) as pool:
        results = pool.map(capture_screenshot, [row for _, row in df_comuni_batch.iterrows()])
    
    # Scrittura nel file CSV
    with open(dataset_path, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        if not os.path.exists(dataset_path) or os.stat(dataset_path).st_size == 0:
            writer.writerow(["Nome Comune", "URL", "Percorso Screenshot", "Conforme", "Bloccato"])
        writer.writerows(results)
    
    print(f"Dataset aggiornato e salvato in {dataset_path}")
