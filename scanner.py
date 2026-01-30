import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import os
import smtplib
from email.mime.text import MIMEText

CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTwRi3TJmwatu-_Q_phF8xM_CachbYcf2AuZsnWJnz9F4IMgYAiu64TuWKsAK-MNpVIPn5NslrJGYFX/pub?output=csv"
HISTORY_FILE = "price_history.json"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def send_mail(subject, body):
    user = os.environ.get('EMAIL_USER')
    password = os.environ.get('EMAIL_PASS')
    if not user or not password: return
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = user
    msg['To'] = user
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(user, password)
            server.send_message(msg)
            print(f"Email inviata per: {subject}")
    except Exception as e: print(f"Errore mail: {e}")

def scan_mercatopoli(keyword, max_price, history):
    url = f"https://shop.mercatopoli.it/index.php?id=ricerca&q={keyword.replace(' ', '+')}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        for item in soup.select('.articolo_vetrina'):
            link = "https://shop.mercatopoli.it/" + item.find('a')['href']
            price = float(item.select_one('.prezzo_vetrina').text.replace('€', '').replace('.', '').replace(',', '.').strip())
            if price <= max_price:
                if link not in history or price < history[link]:
                    send_mail(f"MERCATOPOLI: {keyword}", f"Trovato a {price}€\nLink: {link}")
                    history[link] = price
    except: pass

def scan_mercatinousato(keyword, max_price, history):
    # MercatinoUsato usa una struttura di ricerca diversa
    url = f"https://www.mercatinousato.com/ricerca?q={keyword.replace(' ', '+')}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        # Selettore basato sulla struttura tipica delle card del sito
        items = soup.select('.item-annuncio') 
        for item in items:
            link = item.find('a')['href']
            if not link.startswith('http'): link = "https://www.mercatinousato.com" + link
            price_tag = item.select_one('.price') or item.select_one('.prezzo')
            if not price_tag: continue
            price = float(price_tag.text.replace('€', '').replace('.', '').replace(',', '.').strip())
            if price <= max_price:
                if link not in history or price < history[link]:
                    send_mail(f"MERCATINO USATO: {keyword}", f"Trovato a {price}€\nLink: {link}")
                    history[link] = price
    except: pass

if __name__ == "__main__":
    history = {}
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f: history = json.load(f)
    
    try:
        df = pd.read_csv(CSV_URL)
        for _, row in df.iterrows():
            item_name = str(row['Descrizione']).strip()
            budget = float(row['Prezzo'])
            print(f"Ricerca globale: {item_name}")
            scan_mercatopoli(item_name, budget, history)
            scan_mercatinousato(item_name, budget, history)
    except Exception as e: print(f"Errore: {e}")

    with open(HISTORY_FILE, 'w') as f: json.dump(history, f, indent=4)
