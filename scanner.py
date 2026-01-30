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
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

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
            print(f"   [MAIL] Inviata con successo!")
    except Exception as e: print(f"   [MAIL] Errore: {e}")

def deep_scan_mercato(url, max_price, keyword):
    """Entra nella scheda prodotto e verifica i dati reali"""
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Selettori itemprop come da tua analisi
        price_meta = soup.select_one("span[itemprop='price']")
        title_meta = soup.select_one("h1[itemprop='name']")
        
        if price_meta:
            # Estraiamo il valore numerico pulito
            price_val = float(price_meta.get_text().replace(',', '.').strip())
            print(f"      > Trovato: {title_meta.get_text(strip=True) if title_meta else keyword} a {price_val}€")
            
            if price_val <= max_price:
                return price_val
        return None
    except: return None

def scan_mercatinousato(keyword, max_price, history):
    print(f"\n--- Ricerca MercatinoUsato: {keyword} ---")
    search_url = f"https://www.mercatinousato.com/ricerca?q={keyword.replace(' ', '+')}"
    
    try:
        res = requests.get(search_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Cerchiamo link relativi che contengono ID numerico alla fine (tipico degli annunci)
        found_links = set()
        for a in soup.select("a[href]"):
            href = a["href"]
            # Logica: link relativo, contiene almeno 3 slash, finisce (spesso) con numero ID
            if href.startswith("/") and len(href.split("/")) > 3:
                # Se la keyword o parti di essa sono nel link, è un candidato
                if any(word.lower() in href.lower() for word in keyword.split()):
                    full_url = "https://www.mercatinousato.com" + href
                    if full_url not in history: # Evitiamo di ri-scansionare link già processati
                        found_links.add(full_url)
        
        print(f"    Link potenziali individuati: {len(found_links)}")
        
        for link in found_links:
            prezzo_reale = deep_scan_mercato(link, max_price, keyword)
            if prezzo_reale:
                send_mail(f"AFFARE: {keyword}", f"Trovato a {prezzo_reale}€\nLink: {link}")
                history[link] = prezzo_reale
            time.sleep(1) # Rispettiamo i server
            
    except Exception as e: print(f"    Errore: {e}")

def scan_mercatopoli(keyword, max_price, history):
    print(f"\n--- Ricerca Mercatopoli: {keyword} ---")
    url = f"https://shop.mercatopoli.it/index.php?id=ricerca&q={keyword.replace(' ', '+')}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        # Mercatopoli espone i prezzi già nella lista
        for item in soup.select('.articolo_vetrina'):
            link_tag = item.find('a', href=True)
            price_tag = item.select_one('.prezzo_vetrina')
            if not link_tag or not price_tag: continue
            
            link = "https://shop.mercatopoli.it/" + link_tag['href']
            price = float(price_tag.text.replace('€', '').replace('.', '').replace(',', '.').strip())
            
            if price <= max_price and link not in history:
                send_mail(f"AFFARE MERCATOPOLI: {keyword}", f"Prezzo: {price}€\nLink: {link}")
                history[link] = price
    except: pass

if __name__ == "__main__":
    # Caricamento cronologia
    history = {}
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            try: history = json.load(f)
            except: history = {}

    # Lettura CSV Google Sheet
    try:
        df = pd.read_csv(CSV_URL)
        for _, row in df.iterrows():
            desc = str(row['Descrizione']).strip()
            if not desc or desc.lower() == 'nan': break
            
            p_max = float(row['Prezzo'])
            
            scan_mercatinousato(desc, p_max, history)
            scan_mercatopoli(desc, p_max, history)
            
    except Exception as e: print(f"ERRORE GENERALE: {e}")

    # Salvataggio cronologia
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=4)
