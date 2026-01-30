from playwright.sync_api import sync_playwright
import pandas as pd
import json
import os
import time

CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTwRi3TJmwatu-_Q_phF8xM_CachbYcf2AuZsnWJnz9F4IMgYAiu64TuWKsAK-MNpVIPn5NslrJGYFX/pub?output=csv"
HISTORY_FILE = "price_history.json"
BASE_URL = "https://www.mercatinousato.com"

def scan_keyword(page, keyword, max_price, history):
    print(f"\n🔍 RICERCA: {keyword} (max {max_price}€)")

    search_url = f"{BASE_URL}/ricerca?q={keyword.replace(' ', '+')}"
    page.goto(search_url, timeout=60000)
    page.wait_for_timeout(3000)

    links = set(page.eval_on_selector_all(
        "a[href^='/annuncio/']",
        "els => els.map(e => e.href)"
    ))

    print(f"   annunci trovati: {len(links)}")

    for link in links:
        if link in history:
            continue

        try:
            page.goto(link, timeout=60000)
            page.wait_for_timeout(2000)

            price_el = page.query_selector("span[itemprop='price']")
            if not price_el:
                continue

            price = float(price_el.inner_text().replace(",", "."))
            if price > max_price:
                continue

            title = page.query_selector("h1")
            title_text = title.inner_text().lower() if title else ""

            if not all(w in title_text for w in keyword.lower().split()):
                continue

            print(f"   ✅ MATCH {price}€ → {link}")
            history[link] = price

        except:
            continue

        time.sleep(1)

if __name__ == "__main__":
    history = {}
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE) as f:
            history = json.load(f)

    df = pd.read_csv(CSV_URL)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for _, row in df.iterrows():
            keyword = str(row["Descrizione"]).strip()
            if not keyword or keyword.lower() == "nan":
                break

            max_price = float(row["Prezzo"])
            scan_keyword(page, keyword, max_price, history)

        browser.close()

    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)
