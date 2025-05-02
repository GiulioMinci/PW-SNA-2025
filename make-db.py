import sqlite3
import os
import pandas as pd
import unicodedata

def normalizza_nome(nome):
    nome = str(nome)
    nome = unicodedata.normalize('NFKD', nome).encode('ASCII', 'ignore').decode('utf-8')
    nome = nome.lower().replace("_", " ")
    nome = " ".join(nome.split())
    return nome.strip()

# Percorso assoluto del database
db_path = r"C:\Users\giuli\Desktop\PW addestrato\Comune-a-chi\instance\classificazioni.db"

# Connessione
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Nuove colonne da aggiungere
nuove_colonne = [
    "istat TEXT",
    "regione TEXT",
    "provincia TEXT",
    "prefisso TEXT",
    "cod_fisco TEXT",
    "num_residenti INTEGER",
    "superficie REAL",
    "cf TEXT",
    "sito_web TEXT",
    "wikipedia TEXT",
    "lng REAL",
    "lat REAL"
]

# Aggiunta colonne solo se non esistono
for col_def in nuove_colonne:
    col_name = col_def.split()[0]
    try:
        cursor.execute(f"ALTER TABLE immagini ADD COLUMN {col_def}")
    except sqlite3.OperationalError:
        print(f"Colonna '{col_name}' già esistente, salto.")

# Percorso file CSV
csv_path = r"C:\Users\giuli\Desktop\Scraping comuni\web_comuni_geo.csv"
df = pd.read_csv(csv_path)

# Normalizza i nomi dei comuni nel CSV
df['comune_norm'] = df['comune'].apply(normalizza_nome)

# Recupera immagini
cursor.execute("SELECT id, nome_file FROM immagini")
immagini = cursor.fetchall()

# Funzione helper per pulire valori tipo byte string
def pulisci(valore):
    if pd.isna(valore):
        return None
    try:
        if isinstance(valore, bytes):
            return valore.decode('utf-8', errors='ignore').strip()
        return str(valore).replace("b'", "").replace("'", "").replace("\\x00", "").strip()
    except:
        return str(valore).strip()

for id_img, nome_file in immagini:
    nome_senza_ext = os.path.splitext(nome_file)[0]
    nome_norm = normalizza_nome(nome_senza_ext)
    
    match = df[df['comune_norm'] == nome_norm]
    
    if not match.empty:
        riga = match.iloc[0]
        update_query = '''
            UPDATE immagini
            SET istat = ?, regione = ?, provincia = ?, prefisso = ?, cod_fisco = ?, 
                num_residenti = ?, superficie = ?, cf = ?, sito_web = ?, wikipedia = ?, 
                lng = ?, lat = ?
            WHERE id = ?
        '''
        valori = (
            pulisci(riga.get('istat')),
            pulisci(riga.get('regione')),
            pulisci(riga.get('provincia')),
            pulisci(riga.get('prefisso')),
            pulisci(riga.get('cod_fisco')),
            int(riga.get('num_residenti')) if pd.notna(riga.get('num_residenti')) else None,
            float(riga.get('superficie')) if pd.notna(riga.get('superficie')) else None,
            pulisci(riga.get('cf')),
            pulisci(riga.get('sito_web')),
            pulisci(riga.get('wikipedia')),
            float(riga.get('lng')) if pd.notna(riga.get('lng')) else None,
            float(riga.get('lat')) if pd.notna(riga.get('lat')) else None,
            id_img
        )
        cursor.execute(update_query, valori)
    else:
        print(f"❌ Nessuna corrispondenza trovata per '{nome_file}'")

conn.commit()
conn.close()
print("✅ Database aggiornato correttamente con valori puliti e leggibili.")
