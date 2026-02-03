from playwright.sync_api import sync_playwright
from urllib.parse import urljoin
import time

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
    page.wait_for_selector("body", timeout=15000)

    # scroll per forzare caricamento JS
    page.mouse.wheel(0, 3000)
    page.wait_for_timeout(3000)

    links = set()

    for a in page.locator("a").all():
        href = a.get_attribute("href")
        if href and "/casa-e-cucina/" in href:
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

    except Exception:
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

            if not links:
                print("   ⚠️ Nessun risultato trovato")
                continue

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

if __name__ == "__main__":
    main()

