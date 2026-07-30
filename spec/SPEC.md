# Dragon Boat Analyzer — Especificación del Proyecto

## 1. Visión General

Aplicación web de gestión deportiva para el deporte barco dragón.
Analiza rendimiento en tramos de distancia variable (200m, 500m, 1000m, 2000m) desde datos GPS (RaceBox Drag),
gestiona tripulaciones y genera rankings y documentación de competiciones.

**Stack tecnológico:**
- Backend: Python 3.12 + FastAPI + Jinja2
- Base de datos: SQLite (WAL mode) + SQLAlchemy 2.0 ORM
- Frontend: HTML + CSS (base.css compartido) + vanilla JS + jQuery
- Visualización: ECharts (gráficas web interactivas, vendored local),
  Leaflet.js (mapa GPS con mapa de segmentos),
  matplotlib (gráficas PNG/impresión),
  SVG (diagrama de barco)
- Procesamiento de datos: pandas, numpy, scipy

**Objetivos:**
1. Análisis automático de tramos desde CSV RaceBox Drag (200m, 500m, 1000m, 2000m)
2. Gestión de tripulaciones con fotos y categorías
3. Rankings y estadísticas por barco y por distancia
4. Generación de documentación para competiciones
5. Configuración flexible de barcos, categorías, tipos y notificaciones

---

## 2. Navegación — Bottom Nav Bar

```
┌──────┬──────────┬──────────┬────────────┬──────────┐
│ Home │Registros │Informes  │Deportistas │    ⚙️    │
└──────┴──────────┴──────────┴────────────┴──────────┘
```

- 5 items fijos en la parte inferior de la pantalla
- Mobile-first: diseño optimizado para pantallas pequeñas
- Item activo: resaltado con color accent (#38bdf8)
- Icono + texto corto para cada item
- La sección ⚙️ (Configuración) abre un sub-menú o página dedicada
- "Home" muestra rankings y resumen de sesiones incompletas

---

## 3. Dashboard (Home — GET /)

Página principal de la aplicación. Muestra un resumen del estado actual.

**Contenido:**

- **Rankings por distancia**: tablas con los mejores tiempos agrupados por distancia (200m, 500m, 1000m, 2000m)
  - Top-5 por distancia con colores por podium: oro (#1), plata (#2), bronce (#3)
  - Columnas: #, nombre, barco, categoría, tiempo, vel. media, paladas, dist/palada, fecha
  - Click en fila → navega a `/test/{r.prueba_id}` (detalle de prueba)
  - Cada distancia tiene su propia sección colapsable con header expandible

- **Estadísticas por barco**: tarjetas con métricas agregadas
  - Número de pruebas, mejor tiempo, tiempo promedio
  - Velocidad media, paladas promedio, distancia/palada promedio
  - Badge de color por barco (DB12 verde, DB22 naranja)
  - `worst_tiempo` se calcula pero NO se muestra en el dashboard

- **Por completar**: tarjetas de **sesiones** (no pruebas individuales) con warnings
  - Cada sesión tiene: nombre = "Sesión dd/MM/YYYY", num_pruebas, num_archivos
  - Warning de tripulación: icono muñeco paleando tachado + "falta asignar tripulación"
    (cuando no hay ningún remero asignado en ninguna prueba del día)
  - Warning de timonel: icono de timón tachado + "falta timonel"
    (cuando no hay timonel en ninguna prueba del día)
  - Link "Ver" → navega a `/registros?dia=X&mes=Y&anio=Z` (filtra por día)

**Template:** `home.html` (no `dashboard.html`)

---

## 4. Registros (GET /registros)

> **⚠️ Especificación completa en `spec/registros-detalle.md`**
> Secciones: calendario mensual, tabla DataTables, detalle de test (7 bloques).

### 4.0 Concepto clave: prueba = sesión

**Una "prueba" ES una sesión.** No existe un concepto separado de "sesión" que agrupa pruebas.

- Al subir un CSV, se parte en **pruebas** (tramos). Cada prueba es la unidad atómica.
- Las pruebas se agrupan visualmente **por día** y se ordenan **por hora de ejecución** dentro del día.
- El CSV es solo la **vía de importación** y la **fuente de procedencia**. Los datos originales pueden borrarse manteniendo el registro de procedencia en la tabla `csv_uploads`.
- Una "sesión" y una "prueba" son lo mismo. El código usa `Sesion` como nombre de clase/tabla.

### 4.1 Distancia

Cada prueba tiene un campo `distancia` que indica la distancia del tramo:
- Valores: 200, 500, 1000, 2000 (metros)
- Default: 200
- Se usa para filtrar rankings por distancia y agrupar tramos en informes
- Se muestra como badge en la tabla de registros

### 4.2 Crear prueba manual (POST /registros/new)

Formulario para crear pruebas sin subir CSV:
- **Nombre**: auto-generado como "Prueba #N dd/MM/AAAA"
- **Tipo**: select de `test_types` (entreno / competición)
- **Barco**: select de `boats`
- **Distancia**: select (200 / 500 / 1000 / 2000)
- **Categoría**: select de `categories` (solo visible si tipo = "competición")

### 4.3 Filtros
- Tipo: entreno / competición / todos (select de `test_types`)
- Barco: DB12 / DB22 / todos
- Fecha: rango de fechas
- Categoría: selector de categorías disponibles
- Distancia: 200 / 500 / 1000 / 2000 / todos

### 4.4 Cada prueba muestra (en la tabla)
- Número, nombre, tipo, barco, distancia, tiempo, categoría, fecha, hora
- Botón **Eliminar** con confirmación: "¿Eliminar esta prueba?"

### 4.5 Edición de prueba
- **Nombre**: predefinido como "Prueba #N dd/MM/AAAA" (N = conteo de pruebas de ese día, en orden cronológico por fecha_hora)
- **Tipo**: select de `test_types` (entreno / competición)
- **Barco**: select de `boats`
- **Distancia**: select (200 / 500 / 1000 / 2000)
- **Categoría**: selector (solo visible si tipo = "competición")
- Formulario siempre visible (no `<details>` colapsable)

### 4.6 TestTypes — Tipos de prueba dinámicos

Tabla `test_types` (CRUD desde config):
- **Entreno**: tipo por defecto
- **Competición**: para pruebas de competencia

CRUD desde `GET /config/tipos`:
- Crear nuevo tipo
- Editar nombre
- Eliminar tipo (con verificación de uso en sesiones)

### 4.7 Detalle de prueba (GET /test/{id})

> **⚠️ Especificación completa en `spec/registros-detalle.md` sección 4**
> 7 bloques: breadcrumb + métricas + editar + gráfica interactiva + mapa GPS + datos + tripulación inline.

- Métricas: vel. max, vel. media, 0→12 km/h, paladas, dist/palada, consistencia
- Editar prueba: nombre, barco, distancia, tipo, categoría (siempre visible)
- Gráfica: ECharts interactivo con toggle PNG ↔ ECharts, panel checkboxes (Velocidad, Balanceo, Cabeceo, Dist/palada), overlay Nº palada, expand/collapse, reset zoom
- Mapa GPS Leaflet con trayectoria coloreada por velocidad + legend
- Datos generales: secciones (Tiempos por sector con 4 splits D/4, Velocidad, Paladas)
- Tripulación: SVG lateral interactivo con click-to-assign y type-ahead (inline, no página separada)
- Eliminar prueba: botón con confirmación, cascade delete
- Sesión diaria: link desde breadcrumb a `sesion.html` con métricas generales del día

### 4.8 Eliminar prueba (POST /registros/{id}/delete)
- Popup de confirmación: "¿Eliminar esta prueba?"
- Borra la prueba, su métrica y sus asignaciones de tripulación (cascade).
- Si era la última prueba de su `csv_upload` padre, el `csv_upload` también se borra (y el archivo en disco si `kept=True`).

---

## 5. Informes (GET /informes)

Tres acciones principales: upload CSV, ver reportes existentes y eliminar uploads.

### 5.1 Subir CSV (POST /informes/upload)

- Zona de drag & drop para archivos CSV RaceBox Drag
- Validación: extensión .csv, formato correcto
- Proceso:
  1. Lee CSV con pandas
  2. Detecta tramos por distancia (200m, 500m, 1000m, 2000m) según análisis de gradiente
  3. Detecta paladas (picos de velocidad)
  4. Calcula métricas por tramo
  5. Filtra tramos válidos (tiempo < 85s, t11kmh < 20s, vel media > 9 km/h)
  6. Guarda en DB: sesión + tests + métricas + GPS raw (test_gps_data)
  7. Genera gráficas PNG (4 paneles por test)
  8. Redirige a la página de informes
- Feedback de errores: mensaje claro si falla la validación

### 5.2 Reemplazar CSV duplicado (POST /informes/upload?overwrite=1)

- Si el CSV ya existe (mismo filename): ofrece reemplazar
- Borra la sesión anterior y crea la nueva
- Se pasa `overwrite=1` como query param

### 5.3 Ver reportes existentes

- Lista de reportes generados con paginación (`?pagina=1`, 15 por página)
- Cada reporte muestra: nombre, fecha, conteo de pruebas
- Botón "Ver" abre el reporte en un visor AJAX (modal o inline)
- Botón "Descargar" descarga el archivo .txt

**Resumen de la página de informes:**
- `report_filename`: nombre del último reporte generado
- `conteo_distancias`: dict con conteo de pruebas por distancia
- `distancias_validas`: lista de distancias que tienen pruebas en la DB

### 5.4 Eliminar upload (POST /informes/eliminar-upload/{csv_id})

- Elimina el csv_upload y cascade: sesiones, métricas, assignments, archivos GPS
- Si `csv_upload.kept=True`, elimina el archivo en disco
- Redirige a `GET /informes`

### 5.5 Generar documentación (POST /informes/generate)

- Selector de sesiones tipo "competición"
- Genera documento descargable (.txt) con:
  - Datos por barco
  - Tripulación asignada por posición
  - Datos del barco (nombre, tipo, número de personas)
- El documento se genera en el servidor y se descarga como archivo

---

## 6. Deportistas (GET /deportistas)

Gestión CRUD de los miembros de la tripulación.

**Campos por deportista:**
- Nombre (obligatorio)
- Apellido (obligatorio)
- Categoría (opcional): selector de categorías
- Foto (opcional): subida de imagen, resize a WebP 40x40px
  - Default: placeholder con iniciales del nombre y apellido

**Funcionalidades:**
- **Alta individual**: formulario con nombre, apellido, categoría, foto
- **Importación masiva**: CSV con columnas `nombre`, `apellido`, `categoria` (opcional)
- **Edición inline**: click en fila para editar (POST /deportistas/{id}/edit)
- **Eliminación**: botón con confirmación (onsubmit confirm)
- **Listado**: tabla con foto, nombre, apellido, categoría, acciones

**Endpoint de edición:**
- `POST /deportistas/{id}/edit`: actualiza nombre, apellido, categoría
- Redirige a `GET /deportistas` (302)

---

## 7. Configuración (GET /config) — ⚙️

Menú de configuración de la aplicación. Accesible desde el icono de ruedita dentada en el bottom nav.

### 7.1 Gestión de barcos (/config/barcos)

CRUD de embarcaciones. Actualmente pre-cargados DB12 y DB22.

**Campos por barco:**
- Nombre (ej: DB12, DB22) — único
- Nombre display (ej: "Dragon Boat 12 personas")
- Número de filas (5 para DB12, 10 para DB22)
- Total de personas (12 para DB12, 22 para DB22)

**Funcionalidades:**
- Crear nuevo barco
- Editar barco existente
- Eliminar barco (con verificación de uso en sesiones/tests)

### 7.2 Categorías (/config/categorias)

CRUD dinámico de categorías de competición. Reemplaza la lista hardcodeada actual.

**Tabla `categories` (nueva):**
- id (PK)
- name (único, ej: "Open Sénior", "Mixto Veterano")
- created_at

**Funcionalidades:**
- Añadir categoría
- Editar nombre
- Eliminar categoría (con verificación de uso en tests)
- Las categorías se usan en: selector de tipo "competición" de tests

**Categorías iniciales (seed):**
1. Open Sénior
2. Open Veterano
3. Femenino Sénior
4. Femenino Veterano
5. Mixto Sénior
6. Mixto Veterano
7. ACS
8. PD1
9. PD2
10. PD3

### 7.3 Tipos de prueba (/config/tipos)

CRUD dinámico de tipos de prueba. Reemplaza la lista hardcodeada "entreno"/"competición".

**Tabla `test_types`:**
- id (PK)
- name (único, ej: "Entreno", "Competición")
- created_at

**Funcionalidades:**
- Crear nuevo tipo
- Editar nombre
- Eliminar tipo (con verificación de uso en sesiones)
- Los tipos se usan en: selector de tipo de cada prueba

**Tipos iniciales (seed):**
1. Entreno
2. Competición

### 7.4 Telegram bot (/config/telegram)

Configuración de notificaciones por Telegram.

**Campos:**
- Habilitado: toggle on/off
- Token del bot de Telegram
- Chat ID destino

**Comportamiento:**
- Si habilitado: envía notificación al subir CSV con resumen de tiempos
- Si deshabilitado: stub que imprime en consola (comportamiento actual)

---

## 8. Modelo de Datos

### Concepto clave

**Una "prueba" ES una "sesión".** No existe un concepto separado. El CSV es solo vía de importación y procedencia. Los datos originales pueden borrarse manteniendo el registro en `csv_uploads`.

### Diagrama relacional

```
sesiones (día = sesión de entreno)
  ├─ csv_uploads (1:N) ─ un registro por CSV subido
  │    └─ gps_data (1:1) ─ GPS completo del CSV (25Hz)
  │         └─ test_metrics (0:N) ─ pruebas derivadas
  ├─ test_metrics (1:N) ─ pruebas del día
  │    ├─ crew_assignments (1:N) ─ tripulación de la prueba
  │    └─ gps_data (0..1, FK) ─ GPS del que sale esta prueba
  └─ gps_data (1:N) ─ para queries rápidas por día

boats (referencia)
categories (CRUD dinámico)
test_types (CRUD dinámico)
distancias (catálogo: 200/500/1000/2000m)
app_settings (key-value: umbral_velocidad_parado)
```

### Tablas

**app_settings (key-value config)**
| Campo | Tipo | Constraints |
|-------|------|-------------|
| key | VARCHAR(64) | PK |
| value | VARCHAR(255) | NOT NULL |
| updated_at | DATETIME | DEFAULT now |

**distancias (catálogo de distancias)**
| Campo | Tipo | Constraints |
|-------|------|-------------|
| id | INTEGER | PK |
| metros | INTEGER | UNIQUE, NOT NULL |
| descripcion | VARCHAR(50) | NOT NULL |
| orden | INTEGER | NOT NULL, default 0 |

**boats**
| Campo | Tipo | Constraints |
|-------|------|-------------|
| id | INTEGER | PK |
| name | VARCHAR(10) | UNIQUE |
| display_name | VARCHAR(50) | |
| num_rows | INTEGER | |
| total_persons | INTEGER | |

**categories (CRUD dinámico)**
| Campo | Tipo | Constraints |
|-------|------|-------------|
| id | INTEGER | PK |
| name | VARCHAR(100) | UNIQUE |
| created_at | DATETIME | DEFAULT now |

**test_types (CRUD dinámico)**
| Campo | Tipo | Constraints |
|-------|------|-------------|
| id | INTEGER | PK |
| name | VARCHAR(20) | UNIQUE |
| created_at | DATETIME | DEFAULT now |

**sesiones (un día = una sesión de entreno)**
| Campo | Tipo | Constraints |
|-------|------|-------------|
| id | INTEGER | PK |
| fecha | DATE | nullable |
| categoria | VARCHAR(50) | nullable |
| tipo | VARCHAR(20) | nullable |
| distancia_total_nominal | INTEGER | default 0 |
| distancia_total_real | FLOAT | default 0.0 |
| num_pruebas | INTEGER | default 0 |
| num_archivos | INTEGER | default 0 |
| tiempo_total_entreno | FLOAT | nullable |
| tiempo_parado | FLOAT | nullable |
| tiempo_movimiento | FLOAT | nullable |
| vel_media_movimiento | FLOAT | nullable |
| vel_max_dia | FLOAT | nullable |
| ritmo_medio | FLOAT | nullable |

**csv_uploads (procedencia del GPS)**
| Campo | Tipo | Constraints |
|-------|------|-------------|
| id | INTEGER | PK |
| filename | VARCHAR(255) | UNIQUE |
| uploaded_at | DATETIME | DEFAULT now |
| file_path | VARCHAR(255) | nullable, path en data/input/ |
| kept | BOOLEAN | DEFAULT true, si el archivo sigue en disco |
| metadata_date | DATETIME | nullable |
| sesion_id | INTEGER | FK → sesiones.id, NOT NULL |

**gps_data (GPS completo 25Hz de un CSV)**
| Campo | Tipo | Constraints |
|-------|------|-------------|
| id | INTEGER | PK |
| csv_upload_id | INTEGER | FK → csv_uploads.id, ondelete=CASCADE, UNIQUE |
| sesion_id | INTEGER | FK → sesiones.id, NOT NULL |
| data_json | TEXT | JSON con arrays (time, speed, lat, lon, lean, gforce_x, gforce_z) |
| created_at | DATETIME | DEFAULT now |

**test_metrics (una prueba = un tramo)**
| Campo | Tipo | Constraints |
|-------|------|-------------|
| id | INTEGER | PK |
| sesion_id | INTEGER | FK → sesiones.id, NOT NULL |
| csv_upload_id | INTEGER | FK → csv_uploads.id, nullable |
| gps_data_id | INTEGER | FK → gps_data.id, ondelete=SET NULL, nullable |
| fecha_hora | DATETIME | DEFAULT now, momento de ejecución |
| test_number | INTEGER | nullable, orden dentro del CSV |
| custom_name | VARCHAR(100) | nullable |
| distancia_id | INTEGER | FK → distancias.id, NOT NULL |
| boat_id | INTEGER | FK → boats.id, nullable |
| tipo_id | INTEGER | FK → test_types.id, nullable |
| categoria_id | INTEGER | FK → categories.id, nullable |
| chart_filename | VARCHAR(255) | nullable |
| gps_inicio | TEXT | nullable, JSON {lat, lon, t} |
| gps_fin | TEXT | nullable, JSON {lat, lon, t} |
| tiempos_por_distancia | TEXT | nullable, JSON con tiempos por marcador D/4 |
| segment_gps_json | TEXT | nullable, JSON 25Hz del tramo (time, speed, lean, gforce_x, gforce_z, lat, lon, peak_times, peak_speeds, valley_times, dist_por_palada) |
| sectores_detalle | TEXT | nullable, JSON con sectores calculados (from, to, t_sector, t_acum, vel) |
| paladas_detalle | TEXT | nullable, JSON array con dist_por_palada expandido |
| tiempo_total | FLOAT | NOT NULL |
| velocidad_media | FLOAT | NOT NULL |
| velocidad_maxima | FLOAT | NOT NULL |
| velocidad_min_post10 | FLOAT | nullable |
| aceleracion_max | FLOAT | NOT NULL |
| tiempo_12kmh | FLOAT | nullable |
| num_paladas | INTEGER | NOT NULL |
| dist_media_palada | FLOAT | NOT NULL |
| dist_std_palada | FLOAT | NOT NULL |
| dist_max_palada | FLOAT | nullable |
| dist_min_palada | FLOAT | nullable |

**crew_members**
| Campo | Tipo | Constraints |
|-------|------|-------------|
| id | INTEGER | PK |
| nombre | VARCHAR(100) | |
| apellido | VARCHAR(100) | |
| categoria | VARCHAR(50) | nullable |
| photo_path | VARCHAR(255) | nullable |
| created_at | DATETIME | DEFAULT now |

**crew_assignments**
| Campo | Tipo | Constraints |
|-------|------|-------------|
| id | INTEGER | PK |
| test_metric_id | INTEGER | FK → test_metrics.id, ondelete=CASCADE |
| crew_member_id | INTEGER | FK → crew_members.id |
| role | VARCHAR(20) | "tambor" / "remero" / "timonel" |
| side | VARCHAR(10) | nullable, "estribor" / "babor" |
| row_number | INTEGER | nullable, 1..10 |
| | | UNIQUE(test_metric_id, role, side, row_number) |

### Reglas de campos por prueba

| Campo | Default | Obligatorio | Warning si vacío |
|-------|---------|-------------|------------------|
| Barco | DB12 | Sí (default siempre presente) | No |
| Tipo | "entreno" | Sí (default siempre presente) | No |
| Nombre | "Prueba #N dd/MM/AAAA" | Sí (default siempre presente) | No |
| Distancia | 200 | Sí (default siempre presente) | No |
| Palistas (10 DB12 / 20 DB22) | — | No | SÍ: muñeco paleando tachado, "falta asignar tripulación" |
| Timonel | — | No | SÍ: icono de timón tachado, "falta timonel" |
| Tambor | — | No | No |
| Categoría (solo competición) | — | No | Sí si competición, No si entreno |

**Notas:**
- N en "Prueba #N" = conteo de pruebas de ese día en orden cronológico por `fecha_hora` (no el test_number)
- El default de nombre se genera al crear la prueba, no al mostrarlo
- Si el usuario cambia el nombre, se respeta su cambio
- Los warnings se muestran en el Dashboard (sección 3) y en Registros (sección 4)
- Al borrar la última prueba de un `csv_upload`, el `csv_upload` también se borra (y el archivo si `kept=True`)
- Al subir un CSV duplicado (mismo `filename`), se ofrece reemplazar: borrar la sesión anterior y crear la nueva
- `test_types` es una tabla CRUD: los tipos se gestionan desde `/config/tipos`, no están hardcodeados
- `distancia` soporta 200, 500, 1000, 2000 metros; default 200
- `tiempos_por_distancia` es un JSON con los tiempos por tramo (ej: `{"50m": 4.5, "100m": 9.2, "150m": 14.1, "200m": 18.7}`)
- `test_gps_data.sesion_id` tiene `ondelete=CASCADE` para borrar GPS si se borra la sesión

---

## 9. Rutas Web (Refactor)

### Mapa old → new

| Ruta vieja | Ruta nueva | Acción |
|------------|------------|--------|
| GET / | GET / | Home (rankings por distancia + sesiones incompletas) |
| GET / | GET /registros | Lista de sesiones con calendario |
| POST /upload | POST /informes/upload | Se mueve a Informes |
| GET /session/{id} | GET /test/{id} | Redirige (prueba = sesión) |
| POST /session/{id} | POST /test/{id} | Actualiza campos de la prueba |
| — | POST /registros/new | **NUEVA**: crea prueba manual sin CSV |
| — | POST /test/{id}/delete | **NUEVA**: elimina una prueba con confirmación |
| — | GET /sesion/{id} | **NUEVA**: vista de sesión diaria (métricas generales) |
| — | POST /sesion/{id} | **NUEVA**: actualizar tipo/categoría de la sesión |
| — | POST /sesion/{id}/delete | **NUEVA**: eliminar sesión completa (cascade) |
| — | POST /sesion/{id}/recalcular | **NUEVA**: recalcular agregados |
| GET /dashboard | — | Se elimina, contenido va a GET / |
| GET /crew | GET /deportistas | Se renombra |
| POST /crew/add | POST /deportistas/add | Se renombra |
| POST /crew/import | POST /deportistas/import | Se renombra |
| POST /crew/{id}/delete | POST /deportistas/{id}/delete | Se mantiene POST |
| — | POST /deportistas/{id}/edit | **NUEVA**: edición inline |
| GET /test/{id} | GET /test/{id} | Detalle de prueba (se mantiene) |
| POST /test/{id} | POST /test/{id} | Actualiza prueba (se mantiene) |
| GET /test/{id}/crew | GET /test/{id}/crew | Se mantiene |
| POST /test/{id}/crew | POST /test/{id}/crew | Se mantiene (legacy form) |
| — | POST /test/{id}/crew/json | **NUEVA**: guardar asignaciones JSON |
| — | GET /test/{id}/trajectory | **NUEVA**: puntos GPS para mapa Leaflet (con velocidades) |
| — | GET /test/{id}/chart-data | **NUEVA**: JSON para gráfica ECharts interactiva |
| — | GET /test/{id}/chart.png | **NUEVA**: descarga PNG de la gráfica |
| — | GET /informes | Nueva página de informes |
| — | POST /informes/upload?overwrite=1 | **NUEVA**: reemplaza CSV duplicado |
| — | POST /informes/generate | Nueva: generar documentación |
| — | POST /informes/eliminar-upload/{csv_id} | **NUEVA**: cascade delete de upload |
| — | GET /informes/reporte/{filename} | **NUEVA**: visor AJAX de reporte |
| — | GET /informes/reporte/{filename}/download | **NUEVA**: descarga de reporte |
| — | GET /informes/download-csvs | **NUEVA**: ZIP con todos los CSVs |
| — | GET /config | Nueva página de config |
| — | GET /config/barcos | Nueva: CRUD barcos |
| — | GET /config/categorias | Nueva: CRUD categorías |
| — | GET /config/tipos | Nueva: CRUD tipos de prueba |
| — | GET /config/distancias | **NUEVA**: CRUD distancias |
| — | GET /config/umbral | **NUEVA**: configurar umbral parado/movimiento |
| — | GET /config/telegram | Nueva: config Telegram |

### Archivos a eliminar

- `templates/session.html` — legacy, reemplazado por redirect a `/test/{id}`

### Endpoints API REST

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | /api/ranking | Top 20 tiempos (JSON) — mantiene |
| GET | /api/boat-stats | Stats por barco (JSON) — mantiene |
| GET | /api/sessions | Pruebas filtradas (JSON) — nueva |

---

## 10. Decisiones de Diseño

| Decisión | Valor | Razón |
|----------|-------|-------|
| Tema | Dark: bg #0f172a, text #e2e8f0, accent #38bdf8 | Consistencia visual |
| CSS | Extraer `base.css` compartido | Evitar duplicación de nav bar y tema en cada template |
| Templates | Jinja2 con `{% extends "base.html" %}` | Layout común, herencia de estilos |
| JavaScript | Vanilla JS (no frameworks) | Simplicidad, sin build step |
| Renderizado | Server-side (SSR) con Jinja2 | Rutas FastAPI retornan HTML |
| Base de datos | SQLite WAL mode | Concurrencia, portabilidad |
| Navegación | Bottom nav bar responsive | Mobile-first, UX tipo app |
| Idioma UI | Español | Consistencia con el deporte y usuarios |
| Fotos | Resize a WebP 40x40px | Tamaño uniforme, carga rápida |
| Documentación | Generación server-side .txt | Descarga directa desde el navegador |
| Gráficas web | ECharts (vendored local) | Interactividad cliente, sin dependencia de CDN externa |
| ECharts library | Vendored en `static/vendor/` | Offline-first, evita 404 si Plotly CDN falla |
| Distancia | CRUD dinámico (distancias) | Soporte multi-distancia, no solo 200m |
| Tipos | CRUD dinámico (test_types) | Permite agregar tipos sin cambiar código |
| Sesión = día | Una sesión agrupa pruebas de un día | Coincide con uso real (entreno diario) |
| Pruebas dentro de sesión | TestMetric depende de sesión | Permite múltiples tramos del mismo día |
| GPS completo en gps_data | 25Hz sin reducción | Sin pérdida de datos, ~150KB por CSV |
| Sectores y paladas detalle | Columnas JSON precomputadas | Evitar recalcular en cada render |
| Backfill script | `dragonboat.tools.backfill_sectores_paladas` | Migración de filas existentes |

---

## 11. Estructura del Proyecto

```
spec/
├── README.md                     # Índice + convenciones
├── SPEC.md                       # Este archivo (visión general)
├── registros-detalle.md          # Detalle de registros + test
├── navegacion.md                 # Wireframes de cada pantalla
├── api.md                        # Todos los endpoints HTML + JSON
├── tripulacion.md                # CRUD deportistas, asignación SVG, warnings
├── informes.md                   # Upload CSV, análisis, gráficas, reportes
├── configuracion.md              # Barcos, Categorías, Tipos, Distancias, Umbral, Telegram
├── dragonboat.dbml               # Diagrama de base de datos
└── dragonboat.sql                # SQL DDL

src/dragonboat/
├── __init__.py
├── __main__.py
├── config.py                     # Pydantic settings
├── database.py                   # SQLAlchemy engine
├── db_models.py                  # ORM models (AppSetting, Distancia, Sesion, CsvUpload, GpsData, TestMetric, TestGPSData, TestType, CrewMember, CrewAssignment, Category, Boat)
├── models.py                     # Dataclasses (Metricas, PaladasInfo, TramoDetectado)
├── repo.py                       # Repository layer
├── analysis/
│   ├── __init__.py               # Public API
│   ├── _utils.py                 # fmt, format_duration, calcular_sectores, resumen_paladas
│   ├── loader.py                 # cargar_csv, build_gps_data_json, get_trajectory, classify_gps_segments
│   ├── detection.py              # detectar_tramos, detectar_200m
│   ├── strokes.py                # detectar_paladas, detectar_picos
│   ├── metrics.py                # analizar_tramo, analizar_200m, calcular_pitch
│   ├── report.py                 # generar_informe_str, generar_resumen_sesion
│   └── calm.py
├── visualization/
│   └── charts.py                 # graficar_200m() (PNG con matplotlib)
├── tools/
│   ├── __init__.py
│   └── backfill_sectores_paladas.py  # Backfill sectores_detalle + paladas_detalle
├── bot/                          # Telegram config se expone en UI
├── storage/                      # Legacy, sin cambios
└── web/
    ├── app.py                    # FastAPI factory, mount /static
    ├── routes.py                 # Rutas principales
    ├── deportistas_routes.py     # CRUD tripulantes + assignment endpoints
    ├── static/
    │   ├── base.css              # CSS compartido
    │   ├── photos/               # Fotos de tripulantes
    │   ├── img/                  # SVGs estáticos
    │   │   ├── barcoDB12.svg
    │   │   ├── barcoDB22.svg
    │   │   ├── barcoDragon.svg
    │   │   ├── home_24dp.svg
    │   │   ├── iconoDragon.svg
    │   │   └── add_circle_24dp.svg
    │   ├── js/
    │   │   ├── calendario.js     # Calendario vanilla JS
    │   │   └── registros.js      # Init DataTables + coordinación
    │   └── vendor/
    │       └── echarts.min.js    # ECharts library (vendored)
    └── templates/
        ├── base.html             # Layout común con bottom nav
        ├── home.html             # Home (rankings por distancia + sesiones incompletas)
        ├── registros.html        # Lista de pruebas con calendario + sesión del día
        ├── sesion.html           # Vista de sesión diaria (métricas generales)
        ├── test.html             # Detalle de prueba (métricas + ECharts + mapa + tripulación)
        ├── informes.html         # Upload CSV + reportes existentes + dedupe
        ├── deportistas.html      # CRUD tripulantes
        ├── config.html           # Config (Barcos, Categorías, Tipos, Distancias, Umbral, Telegram)
        ├── boat_hull_db12.svg.j2 # SVG lateral barco DB12 con seat-markers
        └── boat_hull_db22.svg.j2 # SVG lateral barco DB22 con seat-markers

scripts/
└── reset_db.py                   # Reset destructivo: drops sesiones, test_metrics, crew_assignments, gps_data, csv_uploads
```

---

## 12. Especificaciones por funcionalidad

Archivos detallados en `spec/`:

- `spec/registros-detalle.md` — Registros + Detalle de Test (calendario, DataTables, Plotly, mapa GPS, tripulación SVG)
- `spec/navegacion.md` — Wireframes de cada pantalla, bottom nav, breadcrumbs, estados vacíos
- `spec/api.md` — Todos los endpoints HTML y JSON, request/response schemas
- `spec/tripulacion.md` — CRUD deportistas, asignación SVG, warnings, seat markers
- `spec/informes.md` — Upload CSV, análisis de tramos, gráficas, reportes
- `spec/configuracion.md` — Barcos, Categorías, Tipos, Distancias, Umbral, Telegram
