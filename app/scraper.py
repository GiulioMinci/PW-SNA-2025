import os
import time
import sqlite3
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

DB_PATH = os.path.join('instance', 'classificazioni.db')
SCREENSHOT_FOLDER = os.path.join('app', 'static', 'screenshots')
os.makedirs(SCREENSHOT_FOLDER, exist_ok=True)

def setup_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def cattura_screenshot(nome_file, url):
    driver = setup_driver()
    try:
        screenshot_name = nome_file
        if not screenshot_name.endswith(".jpg"):
            screenshot_name += ".jpg"

        screenshot_path = os.path.join(SCREENSHOT_FOLDER, screenshot_name)

        if os.path.exists(screenshot_path):
            print(f"[SKIP] {nome_file} esiste già.")
            return

        driver.get(url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        temp_path = os.path.join(SCREENSHOT_FOLDER, f"temp_{nome_file}.png")
        driver.save_screenshot(temp_path)

        with Image.open(temp_path) as img:
            width, height = img.size
            new_height = int(height * 0.25)
            cropped = img.crop((0, 0, width, new_height))
            cropped.save(screenshot_path, "JPEG", quality=85)

        os.remove(temp_path)
        print(f"[OK] Screenshot salvato per {nome_file}")

    except Exception as e:
        print(f"[ERRORE] {nome_file}: {e}")
    finally:
        driver.quit()

def esegui_scraping(limit):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT nome_file, sito_web FROM immagini ORDER BY nome_file ASC LIMIT ?", (limit,))
    comuni = cursor.fetchall()
    conn.close()

    for nome_file, url in comuni:
        if url and url.startswith("http"):
            cattura_screenshot(nome_file.replace(' ', '_'), url)
