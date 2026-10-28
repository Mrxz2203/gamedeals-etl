import json  # Para convertir estructuras de Python a formato JSON
import logging  # Para registrar mensajes de información y errores en la consola
from datetime import datetime  # Para generar marcas de tiempo en los nombres de archivos
from pathlib import Path  # Para manejar rutas de archivos de forma independiente del SO

import requests  # Para realizar peticiones HTTP a la API pública

# URL base de la API de CheapShark
BASE_URL = "https://www.cheapshark.com/api/1.0"
# Ruta dinámica donde se guardarán los archivos JSON en data/raw
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

# Configuración básica del log con formato de fecha, nivel y mensaje
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


HEADERS = {"User-Agent": "gamedeals-etl/1.0 (proyecto personal de practica)"}


def fetch(endpoint: str, params: dict | None = None) -> list[dict]:
    response = requests.get(
        f"{BASE_URL}/{endpoint}", params=params, headers=HEADERS, timeout=30
    )
    if not response.ok:
        log.error("HTTP %s en %s -> %s", response.status_code, response.url, response.text[:300])
    response.raise_for_status()
    return response.json()


def save_raw(data: list[dict], name: str) -> Path:
    """Guarda una lista de diccionarios en un archivo JSON con marca de tiempo."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)  # Crea la carpeta data/raw si aún no existe
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")  # Genera un string de fecha/hora único
    path = RAW_DIR / f"{name}_{stamp}.json"  # Construye la ruta final del archivo JSON
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")  # Escribe los datos en el JSON
    log.info("Guardado %s (%d registros)", path.name, len(data))  # Muestra en consola el resultado de la operación
    return path


def run(pages: int = 3, page_size: int = 60) -> None:
    """Orquesta la extracción de ofertas y tiendas desde la API."""
    deals: list[dict] = []  # Lista vacía para acumular las ofertas
    for page in range(pages):  # Itera por el número de páginas configurado
        deals += fetch("deals", {"pageNumber": page, "pageSize": page_size})  # Descarga y acumula ofertas
    save_raw(deals, "deals")  # Guarda la lista consolidada de ofertas en un JSON
    save_raw(fetch("stores"), "stores")  # Descarga y guarda la lista de tiendas en un JSON


if __name__ == "__main__":
    run()  # Ejecuta la función principal si el archivo se llama directamente