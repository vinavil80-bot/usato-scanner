from playwright.sync_api import sync_playwright
import pandas as pd
import json
import os
import time
import smtplib
from email.mime.text import MIMEText

CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTwRi3TJmwatu-_Q_phF8xM_CachbYcf2AuZsnWJnz9F4IMgYAiu64TuWKsAK-MNpVIPn5NslrJGYFX/pub?output=csv"
HISTORY_FILE = "price_history.json"
BASE_URL = "https://www.mercatinousato.com"

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
            print(f"      [MAIL] Inviata!")
    except Exception as e: print(f"      [MAIL] Errore: {e}")

def scan_keyword(page, keyword, max_price, history):
    print(f"\n🔍 RICERCA: {keyword} (max {max_price}€)")
    
    # Navigazione con User-Agent reale per evitare blocchi
    search_url = f"{BASE_URL}/ricerca?q={keyword.replace(' ', '+')}"
    page.goto(search_url, wait_until="networkidle", timeout=60000)
    
    # Aspettiamo che i risultati vengano renderizzati (cerchiamo i link degli annunci)
    # Usiamo un selettore più ampio: tutti i link che contengono un ID numerico finale
    page.wait_for_timeout(5000) # Attesa forzata per JS asincrono
    
    # Estraiamo i link che portano alle schede prodotto
    hrefs = page.eval_on_selector_all("a", "elements => elements.map(el => el.href)")
    links = [h for h in hrefs if "/annuncio/" in h or any(char.isdigit() for char in h.split('/')[-1])]
    links = list(set([l for l in links if BASE_URL in l]))

    print(f"   Link potenziali individuati: {len(links)}")

    for link in links:
        if link in history and history[link] <= max_price:
            continue

        try:
            page.goto(link, wait_until="domcontentloaded", timeout=30000)
            
            # Lettura Prezzo (usando itemprop come hai suggerito tu)
            price_el = page.query_selector("span[itemprop='price']")
            if not price_el:
                continue

            price_text = price_el.inner_text().replace(",", ".").strip()
            price = float(price_text)

            if price <= max_price:
                # Verifica keyword nel titolo
                title_el = page.query_selector("h1")
                title_text = title_el.inner_text().lower() if title_el else ""
                
                if any(word.lower() in title_text for word in keyword.split()):
                    print(f"   ✅ MATCH TROVATO: {price}€ → {link}")
                    send_mail(f"OFFERTA: {keyword}", f"Trovato a {price}€\nLink: {link}")
                    history[link] = price
            
            time.sleep(1)
        except Exception as e:
            continue

if __name__ == "__main__":
    history = {}
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE) as f:
            try: history = json.load(f)
            except: history = {}

    try:
        df = pd.read_csv(CSV_URL)
        with sync_playwright() as p:
            # Emuliamo un dispositivo reale
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            for _, row in df.iterrows():
                desc = str(row.iloc[0]).strip()
                if not desc or desc.lower() == "nan": break
                budget = float(row.iloc[1])
                scan_keyword(page, desc, budget, history)

            browser.close()

        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=4)
            
    except Exception as e:
        print(f"ERRORE: {e}")
