# 🎮 GameDeals ETL

Pipeline ETL en Python que descarga ofertas de videojuegos desde la API pública de
[CheapShark](https://apidocs.cheapshark.com/), las limpia con pandas, las guarda en SQLite
con carga incremental y las muestra en un dashboard interactivo de Streamlit.
Cada corrida agrega una "foto" de precios, así que el proyecto va construyendo un historial.

![Dashboard](docs/dashboard.png)

## Qué hace

1. **Extract:** descarga ofertas y tiendas desde la API y guarda las respuestas crudas en `data/raw`.
2. **Transform:** limpia y normaliza los datos con pandas.
3. **Load:** carga los datos en SQLite con upsert, sin duplicar registros.
4. **Consultas y dashboard:** consultas SQL (JOIN, GROUP BY, funciones de ventana) visualizadas con Streamlit y Plotly.
5. **Automatización:** ejecución diaria con el Programador de tareas de Windows.

## Arquitectura

```
CheapShark API
     │  extract.py        (requests)
     ▼
data/raw/*.json           datos crudos, un archivo por corrida
     │  transform.py      (pandas)
     ▼
data/clean/*.csv          datos limpios
     │  load.py           (sqlite3, upsert)
     ▼
SQLite: data/gamedeals.db
     │  queries.sql
     ▼
dashboard/app.py          (Streamlit + Plotly)

run_pipeline.py orquesta extract → transform → load
```

## Modelo de datos

| Tabla | Descripción | Clave |
|---|---|---|
| `stores` | Tiendas (Steam, GOG, Epic...) | `store_id` |
| `games` | Datos del juego: título, puntaje Metacritic, rating de Steam, fecha de lanzamiento | `game_id` |
| `price_snapshots` | Precio y descuento de un juego en una tienda en una fecha | `(game_id, store_id, captured_date)` |

## Decisiones de diseño

- **Carga idempotente:** la clave primaria de `price_snapshots` incluye la fecha y se usa
  `INSERT ... ON CONFLICT DO UPDATE`, así que correr el pipeline varias veces el mismo día
  no duplica datos.
- **Historial de precios:** cada día suma una captura nueva, lo que permite ver la evolución del precio.
- **Limpieza de datos:** precios de texto a número, ceros que significan "sin dato" convertidos a nulos,
  fechas Unix convertidas a fecha, y duplicados entre páginas eliminados.
- **Carga atómica:** todo se guarda en una sola transacción; si algo falla, no queda nada a medias.
- **Pruebas automatizadas:** pytest sobre la transformación y la carga (incluye una prueba de idempotencia).

## Preguntas que responde el dashboard

1. ¿Cuáles son los mayores descuentos de hoy?
2. ¿Qué juegos tienen mejor relación puntaje/precio?
3. ¿Qué tiendas tienen más ofertas y cuál es su descuento promedio?
4. ¿Cómo evolucionó el precio de un juego en el tiempo?

## Cómo correrlo

Requisitos: Python 3.10 o superior.

```powershell
# 1. Clonar y entrar al proyecto
git clone https://github.com/Mrxz2203/gamedeals-etl.git
cd gamedeals-etl

# 2. Entorno virtual e instalación
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 3. Ejecutar el pipeline completo
python run_pipeline.py

# 4. Abrir el dashboard
streamlit run dashboard/app.py
```

También puedes correr cada etapa por separado:

```powershell
python -m src.extract
python -m src.transform
python -m src.load
```

## Pruebas

```powershell
python -m pytest -v
```

## Ejecución diaria automática (Windows)

El archivo `run_daily.bat` ejecuta el pipeline y guarda los logs en `data/pipeline.log`.
Para programarlo todos los días a las 12:00:

```powershell
schtasks /Create /SC DAILY /ST 12:00 /TN "GameDeals ETL" /TR '"RUTA\COMPLETA\AL\PROYECTO\run_daily.bat"'
```

## Estructura del proyecto

```
gamedeals-etl/
├── dashboard/
│   └── app.py
├── data/                  (ignorado por git)
│   ├── raw/
│   ├── clean/
│   └── gamedeals.db
├── docs/
│   └── dashboard.png
├── src/
│   ├── extract.py
│   ├── transform.py
│   ├── load.py
│   └── queries.sql
├── tests/
│   ├── test_transform.py
│   └── test_load.py
├── run_pipeline.py
├── run_daily.bat
├── requirements.txt
└── README.md
```

## Stack

Python · pandas · SQLite · Streamlit · Plotly · pytest · requests

## Próximos pasos

- Ejecutar las pruebas en cada push con GitHub Actions.
- Migrar la base de datos de SQLite a PostgreSQL.
- Alertas cuando un juego baje de un precio objetivo.

## Créditos

Datos proporcionados por la API pública de [CheapShark](https://apidocs.cheapshark.com/).

## Autor

Gabriel García · [GitHub](https://github.com/Mrxz2203)