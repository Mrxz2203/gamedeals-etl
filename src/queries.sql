-- name: snapshot_info
-- Consulta general del estado actual de la base de datos y los snapshots
SELECT MAX(captured_date) AS last_date,       -- Obtiene la fecha de captura más reciente registrada
       COUNT(DISTINCT captured_date) AS days, -- Cuenta cuántos días distintos de datos tenemos guardados
       COUNT(DISTINCT game_id) AS games       -- Cuenta el total de juegos únicos registrados en los precios
FROM price_snapshots;

-- name: top_discounts
-- Obtiene el top de juegos con mayor porcentaje de descuento en la última fecha capturada
SELECT g.title, s.name AS store, p.normal_price, p.sale_price, p.savings_pct
FROM price_snapshots p
JOIN games g ON g.game_id = p.game_id         -- Cruza con la tabla de juegos para obtener el título
JOIN stores s ON s.store_id = p.store_id       -- Cruza con la tabla de tiendas para obtener el nombre de la tienda
WHERE p.captured_date = (SELECT MAX(captured_date) FROM price_snapshots) -- Filtra solo los datos del último día disponible
ORDER BY p.savings_pct DESC                    -- Ordena de mayor a menor porcentaje de ahorro
LIMIT 15;                                      -- Limita los resultados a los 15 mejores descuentos

-- name: best_value
-- Calcula la relación "calidad-precio" (puntos de Metacritic por dólar) para la última fecha
SELECT g.title, g.metacritic_score, MIN(p.sale_price) AS best_price,
       ROUND(g.metacritic_score / MIN(p.sale_price), 1) AS points_per_dollar -- Calcula puntaje dividido entre el precio mínimo de venta
FROM price_snapshots p
JOIN games g ON g.game_id = p.game_id
WHERE p.captured_date = (SELECT MAX(captured_date) FROM price_snapshots)
  AND g.metacritic_score IS NOT NULL           -- Excluye juegos que no tengan puntaje de Metacritic
  AND p.sale_price > 0                         -- Evita divisiones por cero si el juego es gratuito
GROUP BY g.game_id                             -- Agrupa por cada juego único
ORDER BY points_per_dollar DESC                -- Ordena de mayor a menor valor (más puntos por dólar)
LIMIT 15;

-- name: deals_by_store
-- Resumen de ofertas totales y promedio de descuento agrupado por cada tienda en el último snapshot
SELECT s.name AS store, COUNT(*) AS deals, ROUND(AVG(p.savings_pct), 1) AS avg_discount
FROM price_snapshots p
JOIN stores s ON s.store_id = p.store_id
WHERE p.captured_date = (SELECT MAX(captured_date) FROM price_snapshots)
GROUP BY s.store_id                            -- Agrupa por identificador de tienda
ORDER BY deals DESC;                           -- Ordena de la tienda con más ofertas a la que menos tenga

-- name: top_per_store
-- Utiliza una función de ventana (Window Function) para obtener los 3 mejores descuentos de cada tienda de forma individual
SELECT store, title, savings_pct, rank_in_store
FROM (
    SELECT s.name AS store, g.title, p.savings_pct,
           ROW_NUMBER() OVER (PARTITION BY p.store_id ORDER BY p.savings_pct DESC) AS rank_in_store -- Numera las filas por tienda ordenadas por mayor descuento
    FROM price_snapshots p
    JOIN games g ON g.game_id = p.game_id
    JOIN stores s ON s.store_id = p.store_id
    WHERE p.captured_date = (SELECT MAX(captured_date) FROM price_snapshots)
)
WHERE rank_in_store <= 3                       -- Filtra únicamente los puestos 1, 2 y 3 de cada tienda
ORDER BY store, rank_in_store;

-- name: games_list
-- Lista alfabética de todos los juegos disponibles en la base de datos (ideal para selectores en dashboards)
SELECT game_id, title FROM games ORDER BY title;

-- name: price_history
-- Consulta el histórico de precios de un juego específico a lo largo de todas las fechas capturadas
SELECT p.captured_date, s.name AS store, p.sale_price
FROM price_snapshots p
JOIN stores s ON s.store_id = p.store_id
WHERE p.game_id = :game_id                     -- Filtra por un parámetro dinámico de ID de juego (:game_id)
ORDER BY p.captured_date;                      -- Ordena cronológicamente por fecha de captura