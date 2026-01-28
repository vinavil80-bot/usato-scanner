import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import os
import smtplib
from email.mime.text import MIMEText

CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTwRi3TJmwatu-_Q_phF8xM_CachbYcf2AuZsnWJnz9F4IMgYAiu64TuWKsAK-MNpVIPn5NslrJGYFX/pub?output=csv"
HISTORY_FILE = "price_history.json"

def send_mail(subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = os.environ.get('EMAIL_USER')
    msg['To'] = os.environ.get('EMAIL_USER')
    
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(os.environ.get('EMAIL_USER'), os.environ.get('EMAIL_PASS'))
        server.send_message(msg)

def scan_mercatopoli(keyword, max_price, history):
    url = f"https://shop.mercatopoli.it/index.php?id=ricerca&q={keyword.replace(' ', '+')}"
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(res.text, 'html.parser')
    items = soup.select('.articolo_vetrina') # Selettore specifico
    
    for item in items:
        try:
            link = "https://shop.mercatopoli.it/" + item.find('a')['href']
            price_text = item.select_one('.prezzo_vetrina').text
            price = float(price_text.replace('€', '').replace(',', '.').strip())
            
            if price <= max_price:
                if link not in history or price < history[link]:
                    send_mail(f"Affare Mercatopoli: {keyword}", f"Trovato {keyword} a {price}€\nLink: {link}")
                    history[link] = price
        except: continue

# Caricamento dati e storia
df = pd.read_csv(CSV_URL)
if os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, 'r') as f: history = json.load(f)
else: history = {}

# Ciclo di ricerca
for index, row in df.iterrows():
    scan_mercatopoli(row[0], row[1], history)
    # Qui aggiungeremo la funzione per MercatinoUsato simile a questa

with open(HISTORY_FILE, 'w') as f: json.dump(history, f)
