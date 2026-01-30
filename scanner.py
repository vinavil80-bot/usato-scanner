import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import os
import time
import re
import smtplib
from email.mime.text import MIMEText
from urllib.parse import urljoin

BASE_URL = "https://www.mercatinousato.com"
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTwRi3TJmwatu-_Q_phF8xM_CachbYcf2AuZsnWJnz9F4IMgYAiu64TuWKsAK-MNpVIPn5NslrJGYFX/pub?output=csv"
HISTORY_FILE = "price_history.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
}

# ---------------- EMAIL ----------------

def send_mail(subject, body):
    user = os.environ.get("EMAIL_USER")
    pwd = os.environ.get("EMAIL_PASS")
    if not user or not pwd:
        print("      [MAIL] Credenziali mancanti")
        return

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = user

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(user, pwd)
        s.send_message(msg)

# ---------------- NEGOZI ----------------

def get_stores():
    print("--- Mappatura Negozi Reali (API) ---")
    stores = []

    url = "https://www.mercatinousato.com/api/negozi"

    try:
        res = requests.get(url, headers=HEADERS, timeout=20)
        res.raise_for_status()
        data = res.json()

        for n in data:
            slug = n.get("slug")
            if slug:
                stores.append(f"https://www.mercatinousato.com/negozi/{slug}/")

    except Exception as e:
        print("Errore recupero negozi:", e)

    print(f"Totale negozi trovati: {len(stores)}")
    return sorted(set(stores))


# ---------------- PREZZO ----------------

def parse_price(text):
    if not text:
        return None
    m = re.search(r"(\d+[.,]?\d*)", text.replace(".", ""))
    return float(m.group(1).replace(",", ".")) if m else None

# ---------------- SCAN NEGOZIO ----------------

def scan_store(store_url, keyword, max_price, history):
    print(f"  → {store_url}")
    r = requests.get(store_url, headers=HEADERS, timeout=20)
    soup = BeautifulSoup(r.text, "html.parser")

    links = set()
    for a in soup.select("a[href^='/annuncio/']"):
        links.add(urljoin(BASE_URL, a["href"]))

    print(f"     Annunci trovati: {len(links)}")

    for link in links:
        if link in history:
            continue

        try:
            r_item = requests.get(link, headers=HEADERS, timeout=15)
            s_item = BeautifulSoup(r_item.text, "html.parser")

            title = s_item.find("h1")
            desc = s_item.find("p", itemprop="description")
            text = ((title.text if title else "") + " " + (desc.text if desc else "")).lower()

            if not all(w in text for w in keyword.lower().split()):
                continue

            price_tag = s_item.find("span", itemprop="price")
            price = parse_price(price_tag.text if price_tag else "")

            if price and price <= max_price:
                print(f"     ✅ MATCH {price}€ → {link}")
                send_mail(
                    f"AFFARE: {keyword}",
                    f"{price} €\n{link}"
                )
                history[link] = price

            time.sleep(0.6)

        except Exception as e:
            print("     Errore annuncio:", e)

# ---------------- MAIN ----------------

if __name__ == "__main__":
    history = {}
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE) as f:
            history = json.load(f)

    df = pd.read_csv(CSV_URL)
    stores = get_stores()

    for _, row in df.iterrows():
        keyword = str(row["Descrizione"]).strip()
        if not keyword or keyword.lower() == "nan":
            continue

        max_price = float(row["Prezzo"])
        print(f"\n🔍 RICERCA: {keyword} (max {max_price}€)")

        for store in stores:
            scan_store(store, keyword, max_price, history)
            time.sleep(1.2)

    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)
