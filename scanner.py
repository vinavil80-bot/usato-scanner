import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import os
import time

CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTwRi3TJmwatu-_Q_phF8xM_CachbYcf2AuZsnWJnz9F4IMgYAiu64TuWKsAK-MNpVIPn5NslrJGYFX/pub?output=csv"
HISTORY_FILE = "price_history.json"
BASE_URL = "https://www.mercatinousato.com"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "it-IT,it;q=0.9",
}

def scan_global_search(keyword, max_price, history):
    print(f"\n🔍 RICERCA: {keyword} (max {max_price}€)")
    page = 1

    while page <= 3:  # prime 3 pagine
        url = f"{BASE_URL}/ricerca?q={keyword.replace(' ', '+')}&page={page}"
        r = requests.get(url, headers=HEADERS, timeout=20)

        if r.status_code != 200 or len(r.text) < 5000:
            break

        soup = BeautifulSoup(r.text, "html.parser")

        links = set(
            BASE_URL + a["href"]
            for a in soup.select("a[href^='/annuncio/']")
        )

        if not links:
            break

        for link in links:
            if link in history:
                continue

            try:
                r_item = requests.get(link, headers=HEADERS, timeout=20)
                s_item = BeautifulSoup(r_item.text, "html.parser")

                price_tag = s_item.find("span", itemprop="price")
                if not price_tag:
                    continue

                price = float(price_tag.text.replace(",", "."))
                if price > max_price:
                    continue

                title = s_item.find("h1")
                text = title.text.lower() if title else ""

                if not all(w in text for w in keyword.lower().split()):
                    continue

                print(f"   ✅ MATCH: {price}€ → {link}")
                history[link] = price

            except:
                continue

        page += 1
        time.sleep(2)

if __name__ == "__main__":
    history = {}
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE) as f:
            history = json.load(f)

    df = pd.read_csv(CSV_URL)

    for _, row in df.iterrows():
        keyword = str(row["Descrizione"]).strip()
        if not keyword or keyword.lower() == "nan":
            break

        max_price = float(row["Prezzo"])
        scan_global_search(keyword, max_price, history)

    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)
