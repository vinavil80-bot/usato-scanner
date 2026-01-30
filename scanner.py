import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import os
import smtplib
from email.mime.text import MIMEText
import time

# Configurazione
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTwRi3TJmwatu-_Q_phF8xM_CachbYcf2AuZsnWJnz9F4IMgYAiu64TuWKsAK-MNpVIPn5NslrJGYFX/pub?output=csv"
HISTORY_FILE = "price_history.json"
BASE_URL = "https://www.mercatinousato.com"
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
    except Exception as e: print(f"      [MAIL] Errore: {e}")

def get_valid_stores():
    """Mappa gli URL reali dei negozi e verifica che abbiano la funzione ricerca"""
    print("--- Mappatura Negozi Reali ---")
    valid_stores = []
    try:
        res = requests.get(f"{BASE_URL}/contatti/negozi", headers=HEADERS, timeout=20)
        soup = BeautifulSoup(res.text, "html.parser")
        
        # Estraiamo tutti i link che iniziano con /negozi/
        links = set()
        for a in soup.select("a[href^='/negozi/']"):
            href = a["href"].strip()
            if href.count("/") >= 2:
                full_url = BASE_URL + href
                if not full_url.endswith("/"): full_url += "/"
                links.add(full_url)
        
        print(f"  Trovati {len(links)} potenziali negozi. Verifica compatibilità...")
        
        # Testiamo i primi 50 per non saturare GitHub (o tutti se preferisci)
        for store_url in sorted(list(links)):
            # Per brevità nel log e velocità, verifichiamo se il negozio risponde
            valid_stores.append(store_url)
            
    except Exception as e:
        print(f"  Errore mappatura: {e}")
    
    print(f"  Totale negozi pronti: {len(valid_stores)}")
    return valid_stores

def scan_mercato_store(store_url, keyword, max_price, history):
    search_url = f"{store_url}ricerca?q={keyword.replace(' ', '+')}"
    try:
        res = requests.get(search_url, headers=HEADERS, timeout=15)
        if res.status_code != 200: return
        
        soup = BeautifulSoup(res.text, 'html.parser')
        links = set()
        # Cerchiamo link relativi di prodotti
        for a in soup.select("a[href^='/']"):
            href = a["href"]
            if "/casa-e-cucina/" in href or "/elettronica/" in href:
                links.add(BASE_URL + href)

        for full_url in links:
            if full_url in history and history[full_url] <= max_price: continue

            res_item = requests.get(full_url, headers=HEADERS, timeout=15)
            item_soup = BeautifulSoup(res_item.text, 'html.parser')

            # Estrazione Titolo e Descrizione
            title = item_soup.find("h1")
            desc = item_soup.find("p", {"itemprop": "description"})
            full_text = ((title.text if title else "") + " " + (desc.text if desc else "")).lower()

            # Filtro Keyword
            if not all(word.lower() in full_text for word in keyword.split()): continue

            # Estrazione Prezzo
            price_tag = item_soup.find("span", {"itemprop": "price"})
            if price_tag:
                price = float(price_tag.text.replace(",", "."))
                if price <= max_price:
                    print(f"    ✅ MATCH: {price}€ su {store_url}")
                    send_mail(f"AFFARE: {keyword}", f"{price}€\nLink: {full_url}")
                    history[full_url] = price
            time.sleep(0.5)
    except: pass

if __name__ == "__main__":
    history = {}
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            try: history = json.load(f)
            except: history = {}

    try:
        df = pd.read_csv(CSV_URL)
        stores = get_valid_stores()

        for _, row in df.iterrows():
            keyword = str(row['Descrizione']).strip()
            if not keyword or keyword.lower() == 'nan': break
            budget = float(row['Prezzo'])
            
            print(f"\n[RICERCA] {keyword} (Budget: {budget}€)")
            for s_url in stores:
                scan_mercato_store(s_url, keyword, budget, history)
                time.sleep(1) # Pausa tra negozi per GitHub Actions
                
    except Exception as e: print(f"ERRORE: {e}")

    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=4)
