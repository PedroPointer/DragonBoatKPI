# Especificación: API Endpoints

Todos los endpoints HTTP del proyecto. HTML routes y JSON API.

---

## 1. HTML Routes (Server-Side Rendering)

### Home

| Método | Ruta | Descripción | Template |
|--------|------|-------------|----------|
| GET | `/` | Home con rankings + sesiones incompletas | `home.html` |

**Context:**
```json
{
  "rankings": {"200": [...], "500": [...], ...},
  "distancias_validas": [200, 500, 1000, 2000],
  "incomplete": [{"sesion": {...}, "warnings": [...]}],
  "active_nav": "home"
}
```

---

### Registros

| Método | Ruta | Descripción | Template |
|--------|------|-------------|----------|
| GET | `/registros` | Lista pruebas del día + calendario | `registros.html` |
| GET | `/registros/dias` | Días con entrenamientos (JSON) | JSON |
| POST | `/registros/new` | Crear prueba manual | redirect |
| GET | `/sesion/{id}` | Vista de sesión diaria (métricas generales) | `sesion.html` |
| POST | `/sesion/{id}` | Actualizar tipo/categoría de la sesión | redirect |
| POST | `/sesion/{id}/delete` | Eliminar sesión completa (cascade) | redirect |
| POST | `/sesion/{id}/recalcular` | Recalcular agregados de la sesión | redirect |
| POST | `/test/{id}` | Actualizar prueba | redirect |
| POST | `/test/{id}/delete` | Eliminar prueba | redirect |
| GET | `/test/{id}` | Detalle de prueba | `test.html` |
| GET | `/test/{id}/trajectory` | Puntos GPS para mapa (con velocidades) | JSON |
| GET | `/test/{id}/chart-data` | JSON para gráfica ECharts interactiva | JSON |
| GET | `/test/{id}/chart.png` | Descarga PNG gráfica | image/png |

**GET /registros — query params:**
- `dia` (int): día del mes
- `mes` (int): mes (1-12)
- `anio` (int): año
- `tipo` (str): filtro por tipo
- `barco` (str): filtro por barco

**GET /registros/dias — query params:**
- `year` (int): año
- `month` (int): mes (1-12)

**Respuesta:**
```json
{"dias": [1, 15, 22], "dias_competicion": [22]}
```

**POST /registros/new — form data:**
- `custom_name` (str): nombre de la prueba
- `fecha` (str): fecha ISO
- `distancia` (int): 200/500/1000/2000
- `boat_id` (int): ID del barco
- `tiempo` (str): tiempo en segundos o MM:SS
- `categoria` (str): categoría
- `tipo` (str): tipo de prueba

**POST /test/{id} — form data:**
- `custom_name` (str): nombre
- `categoria` (str): categoría
- `boat_id` (int): barco
- `tipo` (str): tipo
- `distancia` (int): distancia

**GET /test/{id}/trajectory — respuesta:**
```json
{
  "points": [[38.881733, -6.980930, 2.47], [38.881734, -6.980928, 2.55]],
  "center": [38.8818, -6.9809],
  "gps_inicio": {"lat": 38.8817, "lon": -6.9809},
  "gps_fin": {"lat": 38.8820, "lon": -6.9812}
}
```

- `points` es array de `[lat, lon, speed]` — decimado a 5Hz
- El frontend usa `speed` para colorear la polilínea por velocidad (gradiente 0→15 km/h)
- `center` es el centroide del mapa o null si no hay datos

**GET /test/{id}/chart-data — respuesta:**
```json
{
  "time": [0.0, 0.04, 0.08, ...],
  "speed": [2.47, 2.55, 2.62, ...],
  "lean": [0.1, 0.2, 0.15, ...],
  "pitch": [0.0, 0.1, 0.2, ...],
  "time_start": 0.0,
  "time_end": 18.7,
  "tiempo_total": 18.7,
  "velocidad_media": 28.5,
  "velocidad_maxima": 32.1,
  "tiempo_12kmh": 3.2,
  "peak_times": [3.24, 4.12, 5.08, ...],
  "peak_speeds": [14.2, 15.1, 14.8, ...],
  "valley_times": [2.91, 3.72, 4.65, ...],
  "dist_por_palada": [2.50, 2.72, 2.61, ...],
  "tiempos_por_distancia": {"50": 4.5, "100": 9.2, "150": 14.1},
  "dist_media_palada": 4.2,
  "num_paladas": 45
}
```

- `time/speed/lean/pitch` son series 25Hz (relativas al inicio del segmento, incluyendo 2s previos)
- `pitch` se calcula server-side con `calcular_pitch(gforce_x, gforce_z)`
- Si la fila no tiene `gps_data` completo, devuelve 404 `{"error": "no segment data"}`
- Si el GPS está corrupto, devuelve 404 `{"error": "corrupt segment data"}`

**GET /test/{id}/chart.png — respuesta:** image/png

---

### Sesiones diarias

| Método | Ruta | Descripción | Template |
|--------|------|-------------|----------|
| GET | `/sesion/{id}` | Vista de sesión diaria con métricas generales | `sesion.html` |
| POST | `/sesion/{id}` | Actualizar sesión (categoria, tipo) | redirect |
| POST | `/sesion/{id}/delete` | Eliminar sesión completa (cascade) | redirect |
| POST | `/sesion/{id}/recalcular` | Recalcular agregados | redirect |

**GET /sesion/{id} — context:**
```json
{
  "sesion": {
    "id": 1,
    "fecha": "2026-06-15",
    "categoria": "Open Sénior",
    "tipo": "entreno",
    "num_pruebas": 6,
    "num_archivos": 1,
    "distancia_total_nominal": 1200,
    "distancia_total_real": 1198.5,
    "tiempo_total_entreno": 1800.5,
    "tiempo_parado": 300.2,
    "tiempo_movimiento": 1500.3,
    "vel_media_movimiento": 8.5,
    "vel_max_dia": 32.1,
    "ritmo_medio": 7.06
  },
  "pruebas": [...],
  "csv_uploads": [...],
  "categorias": [...],
  "tipos": [...],
  "active_nav": "registros"
}
```

**GET /test/{id} — context (test.html):**
```json
{
  "test": { ... TestMetric ORM ... },
  "chart_available": true,
  "has_gps": true,
  "boat": { ... Boat ORM ... },
  "boats": [...],
  "names": [...],
  "categorias": ["Open Sénior", ...],
  "tipos": [{name: "Entreno"}, ...],
  "crew_json": "[{id, nombre, apellido, categoria, photo_path, freq}, ...]",
  "assignments_json": "[{crew_member_id, role, side, row_number}, ...]",
  "sectores": [{"from": 0, "to": 50, "t_sector": 4.5, "t_acum": 4.5, "vel": 12.0}, ...],
  "paladas_resumen": {"max_all": 5.1, "min_salida": 2.1, "min_sin10": 3.1},
  "active_nav": "registros"
}
```

- `sectores` se calcula con `calcular_sectores(tpd, distancia)` y divide la distancia en 4 splits iguales (D/4)
- `paladas_resumen` se calcula con `resumen_paladas(paladas_detalle)` y devuelve max/min globales y sin las 10 primeras
- `crew_json` se ordena por frecuencia de uso (los más usados primero)

---

### Informes

| Método | Ruta | Descripción | Template |
|--------|------|-------------|----------|
| GET | `/informes` | Página de informes | `informes.html` |
| POST | `/informes/upload` | Subir CSV | redirect/JSON |
| POST | `/informes/upload?overwrite=1` | Reemplazar CSV duplicado | redirect |
| POST | `/informes/generate` | Generar informe .txt | redirect |
| POST | `/informes/eliminar-upload/{id}` | Eliminar upload + cascade | JSON |
| GET | `/informes/reporte/{filename}` | Ver reporte (JSON) | JSON |
| GET | `/informes/reporte/{filename}/download` | Descargar reporte .txt | text/plain |
| GET | `/informes/download-csvs` | Descargar todos CSVs (ZIP) | application/zip |

**GET /informes — query params:**
- `pagina` (int): página (default 1, 15 por página)

**POST /informes/upload — form data:**
- `file` (UploadFile): archivo CSV

**POST /informes/generate — form data:**
- `sesion_id` (int): ID de la sesión

**POST /informes/eliminar-upload/{id} — respuesta:**
```json
{"ok": true}
```

**GET /informes/reporte/{filename} — respuesta:**
```json
{"filename": "Informe_15jun.txt", "content": "..."}
```

---

### Deportistas

| Método | Ruta | Descripción | Template |
|--------|------|-------------|----------|
| GET | `/deportistas` | Lista de tripulantes | `deportistas.html` |
| POST | `/deportistas/add` | Agregar tripulante | redirect |
| POST | `/deportistas/{id}/edit` | Editar tripulante | redirect |
| POST | `/deportistas/{id}/delete` | Eliminar tripulante | redirect |
| POST | `/deportistas/import` | Importar CSV masivo | redirect |
| GET | `/test/{id}/crew` | Redirect a `/test/{id}#tripulacion` | redirect |
| POST | `/test/{id}/crew` | Guardar asignaciones (form) | redirect |
| POST | `/test/{id}/crew/json` | Guardar asignaciones (JSON) | JSON |

**POST /deportistas/add — form data:**
- `nombre` (str): nombre
- `apellido` (str): apellido
- `categoria` (str): categoría (opcional)
- `photo` (UploadFile): foto (opcional)

**POST /deportistas/{id}/edit — form data:** (iguales que add)

**POST /deportistas/import — form data:**
- `file` (UploadFile): CSV con columnas `nombre`, `apellido`, `categoria`

**POST /test/{id}/crew/json — body:**
```json
{
  "assignments": [
    {"crew_member_id": 1, "role": "remero", "side": "estribor", "row_number": 1},
    {"crew_member_id": 2, "role": "tambor", "side": null, "row_number": null}
  ]
}
```

**Respuesta:**
```json
{"ok": true}
```

---

### Configuración

| Método | Ruta | Descripción | Template |
|--------|------|-------------|----------|
| GET | `/config` | Menú principal | `config.html` |
| GET | `/config/barcos` | CRUD barcos | `config.html` |
| POST | `/config/barcos` | Crear barco | redirect |
| POST | `/config/barcos/{id}/delete` | Eliminar barco | redirect |
| GET | `/config/categorias` | CRUD categorías | `config.html` |
| POST | `/config/categorias` | Crear categoría | redirect |
| POST | `/config/categorias/{id}/edit` | Editar categoría | redirect |
| POST | `/config/categorias/{id}/delete` | Eliminar categoría | redirect |
| GET | `/config/tipos` | CRUD tipos | `config.html` |
| POST | `/config/tipos` | Crear tipo | redirect |
| POST | `/config/tipos/{id}/edit` | Editar tipo | redirect |
| POST | `/config/tipos/{id}/delete` | Eliminar tipo | redirect |
| GET | `/config/distancias` | CRUD distancias | `config.html` |
| POST | `/config/distancias` | Crear distancia | redirect |
| POST | `/config/distancias/{id}/edit` | Editar distancia | redirect |
| POST | `/config/distancias/{id}/delete` | Eliminar distancia | redirect |
| GET | `/config/umbral` | Configurar umbral | `config.html` |
| POST | `/config/umbral` | Guardar umbral | redirect |
| GET | `/config/telegram` | Configurar Telegram | `config.html` |

**POST /config/barcos — form data:**
- `name` (str): nombre único (ej: "DB12")
- `display_name` (str): nombre display (ej: "Dragon Boat 12 personas")
- `num_rows` (int): número de filas
- `total_persons` (int): total de personas

**POST /config/categorias — form data:**
- `name` (str): nombre único

**POST /config/tipos — form data:**
- `name` (str): nombre único

**POST /config/distancias — form data:**
- `metros` (int): metros (único)
- `descripcion` (str): descripción
- `orden` (int): orden de visualización

**POST /config/umbral — form data:**
- `umbral` (float): velocidad parado (0.5 - 20.0 km/h)

---

## 2. JSON API Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/ranking` | Top 20 tiempos |
| GET | `/api/boat-stats` | Estadísticas por barco |
| GET | `/api/sesiones` | Sesiones diarias |
| GET | `/api/pruebas` | Pruebas (filtrables) |

### GET /api/ranking

**Respuesta:**
```json
[
  {
    "id": 1,
    "nombre": "Ana García",
    "barco": "DB12",
    "categoria": "Open Sénior",
    "tiempo": 42.30,
    "velocidad_media": 28.5,
    "num_paladas": 45,
    "dist_media_palada": 4.2,
    "fecha": "2026-06-15"
  }
]
```

### GET /api/boat-stats

**Respuesta:**
```json
[
  {
    "boat": "DB12",
    "num_pruebas": 15,
    "mejor_tiempo": 42.30,
    "tiempo_promedio": 45.20,
    "vel_media": 28.5,
    "paladas_prom": 45,
    "dist_palada_prom": 4.2
  }
]
```

### GET /api/sesiones

**Respuesta:**
```json
[
  {
    "id": 1,
    "fecha": "2026-06-15",
    "categoria": "Open Sénior",
    "tipo": "entreno",
    "num_pruebas": 6,
    "num_archivos": 1,
    "distancia_total_nominal": 1200,
    "tiempo_total_entreno": 1800.5,
    "tiempo_parado": 300.2,
    "tiempo_movimiento": 1500.3,
    "vel_media_movimiento": 8.5,
    "vel_max_dia": 32.1
  }
]
```

### GET /api/pruebas

**Query params:**
- `sesion_id` (int): filtrar por sesión
- `limit` (int): límite (default 100)

**Respuesta:**
```json
[
  {
    "id": 1,
    "sesion_id": 1,
    "fecha_hora": "2026-06-15T10:30:00",
    "custom_name": "Prueba #1",
    "distancia": 200,
    "tiempo_total": 42.30,
    "velocidad_media": 28.5,
    "boat_name": "DB12"
  }
]
```

---

## 3. Errores comunes

| Código | Descripción |
|--------|-------------|
| 302 | Redirect (operación exitosa) |
| 400 | CSV inválido, datos faltantes |
| 404 | Recurso no encontrado |
| 500 | Error interno del servidor |

Los errores HTML se renderizan en el mismo template con variable `error`.
Los errores JSON retornan `{"error": "mensaje"}`.
