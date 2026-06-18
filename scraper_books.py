import csv
import re
import requests
from bs4 import BeautifulSoup

url = "https://books.toscrape.com/"
response = requests.get(url)

if response.status_code != 200:
    print(f"Error al descargar la pagina: {response.status_code}")
    exit()

soup = BeautifulSoup(response.text, "html.parser")
libros = soup.find_all("article", class_="product_pod")

datos = []
for libro in libros:
    nombre = libro.h3.a["title"]
    precio_texto = libro.find("p", class_="price_color").text
    precio = float(re.sub(r"[^\d.]", "", precio_texto))
    stock = libro.find("p", class_="instock availability").text.strip()
    datos.append([nombre, precio, stock])

with open("libros.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Nombre", "Precio", "Stock"])
    writer.writerows(datos)

print(f"Guardados {len(datos)} libros en libros.csv")
