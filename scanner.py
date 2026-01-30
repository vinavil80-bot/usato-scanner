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
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}

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
        soup = BeautifulSoup(res.text, 'html.parser')
        items = soup.select('.articolo_vetrina')
        for item in items:
            link = "https://shop.mercatopoli.it/" + item.find('a')['href']
            price_text = item.select_one('.prezzo_vetrina').text
            price = float(price_text.replace('€', '').replace('.', '').replace(',', '.').strip())
            if price <= max_price:
                if link not in history or price < history[link]:
                    send_mail(f"MERCATOPOLI: {keyword}", f"Trovato a {price}€\nLink: {link}")
                    history[link] = price
    except: pass

def scan_mercatinousato(keyword, max_price, history):
    print(f"  [MercatinoUsato] Cerco: {keyword}")
    # Passaggio 1: Cerchiamo i link nella pagina di ricerca
    search_url = f"https://www.mercatinousato.com/ricerca?q={keyword.replace(' ', '+')}"
    try:
        res = requests.get(search_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Trova tutti i link che sembrano annunci
        potential_links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            # Filtriamo per keyword e struttura link
            if '/annuncio/' in href and any(word.lower() in href.lower() for word in keyword.split()):
                if not href.startswith('http'): href = "https://www.mercatinousato.com" + href
                if href not in potential_links: potential_links.append(href)

        print(f"    Link trovati da verificare: {len(potential_links)}")

        # Passaggio 2: Entriamo in ogni link e leggiamo l'HTML che hai analizzato tu
        for link in potential_links:
            try:
                # Se abbiamo già visto questo link con questo prezzo, saltiamo per risparmiare tempo
                if link in history and history[link] <= max_price: continue

                res_item = requests.get(link, headers=HEADERS, timeout=10)
                item_soup = BeautifulSoup(res_item.text, 'html.parser')
                
                # Usiamo i selettori itemprop che hai trovato!
                price_meta = item_soup.find('span', {'itemprop': 'price'})
                name_meta = item_soup.find('h1', {'itemprop': 'name'})
                
                if price_meta:
                    price = float(price_meta.text.strip().replace(',', '.'))
                    print(f"    Verifico {link}: Prezzo {price}€")
                    
                    if price <= max_price:
                        if link not in history or price < history[link]:
                            send_mail(f"MERCATINO: {keyword}", f"Oggetto: {name_meta.text if name_meta else keyword}\nPrezzo: {price}€\nLink: {link}")
                            history[link] = price
                time.sleep(1) # Pausa per non essere bloccati
            except: continue
            
    except Exception as e: print(f"    Errore Mercatino: {e}")

if __name__ == "__main__":
    history = {}
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            try: history = json.load(f)
            except: history = {}

    try:
        df = pd.read_csv(CSV_URL)
        for _, row in df.iterrows():
            name = str(row['Descrizione']).strip()
            if not name or name.lower() == 'nan': break 
            budget = float(row['Prezzo'])
            
            scan_mercatopoli(name, budget, history)
            scan_mercatinousato(name, budget, history)
            
    except Exception as e: print(f"Errore: {e}")

    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=4)
