import pandas as pd  # Importa pandas para crear DataFrames simulados en las pruebas

from src.transform import clean_deals  # Importa la función de limpieza que vamos a someter a pruebas


def _sample() -> pd.DataFrame:
    """Función auxiliar para generar un DataFrame de prueba con casos típicos y extremos."""
    base = {
        "gameID": "1", "storeID": "1", "title": "  Hades ", "steamAppID": "1145360",
        "salePrice": "12.49", "normalPrice": "24.99", "savings": "50.020008",
        "metacriticScore": "93", "steamRatingPercent": "98",
        "releaseDate": 1600000000, "dealRating": "9.5",
    }
    # Crea un caso alternativo donde los valores "0" simulan la ausencia de datos en la API
    sin_datos = {
        **base, "gameID": "2", "storeID": "2", "title": "Juego X", "steamAppID": "0",
        "metacriticScore": "0", "steamRatingPercent": "0", "releaseDate": 0,
    }
    # Retorna un DataFrame con 3 filas: la primera repetida a propósito (duplicado) y una con ceros
    return pd.DataFrame([base, base, sin_datos])  


def test_elimina_duplicados():
    """Valida que la función elimine correctamente los registros duplicados (mismo juego y tienda)."""
    # Como pasamos 3 filas pero dos son idénticas, el resultado limpio debe tener exactamente 2 registros
    assert len(clean_deals(_sample(), "2026-10-27")) == 2


def test_precios_son_numericos_y_titulo_sin_espacios():
    """Valida que las conversiones de tipo a flotante y el recorte de espacios en títulos funcionen."""
    out = clean_deals(_sample(), "2026-10-27")
    # Comprueba que la columna de precio de oferta se haya convertido a float64
    assert out["sale_price"].dtype == "float64"
    # Comprueba que el strip() haya eliminado los espacios en blanco del título ("  Hades " -> "Hades")
    assert out.loc[0, "title"] == "Hades"


def test_ceros_se_vuelven_nulos():
    """Valida que los valores '0' provenientes de la API se transformen correctamente en nulos (NaN)."""
    out = clean_deals(_sample(), "2026-10-27")
    # Filtra la fila correspondiente al juego con ID 2 (el caso sin_datos)
    fila = out[out["game_id"] == 2].iloc[0]
    # Comprueba que los campos metacritic_score, steam_app_id y release_date sean nulos (NaN)
    assert pd.isna(fila["metacritic_score"])
    assert pd.isna(fila["steam_app_id"])
    assert pd.isna(fila["release_date"])