import time
from tools.sift_checker import confronta_tutti

def main():
    print("🚀 Avvio analisi SIFT...")
    
    # Chiedi quanti file processare
    try:
        limit = int(input("Quante immagini vuoi analizzare? (default 1000): ") or "1000")
    except ValueError:
        limit = 1000

    start_time = time.time()

    confronta_tutti(limit=limit)

    elapsed = time.time() - start_time
    if elapsed > 0:
        print(f"⏱️ Tempo totale: {elapsed:.2f} secondi")
        print(f"⚡ Velocità: {limit / elapsed:.2f} immagini/secondo")
    else:
        print("⚡ Tempo troppo breve per calcolare la velocità!")

if __name__ == "__main__":
    main()
