
import requests
url = "https://books.toscrape.com/"
headers = {"User-Agent": "Mozilla/5.0"}
r = requests.get(url, headers=headers, timeout=10)
print(r.status_code) # 200 -> todo bien
print(len(r.text), "caracteres de HTML")
