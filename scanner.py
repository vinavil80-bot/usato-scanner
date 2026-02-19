from playwright.sync_api import sync_playwright
from urllib.parse import urljoin

MAX_PRICE = 400.0

KEYWORDS = [
    "la pavoni",
    "gaggia",
    "faema",
    "faemina",
    "caffe leva",
    "san marco caffe"
]

BASE_SEARCH = "https://www.mercatinousato.com/search/prod/"

def scan_keyword(page, keyword):
    url = BASE_SEARCH + keyword.replace(" ", "-")
    print(f"\n🔍 RICERCA: {keyword}")

    page.goto(url, timeout=60000)
    page.wait_for_selector(".list-product-minibox")

    results = []

    boxes = page.locator(".list-product-minibox")
    count = boxes.count()
    print(f"   ➜ Trovati {count} prodotti")

    for i in range(count):
        box = boxes.nth(i)

        try:
            title = box.locator(".list-product-title span").inner_text().lower()
            price = float(
                box.locator("meta[itemprop='price']")
                .get_attribute("content")
            )
            link = box.locator("a").get_attribute("href")

            if not any(k in title for k in KEYWORDS):
                continue

            if price <= MAX_PRICE:
                results.append({
                    "title": title,
                    "price": price,
                    "url": link
                })

                print(f"   ✅ {title} – {price}€")

        except Exception as e:
            print(f"   ⚠️ Errore parsing prodotto: {e}")

    return results


def main():
    found = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for kw in KEYWORDS:
            found.extend(scan_keyword(page, kw))

        browser.close()

    print("\n🎯 RISULTATI FINALI")
    for r in found:
        print(f"\n🟢 {r['title']}\n💰 {r['price']}€\n🔗 {r['url']}")

if __name__ == "__main__":
    main()
