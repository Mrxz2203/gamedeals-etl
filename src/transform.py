import json  # Para cargar datos desde archivos JSON crudos
import logging  # Para registrar mensajes de información y eventos del proceso
from datetime import date  # Para obtener la fecha actual (captura del ETL)
from pathlib import Path  # Para manipular rutas de archivos de manera robusta

import pandas as pd  # Librería principal para manipulación y limpieza de datos en DataFrame

# Configuración de rutas raíz del proyecto y directorios de datos (raw y clean)
ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
CLEAN_DIR = ROOT / "data" / "clean"

# Configura el sistema de logs con formato de marca de tiempo, nivel y mensaje
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def _num(series: pd.Series) -> pd.Series:
    """Convierte a número; lo que no se pueda convertir queda como NaN."""
    return pd.to_numeric(series, errors="coerce")


def load_raw(name: str) -> pd.DataFrame:
    """Carga el JSON crudo más reciente de data/raw."""
    # Busca todos los archivos que coincidan con el patrón name_*.json y los ordena
    files = sorted(RAW_DIR.glob(f"{name}_*.json"))
    if not files:
        raise FileNotFoundError(f"No hay archivos {name}_*.json en {RAW_DIR}")
    log.info("Leyendo %s", files[-1].name)  # Muestra en consola el archivo más reciente que se va a leer
    # Lee el contenido del archivo JSON más reciente y lo convierte en un DataFrame de pandas
    return pd.DataFrame(json.loads(files[-1].read_text(encoding="utf-8")))


def clean_deals(df: pd.DataFrame, captured_date: str) -> pd.DataFrame:
    """Limpia, tipifica y transforma los datos crudos de las ofertas (deals)."""
    out = pd.DataFrame()  # Crea un nuevo DataFrame limpio para la salida
    out["game_id"] = _num(df["gameID"]).astype("Int64")  # Convierte gameID a numérico entero con soporte de nulos
    out["store_id"] = _num(df["storeID"]).astype("Int64")  # Convierte storeID a entero
    out["title"] = df["title"].str.strip()  # Limpia espacios en blanco alrededor del título del juego

    steam = _num(df["steamAppID"])  # Convierte steamAppID a número
    out["steam_app_id"] = steam.where(steam > 0).astype("Int64")  # Filtra valores inválidos (<= 0) dejándolos como nulos

    out["sale_price"] = _num(df["salePrice"])  # Convierte el precio de oferta a número decimal
    out["normal_price"] = _num(df["normalPrice"])  # Convierte el precio normal a número decimal
    out["savings_pct"] = _num(df["savings"]).round(2)  # Convierte el porcentaje de ahorro y lo redondea a 2 decimales

    # En la API, 0 significa "sin dato": lo convertimos a nulo
    meta = _num(df["metacriticScore"])
    out["metacritic_score"] = meta.where(meta > 0).astype("Int64")  # Asigna nulo si el puntaje Metacritic es 0 o menos
    steam_rating = _num(df["steamRatingPercent"])
    out["steam_rating_pct"] = steam_rating.where(steam_rating > 0).astype("Int64")  # Nulo si el rating de Steam es 0 o menos

    # Las fechas vienen como segundos Unix; 0 también es "sin dato"
    release = _num(df["releaseDate"])
    out["release_date"] = pd.to_datetime(release.where(release > 0), unit="s", errors="coerce")  # Convierte epoch a fecha legible

    out["deal_rating"] = _num(df["dealRating"])  # Convierte el puntaje de la oferta a número
    out["captured_date"] = captured_date  # Añade la fecha en la que se ejecutó la captura de datos

    # Un mismo juego en la misma tienda no debe repetirse (páginas solapadas)
    out = out.drop_duplicates(subset=["game_id", "store_id"]).reset_index(drop=True)
    return out


def clean_stores(df: pd.DataFrame) -> pd.DataFrame:
    """Limpia y transforma los datos crudos de las tiendas (stores)."""
    out = pd.DataFrame()  # Crea un nuevo DataFrame limpio
    out["store_id"] = _num(df["storeID"]).astype("Int64")  # Convierte el ID de la tienda a entero
    out["name"] = df["storeName"].str.strip()  # Limpia espacios del nombre de la tienda
    out["is_active"] = _num(df["isActive"]).astype("Int64")  # Convierte el indicador de tienda activa a entero
    return out


def run() -> None:
    """Orquesta el proceso completo de transformación y guardado en archivos CSV limpios."""
    # Procesa las ofertas usando la fecha actual del sistema en formato ISO
    deals = clean_deals(load_raw("deals"), date.today().isoformat())
    # Procesa el catálogo de tiendas
    stores = clean_stores(load_raw("stores"))
    
    # Crea la carpeta data/clean si no existe previamente
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    
    # Guarda los DataFrames limpios en formato CSV sin incluir el índice numérico
    deals.to_csv(CLEAN_DIR / "deals.csv", index=False)
    stores.to_csv(CLEAN_DIR / "stores.csv", index=False)
    
    # Registra en la consola el éxito de la operación y el conteo de registros limpios
    log.info("Limpios: %d ofertas, %d tiendas", len(deals), len(stores))


if __name__ == "__main__":
    run()  # Ejecuta la función principal si el archivo se llama directamente desde la terminal