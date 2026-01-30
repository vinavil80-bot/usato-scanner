import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import os
import smtplib
from email.mime.text import MIMEText
import time

CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTwRi3TJmwatu-_Q_phF8xM_CachbYcf2AuZsnWJnz9F4IMgYAiu64TuWKsAK-MNpVIPn5NslrJGYFX/pub?output=csv"
HISTORY_FILE = "price_history.json"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
}

def send_mail(subject, body):
    user = os.environ.get('EMAIL_USER')
    password = os.environ.get('EMAIL_PASS')
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = user
    msg['To'] = user
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(user, password)
            server.send_message(msg)
            print(f"      [MAIL] Inviata correttamente!")
    except Exception as e: 
        print(f"      [MAIL] Errore: {e}")

def get_all_stores():
    """Mappa i sottodomini dei negozi dal sito ufficiale"""
    stores = ["triuggio", "milano", "roma", "torino", "monza", "bergamo", "bologna"]
    try:
        res = requests.get("https://www.mercatinousato.com/contatti/negozi", headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        for a in soup.find_all('a', href=True):
            if 'mercatinousato.com' in a['href']:
                store = a['href'].replace('https://', '').replace('http://', '').split('.')[0]
                if store not in ['www', 'www2', 'blog', 'formazione', '']:
                    stores.append(store)
    except: pass
    return list(set(stores))

def scan_store(store, keyword, max_price, history):
    url = f"https://{store}.mercatinousato.com/ricerca?q={keyword.replace(' ', '+')}"
    print(f"  → Scansione negozio: {store}")

    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')

        # Raccolta link relativi della categoria casa-e-cucina
        links = set()
        for a in soup.select("a[href^='/']"):
            href = a["href"]
            if "/casa-e-cucina/" in href:
                links.add(f"https://{store}.mercatinousato.com{href}")

        if links:
            print(f"     Trovati {len(links)} link da analizzare...")

        for full_url in links:
            # Salta se già inviato in passato per questo prezzo
            if full_url in history and history[full_url] <= max_price:
                continue

            try:
                res_item = requests.get(full_url, headers=HEADERS, timeout=15)
                item = BeautifulSoup(res_item.text, 'html.parser')

                # Estrazione Titolo e Descrizione per filtraggio keyword
                title_tag = item.find("h1")
                desc_tag = item.find("p", {"itemprop": "description"})
                
                full_text = ((title_tag.text if title_tag else "") + " " + (desc_tag.text if desc_tag else "")).lower()

                # Verifica se TUTTE le parole della keyword sono presenti nel testo dell'annuncio
                if not all(word.lower() in full_text for word in keyword.split()):
                    continue

                # Estrazione Prezzo (itemprop="price" è il più affidabile)
                price_tag = item.find("span", {"itemprop": "price"})
                if not price_tag:
                    continue

                price = float(price_tag.text.replace(",", "."))
                
                if price <= max_price:
                    print(f"      ✅ MATCH: {price}€ → {full_url}")
                    send_mail(
                        f"AFFARE TROVATO: {keyword}",
                        f"Oggetto: {title_tag.text if title_tag else keyword}\nPrezzo: {price}€\nNegozio: {store}\nLink: {full_url}"
                    )
                    history[full_url] = price
                
                time.sleep(0.5) # Pausa cortesia tra schede
            except:
                continue

    except Exception as e:
        print(f"     ❌ Errore su {store}: {e}")

if __name__ == "__main__":
    history = {}
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            try: history = json.load(f)
            except: history = {}

    try:
        df = pd.read_csv(CSV_URL)
        stores = get_all_stores()
        print(f"Inizio scansione su {len(stores)} negozi per ogni ricerca...")

        for _, row in df.iterrows():
            keyword = str(row['Descrizione']).strip()
            if not keyword or keyword.lower() == 'nan': break
            
            budget = float(row['Prezzo'])
            print(f"\n[CERCO] {keyword} (Max: {budget}€)")
            
            for store in stores:
                scan_store(store, keyword, budget, history)
                
    except Exception as e:
        print(f"ERRORE GENERALE SCRIPT: {e}")

    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=4)
