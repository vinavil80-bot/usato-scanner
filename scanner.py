from playwright.sync_api import sync_playwright
from urllib.parse import urljoin
import time

# =======================
# CONFIGURAZIONE
# =======================

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
    "Gaggia factory",
    "san marco leva",
    "faema leva",
    "faemina leva",
    "faemina caffe",
    "faema caffe"
]

# =======================
# FUNZIONI
# =======================

def search_keyword(page, keyword):
    search_url = f"{BASE_URL}/search/prod/{keyword.replace(' ', '-')}"
    print(f"\n🔍 RICERCA: {keyword}")
    page.goto(search_url, timeout=60000)
    page.wait_for_timeout(3000)

    links = set()

    for a in page.locator("a[href]").all():
        href = a.get_attribute("href")
        if href and "/casa-e-cucina/" in href:
            full_url = urljoin(BASE_URL, href)
            links.add(full_url)

    print(f"   ➜ Inserzioni trovate: {len(links)}")
    return list(links)


def scan_product(page, url):
    page.goto(url, timeout=60000)
    page.wait_for_timeout(2000)

    try:
        title = page.locator("h1[itemprop='name']").inner_text().strip()
        price = page.locator("span[itemprop='price']").inner_text().strip()
        price = float(price)

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


# =======================
# MAIN
# =======================

def main():
    risultati = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for keyword in KEYWORDS:
            product_links = search_keyword(page, keyword)

            for link in product_links:
                data = scan_product(page, link)
                if not data:
                    continue

                if data["price"] <= MAX_PRICE:
                    risultati.append(data)
                    print(f"   ✅ {data['title']} - {data['price']}€")
                else:
                    print(f"   ❌ Scartato ({data['price']}€)")

                time.sleep(1)

        browser.close()

    print("\n=======================")
    print("🎯 RISULTATI FINALI")
    print("=======================")

    if not risultati:
        print("Nessuna inserzione trovata sotto il budget.")
    else:
        for r in risultati:
            print(f"\n🟢 {r['title']}")
            print(f"   💰 {r['price']}€")
            print(f"   🔗 {r['url']}")
            if r["description"]:
                print(f"   📝 {r['description']}")


if __name__ == "__main__":
    main()
