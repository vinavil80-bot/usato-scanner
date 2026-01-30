import requests
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
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(res.text, 'html.parser')
        items = soup.select('.articolo_vetrina')
        for item in items:
            link = "https://shop.mercatopoli.it/" + item.find('a')['href']
            price_text = item.select_one('.prezzo_vetrina').text
            price = float(price_text.replace('€', '').replace('.', '').replace(',', '.').strip())
            if price <= max_price:
                if link not in history or price < history[link]:
                    send_mail(f"MERCATOPOLI: {keyword}", f"Trovato {keyword} a {price}€\nLink: {link}")
                    history[link] = price
    except: pass

def scan_mercatinousato(keyword, max_price, history):
    print(f"  [MercatinoUsato] Cerco: {keyword}")
    # Usiamo l'endpoint di ricerca interna che restituisce dati puliti
    search_url = f"https://www.mercatinousato.com/ricerca?q={keyword.replace(' ', '+')}"
    try:
        res = requests.get(search_url, headers=HEADERS, timeout=15)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Cerchiamo tutti i blocchi annuncio
        annunci = soup.find_all('div', class_='item-annuncio')
        found_on_page = 0
        
        for annuncio in annunci:
            try:
                link_tag = annuncio.find('a', href=True)
                title_tag = annuncio.find('h3') or annuncio.find('div', class_='title')
                price_tag = annuncio.find('div', class_='price')
                
                if not link_tag or not price_tag: continue
                
                link = link_tag['href']
                if not link.startswith('http'): link = "https://www.mercatinousato.com" + link
                
                # Pulizia prezzo estrema
                raw_price = price_tag.text.split('€')[0].replace('.', '').replace(',', '.').strip()
                price = float(raw_price)
                
                if price <= max_price:
                    found_on_page += 1
                    if link not in history or price < history[link]:
                        send_mail(f"MERCATINO: {keyword}", f"Trovato: {keyword} a {price}€\nLink: {link}")
                        history[link] = price
            except: continue
        print(f"    Match trovati: {found_on_page}")
    except Exception as e: print(f"    Errore: {e}")

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
            time.sleep(1)
    except Exception as e: print(f"Errore CSV: {e}")

    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=4)
