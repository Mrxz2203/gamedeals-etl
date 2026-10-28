import sqlite3  # Para crear bases de datos temporales en memoria RAM durante los tests

import pandas as pd  # Para estructurar DataFrames de prueba

# Importa las funciones y esquemas del script de carga que queremos poner a prueba
from src.load import SCHEMA, upsert_games, upsert_snapshots, upsert_stores


def _conn() -> sqlite3.Connection:
    """Función auxiliar que crea una base de datos SQLite en memoria volátil (:memory:) para las pruebas."""
    conn = sqlite3.connect(":memory:")  # Crea una BD rápida que no deja archivos físicos en disco
    conn.execute("PRAGMA foreign_keys = ON")  # Habilita las restricciones de llaves foráneas
    conn.executescript(SCHEMA)  # Inicializa las tablas ejecutando el esquema SQL
    return conn


def _stores() -> pd.DataFrame:
    """Función auxiliar que devuelve un DataFrame básico con datos de tiendas de prueba."""
    return pd.DataFrame({"store_id": [1], "name": ["Steam"], "is_active": [1]})


def _deals(price: float) -> pd.DataFrame:
    """Función auxiliar que genera un DataFrame de ofertas de prueba con un precio configurable."""
    return pd.DataFrame({
        "game_id": [10], "store_id": [1], "title": ["Hades"], "steam_app_id": [1145360],
        "metacritic_score": [93], "steam_rating_pct": [98], "release_date": ["2020-09-17"],
        "sale_price": [price], "normal_price": [24.99], "savings_pct": [50.0],
        "deal_rating": [9.5], "captured_date": ["2026-10-27"],
    })


def test_cargar_dos_veces_no_duplica_y_actualiza():
    """Valida que insertar múltiples veces el mismo registro en la misma fecha actualice el precio en lugar de duplicar filas."""
    conn = _conn()
    upsert_stores(conn, _stores())  # Inserta la tienda base requerida por la llave foránea
    
    # Simula dos cargas consecutivas para el mismo juego, tienda y fecha, pero con precios distintos (12.49 y luego 9.99)
    for price in (12.49, 9.99):  
        deals = _deals(price)
        upsert_games(conn, deals)
        upsert_snapshots(conn, deals)
        
    # Comprueba que el total de registros en la tabla de snapshots siga siendo exactamente 1 (gracias al UPSERT por clave primaria compuesta)
    assert conn.execute("SELECT COUNT(*) FROM price_snapshots").fetchone()[0] == 1
    # Comprueba que el precio de oferta se haya actualizado correctamente al último valor procesado (9.99)
    assert conn.execute("SELECT sale_price FROM price_snapshots").fetchone()[0] == 9.99


def test_nulos_quedan_como_null():
    """Valida que los valores nulos de Pandas (pd.NA) se traduzcan correctamente en NULL de SQL en la base de datos."""
    conn = _conn()
    deals = _deals(12.49)
    deals["metacritic_score"] = pd.array([pd.NA], dtype="Int64")  # Fuerza un valor nulo de tipo entero en la columna
    
    upsert_games(conn, deals)  # Ejecuta la inserción del juego con el puntaje nulo
    
    # Comprueba que el valor almacenado en SQLite sea efectivamente None (lo cual se traduce en NULL)
    assert conn.execute("SELECT metacritic_score FROM games").fetchone()[0] is None