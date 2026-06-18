import csv
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://books.toscrape.com/"
CATALOGUE_URL = "https://books.toscrape.com/catalogue/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
MAX_WORKERS = 8


def crear_session():
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def fetch(url, session, intentos=3):
    for i in range(intentos):
        try:
            resp = session.get(url, timeout=15)
            if resp.status_code == 200:
                return resp
        except requests.RequestException:
            if i < intentos - 1:
                time.sleep(1)
    return None


def extraer_libros_de_pagina(html):
    soup = BeautifulSoup(html, "html.parser")
    resultados = []
    for libro in soup.find_all("article", class_="product_pod"):
        nombre = libro.h3.a["title"]
        precio = float(re.sub(r"[^\d.]", "", libro.find("p", class_="price_color").text))
        stock = libro.find("p", class_="instock availability").text.strip()
        rating = libro.find("p", class_="star-rating")["class"][1]
        img_src = libro.find("img")["src"]
        img_url = BASE_URL + img_src[3:] if img_src.startswith("../") else BASE_URL + img_src
        link = libro.h3.a["href"]
        detalle_url = CATALOGUE_URL + link.replace("../", "") if link.startswith("../") else CATALOGUE_URL + link
        resultados.append({
            "nombre": nombre, "precio": precio, "stock": stock,
            "rating": rating, "img_url": img_url, "detalle_url": detalle_url,
        })
    return resultados


def extraer_detalle_libro(html):
    soup = BeautifulSoup(html, "html.parser")
    datos = {}
    table = soup.find("table", class_="table table-striped")
    if table:
        for fila in table.find_all("tr"):
            th, td = fila.find("th"), fila.find("td")
            if th and td:
                datos[th.text.strip()] = td.text.strip()
    desc_div = soup.find("div", id="product_description")
    if desc_div:
        p = desc_div.find_next_sibling("p")
        if p:
            datos["Description"] = p.text.strip()
    return datos


def fetch_page(num, session):
    url = BASE_URL if num == 1 else f"{CATALOGUE_URL}page-{num}.html"
    resp = fetch(url, session)
    if resp is None:
        return num, None
    return num, extraer_libros_de_pagina(resp.text)


def fetch_detail(libro, session):
    resp = fetch(libro["detalle_url"], session)
    if resp is None:
        return libro
    detalle = extraer_detalle_libro(resp.text)
    libro["upc"] = detalle.get("UPC", "")
    libro["tipo_producto"] = detalle.get("Product Type", "")
    libro["precio_sin_impuesto"] = detalle.get("Price (excl. tax)", "")
    libro["precio_con_impuesto"] = detalle.get("Price (incl. tax)", "")
    libro["impuesto"] = detalle.get("Tax", "")
    libro["disponibilidad"] = detalle.get("Availability", "")
    libro["num_resenas"] = detalle.get("Number of reviews", "")
    libro["descripcion"] = detalle.get("Description", "")
    return libro


# ---- 1. DESCUBRIR CUANTAS PAGINAS HAY ----
print("Descubriendo paginas...")
with crear_session() as s:
    resp = fetch(BASE_URL, s)
    if resp is None:
        exit("Error al conectar")
    soup = BeautifulSoup(resp.text, "html.parser")
    current = soup.find("li", class_="current")
    total_paginas = int(current.text.strip().split()[-1]) if current else 1
print(f"Total de paginas: {total_paginas}")

# ---- 2. EXTRAER LISTADO DE TODAS LAS PAGINAS EN PARALELO ----
print("Extrayendo listado de libros...")
todos_los_libros = []
with crear_session() as s:
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futuros = {pool.submit(fetch_page, p, s): p for p in range(1, total_paginas + 1)}
        for futuro in as_completed(futuros):
            num, libros = futuro.result()
            if libros:
                todos_los_libros.extend(libros)
                print(f"  Pagina {num}: {len(libros)} libros")

todos_los_libros.sort(key=lambda x: x["detalle_url"])
print(f"Total: {len(todos_los_libros)} libros\n")

# ---- 3. EXTRAER DETALLE DE CADA LIBRO EN PARALELO ----
print("Extrayendo detalle de cada libro...")
with crear_session() as s:
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futuros = {pool.submit(fetch_detail, libro, s): i for i, libro in enumerate(todos_los_libros)}
        for futuro in as_completed(futuros):
            idx = futuros[futuro]
            libro = futuro.result()
            todos_los_libros[idx] = libro
            print(f"  [{idx+1}/{len(todos_los_libros)}] {libro['nombre'][:50]}")

# ---- 4. GUARDAR CSV ----
print("\nGuardando a libros_completo.csv...")
with open("libros_completo.csv", "w", newline="", encoding="utf-8") as f:
    campos = [
        "nombre", "precio", "stock", "rating", "upc",
        "tipo_producto", "precio_sin_impuesto", "precio_con_impuesto",
        "impuesto", "disponibilidad", "num_resenas",
        "descripcion", "img_url", "detalle_url"
    ]
    writer = csv.DictWriter(f, fieldnames=campos)
    writer.writeheader()
    writer.writerows(todos_los_libros)

print(f"Completado. {len(todos_los_libros)} libros en libros_completo.csv")
