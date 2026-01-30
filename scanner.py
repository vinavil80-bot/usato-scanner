import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import os
import smtplib
from email.mime.text import MIMEText

# Configurazione
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTwRi3TJmwatu-_Q_phF8xM_CachbYcf2AuZsnWJnz9F4IMgYAiu64TuWKsAK-MNpVIPn5NslrJGYFX/pub?output=csv"
HISTORY_FILE = "price_history.json"

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
            print(f"Email inviata: {subject}")
    except Exception as e:
        print(f"Errore email: {e}")

def scan_mercatopoli(keyword, max_price, history):
    # Trasformiamo la keyword in stringa sicura per evitare l'errore 'float'
    str_keyword = str(keyword).strip()
    if not str_keyword or str_keyword == "nan": 
        return

    print(f"Scansione: {str_keyword} (Budget: {max_price}€)")
    url = f"https://shop.mercatopoli.it/index.php?id=ricerca&q={str_keyword.replace(' ', '+')}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0'}
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        items = soup.select('.articolo_vetrina')
        
        for item in items:
            link_tag = item.find('a')
            price_tag = item.select_one('.prezzo_vetrina')
            if not link_tag or not price_tag: continue
            
            link = "https://shop.mercatopoli.it/" + link_tag['href']
            # Pulizia prezzo: toglie € e trasforma virgola in punto
            p_raw = price_tag.text.replace('€', '').replace('.', '').replace(',', '.').strip()
            price = float(p_raw)
            
            if price <= max_price:
                last_price = history.get(link)
                if last_price is None or price < last_price:
                    send_mail(f"AFFARONE: {str_keyword}", f"Trovato a {price}€\nLink: {link}")
                    history[link] = price
    except Exception as e:
        print(f"Errore su {str_keyword}: {e}")

if __name__ == "__main__":
    # Carica storia
    history = {}
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f: history = json.load(f)

    # Leggi CSV
    try:
        # Usiamo i nomi delle colonne che hai creato
        df = pd.read_csv(CSV_URL)
        for _, row in df.iterrows():
            # row['Descrizione'] e row['Prezzo'] usano le tue intestazioni
            scan_mercatopoli(row['Descrizione'], row['Prezzo'], history)
    except Exception as e:
        print(f"Errore CSV: {e}")

    # Salva storia
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=4)
