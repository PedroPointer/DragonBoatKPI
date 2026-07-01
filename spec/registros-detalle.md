# Especificación: Pantalla Registros + Detalle de Test

## 1. Objetivo

Rediseñar la pantalla de **Registros** con calendario + tabla interactiva,
y el **Detalle de Test** con visualizador interactivo (Plotly), mapa GPS
(Leaflet) y datos crudos de carrera.

Alcance: 100% — incluye gráficas interactivas, mapa GPS, tabla filtrable y calendario.

---

## 2. Stack

| Componente | Tecnología | Forma |
|------------|------------|-------|
| Gráficas web | Plotly Python (server-side) | `fig.to_html()` → HTML interactivo embebido |
| Gráficas PDF | matplotlib (se mantiene) | Calidad de impresión, sin interactividad |
| Mapa GPS | Leaflet.js (CDN) | OpenStreetMap, sin API key |
| Tabla | DataTables (CDN) + jQuery | Sort/filter/paginación nativo |
| Calendario | Vanilla JS | CSS grid + JS hand-rolled, sin dependencias |

Plotly Python genera HTML+JS interactivo desde el servidor. Reutiliza la lógica
de `charts.py` sin necesidad de escribir JS para las gráficas.
Leaflet, DataTables y el calendario son JavaScript client-side liviano.

---

## 3. Pantalla Registros (GET /registros)

### 3.1 Layout general

Dos zonas verticales:
1. **Parte superior**: calendario mensual
2. **Parte inferior**: tabla de tests/sesiones

La tabla ocupa todo el ancho. El calendario tiene un ancho máximo de ~400px
centrado en la parte superior, o se puede hacer responsivo.

### 3.2 Calendario (vanilla JS)

**Comportamiento:**
- Días con entrenamientos (que tienen tests en DB): marcados con badge verde
- Día actual: marcado con badge gris
- Días sin entrenamientos: sin marca
- Navegación: flechas ◀ ▶ para cambiar de mes
- Año: input editable a mano debajo del mes

**Interacción:**
- Al cargar la página: se muestra el mes actual, se llama a `GET /registros/dias?year=X&month=Y`
- Respuesta JSON: `{dias: [1, 15, 22]}`
- Click en un día marcado → se filtra la tabla a los tests de ese día
- Click en un día sin marca → no hace nada (o se limpia el filtro)

**Generación del calendario:**
- JS calcula primer día del mes, número de días, dibuja grid CSS
- Sin librerías externas. Archivo: `static/js/calendario.js`

### 3.3 Tabla (vía DataTables)

**Columnas:**

| Columna | Origen | Ordenable | Filtrable |
|---------|--------|-----------|-----------|
| # | test.test_number | Sí | No |
| Nombre | test.custom_name | Sí | Sí |
| Tipo | session.tipo | Sí | Sí (select) |
| Barco | boat.display_name | Sí | Sí (select) |
| Tiempo | test_metric.tiempo_total | Sí | No |
| Categoría | test.categoria | Sí | Sí (select) |
| Fecha | session.fecha | Sí | Sí (input date) |
| Hora | session.fecha (time) | Sí | No |

**Comportamiento sin filtro:**
- Orden default: por **fecha descendente** (agrupado por día),
  dentro del mismo día por **test_number ascendente** (orden de ejecución)

**Click en fila:**
- Navega a `GET /test/{id}` (detalle de test)

**Botón "Limpiar filtros":**
- Resetea todos los filtros de DataTables al estado inicial

**Datos iniciales:**
- La tabla se renderiza en SSR (server-side rendering inicial con Jinja2)
- DataTables inicializa sobre el HTML existente: `$("#tabla-registros").DataTable()`
- Las columnas que usan select para filtrar usan `DataTable().column().search()` con inputs custom

### 3.4 Endpoints

**GET /registros** (HTML):
- Parámetros opcionales: `?dia=15&mes=6&anio=2026`
- Si se pasan, la tabla se renderiza filtrada a ese día desde el servidor
- El JS del calendario puede hacer un fetch y re-renderizar la tabla, o recargar la página con query params

**GET /registros/dias?year=2026&month=6** → JSON:
```json
{"dias": [1, 15, 22]}
```

---

## 4. Detalle de Test (GET /test/{id}) — rediseño completo

La página de detalle de test se reorganiza en 7 bloques verticales:

1. Navegación y cabecera (back link + título + metadatos)
2. Encabezado de métricas (stat-cards + editar prueba)
3. Mini-mapa GPS (Leaflet con trayectoria)
4. Visualizador de carrera (PNG actual + Plotly futuro)
5. Datos generales de la carrera (3 tablas: tramos, velocidades, paladas)
6. Tripulación con SVG interactivo (configurador inline)
7. Eliminar prueba (botón con confirmación)

---

### 4.1 Navegación y cabecera

**Back link:**
- `<a href="/registros" class="back-link">← Volver a registros</a>` en la parte superior
- Navega a `GET /registros`

**Título:**
- `<h1>` con `test.custom_name` si existe
- Si no: `Prueba #{{ test.test_number }}`

**Metadatos:**
- `<p class="page-meta">` con `test.boat.display_name` + `test.categoria`
- Separador ` — ` entre ambos si los dos existen

**Anchor `#tripulacion`:**
- Dashboard enlaza a `/test/{id}#tripulacion` para scroll directo al card de tripulación
- `session.html` también enlaza a `/test/{id}#tripulacion`

---

### 4.2 Encabezado de métricas

**Layout:** card con título "Métricas" + tiempo total grande a la derecha.
- Tiempo total: `{{ "%.2f"|format(test.metric.tiempo_total) }}s`

**Stat-cards (6, grid auto-fit):**
| Métrica | Fuente | Unidad |
|---------|--------|--------|
| Vel. máxima | test_metric.velocidad_maxima | km/h |
| Vel. media | test_metric.velocidad_media | km/h |
| 0 → 12 km/h | test_metric.tiempo_12kmh | s (— si null) |
| Paladas | test_metric.num_paladas | total |
| Dist. palada | test_metric.dist_media_palada | m |
| Consistencia | test_metric.dist_std_palada | m (— si 0) |

Formato: mismo estilo que las stat-cards del Dashboard (base.css).
Grid: `grid-template-columns: repeat(auto-fit, minmax(130px, 1fr))`

**Editar prueba (sub-sección colapsable):**
- `<details>` con `border-top`, dentro del mismo card
- `<summary>`: "Editar prueba"
- Formulario `POST /test/{id}` en fila con `flex-wrap: wrap`:
  - **Nombre**: `<input type="text" name="custom_name">` con `<datalist>` de nombres existentes
  - **Barco**: `<select name="boat_id">` con opciones de tabla `boats`
  - **Categoría**: `<select name="categoria">` con lista fija de categorías
- Botón "Guardar" (`<button type="submit" class="btn small">`)
- Acción server-side: `update_sesion()` con valores no vacíos, redirect 302 a `GET /test/{id}`

---

### 4.3 Mini-mapa GPS (Leaflet)

**Contenido:**
- Mapa centrado en la trayectoria del barco
- Polyline con puntos lat/lon del test, color azul (#38bdf8), weight 3
- Marcador inicio verde (#22c55e, radio 6) con tooltip "Salida"
- Marcador fin rojo (#ef4444, radio 6) con tooltip "Llegada"
- `map.fitBounds(latlngs, {padding: [20, 20]})`
- `setTimeout(invalidateSize, 200)` post-render para evitar tile glitch

**Interacción:**
- Botón "Minimizar" / "Mostrar mapa" togglea clase `.minimized`
- CSS: `transition: height 0.3s ease`, `.minimized { height: 0; margin-bottom: 0; }`
- Zoom y pan nativos de Leaflet

**Datos:**
- `GET /test/{id}/trajectory` → `{points: [[lat, lon, speed], ...], center: [lat, lon] | null}`
- Sin `bounds` en la respuesta actual (spec anterior listaba `bounds`, implementación usa `center` + `fitBounds`)
- Si puntos vacíos o < 2: mensaje "Mapa no disponible — datos GPS no registrados"
- Si error fetch: mensaje "Mapa no disponible"

**Implementación:**
- CDN Leaflet + CSS en base.html
- Inicialización en `<script>` inline en test.html (IIFE)
- `onclick="toggleMapa()"` en el botón
- Sin dependencia de tiles caros (OSM gratuito)

---

### 4.4 Visualizador de carrera

**Estado actual — PNG desde matplotlib:**
- Muestra gráfica generada por `graficar_200m()` como imagen base64 embebida
- Si `test.metric.chart_filename` existe y PNG está en `data/output/`:
  `<img src="data:image/png;base64,{{ chart_b64 }}">`
- Si no: `<p style="color: #64748b; text-align: center;">Gráfica no disponible</p>`
- No hay interactividad (zoom, pan, hover)

**Estado futuro — Plotly interactivo (pendiente implementación):**
- Reemplazará el PNG cuando se implemente la persistencia de GPS raw
- 4 subplots sincronizados (eje X compartido):

  1. **Velocidad (km/h):** línea por segmento (verde acelera / rojo frena), línea media punteada azul, sombreado 0→12 km/h naranja, sombreado últimos 50m rojo, anotaciones 50/100/150m, picos numerados, valles catch, stats box
  2. **Roll / Balanceo (deg):** barras estribor (#D2691E), babor (#FFB347), inestable (#c0392b), línea 0
  3. **Pitch / Cabeceo (deg):** barras proa (#6a9ad8), popa (#1a3a8a), línea 0
  4. **Distancia por palada (m):** barras verde ≥ media / rojo < media, línea media, número en cada barra, estrella mejor palada

- Comportamiento: zoom rec sincronizado, pan sincronizado, tooltip hover, doble click reset, export PNG
- Generación: `graficar_200m_plotly()` en charts.py → `fig.to_html(full_html=False, include_plotlyjs='cdn', div_id='chart-200m')`
- Endpoints planificados: `GET /test/{id}/raw` y `GET /test/{id}/chart`
- Ver sección 6 para estado de implementación

---

### 4.5 Datos generales de la carrera

Dos columnas con tablas HTML estáticas (sin interactividad).

**Columna 1 — Tramos:**
| Tramo | Tiempo (s) |
|-------|-----------|
| 0 → 50m | test_metric.tiempo_50m |
| 0 → 100m | test_metric.tiempo_100m |
| 0 → 150m | test_metric.tiempo_150m |
| **200m** | **test_metric.tiempo_total** |

Filas 50m/100m/150m se muestran solo si tienen valor (`{% if %}`).

**Columna 2 — Velocidades:**
| Métrica | Valor |
|---------|-------|
| Vel. máxima | test_metric.velocidad_maxima km/h |
| Vel. media | test_metric.velocidad_media km/h |
| Vel. mínima post-10m | test_metric.velocidad_min_post10 km/h |
| Acel. máxima | test_metric.aceleracion_max m/s² |
| 0 → 12 km/h | test_metric.tiempo_12kmh s |

Fila "Vel. mínima post-10m" solo si tiene valor.

**Columna 3 — Paladas:**
| Métrica | Valor |
|---------|-------|
| Paladas totales | test_metric.num_paladas |
| Dist. media/palada | test_metric.dist_media_palada m |
| Dist. máxima | test_metric.dist_max_palada m (— si null) |
| Dist. mínima (sin las 15 primeras) | test_metric.dist_min_palada m (— si null) |
| Consistencia (std) | test_metric.dist_std_palada m (— si 0) |

---

### 4.6 Tripulación con SVG interactivo

**Visión general:**
Configurador visual de tripulación inline — sin navegación a página separada.
Click en la cabeza de cada palista sobre el SVG del barco → dropdown type-ahead para seleccionar tripulante.
El SVG usa vista lateral con cabeza de dragón a la izquierda (proa) y cola a la derecha (popa).

**Layout del card:**
- Título "Tripulación" + badge del barco (`.badge.db12` verde, `.badge.db22` naranja)
- Subtítulo: "Haz clic en la cabeza de cada palista para asignarlo"
- SVG inline + contador `X / N asignados`
- Botones: "Limpiar" (con confirm) + "Guardar"

**SVG del barco:**
- Dos partials Jinja2, incluidos según `boat.name`:
  - `boat_hull_db12.svg.j2` — 5 filas (12 palistas), viewBox "0 0 1177 340"
  - `boat_hull_db22.svg.j2` — 10 filas (22 palistas), viewBox "0 0 1718 359"
- Color principal: púrpura (#7c2a78), basado en `imagen/dragon.html`
- Los partials contienen círculos `.seat-marker` (invisibles) con atributos data-role/data-side/data-row
- JS convierte cada `.seat-marker` en un grupo `<g class="seat">` con:
  - Círculo placeholder (fill #334155, stroke #475569, radio dinámico)
  - Imagen con `clip-path: url(#circleClip)`
  - Texto de iniciales (font-size proporcional al radio)
  - Label del nombre (blanco, bold, debajo del círculo)

**Seat markers esperados por barco:**

| Barco | Tambor | Remeros estribor | Remeros babor | Timonel | Total |
|-------|--------|------------------|---------------|---------|-------|
| DB12 | 1 | 5 | 5 | 1 | 12 |
| DB22 | 1 | 10 | 10 | 1 | 22 |

**Interacción — click-to-assign:**
1. Click en la cabeza → dropdown posicionado en `position: fixed` a nivel body (z-index: 99999)
2. Dropdown contiene: header "SELECCIONAR TRIPULANTE", input búsqueda, lista filtrada, contador
3. Búsqueda type-ahead con normalización NFD + eliminación de combining chars (acentos españoles)
4. Tripulantes ya asignados a OTRO puesto: opacity 0.35 + "asignado" label + pointer-events: none
5. Navegación teclado: ArrowUp/ArrowDown/Enter/Escape
6. Click fuera del dropdown → cierra

**Orden de tripulantes:**
- `list_crew_by_frequency()` en repo.py
- LEFT JOIN con crew_assignments + COUNT + GROUP BY + ORDER BY COUNT DESC
- Los más usados aparecen primero en el dropdown

**Labels por defecto (asiento vacío):**
| Rol | Label |
|-----|-------|
| Tambor | "Tambor" |
| Timonel | "Timonel" |
| Remero estribor | "E{row}" (E1…E10) |
| Remero babor | "B{row}" (B1…B10) |

**Visualización del tripulante asignado:**
- Con foto (`photo_path`): `<image>` con clip-path circular, oculta placeholder e iniciales
- Sin foto: iniciales (1ª letra nombre + 1ª letra apellido) en #334155, bold, #e2e8f0
- Label debajo del círculo: solo `member.nombre` (sin apellido)

**Contador:**
- `document.getElementById('assigned-count')` se actualiza en cada asignación
- Cuenta claves no vacías en el mapa `assignments`

**Guardar:**
- `window.guardarTripulacion()` recorre seats, construye payload `{assignments: [{crew_member_id, role, side, row_number}, ...]}`
- `POST /test/{id}/crew/json` con Content-Type application/json
- Éxito: toast verde "✓ Guardado" (fixed top-right, autodestrucción 2s)
- Error: `alert("Error al guardar")`

**Limpiar todo:**
- `window.limpiarTodo()` con `confirm("¿Limpiar todas las asignaciones?")`
- Vacía mapa de asignaciones, resetea cada seat: placeholder visible, image/initials ocultos, label default

**Endpoint POST /test/{id}/crew/json:**
- Ruta: `POST /test/{id}/crew/json`
- Body: `{"assignments": [{"crew_member_id": int, "role": str, "side": str|null, "row_number": int|null}, ...]}`
- Lógica: reemplaza todas las asignaciones existentes por las nuevas (DELETE + INSERT)
- Respuesta: JSON `{"ok": true}` o error

---

### 4.7 Eliminar prueba

Botón con confirmación antes de la acción destructiva:

- Formulario que POST a `POST /registros/{prueba_id}/delete`
- `onsubmit="return confirm('¿Eliminar esta prueba?')"`
- Comportamiento server-side (`delete_sesion()`):
  - Borra la sesión, su métrica y sus crew_assignments (cascade)
  - Si era la última prueba del csv_upload padre → el csv_upload también se borra
  - Si `csv_upload.kept=True`, el archivo en disco se borra también
- Redirige a `GET /registros` (302)

Ruta: `routes.py`:
```python
@router.post("/registros/{prueba_id}/delete")
async def sesion_delete(prueba_id: int):
    delete_sesion(prueba_id)
    return RedirectResponse(url="/registros", status_code=302)
```

---

### 4.8 Fallbacks y estados vacíos

| Condición | Comportamiento |
|-----------|---------------|
| `test` es None | Redirige a /registros (302) |
| `test.metric` es None | Oculta métricas, mapa, gráfica y datos generales |
| `test.boat` es None | Usa DB12 como default para tripulación |
| Sin datos GPS (points vacío) | Mapa: "Mapa no disponible — datos GPS no registrados" |
| Error fetch trayectoria | Mapa: "Mapa no disponible" |
| `chart_filename` no existe | Gráfica: "Gráfica no disponible" |
| `dist_std_palada` es 0 | Consistencia muestra "—" |
| `tiempo_12kmh` es None | Muestra "—" |
| `velocidad_min_post10` es None | Fila oculta |
| `tiempo_50m/100m/150m` son None | Filas ocultas en tabla tramos |
| Sin tripulantes en DB | Dropdown muestra "Sin resultados" |
| Error en POST save tripulación | `alert("Error al guardar")` |
| Error de conexión en save | `alert("Error de conexión")` |

---

## 5. Modelo de Datos — tabla nueva

### test_gps_data

Nueva tabla para persistir los datos GPS muestreados de cada test.

| Campo | Tipo | Constraints |
|-------|------|-------------|
| id | INTEGER | PK |
| test_id | INTEGER | FK → tests.id, UNIQUE |
| data_json | TEXT | JSON con arrays muestreados (ver formato) |

**Formato del JSON en data_json:**

```json
{
  "time": [0.0, 0.1, 0.2, ...],
  "speed": [2.47, 2.55, 2.62, ...],
  "lean": [0.1, 0.2, 0.15, ...],
  "gforce_x": [-0.103, -0.088, ...],
  "gforce_z": [0.972, 0.968, ...],
  "lat": [38.881733, 38.881734, ...],
  "lon": [-6.980930, -6.980928, ...],
  "peak_times": [3.24, 4.12, 5.08, ...],
  "peak_speeds": [14.2, 15.1, 14.8, ...],
  "valley_times": [2.91, 3.72, 4.65, ...],
  "dist_por_palada": [2.50, 2.72, 2.61, ...]
}
```

**Muestreo:**
- Frecuencia original del GPS: ~25 Hz (1 punto cada 40ms)
- Se almacenan TODOS los puntos sin reducción de frecuencia
- Tamaño aprox: ~150 KB por test (200m × 25Hz = ~1500 puntos × 10 campos)
- Perfectamente manejable en SQLite como campo TEXT/JSON

**Generación:**
- Se crea al mismo tiempo que `TestMetric` durante el análisis del CSV
- En el flujo de `POST /informes/upload`, después de `analizar_200m()`
- Se guarda en la misma transacción que `crear_test()`

---

## 6. Rutas API

| Método | Ruta | Descripción | Respuesta | Estado |
|--------|------|-------------|-----------|--------|
| GET | /registros/dias?year=X&month=Y | Días del mes con entrenamientos | JSON: `{dias: [1,15,22]}` | ✅ Implementado |
| GET | /test/{id}/trajectory | Puntos GPS para el mapa Leaflet | JSON: `{points, center}` | ✅ Implementado (points siempre [] por ahora) |
| POST | /test/{id}/crew/json | Guardar asignaciones tripulación inline | JSON: `{ok: true}` | ✅ Implementado |
| POST | /registros/{prueba_id}/delete | Eliminar prueba con cascade | Redirect 302 /registros | ✅ Implementado |
| GET | /test/{id}/raw | Datos muestreados para Plotly | JSON completo (ver sección 5) | 🔄 Pendiente |
| GET | /test/{id}/chart | HTML del visualizador Plotly | HTML parcial (`fig.to_html()`) | 🔄 Pendiente |

### GET /registros/dias

**Parámetros:** year (int), month (int, 1-12)
**Lógica:** consulta `sessions` por año/mes, agrupa por día, filtra las que tienen tests
**Respuesta:**
```json
{"dias": [1, 15, 22]}
```

### GET /test/{id}/trajectory

**Lógica:** busca `test_gps_data` por test_id, extrae lat/lon/speed
**Respuesta actual (points siempre vacío — pendiente migración GPS raw):**
```json
{"points": [], "center": null}
```
**Respuesta futura** (cuando existan datos GPS raw en DB):
```json
{
  "points": [[38.881733, -6.980930, 2.47], [38.881734, -6.980928, 2.55]],
  "center": [38.8818, -6.9809]
}
```

### POST /test/{id}/crew/json

**Body:**
```json
{
  "assignments": [
    {"crew_member_id": 1, "role": "remero", "side": "estribor", "row_number": 1},
    {"crew_member_id": 2, "role": "tambor", "side": null, "row_number": null}
  ]
}
```
**Lógica:** reemplaza todas las asignaciones existentes de la sesión por las nuevas (DELETE + INSERT en transacción)
**Respuesta:** `{"ok": true}` (200) o error (500)

### POST /registros/{prueba_id}/delete

**Lógica:** `delete_sesion()` — borra sesión, metric, assignments (cascade); si era última del csv_upload, borra csv_upload y archivo
**Respuesta:** Redirect 302 a `/registros`

### GET /test/{id}/raw (pendiente)

**Lógica:** busca `test_gps_data` por test_id, retorna el JSON completo
**Respuesta:** el JSON de la sección 5 (time, speed, lean, gforce_x, gforce_z, lat, lon, peak_times, peak_speeds, valley_times, dist_por_palada)

### GET /test/{id}/chart (pendiente)

**Lógica:** genera la gráfica Plotly con los datos raw, retorna HTML
**Respuesta:** `text/html` con el div Plotly + script (para incrustar vía AJAX o iframe)

---

## 7. Migración

### Estado inicial
- Tests existentes en DB (1 sesión del 29/06/2026 con 6 tests)
- Gráficas PNG en data/output/
- NO hay datos GPS raw en DB

### Proceso de migración
1. **Script `scripts/reset_tests.py`** que:
   - Trunca las tablas: `tests`, `test_metrics`, `crew_assignments`, `test_gps_data`
   - Elimina archivos PNG en `data/output/`
   - Mantiene `boats`, `crew_members`, `categories` intactos
2. **Subir CSV de nuevo** desde `POST /informes/upload`
3. El nuevo flujo genera:
   - GPS raw → `test_gps_data`
   - Métricas → `test_metrics`
   - PNG (opcional, para respaldo) → `data/output/`

### Dependencia temporal
- Después de la migración, los tests viejos no existen más
- Solo los tests nuevos (subidos post-migración) tienen GPS raw
- El visualizador Plotly verifica si hay GPS raw; si no, muestra mensaje
  "Datos no disponibles — subir el CSV nuevamente"

---

## 8. Archivos afectados

### Nuevos

| Archivo | Contenido |
|---------|-----------|
| `src/dragonboat/web/static/js/calendario.js` | Generación y navegación del calendario mensual |
| `src/dragonboat/web/static/js/registros.js` | Inicialización de DataTables + coordinación calendario-tabla |
| `src/dragonboat/web/templates/boat_hull_db12.svg.j2` | SVG lateral barco DB12 con seat-markers (12 palistas) |
| `src/dragonboat/web/templates/boat_hull_db22.svg.j2` | SVG lateral barco DB22 con seat-markers (22 palistas) |
| `src/dragonboat/web/deportistas_routes.py` | CRUD tripulantes + endpoints crew assignment |
| `src/dragonboat/web/static/img/barcoDB12.svg` | SVG de referencia para DB12 |
| `src/dragonboat/web/static/img/barcoDB22.svg` | SVG de referencia para DB22 |
| `scripts/reset_tests.py` | Borra tests existentes para migración |

### Modificados

| Archivo | Cambio |
|---------|--------|
| `src/dragonboat/db_models.py` | Añadir `TestGPSData` model |
| `src/dragonboat/migrations.py` | Nueva tabla |
| `src/dragonboat/repo.py` | Añadir `crear_test_gps_data()`, `get_test_gps_data()`, `get_dias_con_entrenamientos()`, `list_crew_by_frequency()` |
| `src/dragonboat/web/routes.py` | Añadir rutas: `/registros/dias`, `/test/{id}/trajectory`, `/test/{id}/crew/json`, `/test/{id}/raw` (pendiente), `/test/{id}/chart` (pendiente) |
| `src/dragonboat/web/deportistas_routes.py` | Añadir ruta `GET /test/{id}/crew` redirect a `/test/{id}#tripulacion`, `POST /test/{id}/crew/json` |
| `src/dragonboat/visualization/charts.py` | Añadir `graficar_200m_plotly()` usando Plotly Python (pendiente implementación completa) |
| `src/dragonboat/web/templates/base.html` | Añadir CDNs: Plotly.js (futuro), Leaflet, DataTables, jQuery |
| `src/dragonboat/web/templates/registros.html` | Rediseño completo: calendario + tabla |
| `src/dragonboat/web/templates/test.html` | Rediseño completo: 7 bloques, SVG interactivo tripulación (sin Plotly, usa PNG base64) |
| `src/dragonboat/web/templates/dashboard.html` | Link "Asignar →" apunta a `/test/{id}#tripulacion` |
| `src/dragonboat/web/templates/session.html` | Eliminada (reemplazada por redirect a `/test/{id}`) |
| `pyproject.toml` | Añadir `plotly>=5.20` a dependencias |

---

## 9. Dependencias nuevas

### Python (pip)
- `plotly>=5.20` — generación de gráficas interactivas server-side

### CDN (sin install, en base.html)
- `plotly.js` — renderizado cliente de las gráficas generadas
- `leaflet.js` + `leaflet.css` — mapa GPS
- `jquery.js` — requerido por DataTables
- `datatables.js` + `datatables.css` — tabla interactiva

### Versiones CDN sugeridas
```html
<!-- Plotly -->
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>

<!-- Leaflet -->
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

<!-- jQuery + DataTables -->
<link rel="stylesheet" href="https://cdn.datatables.net/1.13.11/css/jquery.dataTables.min.css" />
<script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
<script src="https://cdn.datatables.net/1.13.11/js/jquery.dataTables.min.js"></script>
```

---

## 10. Decisiones de Diseño

| Decisión | Valor | Razón |
|----------|-------|-------|
| Gráficas web | Plotly Python server-side | Reutiliza lógica de charts.py, interactivo sin JS |
| Gráficas PDF/impresión | matplotlib (se mantiene) | Calidad vectorial, sin interactividad |
| Mapa GPS | Leaflet.js (CDN) | Estándar open-source, sin API key |
| Tabla filtrable | DataTables (CDN) + jQuery | Sort/filter/paginación nativo, ~1 línea JS |
| Calendario | Vanilla JS | Full control visual, sin dependencia |
| GPS raw en DB | JSON completo 25Hz en `test_gps_data.data_json` | Todos los puntos del sensor, ~150KB/test, sin pérdida de datos |
| Tests existentes | Se borran (script reset_tests.py) | Empezar de 0, validar subida limpia |
| CDNs | Versiones fijas en base.html | Evitar roturas por actualizaciones automáticas |
| Plotly caching | Se regenera cada request desde raw data | Rápido (<100ms), sin complejidad de caché |
| SVG barco | Vista lateral con seat-markers invisibles | El usuario diseñó la vista lateral en dragon.html; seat-markers garantizan alineación perfecta |
| Configurador tripulación | Inline en test.html (no página separada) | UX más rápida: click + asignar sin navegación |
| Dropdown tripulación | `position: fixed` a nivel body, z-index 99999 | Soluciona clipping por overflow del contenedor SVG |
| Orden tripulantes | Por frecuencia de uso (freq DESC) | Los más usados aparecen primero, reduce búsqueda |
| Búsqueda type-ahead | NFD + strip combining chars | Acentos españoles (é, í, ó, etc.) no deben romper la búsqueda |
| Visualización sin foto | Iniciales en círculo #334155 | Consistente con placeholder de deportistas |
| Labels asiento vacío | E{row}/B{row} / Tambor / Timonel | Identificación rápida sin tener que contar filas |
| Gráfica de carrera (actual) | PNG base64 embebido | Sin build step ni CDN adicional, funcional desde el inicio |
| Gráfica de carrera (futuro) | Plotly server-side vía `GET /test/{id}/chart` | Interactividad completa cuando existan datos GPS raw |
