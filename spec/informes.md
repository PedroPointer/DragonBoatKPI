# Especificación: Informes — Upload CSV y Análisis

## 1. Flujo principal: subir CSV

### 1.1 Entrada

- Zona de drag & drop en `/informes`
- Acepta archivos `.csv` (RaceBox Drag format)
- Validación de extensión antes de procesar

### 1.2 Detección de duplicado

```
POST /informes/upload
```

- Si el filename ya existe en `csv_uploads`: retorna HTML con `duplicate_filename`
- El usuario decide: reemplazar o cancelar
- Reemplazo: `POST /informes/upload?overwrite=1` → borra el anterior + crea el nuevo

### 1.3 Proceso de análisis

1. **Leer CSV** con pandas (`cargar_csv()` en `analysis/loader.py`)
   - Detecta fila de cabecera (`Record,Time...` o `timestamp,...`)
   - Normaliza columnas: `Time`, `elapsed_time`, `speed_kmh`, `lean_angle`, `gforce_x`, `gforce_z`, `lat`, `lon`
   - Calcula `distance_m` cumulativo
2. **Extraer metadata_date**: fecha del header del CSV o primera fila
3. **Detectar tramos** (`detectar_tramos()` en `analysis/detection.py`): análisis de gradiente de velocidad
   - Detecta tramos de 200m, 500m, 1000m, 2000m
   - Retorna lista de `TramoDetectado` con `start_idx`, `end_idx`, `distancia`
4. **Detectar paladas** (`detectar_paladas()` en `analysis/strokes.py`): picos de velocidad dentro de cada tramo
5. **Analizar cada tramo** (`analizar_tramo()` en `analysis/metrics.py`):
   - Calcula métricas: tiempo_total, velocidad_media, velocidad_maxima, etc.
   - Detecta tiempos intermedios (D/4 splits para `tiempos_por_distancia`)
   - Calcula distancias por palada
6. **Filtrar tramos válidos:**
   - `tiempo_total < limite_tiempo_max[distancia]`
   - `tiempo_11kmh < 20s`
   - `velocidad_media > 9.0 km/h` (excepto 2000m)
7. **Calcular `dist_max_palada` y `dist_min_palada`** de las paladas después de las 15 primeras
8. **Guardar en DB:**
   - `CsvUpload` (procedencia)
   - `GpsData` (GPS completo 25Hz del CSV)
   - `Sesion` diaria (agrupa pruebas del mismo día)
   - `TestMetric` por cada tramo válido, con `segment_gps_json`, `tiempos_por_distancia`, `gps_inicio`, `gps_fin`
9. **Pre-calcular columnas JSON**:
   - `sectores_detalle` = `calcular_sectores(tpd, distancia)` → 4 splits D/4
   - `paladas_detalle` = JSON array con `dist_por_palada`
10. **Generar gráficas PNG** (`graficar_200m()`): 4 paneles por test
11. **Generar reporte .txt** (`generar_resumen_sesion()`)
12. **Recalcular agregados de la sesión** (`recalc_sesion_aggregates()`)
13. **Redirect** a `/informes` con resumen

### 1.4 GPS Data

El GPS completo del CSV se guarda una sola vez en `gps_data`:
```json
{
  "time": [0.0, 0.1, 0.2, ...],
  "speed": [2.47, 2.55, 2.62, ...],
  "lat": [38.881733, 38.881734, ...],
  "lon": [-6.980930, -6.980928, ...],
  "lean": [0.1, 0.2, 0.15, ...],
  "gforce_x": [-0.103, -0.088, ...],
  "gforce_z": [0.972, 0.968, ...]
}
```

Cada tramo válido tiene su propio `segment_gps_json` con los puntos recortados del segmento.

### 1.5 Columnas pre-computadas (JSON en test_metrics)

**`tiempos_por_distancia`** (TEXT, JSON):
- Marcadores D/4: `{"50": 4.5, "100": 9.2, "150": 14.1, "200": 18.7}` para 200m
- Para 500m: `{"125": 44.25, "250": 84.87, "375": 126.64, "500": 168.39}`
- Se construye con análisis de gradiente

**`sectores_detalle`** (TEXT, JSON):
- Calculado con `calcular_sectores(tpd, distancia)` en `analysis/_utils.py`
- Array de `{from, to, t_sector, t_acum, vel}` para 4 splits
- Ejemplo: `[{"from": 0, "to": 50, "t_sector": 4.5, "t_acum": 4.5, "vel": 12.0}, ...]`

**`paladas_detalle`** (TEXT, JSON):
- Calculado con JSON array de `dist_por_palada` (sin las 15 primeras)
- Ejemplo: `[2.50, 2.72, 2.61, ...]`

---

## 2. Gráficas

### PNG (matplotlib)

- Generada por `graficar_200m()` en `visualization/charts.py`
- 4 paneles: velocidad, roll, pitch, distancia por palada
- Guardada como `{chart_filename}.png` en `data/output/`
- Se sirve via `GET /test/{id}/chart.png`
- Se descarga con el botón "Descargar PNG" en test.html

### ECharts interactivo (web)

- **NO se genera HTML server-side**. El cliente renderiza con ECharts.
- Endpoint: `GET /test/{id}/chart-data` → JSON con:
  - `time`, `speed`, `lean`, `pitch` (series 25Hz, t relativa al segmento incluyendo 2s previos)
  - `peak_times`, `peak_speeds`, `valley_times` (eventos)
  - `dist_por_palada` (per-stroke)
  - `tiempos_por_distancia`, métricas de la prueba
- ECharts library se sirve local en `static/vendor/echarts.min.js` (sin CDN)
- Render: una instancia ECharts, 4 grids apilados, dataZoom `inside` + `slider`
- Toggle PNG ↔ Interactivo: el usuario puede alternar entre la imagen PNG y la gráfica interactiva
- Paneles checkboxes: Velocidad, Balanceo, Cabeceo, Dist/palada (toggle client-side)

---

## 3. Reportes

### Generación

- Se genera un `.txt` por CSV subido
- Nombre: `Informe_{base_filename}.txt`
- Contenido: resumen de sesiones, pruebas, métricas
- Generado por `generar_resumen_sesion()` en `analysis/report.py`

### Visualización

- **Visor AJAX**: `GET /informes/reporte/{filename}` → JSON con contenido
- Se muestra en modal o inline
- **Descarga**: `GET /informes/reporte/{filename}/download` → FileResponse con `Content-Disposition`

### Seguridad

- Validación de filename: no permite `..`, `/` al inicio
- Solo sirve archivos desde `data/output/`

---

## 4. Eliminar upload

### Endpoint

```
POST /informes/eliminar-upload/{csv_id}
```

**Lógica:**
1. Busca `csv_upload` por ID
2. Elimina `GpsData` asociado (cascade por FK con `ondelete=CASCADE`)
3. Elimina `TestMetric` asociados (cascade por FK)
4. Elimina `CrewAssignment` asociados (cascade por FK)
5. Elimina `Sesion` si queda vacía
6. Elimina archivo en disco si `kept=True`
7. Elimina `csv_upload`

**Respuesta:** `{"ok": true}` o `{"error": "No se encontró el upload"}`

---

## 5. Descarga masiva de CSVs

### Endpoint

```
GET /informes/download-csvs
```

**Lógica:**
1. Lista todos los `csv_uploads`
2. Empaqueta los archivos en un ZIP
3. Nombres duplicados: agrega `_{id}` al final
4. Retorna como `StreamingResponse` con `application/zip`

**Nombre del ZIP:** `dragonboat_csvs_YYYYMMDD.zip`

---

## 6. Generar reporte manual

### Endpoint

```
POST /informes/generate
```

**Form data:** `sesion_id` (int)

**Lógica:**
1. Lista pruebas de la sesión
2. Genera archivo `Informe_sesion_{id}.txt` con header y lista de pruebas
3. Cada línea: `Prueba #N: {distancia}m - {tiempo_total}s`
4. Retorna redirect a `/informes` con mensaje

---

## 7. Backfill de sectores y paladas

### Script

`src/dragonboat/tools/backfill_sectores_paladas.py`

**Uso:**
```bash
python -m dragonboat.tools.backfill_sectores_paladas
```

**Lógica:**
- Itera todas las filas de `test_metrics`
- Para cada fila:
  - Si `sectores_detalle` es null pero `tiempos_por_distancia` y `distancia` existen: calcular y guardar
  - Si `paladas_detalle` es null pero `segment_gps_json` existe: extraer `dist_por_palada` y guardar
- Idempotente: las filas que ya tienen las columnas se saltan
- Retorna `{"updated": N, "skipped": M, "failed": K}`

**Cuándo correrlo:**
- Después de agregar las columnas `sectores_detalle` y `paladas_detalle` al modelo
- Para migrar datos existentes sin perder información

---

## 8. Validaciones

| Condición | Resultado |
|-----------|-----------|
| Archivo no es .csv | Error "Solo se aceptan archivos CSV" |
| CSV vacío | Error "CSV vacío o no se pudo leer" |
| Error al leer CSV | Error "Error al leer el CSV" |
| No hay tramos válidos | Warning "No se detectaron pruebas de velocidad" |
| Tiempo > limite | Tramo descartado |
| tiempo_11kmh > 20s | Tramo descartado |
| vel_media < 9 km/h | Tramo descartado (excepto 2000m) |

---

## 9. Archivos afectados

| Archivo | Rol |
|---------|-----|
| `routes.py` | Endpoints upload, generate, reporte, delete, download-csvs |
| `analysis/loader.py` | `cargar_csv()`, `build_gps_data_json()`, `get_trajectory()`, `classify_gps_segments()` |
| `analysis/detection.py` | `detectar_tramos()`, `detectar_200m()` |
| `analysis/strokes.py` | `detectar_paladas()`, `detectar_picos()` |
| `analysis/metrics.py` | `analizar_tramo()`, `analizar_200m()`, `calcular_pitch()` |
| `analysis/_utils.py` | `calcular_sectores()`, `resumen_paladas()`, `format_duration()` |
| `analysis/report.py` | `generar_informe_str()`, `generar_resumen_sesion()`, `nombre_base()`, `imprimir_metricas()` |
| `visualization/charts.py` | `graficar_200m()` (PNG con matplotlib) |
| `tools/backfill_sectores_paladas.py` | Backfill `sectores_detalle` + `paladas_detalle` |
| `repo.py` | `crear_csv_upload()`, `crear_gps_data()`, `crear_prueba()`, `recalc_sesion_aggregates()`, etc. |
| `templates/informes.html` | UI de upload + reportes con paginación |
| `templates/test.html` | Visualización de gráficas (ECharts + PNG) |
| `static/vendor/echarts.min.js` | ECharts library (vendored, sin CDN) |
