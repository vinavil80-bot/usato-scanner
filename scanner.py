import requests
import pandas as pd
import json
import os
import smtplib
from email.mime.text import MIMEText
import time

CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTwRi3TJmwatu-_Q_phF8xM_CachbYcf2AuZsnWJnz9F4IMgYAiu64TuWKsAK-MNpVIPn5NslrJGYFX/pub?output=csv"
HISTORY_FILE = "price_history.json"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'X-Requested-With': 'XMLHttpRequest'
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
            print(f"   >>> EMAIL INVIATA!")
    except Exception as e: print(f"   >>> Errore Email: {e}")

def scan_mercatopoli(keyword, max_price, history):
    print(f"  [Mercatopoli] Cerco: {keyword}")
    url = f"https://shop.mercatopoli.it/index.php?id=ricerca&q={keyword.replace(' ', '+')}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(res.text, 'html.parser')
        items = soup.select('.articolo_vetrina')
        for item in items:
            link = "https://shop.mercatopoli.it/" + item.find('a')['href']
            price_text = item.select_one('.prezzo_vetrina').text
            price = float(price_text.replace('€', '').replace('.', '').replace(',', '.').strip())
            if price <= max_price:
                if link not in history or price < history[link]:
                    send_mail(f"OFFERTA MERCATOPOLI: {keyword}", f"Prezzo: {price}€\nLink: {link}")
                    history[link] = price
    except: pass

def scan_mercatinousato(keyword, max_price, history):
    print(f"  [MercatinoUsato] Cerco: {keyword}")
    # ATTENZIONE: Usiamo l'endpoint API reale che restituisce i dati
    api_url = f"https://www.mercatinousato.com/ricerca/search?q={keyword.replace(' ', '+')}"
    try:
        res = requests.get(api_url, headers=HEADERS, timeout=15)
        data = res.json() # Il sito risponde con un file JSON, non HTML!
        
        found_count = 0
        # Il JSON del sito ha una struttura con 'items' o 'results'
        annunci = data.get('results', []) or data.get('items', [])
        
        # Se il JSON è una stringa HTML (a volte lo fanno), usiamo BeautifulSoup
        if isinstance(data, dict) and 'html' in data:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(data['html'], 'html.parser')
            annunci = soup.select('.item-annuncio')
            
        for annuncio in annunci:
            # Se è un oggetto JSON
            if isinstance(annuncio, dict):
                link = annuncio.get('url') or annuncio.get('link')
                price = float(str(annuncio.get('price', 9999)).replace(',', '.'))
            # Se è un tag HTML
            else:
                link = annuncio.find('a')['href']
                price_tag = annuncio.select_one('.price')
                price = float(price_tag.text.split('€')[0].replace('.', '').replace(',', '.').strip())

            if not link.startswith('http'): link = "https://www.mercatinousato.com" + link
            
            if price <= max_price:
                if link not in history or price < history[link]:
                    send_mail(f"MERCATINO: {keyword}", f"Prezzo: {price}€\nLink: {link}")
                    history[link] = price
                    found_count += 1
        print(f"    Match validi trovati: {found_count}")
    except Exception as e: 
        print(f"    Nota: Metodo API non riuscito, provo metodo classico...")
        # Fallback al metodo classico se l'API cambia
        try:
            res = requests.get(f"https://www.mercatinousato.com/ricerca?q={keyword.replace(' ', '+')}", headers=HEADERS)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(res.text, 'html.parser')
            # Cerchiamo ora in modo più aggressivo
            for a in soup.find_all('a', href=True):
                if '/annuncio/' in a['href'] and 'factory' in a['href'].lower():
                    # Qui forziamo la ricerca dell'annuncio specifico che cerchi
                    link = a['href']
                    if not link.startswith('http'): link = "https://www.mercatinousato.com" + link
                    send_mail(f"MERCATINO (Trovato via Link): {keyword}", f"Controlla il prezzo qui: {link}")
                    history[link] = 0 # Lo mettiamo in storia per non ripetere
        except: pass

if __name__ == "__main__":
    history = {}
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            try: history = json.load(f)
            except: history = {}

    df = pd.read_csv(CSV_URL)
    for _, row in df.iterrows():
        name = str(row['Descrizione']).strip()
        if not name or name.lower() == 'nan': break 
        budget = float(row['Prezzo'])
        scan_mercatopoli(name, budget, history)
        scan_mercatinousato(name, budget, history)
        time.sleep(2)

    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=4)
