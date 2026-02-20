page.goto(url, timeout=60000)
page.wait_for_timeout(5000)

print("DEBUG URL:", page.url)
print("DEBUG TITLE:", page.title())

content = page.content()
print("DEBUG LENGTH HTML:", len(content))
