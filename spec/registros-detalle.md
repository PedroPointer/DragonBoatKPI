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
| Gráficas web | ECharts (vendored local) | `echarts.init()` + JSON del servidor, sin CDN |
| Gráficas PDF | matplotlib (se mantiene) | Calidad de impresión, sin interactividad |
| Mapa GPS | Leaflet.js (CDN) | OpenStreetMap, sin API key |
| Tabla | Server-side rendered + row-link | Sin DataTables (eliminado en refactor) |
| Calendario | Vanilla JS | CSS grid + JS hand-rolled, sin dependencias |

ECharts se sirve como archivo local en `static/vendor/echarts.min.js` (sin dependencia de CDN externa).
El servidor devuelve un JSON con las series 25Hz en `GET /test/{id}/chart-data`.
Leaflet y el calendario son JavaScript client-side liviano.

---

## 3. Pantalla Registros (GET /registros)

### 3.1 Layout general

Cuatro zonas verticales cuando hay sesión del día seleccionado:
1. **Parte superior**: calendario mensual (vanilla JS)
2. **Parte media-alta**: mapa GPS Leaflet del día (segmentos moving/stopped + tramos de prueba)
3. **Parte media-baja**: cabecera de sesión con métricas generales (stat-cards)
4. **Parte inferior**: tabla de pruebas del día seleccionado

Si no hay día seleccionado con entrenamientos: muestra empty state sugiriendo subir un CSV.

### 3.2 Calendario (vanilla JS)

**Comportamiento:**
- Días con entrenamientos: marcados con badge verde
- Días con competición: marcados con badge amarillo borde dorado
- Día actual: marcado con badge gris
- Día seleccionado: outline azul + fondo cyan
- Días sin entrenamientos: sin marca
- Navegación: flechas ◀ ▶ para cambiar de mes
- Año: input editable a mano

**Interacción:**
- Al cargar la página: `GET /registros/dias?year=X&month=Y`
- Respuesta JSON: `{dias: [...], dias_competicion: [...]}`
- Click en un día marcado → navega a `/registros?dia=X&mes=Y&anio=Z`

**Generación del calendario:**
- JS calcula primer día del mes, número de días, dibuja grid CSS
- Sin librerías externas. Archivo: `static/js/calendario.js`

### 3.3 Cabecera de sesión (si hay día seleccionado)

Cuando hay sesión del día, se muestra:
- Título: "Sesión del dd/MM/YYYY"
- Subtítulo: "{num_pruebas} pruebas · {num_archivos} archivos · {tipo} · {categoria}"
- **Stats grid** (8 stat-cards):
  - Distancia total real (highlight, fondo azul) + nominal
  - Tiempo total (duración GPS)
  - Tiempo parado (sin moverse)
  - Tiempo en movimiento (remando)
  - **% en movimiento (highlight, fondo azul)** — `tiempo_movimiento / tiempo_total_entreno × 100`, formato `N.N%`, "—" si no hay datos
  - Vel. media en mov.
  - Vel. máxima del día
  - Ritmo medio (min/km)

**Mapa de sesión:**
- Mapa Leaflet con segmentos GPS coloreados por estado (verde = moving, rojo = stopped)
- Leyenda con 5 categorías de velocidad (0-3, 3-6, 6-9, 9-12, 12-15 km/h)
- Test segments coloreados por distancia (200m azul, 500m amarillo, 1000m naranja)
- Botón Minimizar togglea `.minimized` class

### 3.4 Tabla de pruebas del día

**Columnas:**

| Columna | Origen |
|---------|--------|
| # | loop.index |
| Nombre | test.custom_name |
| Distancia | test.distancia.metros (badge) |
| Barco | test.boat.name (badge) |
| Tiempo | test.tiempo_total (formato duration) |
| Paladas | test.num_paladas |
| Acciones | Ver / Eliminar |

**Click en fila:**
- Navega a `GET /test/{id}` (detalle de test)
- Click en Ver / Eliminar hace `event.stopPropagation()` para no disparar el row click

**Eliminación:**
- `POST /test/{id}/delete` con `confirm('¿Eliminar esta prueba?')`
- Cascade: borra test_metric, crew_assignments

### 3.5 Archivos CSV del día

Lista de archivos CSV subidos en la sesión con fecha de upload y datos.

### 3.6 Eliminar sesión completa

`POST /sesion/{id}/delete` con `confirm('¿Eliminar esta sesión y todos sus datos? Esta acción no se puede deshacer.')`
- Borra sesión + cascade (csv_uploads, gps_data, test_metrics, crew_assignments, archivos físicos)

### 3.7 Endpoints

**GET /registros** (HTML):
- Parámetros opcionales: `?dia=15&mes=6&anio=2026&tipo=&barco=`
- Si se pasan `dia/mes/anio`, se renderiza la sesión de ese día

**GET /registros/dias?year=2026&month=6** → JSON:
```json
{"dias": [1, 15, 22], "dias_competicion": [22]}
```

---

## 4. Detalle de Test (GET /test/{id}) — rediseño completo

La página de detalle de test se reorganiza en 7 bloques verticales:

1. Breadcrumb navigation + título + metadatos
2. Encabezado de métricas (stat-cards + botón Editar prueba)
3. Mini-mapa GPS (Leaflet con trayectoria coloreada por velocidad)
4. Visualizador de carrera (ECharts interactivo con toggle PNG ↔ Interactivo)
5. Datos generales de la carrera (formato reporte: sectores D/4, velocidad, paladas)
6. Tripulación con SVG interactivo (configurador inline)
7. Eliminar prueba (botón con confirmación)

---

### 4.1 Breadcrumb navigation

**Breadcrumb:**
- `<nav class="breadcrumb">` con `Home / Registros / Prueba #X`
- `Home` enlaza a `GET /`
- `Registros` enlaza a `GET /registros`
- Último item: texto del título (no es link)

**Título:**
- `<h1>` con `test.custom_name` si existe
- Si no: `Prueba #{{ test.test_number }}`

**Metadatos:**
- `<p class="page-meta">` con `test.boat.display_name` + `test.categoria`
- Separador ` — ` entre ambos si los dos existen

---

### 4.2 Encabezado de métricas

**Layout:** card con título "Métricas" + botón "Editar prueba ▾" + tiempo total grande a la derecha.
- Tiempo total: `{{ test.tiempo_total|duration }}` (formato HH:MM:SS,MM)

**Stat-cards (6, grid auto-fit):**
| Métrica | Fuente | Unidad |
|---------|--------|--------|
| Vel. máxima | test.velocidad_maxima | km/h |
| Vel. media | test.velocidad_media | km/h |
| 0 → 12 km/h | test.tiempo_12kmh | hh:mm:ss,mm (— si null) |
| Paladas | test.num_paladas | total |
| Dist. palada | test.dist_media_palada | m |
| Consistencia | test.dist_std_palada | m (— si 0) |

Formato: mismo estilo que las stat-cards del Dashboard (base.css).
Grid: `grid-template-columns: repeat(auto-fit, minmax(130px, 1fr))`

**Editar prueba (sub-sección OCULTA, toggle con botón):**
- Botón "Editar prueba ▾" junto al título "Métricas"
- Al click: `toggleEditarPrueba()` muestra/oculta el panel `#editar-prueba-panel`
- Texto del botón cambia a "Editar prueba ▴" cuando está abierto
- Panel tiene `border-top` separador
- Formulario `POST /test/{id}` en fila con `flex-wrap: wrap`:
  - **Nombre**: `<input type="text" name="custom_name">` con `<datalist>` de nombres existentes
  - **Número**: `<input type="number" name="test_number">` (Nº)
  - **Barco**: `<select name="boat_id">` con opciones de tabla `boats`
  - **Categoría**: `<select name="categoria">` con lista de `categories`
  - **Tipo**: `<select name="tipo">` con opciones de `test_types`
- Botón "Guardar" (`<button type="submit" class="btn small">`)
- Acción server-side: `update_prueba()` con valores no vacíos, redirect 302 a `GET /test/{id}`

---

### 4.3 Mini-mapa GPS (Leaflet)

**Contenido:**
- Mapa centrado en la trayectoria del barco
- **Polilínea coloreada por velocidad**: cada segmento se colorea según la velocidad media
  - Gradiente de 0 a 15 km/h: rojo → naranja → amarillo → verde claro → verde oscuro
  - `STOPS = [{0,#ef4444}, {3,#f97316}, {6,#eab308}, {9,#84cc16}, {12,#22c55e}, {15,#10b981}]`
  - Cada segmento se dibuja entre 2 puntos consecutivos con la velocidad media entre ellos
- Marcador inicio: flecha `➡` rotada con el bearing de salida + tooltip "Salida"
- Marcador fin: bandera `🏁` + tooltip "Llegada"
- Legend en `bottomright` con 5 rangos de velocidad
- `map.fitBounds(latlngs, {padding: [20, 20]})`
- `setTimeout(invalidateSize, 200)` post-render para evitar tile glitch

**Interacción:**
- Botón "Minimizar mapa" / "Mostrar mapa" togglea clase `.minimized`
- CSS: `transition: height 0.3s ease`, `.minimized { height: 0; margin-bottom: 0; }`
- Zoom y pan nativos de Leaflet

**Datos:**
- `GET /test/{id}/trajectory` → `{points: [[lat, lon, speed], ...], center, gps_inicio, gps_fin}`
- Points decimados a 5Hz con velocidad
- Si puntos vacíos o < 2: mensaje "Mapa no disponible — datos GPS no registrados"
- Si error fetch: mensaje "Mapa no disponible"

**Implementación:**
- CDN Leaflet + CSS en base.html
- Inicialización en `<script>` inline en test.html (IIFE)
- `onclick="toggleMapa()"` en el botón
- `bearingRad(p1, p2)` calcula el ángulo de la flecha de salida en radianes

---

### 4.4 Visualizador de carrera — ECharts interactivo

**Implementado: Apache ECharts 5 + PNG toggle**

El visualizador muestra gráficas interactivas con opción de alternar a PNG. Diseñado
con prioridad móvil: pinch-to-zoom, arrastre para pan, tooltip sincronizado entre
paneles y línea roja de salida atravesando los 4 grids a la vez.

**Ventana temporal visible:** desde **2 segundos antes de la salida** (cuando los
datos están disponibles) hasta el final del tramo. La **salida (t=0)** se marca con
una línea vertical roja sólida de 2px de ancho que cruza los 4 paneles sincronizada
(los ejes X están enlazados vía `xAxisIndex: "all"`).

**4 subplots sincronizados** (eje X compartido vía `axisPointer.link`):
1. **Velocidad (km/h):** línea verde (#27ae60), línea media punteada azul (#3498db) con etiqueta, marcadores dashed de distancia (gris/naranja/rojo según tramo), valles catch como puntos azules (#2980b9), números de pico en cada stroke (1, 2, 3…)
2. **Roll / Balanceo (deg):** barras estribor (#D2691E), babor (#FFB347), inestable (#c0392b cuando |roll| > 10°)
3. **Pitch / Cabeceo (deg):** barras proa (#6a9ad8), popa (#1a3a8a)
4. **Distancia por palada (m):** barras verde ≥ media / rojo < media, línea media roja dashed con etiqueta, ★ dorada en la mejor palada

**Interacción táctil (móvil-first):**
- **Pellizcar** (dos dedos) → zoom simultáneo en los 4 paneles
- **Arrastrar** (un dedo) sobre la gráfica → pan
- **Tocar** → crosshair unificado + tooltip con t, km/h, roll°, pitch° (no valores internos)
- **Slider inferior** → tiradores táctiles para seleccionar tramos con precisión
- **Botón "Reset zoom"** → vuelve al rango completo
- **Doble-tap / wheel** → zoom (desktop)

**UI del visualizador:**
- Botón "Reset zoom" — vuelve al rango completo
- Botón "PNG" / "Interactivo" para alternar entre imagen estática y ECharts
- Panel de checkboxes: Velocidad, Balanceo, Cabeceo, Dist/palada (toggle client-side, sin recarga)
- Botón "Expandir ⛶" / "Colapsar ⛶" para maximizar la gráfica (llama a `chart.resize()`)
- Escape para colapsar si está expandido
- Descarga PNG: botón "Descargar PNG" → `GET /test/{id}/chart.png`

**Endpoints:**
- `GET /test/{id}/chart-data` → JSON con series (`time`, `speed`, `lean`, `pitch`), eventos (`peak_times`, `peak_speeds`, `valley_times`, `dist_por_palada`) y marcadores (`tiempos_por_distancia`, `velocidad_media`, `velocidad_maxima`, `tiempo_12kmh`, `dist_media_palada`, `tiempo_total`)
- `GET /test/{id}/chart.png` → imagen PNG descargable (matplotlib, sin cambios)

**Generación:**
- Series 25Hz: leídas de `gps_data.data_json` (sesión completa del CSV) con slicing por coincidencia exacta de las primeras 5 muestras de velocidad → garantiza 2s previos para tests **existentes** sin migrar DB
- `pitch` se calcula server-side con `calcular_pitch(gforce_x, gforce_z)` (idéntico a la versión anterior)
- Render: una instancia ECharts, 4 grids apilados (velocidad ×3 altura, resto ×1), dataZoom `inside` + `slider` enlazado a los 4 ejes X

**Vendor / dependencias:**
- ECharts 5.5.1 self-hosted en `static/vendor/echarts.min.js` (~1 MB, sin CDN — funciona offline)
- Plotly eliminado de `base.html` (~1,2 MB menos en TODAS las páginas)

**Estado fallback:**
- Sin `segment_gps_json`: muestra solo PNG si existe, o "Gráfica no disponible"
- Sin `gps_data` (pruebas manuales): chart-data degrada a `segment_gps_json` (empieza en t=0, sin tramo negativo; la línea roja sigue funcionando)

---

### 4.5 Datos generales de la carrera (formato reporte)

Card con título "Datos generales". Estilo "reporte" con jerarquía visual tipo resumen impreso.

**Header:**
- Título: "Dragon Boat - {distancia}m"
- Fecha: "dd/MM/YYYY HH:MM · Prueba #N"

**Tiempo total (highlight):**
- Caja con border-left azul, icono ⏱️, label "Tiempo total:", valor `{{ test.tiempo_total|duration }}`

**Sección 1 — Tiempos por sector (4 splits D/4):**
Generada por `calcular_sectores(tpd, distancia)` server-side. Cada sector tiene `{from, to, t_sector, t_acum, vel}`.

Ejemplo para 200m (split cada 50m):
- 0 a 50m: t_sector (vel km/h) t_acum
- 50 a 100m: t_sector (vel km/h) t_acum
- 100 a 150m: t_sector (vel km/h) t_acum
- 150 a 200m: t_sector (vel km/h) t_acum

Ejemplo para 500m (split cada 125m):
- 0 a 125m, 125 a 250m, 250 a 375m, 375 a 500m

Línea previa: "Aceleracion 0 a 12 km/h: {tiempo_12kmh|duration}"

**Sección 2 — Velocidad:**
- Media: {velocidad_media|comma_es} km/h ({velocidad_media/3.6|comma_es} m/s)
- Maxima: {velocidad_maxima|comma_es} km/h
- Minima: {velocidad_min_post10|comma_es} km/h (sin 15 primeras) — si tiene valor
- Acel maxima: {aceleracion_max|comma_es} m/s2 ({aceleracion_max/9.81|comma_es} G)

**Sección 3 — Paladas:**
- Total: {num_paladas}
- Distancia por palada: {dist_media_palada|comma_es} m
- Maxima: {paladas_resumen.max_all|comma_es} m — si hay datos
- Minima: {paladas_resumen.min_salida|comma_es} m (salida) — si hay datos
- Minima: {paladas_resumen.min_sin10|comma_es} m (sin 10 primeras) — si hay datos
- Consistencia: {dist_std_palada|comma_es} m — si > 0

**Jinja filters usados:**
- `duration` — formato HH:MM:SS,MM
- `duration_short` — formato MM:SS,CC
- `comma` — formato N.NN
- `comma_es` — formato N,NN (estilo español)
- `from_json` — parsear JSON de string

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

Toast notifications (en registros.html):
- Al eliminar: toast verde "✓ Prueba eliminada" (fixed top-right, autodestrucción 2s)
- Al guardar tripulación: toast verde "✓ Guardado"

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
| GET | /registros/dias?year=X&month=Y | Días del mes con entrenamientos | JSON: `{dias, dias_competicion}` | ✅ Implementado |
| GET | /test/{id}/trajectory | Puntos GPS para el mapa Leaflet (con velocidades) | JSON: `{points: [[lat,lon,spd]], center, gps_inicio, gps_fin}` | ✅ Implementado |
| GET | /test/{id}/chart-data | Series 25Hz + eventos para ECharts | JSON: `{time, speed, lean, pitch, peak_times, ...}` | ✅ Implementado |
| GET | /test/{id}/chart.png | Descarga PNG de la gráfica | image/png | ✅ Implementado |
| POST | /test/{id}/crew/json | Guardar asignaciones tripulación inline | JSON: `{ok: true}` | ✅ Implementado |
| POST | /test/{id}/delete | Eliminar prueba con cascade | Redirect 302 /registros | ✅ Implementado |
| GET | /sesion/{id} | Vista de sesión diaria con métricas generales | HTML: sesion.html | ✅ Implementado |
| POST | /sesion/{id} | Actualizar tipo/categoría de la sesión | Redirect 302 | ✅ Implementado |
| POST | /sesion/{id}/delete | Eliminar sesión completa (cascade) | Redirect 302 /registros | ✅ Implementado |
| POST | /sesion/{id}/recalcular | Recalcular agregados de la sesión | Redirect 302 /registros | ✅ Implementado |

### GET /registros/dias

**Parámetros:** year (int), month (int, 1-12)
**Lógica:** consulta `sessions` por año/mes, agrupa por día, filtra las que tienen tests
**Respuesta:**
```json
{"dias": [1, 15, 22]}
```

### GET /test/{id}/trajectory

**Lógica:** lee `prueba.segment_gps_json` o `prueba.gps_data.data_json`, decima a 5Hz
**Respuesta:**
```json
{
  "points": [[38.881733, -6.980930, 2.47], [38.881734, -6.980928, 2.55]],
  "center": [38.8818, -6.9809],
  "gps_inicio": {"lat": 38.8817, "lon": -6.9809},
  "gps_fin": {"lat": 38.8820, "lon": -6.9812}
}
```
- Points es array de `[lat, lon, speed]` decimado a 5Hz (cada 5 samples)
- Center es el centroide del mapa o null si no hay datos
- gps_inicio/gps_fin vienen de `prueba.gps_inicio` y `prueba.gps_fin`

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

### GET /test/{id}/chart-data (implementado)

**Lógica:** lee `segment_gps_json` (eventos: picos, valles, dist/palada) +
`gps_data.data_json` (series 25Hz completas de la sesión) + fila de la prueba
(marcadores y métricas). Localiza el inicio del tramo en la sesión completa por
coincidencia exacta de las primeras 5 muestras de velocidad, y devuelve las series
desde `start_t − 2s` (cuando los datos están disponibles) hasta el fin del tramo,
con tiempos relativos a la salida (t=0).

**Respuesta:** JSON
```json
{
  "time": [-2.0, -1.96, ..., 0, 0.04, ..., 45.8],
  "speed": [0.5, 0.6, ..., 12.0, 12.1, ..., 14.2],
  "lean": [...],
  "pitch": [...],
  "time_start": -2.0,
  "time_end": 45.8,
  "tiempo_total": 45.8,
  "velocidad_media": 13.5,
  "velocidad_maxima": 17.2,
  "tiempo_12kmh": 4.2,
  "peak_times": [0.7, 1.4, 2.1, ...],
  "peak_speeds": [13.1, 14.2, 14.8, ...],
  "valley_times": [0.4, 1.05, 1.75, ...],
  "dist_por_palada": [3.1, 3.3, 3.0, ...],
  "tiempos_por_distancia": {"50": 4.5, "100": 9.2, "150": 14.1, "200": 18.7},
  "dist_media_palada": 3.2,
  "num_paladas": 28
}
```

### GET /test/{id}/chart.png (implementado)

**Lógica:** genera la gráfica PNG con matplotlib, retorna imagen
**Respuesta:** `image/png` — descarga en nueva pestaña

---

## 7. Migración

### Estado inicial
- Tests existentes en DB (1 sesión del 29/06/2026 con 6 tests)
- Gráficas PNG en data/output/
- NO hay datos GPS raw en DB

### Proceso de migración
1. **Script `scripts/reset_db.py`** que:
   - Trunca las tablas: `sesiones`, `test_metrics`, `crew_assignments`, `test_gps_data`
   - Elimina archivos PNG en `data/output/`
   - Mantiene `boats`, `crew_members`, `categories`, `test_types` intactos
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
| `src/dragonboat/web/static/js/registros.js` | Init de registros.html (toast notifications, etc.) |
| `src/dragonboat/web/static/vendor/echarts.min.js` | ECharts library self-hosted (~1 MB, sin CDN) |
| `src/dragonboat/web/templates/boat_hull_db12.svg.j2` | SVG lateral barco DB12 con seat-markers (12 palistas) |
| `src/dragonboat/web/templates/boat_hull_db22.svg.j2` | SVG lateral barco DB22 con seat-markers (22 palistas) |
| `src/dragonboat/web/templates/sesion.html` | Vista de sesión diaria con métricas generales + tabla de pruebas + archivos CSV + acciones de edición/eliminación |
| `src/dragonboat/web/deportistas_routes.py` | CRUD tripulantes + endpoints crew assignment |
| `src/dragonboat/web/static/img/barcoDB12.svg` | SVG de referencia para DB12 |
| `src/dragonboat/web/static/img/barcoDB22.svg` | SVG de referencia para DB22 |
| `src/dragonboat/web/static/img/barcoDragon.svg` | SVG decorativo |
| `src/dragonboat/web/static/img/home_24dp.svg` | Icono Home |
| `src/dragonboat/web/static/img/iconoDragon.svg` | Icono Dragon |
| `src/dragonboat/web/static/img/add_circle_24dp.svg` | Icono agregar |
| `src/dragonboat/tools/backfill_sectores_paladas.py` | Backfill: pobla `sectores_detalle` y `paladas_detalle` en filas existentes |
| `scripts/reset_db.py` | Reset destructivo de tests/metrics/assignments/GPS |

### Modificados

| Archivo | Cambio |
|---------|--------|
| `src/dragonboat/db_models.py` | Añadir `AppSetting`, `Distancia`, `GpsData`, `TestType`, columna `sectores_detalle` y `paladas_detalle` en `TestMetric` |
| `src/dragonboat/repo.py` | Añadir `calcular_sectores()`, `resumen_paladas()`, `get_trajectory()`, `classify_gps_segments()`, CRUD TestType y Distancia |
| `src/dragonboat/analysis/_utils.py` | `format_duration`, `format_duration_short`, `calcular_sectores`, `resumen_paladas` |
| `src/dragonboat/analysis/loader.py` | `cargar_csv`, `build_gps_data_json`, `build_gps_inicio_fin`, `get_trajectory`, `classify_gps_segments`, `downsample_5hz` |
| `src/dragonboat/analysis/metrics.py` | `analizar_tramo`, `analizar_200m`, `calcular_pitch` |
| `src/dragonboat/analysis/detection.py` | `detectar_tramos`, `detectar_200m` |
| `src/dragonboat/analysis/strokes.py` | `detectar_paladas`, `detectar_picos` |
| `src/dragonboat/analysis/report.py` | `generar_informe_str`, `generar_resumen_sesion`, `nombre_base`, `imprimir_metricas` |
| `src/dragonboat/web/routes.py` | Reescrito: home, registros, sesion CRUD, test CRUD, trajectory, chart-data, chart.png, informes, config (incluye distancias y umbral), 4 endpoints API |
| `src/dragonboat/web/deportistas_routes.py` | `POST /deportistas/{id}/edit` para edición inline |
| `src/dragonboat/visualization/charts.py` | Solo `graficar_200m()` (PNG con matplotlib); `graficar_200m_plotly()` eliminado |
| `src/dragonboat/web/templates/base.html` | Removido CDN de Plotly; ECharts se carga local desde `/static/vendor/echarts.min.js` |
| `src/dragonboat/web/templates/registros.html` | Rediseño completo: calendario + sesión del día + mapa con leyenda + tabla de pruebas |
| `src/dragonboat/web/templates/test.html` | Rediseño completo: ECharts interactivo, SVG tripulación, breadcrumb, edit form oculto con toggle |
| `src/dragonboat/web/templates/home.html` | Rankings por distancia con `prueba_id` + sesiones incompletas |
| `src/dragonboat/web/templates/informes.html` | Upload CSV + reportes con paginación + descarga ZIP de CSVs |
| `src/dragonboat/web/templates/config.html` | 6 secciones: Barcos, Categorías, Tipos, Distancias, Umbral, Telegram |
| `pyproject.toml` | Eliminado `plotly>=5.20` de dependencias |

### Eliminados

| Archivo | Razón |
|---------|-------|
| `src/dragonboat/migrations.py` | No existe — se usa reset_db.py |
| `src/dragonboat/web/static/js/dataTables.js` | DataTables eliminado del refactor (tabla server-side) |
| `src/dragonboat/visualization/charts.py::graficar_200m_plotly` | Reemplazado por ECharts client-side |

---

## 9. Dependencias

### Python (pip)
- `pandas`, `numpy`, `scipy` — procesamiento de CSV
- `matplotlib` — gráficas PNG
- `sqlalchemy>=2.0`, `aiosqlite` — ORM
- `fastapi`, `jinja2` — web framework
- `pillow` — fotos de tripulantes

### Vendored (sin install, en `static/vendor/`)
- `echarts.min.js` (~1 MB) — renderizado cliente de las gráficas interactivas
- Cargado en `test.html` con `<script src="/static/vendor/echarts.min.js"></script>`

### CDN (sin install, en `base.html`)
- `leaflet.js` + `leaflet.css` — mapa GPS

### Versiones CDN usadas
```html
<!-- Leaflet -->
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
```

---

## 10. Decisiones de Diseño

| Decisión | Valor | Razón |
|----------|-------|-------|
| Gráficas web | ECharts 5 (vendored) | Interactividad rica, sin dependencia de CDN, offline-first |
| Gráficas PDF/impresión | matplotlib (se mantiene) | Calidad vectorial, sin interactividad |
| Mapa GPS | Leaflet.js (CDN) | Estándar open-source, sin API key |
| Mapa coloreado por velocidad | 6 stops de gradiente (rojo→verde) | Visualización clara de zonas rápidas/lentas |
| Tabla pruebas | Server-side render (sin DataTables) | Sin dependencia, fila con click + botones de acción |
| Calendario | Vanilla JS | Full control visual, sin dependencia |
| GPS raw en DB | JSON 25Hz en `gps_data.data_json` | Todos los puntos del sensor, ~150KB por CSV |
| Cálculo pitch server-side | `calcular_pitch(gforce_x, gforce_z)` | Reducir trabajo del cliente |
| Sectores pre-calculados | `sectores_detalle` columna JSON | 4 splits D/4 sin recalcular en cada render |
| Paladas detalle pre-calculadas | `paladas_detalle` columna JSON | max/min por categorías sin recalcular |
| Backfill script | `dragonboat.tools.backfill_sectores_paladas` | Idempotente, rellena filas existentes |
| Tests existentes | Se borran (script reset_db.py) | Empezar de 0, validar subida limpia |
| Plotly eliminado | Reemplazado por ECharts client-side | -1.2 MB en TODAS las páginas, mejor UX móvil |
| ECharts vendored | `static/vendor/echarts.min.js` | Offline-first, sin 404 si CDN falla |
| SVG barco | Vista lateral con seat-markers invisibles | El usuario diseñó la vista lateral; seat-markers garantizan alineación perfecta |
| Configurador tripulación | Inline en test.html (no página separada) | UX más rápida: click + asignar sin navegación |
| Dropdown tripulación | `position: fixed` a nivel body, z-index 99999 | Soluciona clipping por overflow del contenedor SVG |
| Orden tripulantes | Por frecuencia de uso (freq DESC) | Los más usados aparecen primero, reduce búsqueda |
| Búsqueda type-ahead | NFD + strip combining chars | Acentos españoles (é, í, ó, etc.) no deben romper la búsqueda |
| Visualización sin foto | Iniciales en círculo #334155 | Consistente con placeholder de deportistas |
| Labels asiento vacío | E{row}/B{row} / Tambor / Timonel | Identificación rápida sin tener que contar filas |
| Edit prueba | Toggle "Editar prueba ▾" con panel oculto | Card de métricas más limpia por defecto |
| Distancia | CRUD dinámico (distancias) | Soporte multi-distancia |
| Tipos de prueba | CRUD dinámico (test_types) | Permite agregar tipos sin cambiar código |
| Sesión diaria | Template dedicado (sesion.html) con métricas agregadas | Vista de "día completo" complementaria al detalle de prueba individual |
