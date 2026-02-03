from playwright.sync_api import sync_playwright
from urllib.parse import urljoin
import time
import re

BASE_URL = "https://www.mercatinousato.com"
MAX_PRICE = 400.0

KEYWORDS = [
    "la pavoni caffe",
    "pavoni caffe",
    "pavoni leva",
    "macchina caffe leva",
    "caffe leva",
    "gaggia leva",
    "gaggia caffe leva",
    "gaggia factory",
    "san marco leva",
    "faema leva",
    "faemina leva",
    "faemina caffe",
    "faema caffe"
]

# =========================
# SEARCH
# =========================
def search_keyword(page, keyword):
    search_url = f"{BASE_URL}/search/prod/{keyword.replace(' ', '-')}"
    print(f"\n🔍 RICERCA: {keyword}")

    page.goto(search_url, timeout=60000)
    page.wait_for_selector("a[href*='/casa-e-cucina/']", timeout=15000)

    links = set()

    for a in page.locator("a[href*='/casa-e-cucina/']").all():
        href = a.get_attribute("href")
        if href:
            links.add(urljoin(BASE_URL, href.split("?")[0]))

    print(f"   ➜ Inserzioni trovate: {len(links)}")
    return list(links)

# =========================
# PRODUCT SCAN
# =========================
def scan_product(page, url):
    page.goto(url, timeout=60000)

    try:
        page.wait_for_selector("h1[itemprop='name']", timeout=10000)

        title = page.locator("h1[itemprop='name']").inner_text().strip()

        # PREZZO HIDDEN → get_attribute
        price_raw = page.locator("span[itemprop='price']").get_attribute("textContent")
        if not price_raw:
            return None

        price = float(price_raw.replace(",", ".").strip())

        description = ""
        if page.locator("p[itemprop='description']").count() > 0:
            description = page.locator("p[itemprop='description']").inner_text().strip()

        return {
            "title": title,
            "price": price,
            "url": url,
            "description": description
        }

    except Exception as e:
        print(f"   ⚠️ Errore parsing {url}")
        return None

# =========================
# MAIN
# =========================
def main():
    risultati = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for keyword in KEYWORDS:
            links = search_keyword(page, keyword)

            for link in links:
                data = scan_product(page, link)
                if not data:
                    continue

                if data["price"] <= MAX_PRICE:
                    risultati.append(data)
                    print(f"   ✅ {data['title']} – {data['price']}€")
                else:
                    print(f"   ❌ Scartato ({data['price']}€)")

                time.sleep(1)

        browser.close()

    print("\n=======================")
    print("🎯 RISULTATI FINALI")
    print("=======================")

    if not risultati:
        print("Nessuna inserzione sotto budget.")
    else:
        for r in risultati:
            print(f"\n🟢 {r['title']}")
            print(f"   💰 {r['price']}€")
            print(f"   🔗 {r['url']}")
            if r["description"]:
                print(f"   📝 {r['description']}")

if __name__ == "__main__":
    main()
