def scan_keyword(page, keyword):
    url = BASE_SEARCH + keyword.replace(" ", "-")
    print(f"\n🔍 RICERCA: {keyword}")

    page.goto(url, timeout=60000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)

    boxes = page.locator(".list-product-minibox")
    count = boxes.count()

    print(f"   ➜ Trovati {count} prodotti")

    results = []

    if count == 0:
        print("   ⚠️ Nessun prodotto trovato - possibile blocco headless")
        return results

    for i in range(count):
        box = boxes.nth(i)

        try:
            title = box.locator(".list-product-title span").inner_text().lower()
            price_raw = box.locator("meta[itemprop='price']").get_attribute("content")

            if not price_raw:
                continue

            price = float(price_raw)
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
