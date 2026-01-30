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
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'}

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
            print(f"   [MAIL] Inviata!")
    except Exception as e: print(f"   [MAIL] Errore: {e}")

def get_all_stores():
    """Recupera i sottodomini dei negozi per mappare il network"""
    print("Mappatura negozi in corso...")
    stores = ["triuggio", "milano", "roma", "torino", "bologna", "napoli", "firenze"] # Lista base di partenza
    try:
        res = requests.get("https://www.mercatinousato.com/contatti/negozi", headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        for a in soup.find_all('a', href=True):
            if 'mercatinousato.com' in a['href'] and 'https://' in a['href']:
                store = a['href'].replace('https://', '').split('.')[0]
                if store not in ['www', 'www2', 'blog', 'formazione']:
                    stores.append(store)
    except: pass
    return list(set(stores))

def scan_store(store, keyword, max_price, history):
    url = f"https://{store}.mercatinousato.com/ricerca?q={keyword.replace(' ', '+')}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if len(res.text) < 6000: return # Pagina probabilmente vuota o bloccata
        
        soup = BeautifulSoup(res.text, 'html.parser')
        # Cerchiamo i link relativi come suggerito
        for a in soup.select("a[href]"):
            href = a["href"]
            if "/annuncio/" in href and any(w.lower() in href.lower() for w in keyword.split()):
                full_url = f"https://{store}.mercatinousato.com{href}"
                
                if full_url in history and history[full_url] <= max_price: continue
                
                # Deep scan della scheda
                res_item = requests.get(full_url, headers=HEADERS, timeout=10)
                item_soup = BeautifulSoup(res_item.text, 'html.parser')
                price_tag = item_soup.find('span', {'itemprop': 'price'})
                
                if price_tag:
                    price = float(price_tag.text.replace(',', '.').strip())
                    if price <= max_price:
                        print(f"      !!! TROVATO su {store}: {price}€")
                        send_mail(f"AFFARE: {keyword}", f"Trovato a {price}€ su negozio {store}\nLink: {full_url}")
                        history[full_url] = price
    except: pass

if __name__ == "__main__":
    history = {}
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            try: history = json.load(f)
            except: history = {}

    df = pd.read_csv(CSV_URL)
    # Prendiamo i negozi (per velocizzare il test iniziamo da una lista ristretta o mappata)
    target_stores = get_all_stores()
    print(f"Negozi pronti per la scansione: {len(target_stores)}")

    for _, row in df.iterrows():
        name = str(row['Descrizione']).strip()
        if not name or name.lower() == 'nan': break
        budget = float(row['Prezzo'])
        
        print(f"\nCerco: {name} (Budget: {budget}€)")
        # Scansione distribuita sui negozi
        for store in target_stores:
            scan_store(store, name, budget, history)
            # Piccola pausa per non saturare GitHub Actions
            time.sleep(0.5)

    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=4)
