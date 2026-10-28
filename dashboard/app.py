import sqlite3  # Para conectar y consultar la base de datos SQLite
from contextlib import closing  # Para asegurar el cierre automático de la conexión a la BD
from pathlib import Path  # Para gestionar las rutas de archivos de manera robusta

import pandas as pd  # Para manipular los resultados de SQL en formato DataFrame
import plotly.express as px  # Para generar gráficos interactivos de forma sencilla
import streamlit as st  # Librería principal para construir la interfaz web del dashboard

# Configuración de las rutas raíz del proyecto, archivo SQLite y archivo de consultas SQL
ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "gamedeals.db"
QUERIES_PATH = ROOT / "src" / "queries.sql"

# Configura la página web de Streamlit: título en pestaña, icono y diseño expandido (wide)
st.set_page_config(page_title="GameDeals", page_icon="🎮", layout="wide")


@st.cache_data
def load_queries() -> dict[str, str]:
    """Lee el archivo queries.sql y separa cada consulta mediante su etiqueta '-- name:'."""
    queries: dict[str, str] = {}
    name, buffer = None, []
    # Lee línea por línea el archivo de consultas SQL codificado en UTF-8
    for line in QUERIES_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("-- name:"):
            if name:
                queries[name] = "\n".join(buffer).strip()  # Guarda la consulta acumulada anterior
            name, buffer = line.split(":", 1)[1].strip(), []  # Extrae el nuevo nombre de la consulta
        else:
            buffer.append(line)  # Acumula las líneas de código SQL
    if name:
        queries[name] = "\n".join(buffer).strip()  # Guarda la última consulta del archivo
    return queries


def run_query(name: str, params: dict | None = None) -> pd.DataFrame:
    """Ejecuta una consulta SQL específica buscando por su nombre y retorna un DataFrame de Pandas."""
    with closing(sqlite3.connect(DB_PATH)) as conn:  # Conecta y asegura el cierre de la BD al terminar
        return pd.read_sql_query(load_queries()[name], conn, params=params)


# Validación previa: si el archivo de base de datos no existe, muestra un error y detiene la ejecución
if not DB_PATH.exists():
    st.error("No existe la base de datos. Ejecuta primero: python run_pipeline.py")
    st.stop()

# Título principal de la aplicación web
st.title("🎮 GameDeals")

# Obtiene los metadatos generales (última fecha, días acumulados, total de juegos) para las tarjetas métricas
info = run_query("snapshot_info").iloc[0]
c1, c2, c3 = st.columns(3)  # Divide la interfaz en 3 columnas métricas
c1.metric("Última captura", str(info["last_date"]))
c2.metric("Días acumulados", int(info["days"]))
c3.metric("Juegos en la base", int(info["games"]))

# Crea las pestañas de navegación (tabs) para organizar las secciones visuales del dashboard
tab1, tab2, tab3, tab4 = st.tabs(
    ["Mayores descuentos", "Mejor relación puntaje/precio", "Tiendas", "Evolución de precio"]
)

# Pestaña 1: Gráfico de barras horizontales y tabla con los mayores descuentos actuales
with tab1:
    df = run_query("top_discounts")
    fig = px.bar(df, x="savings_pct", y="title", color="store", orientation="h",
                 labels={"savings_pct": "Descuento (%)", "title": "", "store": "Tienda"})
    fig.update_layout(yaxis={"categoryorder": "total ascending"})  # Ordena las barras de mayor a menor
    st.plotly_chart(fig, use_container_width=True)  # Muestra el gráfico interactivo de Plotly
    st.dataframe(df, use_container_width=True)  # Muestra la tabla completa de datos

# Pestaña 2: Análisis de calidad-precio (Puntos de Metacritic por cada dólar invertido)
with tab2:
    df = run_query("best_value")
    fig = px.bar(df, x="points_per_dollar", y="title", orientation="h",
                 labels={"points_per_dollar": "Puntos Metacritic por dólar", "title": ""})
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df, use_container_width=True)

# Pestaña 3: Resumen por tiendas y su respectivo Top 3 de ofertas
with tab3:
    df = run_query("deals_by_store")
    fig = px.bar(df, x="store", y="deals", hover_data=["avg_discount"],
                 labels={"store": "Tienda", "deals": "Ofertas"})
    st.plotly_chart(fig, use_container_width=True)
    st.subheader("Top 3 descuentos por tienda")
    st.dataframe(run_query("top_per_store"), use_container_width=True)

# Pestaña 4: Gráfico de líneas interactivo con el histórico de precios de un juego seleccionado
with tab4:
    games = run_query("games_list")  # Obtiene la lista alfabética de juegos
    opciones = dict(zip(games["game_id"], games["title"]))  # Crea un diccionario ID -> Título
    
    # Selector desplegable para buscar y elegir un juego
    game_id = st.selectbox("Juego", list(opciones.keys()), format_func=lambda i: opciones[i])
    
    # Consulta el histórico de precios aplicando el game_id seleccionado
    hist = run_query("price_history", {"game_id": int(game_id)})
    
    # Alerta informativa si el juego cuenta con una sola captura histórica
    if hist["captured_date"].nunique() < 2:
        st.info("Solo hay una captura de este juego. Corre el pipeline en otros días para ver la evolución.")
        
    # Genera el gráfico de líneas por tienda a lo largo del tiempo
    fig = px.line(hist, x="captured_date", y="sale_price", color="store", markers=True,
                  labels={"captured_date": "Fecha", "sale_price": "Precio (USD)", "store": "Tienda"})
    st.plotly_chart(fig, use_container_width=True)