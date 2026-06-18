import io
import time
import concurrent.futures

import pandas as pd
import pyarrow.parquet as pq
from azure.storage.blob import ContainerClient, StorageStreamDownloader
from azure.core.exceptions import ServiceRequestError

# --- CONFIG ---
sas_url = "URL_DEL_CONTENEDOR_CON_SAS_TOKEN"

# --- CLIENTE ---
container_client = ContainerClient.from_container_url(sas_url)

# --- FILTROS DE ARCHIVOS ---
filtros = [
    "IR_Session_2025-10", "IR_Session_2025-11", "IR_Session_2025-12",
    "IR_Session_2026-01", "IR_Session_2026-02", "IR_Session_2026-03",
    "IR_Session_2026-04", "IR_Session_2026-05"
]

archivos_filtrados = [
    blob.name for blob in container_client.list_blobs()
    if any(filtro in blob.name for filtro in filtros) and blob.name.endswith(".parquet")
]

# --- DESCARGA CON REINTENTOS ---
def descargar_blob_en_memoria(blob_client, max_retries=3):
    retries = 0
    while retries <= max_retries:
        try:
            downloader: StorageStreamDownloader = blob_client.download_blob(
                max_concurrency=4,
                read_timeout=600
            )
            stream = io.BytesIO()
            for chunk in downloader.chunks():
                stream.write(chunk)
            stream.seek(0)
            return stream
        except ServiceRequestError as e:
            print(f"Error de red: {e}. Reintentando {retries+1}/{max_retries}...")
            retries += 1
            time.sleep(2)
    raise Exception("Fallo al descargar el blob después de varios intentos.")

# --- LECTURA CON FILTRO POR PROGRAMA ---
def leer_parquet_en_partes(archivo):
    try:
        blob_client = container_client.get_blob_client(archivo)
        stream = descargar_blob_en_memoria(blob_client)

        parquet_file = pq.ParquetFile(stream)
        total_row_groups = parquet_file.num_row_groups
        dfs = []

        for rg in range(total_row_groups):
            table = parquet_file.read_row_groups([rg])
            df_chunk = table.to_pandas()
            df_chunk = df_chunk[df_chunk["Program Item Name"] == "TAREAS ADT"]
            if not df_chunk.empty:
                dfs.append(df_chunk)
            print(
                f"Archivo {archivo} - Row group {rg+1}/{total_row_groups} "
                f"-> {df_chunk.shape[0]} filas filtradas."
            )

        if dfs:
            return pd.concat(dfs, ignore_index=True)
        return pd.DataFrame()

    except Exception as e:
        print(f"Error leyendo {archivo}: {e}")
        return pd.DataFrame()

# --- PROCESAMIENTO EN PARALELO ---
def procesar_archivos_en_paralelo(archivos):
    dfs = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(leer_parquet_en_partes, archivos)
        for df in results:
            if not df.empty:
                dfs.append(df)
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame()

# --- EJECUCIÓN ---
df_session = procesar_archivos_en_paralelo(archivos_filtrados)

print("\n=== RESULTADO ===")
print("Registros 2025-2026 con TAREAS ADT:", df_session.shape)
print("SliceStartTime min:", df_session["SliceStartTime"].min())
print("SliceStartTime max:", df_session["SliceStartTime"].max())
