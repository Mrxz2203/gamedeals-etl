import logging  # Para registrar mensajes de información y estado en la consola
import sqlite3  # Librería nativa para interactuar con bases de datos SQLite
from pathlib import Path  # Para el manejo robusto de rutas de archivos

import pandas as pd  # Para leer los archivos CSV limpios

# Definición de rutas raíz, directorio de datos limpios y ubicación del archivo SQLite
ROOT = Path(__file__).resolve().parent.parent
CLEAN_DIR = ROOT / "data" / "clean"
DB_PATH = ROOT / "data" / "gamedeals.db"

# Configuración básica del sistema de logs con formato de tiempo, nivel y mensaje
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# Definición del esquema de la base de datos relacional en SQL
SCHEMA = """
CREATE TABLE IF NOT EXISTS stores (
    store_id    INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    is_active   INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS games (
    game_id            INTEGER PRIMARY KEY,
    title              TEXT NOT NULL,
    steam_app_id       INTEGER,
    metacritic_score   INTEGER,
    steam_rating_pct   INTEGER,
    release_date       TEXT
);

CREATE TABLE IF NOT EXISTS price_snapshots (
    game_id         INTEGER NOT NULL REFERENCES games(game_id),
    store_id        INTEGER NOT NULL REFERENCES stores(store_id),
    captured_date   TEXT    NOT NULL,
    sale_price      REAL    NOT NULL,
    normal_price    REAL    NOT NULL,
    savings_pct     REAL,
    deal_rating     REAL,
    PRIMARY KEY (game_id, store_id, captured_date)
);
"""

# Sentencia SQL UPSERT para la tabla stores: inserta o actualiza si la tienda ya existe
UPSERT_STORES = """
INSERT INTO stores (store_id, name, is_active) VALUES (?, ?, ?)
ON CONFLICT(store_id) DO UPDATE SET
    name = excluded.name,
    is_active = excluded.is_active
"""

# COALESCE: si hoy un dato viene vacío, no borramos el que ya teníamos guardado previamente
UPSERT_GAMES = """
INSERT INTO games (game_id, title, steam_app_id, metacritic_score, steam_rating_pct, release_date)
VALUES (?, ?, ?, ?, ?, ?)
ON CONFLICT(game_id) DO UPDATE SET
    title = excluded.title,
    steam_app_id = COALESCE(excluded.steam_app_id, games.steam_app_id),
    metacritic_score = COALESCE(excluded.metacritic_score, games.metacritic_score),
    steam_rating_pct = COALESCE(excluded.steam_rating_pct, games.steam_rating_pct),
    release_date = COALESCE(excluded.release_date, games.release_date)
"""

# Sentencia UPSERT para guardar los snapshots de precios diarios sin duplicar claves primarias
UPSERT_SNAPSHOTS = """
INSERT INTO price_snapshots
    (game_id, store_id, captured_date, sale_price, normal_price, savings_pct, deal_rating)
VALUES (?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(game_id, store_id, captured_date) DO UPDATE SET
    sale_price = excluded.sale_price,
    normal_price = excluded.normal_price,
    savings_pct = excluded.savings_pct,
    deal_rating = excluded.deal_rating
"""


def _rows(df: pd.DataFrame, cols: list[str]) -> list[tuple]:
    """DataFrame -> lista de tuplas, con los nulos de pandas convertidos a None (NULL en SQL)."""
    sub = df[cols].astype(object)
    sub = sub.where(df[cols].notna(), None)
    return list(sub.itertuples(index=False, name=None))


def upsert_stores(conn: sqlite3.Connection, stores: pd.DataFrame) -> int:
    """Inserta o actualiza las tiendas en la base de datos y retorna el total procesado."""
    rows = _rows(stores, ["store_id", "name", "is_active"])
    conn.executemany(UPSERT_STORES, rows)
    return len(rows)


def upsert_games(conn: sqlite3.Connection, deals: pd.DataFrame) -> int:
    """Extrae los juegos únicos de las ofertas, los inserta o actualiza, y retorna el total."""
    games = deals.drop_duplicates(subset=["game_id"])
    rows = _rows(
        games,
        ["game_id", "title", "steam_app_id", "metacritic_score", "steam_rating_pct", "release_date"],
    )
    conn.executemany(UPSERT_GAMES, rows)
    return len(rows)


def upsert_snapshots(conn: sqlite3.Connection, deals: pd.DataFrame) -> int:
    """Inserta o actualiza los registros históricos de precios y ofertas, y retorna el total."""
    rows = _rows(
        deals,
        ["game_id", "store_id", "captured_date", "sale_price", "normal_price", "savings_pct", "deal_rating"],
    )
    conn.executemany(UPSERT_SNAPSHOTS, rows)
    return len(rows)


def run() -> None:
    """Orquesta la lectura de los CSV limpios y su carga transaccional en SQLite."""
    # Lee los datos limpios desde los archivos CSV generados en la fase anterior
    deals = pd.read_csv(CLEAN_DIR / "deals.csv")
    stores = pd.read_csv(CLEAN_DIR / "stores.csv")
    
    # read_csv deja como float las columnas enteras con nulos; las devolvemos a entero de Pandas ("Int64")
    for col in ["game_id", "store_id", "steam_app_id", "metacritic_score", "steam_rating_pct"]:
        deals[col] = deals[col].astype("Int64")

    # Asegura que la carpeta data/ exista antes de conectar con SQLite
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        # Habilita las restricciones de llaves foráneas (foreign keys) en SQLite
        conn.execute("PRAGMA foreign_keys = ON")
        # Crea las tablas si no existen utilizando el esquema definido
        conn.executescript(SCHEMA)
        
        # Bloque transaccional: asegura que o se guarda todo correctamente o no se aplica ningún cambio
        with conn:  
            n_stores = upsert_stores(conn, stores)
            n_games = upsert_games(conn, deals)
            n_snaps = upsert_snapshots(conn, deals)
    finally:
        # Cierra la conexión a la base de datos de manera segura al terminar
        conn.close()
        
    # Registra un mensaje de éxito con el conteo de registros insertados/actualizados
    log.info("Cargado: %d tiendas, %d juegos, %d precios", n_stores, n_games, n_snaps)


if __name__ == "__main__":
    run()  # Ejecuta el script de carga si se llama directamente desde la terminal