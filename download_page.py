import requests

url = "https://books.toscrape.com/"
response = requests.get(url)

if response.status_code == 200:
    with open("books_toscrape.html", "w", encoding="utf-8") as f:
        f.write(response.text)
    print(f"Pagina descargada exitosamente ({len(response.text)} caracteres)")
else:
    print(f"Error: {response.status_code}")
