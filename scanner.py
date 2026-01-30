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

# Header molto più dettagliati per evitare il blocco bot
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://www.google.com/',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
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
        res = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        items = soup.select('.articolo_vetrina')
        for item in items:
            link = "https://shop.mercatopoli.it/" + item.find('a')['href']
            price_tag = item.select_one('.prezzo_vetrina')
            if not price_tag: continue
            price = float(price_tag.text.replace('€', '').replace('.', '').replace(',', '.').strip())
            if price <= max_price:
                if link not in history or price < history[link]:
                    send_mail(f"MERCATOPOLI: {keyword}", f"Trovato a {price}€\nLink: {link}")
                    history[link] = price
    except: pass

def scan_mercatinousato(keyword, max_price, history):
    print(f"  [MercatinoUsato] Cerco: {keyword}")
    # Proviamo a usare l'URL di ricerca con filtri di ordinamento per forzare il caricamento
    search_url = f"https://www.mercatinousato.com/ricerca?q={keyword.replace(' ', '+')}&sort=newest"
    
    try:
        session = requests.Session() # Usiamo una sessione per gestire i cookie
        res = session.get(search_url, headers=HEADERS, timeout=20)
        
        # Debug: stampiamo la lunghezza della risposta
        print(f"    Risposta ricevuta: {len(res.text)} caratteri")
        
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Cerchiamo i link degli annunci in modo estremamente generico
        links_found = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            # Cerca link che contengono la keyword (o parte di essa) e la parola annuncio
            parts = keyword.lower().split()
            if '/annuncio/' in href and any(p in href.lower() for p in parts):
                if not href.startswith('http'): 
                    href = "https://www.mercatinousato.com" + href
                if href not in links_found:
                    links_found.append(href)
        
        print(f"    Link identificati: {len(links_found)}")

        for link in links_found:
            try:
                # Se è già in cronologia con prezzo minore, saltiamo
                if link in history and history[link] <= max_price: continue
                
                time.sleep(2) # Pausa tra un annuncio e l'altro
                res_item = session.get(link, headers=HEADERS, timeout=15)
                item_soup = BeautifulSoup(res_item.text, 'html.parser')
                
                # Cerchiamo il prezzo nel formato itemprop che ci hai dato
                price_tag = item_soup.find('span', {'itemprop': 'price'}) or item_soup.select_one('.price')
                
                if price_tag:
                    # Pulizia robusta del prezzo
                    p_text = price_tag.text.split('€')[0].replace('.', '').replace(',', '.').strip()
                    price = float(p_text)
                    print(f"    -> Trovato {link} a {price}€")
                    
                    if price <= max_price:
                        if link not in history or price < history[link]:
                            send_mail(f"MERCATINO: {keyword}", f"Prezzo: {price}€\nLink: {link}")
                            history[link] = price
            except: continue
            
    except Exception as e: 
        print(f"    Errore durante la scansione: {e}")

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
        time.sleep(3) # Aumentiamo la pausa per non insospettire i server
        scan_mercatinousato(name, budget, history)
