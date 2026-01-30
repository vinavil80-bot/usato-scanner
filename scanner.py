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
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

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
                    send_mail(f"OFFERTA MERCATOPOLI: {keyword}", f"Prezzo: {price}€\nLink: {link}")
                    history[link] = price
    except Exception as e: print(f"   ! Errore Mercatopoli: {e}")

def scan_mercatinousato(keyword, max_price, history):
    print(f"  [MercatinoUsato] Cerco: {keyword}")
    url = f"https://www.mercatinousato.com/ricerca?q={keyword.replace(' ', '+')}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        # Cerchiamo tutti i link che portano a un annuncio
        links = soup.find_all('a', href=True)
        found_count = 0
        for l in links:
            href = l['href']
            if '/annuncio/' in href:
                found_count += 1
                if not href.startswith('http'): href = "https://www.mercatinousato.com" + href
                # Proviamo a trovare il prezzo vicino al link
                parent = l.find_parent('div')
                price_tag = parent.find(text=lambda t: '€' in t) if parent else None
                if price_tag:
                    try:
                        price = float(price_tag.replace('€', '').replace('.', '').replace(',', '.').strip())
                        if price <= max_price:
                            if href not in history or price < history[href]:
                                send_mail(f"OFFERTA MERCATINO: {keyword}", f"Prezzo: {price}€\nLink: {href}")
                                history[href] = price
                    except: continue
        print(f"    Analizzati {found_count} link annuncio")
    except Exception as e: print(f"   ! Errore Mercatino: {e}")

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
            # SE INCONTRA RIGHE VUOTE, FERMA IL CICLO
            if not name or name.lower() == 'nan' or name == "": 
                break 
            
            budget = float(row['Prezzo'])
            scan_mercatopoli(name, budget, history)
            scan_mercatinousato(name, budget, history)
            time.sleep(1)
    except Exception as e: print(f"Errore CSV: {e}")

    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=4)
