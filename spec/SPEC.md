# Dragon Boat Analyzer — Especificación del Proyecto

## 1. Visión General

Aplicación web de gestión deportiva para el deporte barco dragón.
Analiza rendimiento en tramos de 200 metros desde datos GPS (RaceBox Drag),
gestiona tripulaciones y genera rankings y documentación de competiciones.

**Stack tecnológico:**
- Backend: Python 3.12 + FastAPI + Jinja2
- Base de datos: SQLite (WAL mode) + SQLAlchemy 2.0 ORM
- Frontend: HTML + CSS (base.css compartido) + vanilla JS + jQuery
- Visualización: Plotly Python (gráficas web interactivas), Leaflet.js (mapa GPS),
  DataTables (tablas filtrables), matplotlib (gráficas PDF/impresión),
  SVG (diagrama de barco)
- Procesamiento de datos: pandas, numpy, scipy

**Objetivos:**
1. Análisis automático de tramos 200m desde CSV RaceBox Drag
2. Gestión de tripulaciones con fotos y categorías
3. Rankings y estadísticas por barco
4. Generación de documentación PDF para competiciones
5. Configuración flexible de barcos, categorías y notificaciones

---

## 2. Navegación — Bottom Nav Bar

```
┌──────────┬──────────┬──────────┬────────────┬──────────┐
│Dashboard │Registros │Informes  │Deportistas │    ⚙️    │
└──────────┴──────────┴──────────┴────────────┴──────────┘
```

- 5 items fijos en la parte inferior de la pantalla
- Mobile-first: diseño optimizado para pantallas pequeñas
- Item activo: resaltado con color accent (#38bdf8)
- Icono + texto corto para cada item
- La sección ⚙️ (Configuración) abre un sub-menú o página dedicada

---

## 3. Dashboard (Home — GET /)

Página principal de la aplicación. Muestra un resumen del estado actual.

**Contenido:**

- **Rankings top-20**: tabla con los mejores tiempos de 200m
  - Columnas: #, nombre, barco, categoría, tiempo, vel. media, paladas, dist/palada, fecha
  - Colores por podium: oro (#1), plata (#2), bronce (#3)

- **Estadísticas por barco**: tarjetas con métricas agregadas
  - Número de pruebas, mejor tiempo, tiempo promedio, peor tiempo
  - Velocidad media, paladas promedio, distancia/palada promedio
  - Badge de color por barco (DB12 verde, DB22 naranja)

- **Por completar**: tarjetas de sesiones/tests con campos pendientes
  - Warning de tripulación: icono muñeco paleando tachado + "falta asignar tripulación" (si faltan palistas)
  - Warning de timonel: icono de timón tachado + "falta timonel"
  - Solo aparecen warnings para campos obligatorios u opcionales con warning (ver sección 8)

---

## 4. Registros (GET /registros)

> **⚠️ Diseño rediseñado en `spec/registros-detalle.md`**
> El diseño actual de esta sección es un placeholder.
> La implementación final debe seguir la especificación detallada en `registros-detalle.md`
> que incluye: calendario mensual interactivo + tabla DataTables filtrable/ordenable.

### 4.0 Concepto clave: prueba = sesión

**Una "prueba" ES una sesión.** No existe un concepto separado de "sesión" que agrupa pruebas.

- Al subir un CSV, se parte en **pruebas** (tramos de 200m). Cada prueba es la unidad atómica.
- Las pruebas se agrupan visualmente **por día** y se ordenan **por hora de ejecución** dentro del día.
- El CSV es solo la **vía de importación** y la **fuente de procedencia**. Los datos originales pueden borrarse manteniendo el registro de procedencia en la tabla `csv_uploads`.
- Una "sesión" y una "prueba" son lo mismo. El código usa `Sesion` como nombre de clase/tabla.

Vista histórica de todas las pruebas. Todos los campos son editables.

**Filtros:**
- Tipo: entreno / competición / todos
- Barco: DB12 / DB22 / todos
- Fecha: rango de fechas
- Categoría: selector de categorías disponibles

**Cada prueba muestra (en la tabla):**
- Número, nombre, tipo, barco, tiempo, categoría, fecha, hora
- Botón **Eliminar** con confirmación: "¿Eliminar esta prueba?"

**Edición inline (campos por prueba):**
- Nombre: predefinido como "Prueba #N dd/MM/AAAA" (N = conteo de pruebas de ese día, en orden cronológico por fecha_hora)
- Tipo: por defecto "entreno"
- Barco: por defecto DB12
- Categoría: selector (solo visible si tipo = "competición")

**Detalle de prueba (GET /test/{id}):**
> **⚠️ Especificación completa en `spec/registros-detalle.md` sección 4**
> 7 bloques: navegación + métricas + editar + mapa GPS + gráfica + datos + tripulación inline.

- Métricas: vel. max, vel. media, 0→12 km/h, paladas, dist/palada, consistencia
- Editar prueba: nombre, barco, categoría (colapsable inline)
- Gráfica: PNG base64 (actual) → Plotly interactivo (futuro, 4 paneles sincronizados)
- Mapa GPS Leaflet con trayectoria, minimizable
- Datos generales: 3 tablas (tramos, velocidades, paladas)
- Tripulación: SVG lateral interactivo con click-to-assign y type-ahead (inline, no página separada)
- Eliminar prueba: botón con confirmación, cascade delete
- Fallbacks documentados para cada estado vacío

**Eliminar prueba (POST /registros/{id}/delete):**
- Popup de confirmación: "¿Eliminar esta prueba?"
- Borra la prueba, su métrica y sus asignaciones de tripulación (cascade).
- Si era la última prueba de su `csv_upload` padre, el `csv_upload` también se borra (y el archivo en disco si `kept=True`).

---

## 5. Informes (GET /informes)

Dos acciones principales para análisis y documentación.

### 5.1 Subir CSV (POST /informes/upload)

- Zona de drag & drop para archivos CSV RaceBox Drag
- Validación: extensión .csv, formato correcto
- Proceso:
  1. Lee CSV con pandas
  2. Detecta tramos de 200m (análisis de gradiente)
  3. Detecta paladas (picos de velocidad)
  4. Calcula métricas por tramo
  5. Filtra tramos válidos (tiempo < 85s, t11kmh < 20s, vel media > 9 km/h)
  6. Guarda en DB: sesión + tests + métricas
  7. Genera gráficas PNG (4 paneles por test)
  8. Redirige a la sesión creada
- Feedback de errores: mensaje claro si falla la validación

### 5.2 Generar documentación (POST /informes/generate)

- Selector de sesiones tipo "competición"
- Genera PDF descargable con:
  - Una página por barco
  - Tripulación asignada por posición (tambor, estribor/babor por fila, timonel)
  - Datos del barco (nombre, tipo, número de personas)
- El PDF se genera en el servidor y se descarga como archivo

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
- **Búsqueda/filtro**: por nombre o categoría
- **Edición**: click en fila para editar inline
- **Eliminación**: botón con confirmación (onsubmit confirm)
- **Listado**: tabla con foto, nombre, apellido, categoría, acciones

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

### 7.3 Telegram bot (/config/telegram)

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
csv_uploads (procedencia) ──< sesiones (pruebas) ──< test_metrics
                                          └──< crew_assignments >── crew_members
boats (referencia)
categories (CRUD dinámico)
```

### Tablas

**boats**
| Campo | Tipo | Constraints |
|-------|------|-------------|
| id | INTEGER | PK |
| name | VARCHAR(10) | UNIQUE |
| display_name | VARCHAR(50) | |
| num_rows | INTEGER | |
| total_persons | INTEGER | |

**csv_uploads (NUEVA — procedencia)**
| Campo | Tipo | Constraints |
|-------|------|-------------|
| id | INTEGER | PK |
| filename | VARCHAR(255) | UNIQUE |
| uploaded_at | DATETIME | DEFAULT now |
| file_path | VARCHAR(255) | nullable, path en data/input/ |
| kept | BOOLEAN | DEFAULT true, si el archivo sigue en disco |

**sesiones (era "tests" + hereda de "session")**
| Campo | Tipo | Constraints |
|-------|------|-------------|
| id | INTEGER | PK |
| csv_upload_id | INTEGER | FK → csv_uploads.id, nullable |
| fecha_hora | DATETIME | DEFAULT now, momento de ejecución del tramo |
| test_number | INTEGER | nullable, orden dentro del CSV |
| custom_name | VARCHAR(100) | nullable |
| tipo | VARCHAR(20) | "entreno" / "competición" |
| boat_id | INTEGER | FK → boats.id, nullable |
| categoria | VARCHAR(50) | nullable |

**test_metrics**
| Campo | Tipo | Constraints |
|-------|------|-------------|
| id | INTEGER | PK |
| sesion_id | INTEGER | FK → sesiones.id, UNIQUE |
| tiempo_total | FLOAT | |
| velocidad_media | FLOAT | |
| velocidad_maxima | FLOAT | |
| velocidad_min_post10 | FLOAT | nullable |
| aceleracion_max | FLOAT | |
| tiempo_11kmh | FLOAT | nullable |
| tiempo_12kmh | FLOAT | nullable |
| tiempo_50m | FLOAT | nullable |
| tiempo_100m | FLOAT | nullable |
| tiempo_150m | FLOAT | nullable |
| num_paladas | INTEGER | |
| dist_media_palada | FLOAT | |
| dist_std_palada | FLOAT | |
| chart_filename | VARCHAR(255) | nullable |

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
| sesion_id | INTEGER | FK → sesiones.id |
| crew_member_id | INTEGER | FK → crew_members.id |
| role | VARCHAR(20) | "tambor" / "remero" / "timonel" |
| side | VARCHAR(10) | nullable, "estribor" / "babor" |
| row_number | INTEGER | nullable, 1..10 |
| | | UNIQUE(sesion_id, role, side, row_number) |

**categories**
| Campo | Tipo | Constraints |
|-------|------|-------------|
| id | INTEGER | PK |
| name | VARCHAR(100) | UNIQUE |
| created_at | DATETIME | DEFAULT now |

### Reglas de campos por prueba

| Campo | Default | Obligatorio | Warning si vacío |
|-------|---------|-------------|------------------|
| Barco | DB12 | Sí (default siempre presente) | No |
| Tipo | "entreno" | Sí (default siempre presente) | No |
| Nombre | "Prueba #N dd/MM/AAAA" | Sí (default siempre presente) | No |
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

---

## 9. Rutas Web (Refactor)

### Mapa old → new

| Ruta vieja | Ruta nueva | Acción |
|------------|------------|--------|
| GET / | GET / | Dashboard (ahora muestra pruebas directamente) |
| GET / | GET /registros | Lista de pruebas (antes lista de sesiones con tests anidados) |
| POST /upload | POST /informes/upload | Se mueve a Informes |
| GET /session/{id} | GET /registros/{id} | Redirige a /test/{id} (prueba = sesión) |
| POST /session/{id} | POST /registros/{id} | Actualiza campos de la prueba |
| — | POST /registros/{id}/delete | **NUEVA**: elimina una prueba con confirmación |
| GET /dashboard | — | Se elimina, contenido va a GET / |
| GET /crew | GET /deportistas | Se renombra |
| POST /crew/add | POST /deportistas/add | Se renombra |
| POST /crew/import | POST /deportistas/import | Se renombra |
| POST /crew/{id}/delete | POST /deportistas/{id}/delete | Se mantiene POST |
| GET /test/{id} | GET /test/{id} | Detalle de prueba (se mantiene) |
| POST /test/{id} | POST /test/{id} | Actualiza prueba (se mantiene) |
| GET /test/{id}/crew | GET /test/{id}/crew | Se mantiene |
| POST /test/{id}/crew | POST /test/{id}/crew | Se mantiene |
| — | GET /informes | Nueva página de informes |
| — | POST /informes/upload?overwrite=1 | **NUEVA**: reemplaza CSV duplicado |
| — | POST /informes/generate | Nueva: generar PDF |
| — | GET /config | Nueva página de config |
| — | GET /config/barcos | Nueva: CRUD barcos |
| — | GET /config/categorias | Nueva: CRUD categorías |
| — | GET /config/telegram | Nueva: config Telegram |

### Archivos a eliminar

- `templates/result.html` — código muerto, no lo usa ninguna ruta

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
| PDF | Generación server-side | Descarga directa desde el navegador |

---

## 11. Estructura del Proyecto

```
spec/
├── README.md                     # Índice + convenciones
└── SPEC.md                       # Este archivo

src/dragonboat/web/
├── app.py                        # FastAPI factory, mount /static
├── routes.py                     # Rutas refactorizadas
├── deportistas_routes.py         # CRUD tripulantes + assignment endpoints
├── static/
│   ├── base.css                  # CSS compartido
│   └── photos/                   # Fotos de tripulantes
├── templates/
│   ├── base.html                 # Layout común con bottom nav
│   ├── dashboard.html            # Home (pruebas incompletas + ranking)
│   ├── registros.html            # Lista de pruebas con botón Eliminar
│   ├── session.html              # Legacy (redirect a /test/{id})
│   ├── informes.html             # Upload CSV + generar doc + dedupe reemplazo
│   ├── deportistas.html          # CRUD tripulantes
│   ├── config.html               # Config landing
│   ├── test.html                 # Detalle de prueba (métricas + mapa + gráfica + tripulación)
│   └── [ELIMINAR] result.html    # Código muerto

scripts/
└── reset_db.py                   # Reset destructivo: drops sesiones, test_metrics, crew_assignments, csv_uploads

src/dragonboat/
├── __init__.py
├── __main__.py
├── config.py                     # Pydantic settings
├── database.py                   # SQLAlchemy engine
├── db_models.py                  # ORM models (CsvUpload, Sesion, TestMetric, CrewMember, CrewAssignment, Category, Boat)
├── models.py                     # Dataclasses (Metricas, PaladasInfo, TramoDetectado)
├── repo.py                       # Repository layer (CsvUpload CRUD, Sesion CRUD, Crew CRUD, Category CRUD)
├── analysis/                     # Sin cambios
├── visualization/                # Sin cambios
├── bot/                          # Sin cambios (Telegram config se expone en UI)
├── storage/                      # Legacy, sin cambios
└── web/                          # Ver arriba
```

---

## 12. Futuras Especificaciones

Al avanzar el desarrollo, crear archivos adicionales en esta carpeta:

- `spec/navegacion.md` — Wireframes detallados de cada sección
- `spec/api.md` — Schemas JSON de cada endpoint API
- `spec/tripulacion.md` — Lógica completa de warnings, validaciones, defaults
- `spec/informes.md` — Detalle del generador de PDF y documentación
- `spec/configuracion.md` — Detalle de cada sub-sección de config

Actualizar `spec/README.md` con el link a cada nuevo archivo.
