import csv
import json
import time
import requests

OVERPASS_URL = "http://overpass-api.de/api/interpreter"
HEADERS = {"User-Agent": "curl/8.5.0", "Accept-Encoding": ""}

def overpass_query(query, max_retry=5):
    for intento in range(max_retry):
        resp = requests.post(OVERPASS_URL, data={"data": query}, headers=HEADERS, timeout=900)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 429:
            espera = 15 * (intento + 1)
            print(f"  Rate limit, esperando {espera}s...")
            time.sleep(espera)
            continue
        print(f"  Error {resp.status_code}, reintentando...")
        time.sleep(5)
    raise Exception("Max retries alcanzado")

# Ecuador dividido en grids (lat_min, lon_min, lat_max, lon_max)
GRID = [
    # Costa norte
    (0.0, -81.0, 1.5, -78.0),
    # Costa sur
    (-3.0, -81.0, 0.0, -78.0),
    # Sierra norte
    (0.0, -78.0, 1.5, -77.0),
    # Sierra centro
    (-2.0, -78.0, 0.0, -77.0),
    # Amazonia norte
    (0.0, -77.0, 1.5, -75.0),
    # Amazonia sur
    (-2.0, -77.0, 0.0, -75.0),
    # Sur (Cuenca, Loja)
    (-5.0, -80.0, -2.0, -75.0),
    # Galapagos
    (-1.5, -92.0, 1.5, -89.0),
]

todos = []
for i, (lat_max, lat_min, lon_max, lon_min) in enumerate(GRID, 1):
    print(f"\nGrid {i}/{len(GRID)}: ({lat_min},{lon_min}) a ({lat_max},{lon_max})")
    query = f"""
    [out:json][timeout:300];
    (
      node["amenity"="restaurant"]({lat_min},{lon_min},{lat_max},{lon_max});
      way["amenity"="restaurant"]({lat_min},{lon_min},{lat_max},{lon_max});
      relation["amenity"="restaurant"]({lat_min},{lon_min},{lat_max},{lon_max});
    );
    out center meta;
    """
    try:
        data = overpass_query(query)
        elems = data.get("elements", [])
        print(f"  -> {len(elems)} restaurantes")
        for elem in elems:
            tags = elem.get("tags", {})
            lat = elem.get("lat") or elem.get("center", {}).get("lat")
            lon = elem.get("lon") or elem.get("center", {}).get("lon")
            todos.append({
                "id": elem["id"],
                "tipo": elem["type"],
                "nombre": tags.get("name", ""),
                "latitud": lat,
                "longitud": lon,
                "direccion": tags.get("addr:full", "") or tags.get("address", ""),
                "ciudad": tags.get("addr:city", ""),
                "calle": tags.get("addr:street", ""),
                "codigo_postal": tags.get("addr:postcode", ""),
                "telefono": tags.get("phone", ""),
                "cuisine": tags.get("cuisine", ""),
                "website": tags.get("website", ""),
                "horario": tags.get("opening_hours", ""),
                "nivel_precio": tags.get("level", ""),
                "descripcion": tags.get("description", ""),
            })
        time.sleep(2)  # pausa entre grids
    except Exception as e:
        print(f"  Error: {e}")

csv_file = "restaurantes_ecuador.csv"
with open(csv_file, "w", newline="", encoding="utf-8") as f:
    campos = ["id", "tipo", "nombre", "latitud", "longitud", "direccion",
              "ciudad", "calle", "codigo_postal", "telefono", "cuisine",
              "website", "horario", "nivel_precio", "descripcion"]
    writer = csv.DictWriter(f, fieldnames=campos)
    writer.writeheader()
    writer.writerows(todos)

print(f"\nCompletado: {len(todos)} restaurantes en total → {csv_file}")
