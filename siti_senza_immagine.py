import os
import pandas as pd

# Percorsi
screenshot_folder = "C:\\Users\\giuli\\Desktop\\Scraping comuni\\Screenshots"
dataset_source_path = "C:\\Users\\giuli\\Desktop\\Scraping comuni\\web_comuni_join.csv"
output_path = "C:\\Users\\giuli\\Desktop\\Scraping comuni\\comuni_senza_screenshot.csv"

# Numero di siti da controllare
batch_size = 1341  # Modifica questo valore per cambiare il numero di comuni da controllare

# Carica il dataset dei comuni, gestendo NaN
df_comuni = pd.read_csv(dataset_source_path)

# Sostituisci NaN con stringa vuota per evitare errori
df_comuni['comune'] = df_comuni['comune'].fillna('')
df_comuni['sito_web'] = df_comuni['sito_web'].fillna('')

# Lista per i comuni senza screenshot
comuni_senza_screenshot = []

# Itera sui comuni e controlla se lo screenshot esiste
total_checked = 0
for _, row in df_comuni.iterrows():
    nome_comune = str(row['comune']).strip()  # Converte in stringa e rimuove spazi extra
    url = str(row['sito_web']).strip()
    
    if not nome_comune:  # Salta i comuni senza nome valido
        continue

    screenshot_name = f"{nome_comune.replace(' ', '_')}.jpg"
    screenshot_path = os.path.join(screenshot_folder, screenshot_name)
    
    if not os.path.exists(screenshot_path):  # Controlla se manca l'immagine
        comuni_senza_screenshot.append([nome_comune, url])
    
    total_checked += 1
    if total_checked >= batch_size:
        break

# Creazione DataFrame e salvataggio CSV
df_senza_screenshot = pd.DataFrame(comuni_senza_screenshot, columns=["Nome Comune", "URL"])
df_senza_screenshot.to_csv(output_path, index=False, encoding='utf-8')

print(f"File aggiornato: {output_path} con {len(comuni_senza_screenshot)} comuni senza screenshot.")
