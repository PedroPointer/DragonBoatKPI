# Especificación: Navegación y Wireframes

## 1. Bottom Nav Bar

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
- Implementado en `base.html` con `{% block nav %}`

### Item activo

Cada template pasa `active_nav` al context:
- `home.html` → `"home"`
- `registros.html` → `"registros"`
- `test.html` → `"registros"`
- `informes.html` → `"informes"`
- `deportistas.html` → `"deportistas"`
- `config.html` → `"config"`

---

## 2. Home (GET /)

**Template:** `home.html`

### Wireframe

```
┌─────────────────────────────┐
│  🐉 Dragon Boat Analyzer    │  ← header
├─────────────────────────────┤
│                             │
│  ┌─── 200m ──────────────┐  │  ← sección colapsable
│  │ # │ Nombre │ Tiempo   │  │
│  │ 1 │ Ana    │ 42.30s   │  │  ← podium: oro
│  │ 2 │ Luis   │ 43.10s   │  │  ← plata
│  │ 3 │ Marta  │ 43.80s   │  │  ← bronce
│  └───────────────────────┘  │
│                             │
│  ┌─── 500m ──────────────┐  │
│  │ ...                   │  │
│  └───────────────────────┘  │
│                             │
│  ┌─── Estadísticas ──────┐  │
│  │ DB12: 15 pruebas      │  │
│  │ Mejor: 42.30s         │  │
│  │ Promedio: 45.20s      │  │
│  └───────────────────────┘  │
│                             │
│  ┌─── Por completar ─────┐  │
│  │ ⚠️ 15/06: falta       │  │
│  │    tripulación         │  │
│  │ ⚠️ 15/06: falta       │  │
│  │    timonel             │  │
│  └───────────────────────┘  │
│                             │
├──────┬──────┬──────┬───┬────┤
│ Home │Regis │Infor │Dep│ ⚙️ │
└──────┴──────┴──────┴───┴────┘
```

### Comportamiento

- Rankings por distancia: secciones colapsables (200m, 500m, 1000m, 2000m)
- Top-5 por distancia (no top-20 como decía el spec anterior)
- Podium: oro (#1), plata (#2), bronce (#3)
- Estadísticas por barco: tarjetas con métricas agregadas
- Por completar: sesiones con warnings de tripulación/timonel
- `worst_tiempo` se calcula pero NO se muestra

---

## 3. Registros (GET /registros)

**Template:** `registros.html`

### Wireframe

```
┌─────────────────────────────┐
│  Registros                  │
├─────────────────────────────┤
│                             │
│  ◀  Junio 2026  ▶          │  ← calendario
│  Lu Ma Mi Ju Vi Sa Do       │
│     1  2  3  4  5  6       │
│  7  8  9 10 11 12 13       │
│ 14 [15] 16 17 18 19 20     │  ← día marcado = badge verde
│ 21 22 23 24 25 26 27       │     día con comp = badge dorado
│ 28 29 30                   │
│                             │
├─────────────────────────────┤
│  Sesión del 15/06/2026      │  ← cabecera día
│  6 pruebas · 1 archivo      │
│  Dist.total: 1198m  Tiempo: 1h 30m  │
│  T.parado: 5m  T.mov: 25m  V.media: 8.5 km/h │
├─────────────────────────────┤
│  ┌─ Mapa GPS ──────────────┐│
│  │ ▬▬moving▬▬  ▬▬stopped▬▬ ││  ← Leaflet coloreado
│  │ [Minimizar]              ││
│  └─────────────────────────┘│
├─────────────────────────────┤
│  Pruebas de velocidad       │
│  # │ Nom │ Dist │ Bar │ T │  ← tabla
│  1 │ Pr1 │ 200m │ DB12│ 42s│
│  2 │ Pr2 │ 200m │ DB12│ 45s│
│  [Ver] [Eliminar]           │
├─────────────────────────────┤
│  Archivos CSV                │
│  - 15jun.csv subido 10:30   │
├─────────────────────────────┤
│  [🗑 Eliminar sesión]        │  ← botón rojo
├──────┬──────┬──────┬───┬────┤
│ Home │Regis │Infor │Dep│ ⚙️ │
└──────┴──────┴──────┴───┴────┘
```

### Comportamiento

- Calendario vanilla JS (`static/js/calendario.js`)
- Click en día → `GET /registros?dia=X&mes=Y&anio=Z`
- Cabecera de sesión: 7 stat-cards (distancia, tiempo total/parado/mov, vel media/max, ritmo)
- Mapa Leaflet con leyenda (verde=moving, rojo=stopped, dots 200/500/1000m)
- Tabla pruebas con badges (distancia, barco)
- Botón "Eliminar sesión" en card rojo (cascade)

---

## 4. Detalle de Prueba (GET /test/{id})

**Template:** `test.html`

### Wireframe

```
┌─────────────────────────────┐
│ Home / Registros / Prueba #1│  ← breadcrumb
├─────────────────────────────┤
│  Prueba #1 — Detalle        │
│  DB12 — Open Sénior         │  ← metadatos
├─────────────────────────────┤
│  Métricas [Editar ▾]  42.30s│  ← botón toggle
│  ┌────┬────┬────┐          │
│  │Vel │Vel │0→12│          │
│  │Max │Med │km/h│          │
│  │32.1│28.5│3.2 │          │
│  ├────┼────┼────┤          │
│  │Pala│Dist│Cons│          │
│  │45  │4.2 │0.3 │          │
│  └────┴────┴────┘          │
│                             │
│  [panel Editar OCULTO]      │  ← toggle "▾" abre
│  [Nombre] [Nº]              │
│  [Barco] [Categoría] [Tipo] │
│  [Guardar]                  │
├─────────────────────────────┤
│  ┌─ Mapa GPS ─────────────┐│  ← Leaflet
│  │▬▬▬▬▬▬▬▬▬▬▬▬▬         ││  ← coloreado por velocidad
│  │▬▬▬▬▬▬▬▬▬▬             ││
│  │       ▬▬▬▬▬▬▬▬▬▬▬    ││
│  │▶ (entrada)    🏁 (fin) ││
│  │ [Minimizar] [Legend ▼] ││
│  └─────────────────────────┘│
├─────────────────────────────┤
│  Análisis de la carrera     │
│  [Reset] [PNG] [Expand ⛶]  │
│  ☑ Velocidad ☑ Dist/palada  │
│  ☑ Nº palada  ☐ Balanceo    │
│  ☐ Cabeceo                  │
│  ┌─────────────────────────┐│
│  │   4 subplots ECharts    ││
│  │  - Velocidad            ││
│  │  - Roll                 ││
│  │  - Pitch                ││
│  │  - Dist/palada          ││
│  │  dataZoom inside+slider ││
│  └─────────────────────────┘│
│  [Descargar PNG]            │
├─────────────────────────────┤
│  Datos generales            │  ← formato reporte
│  Dragon Boat - 200m         │
│  15/06/2026 10:30 · Prueba#1│
│  ⏱ Tiempo total: 00:00:42,30│
│  📍 Tiempos por sector:     │
│   0 a 50m: 9,20s (19,57km/h)│
│   50 a 100m: 8,80s (20,45km/h)│
│   ...                       │
│  📊 Velocidad:              │
│   Media: 28,50 km/h (7,92 m/s)│
│   Maxima: 32,10 km/h        │
│  🔄 Paladas:                │
│   Total: 45                 │
│   Dist/palada: 4,20 m       │
│   Maxima: 5,10 m            │
│   Minima: 2,10 m (salida)   │
│   Minima: 3,10 m (sin 10 primeras)│
├─────────────────────────────┤
│  Tripulación        DB12   │
│  [SVG barco lateral]        │
│  8 / 12 asignados           │
│  [Limpiar] [Guardar]        │
├─────────────────────────────┤
│  [🗑 Eliminar prueba]       │  ← botón rojo
├──────┬──────┬──────┬───┬────┤
│ Home │Regis │Infor │Dep│ ⚙️ │
└──────┴──────┴──────┴───┴────┘
```

### Comportamiento

- Breadcrumb: `Home / Registros / Prueba #X` (con iconos SVG)
- Editar OCULTO por defecto — botón "Editar prueba ▾" togglea el panel
- ECharts: 4 paneles toggleables con checkboxes
- Mapa Leaflet coloreado por velocidad (gradiente 6 stops)
- "Datos generales" en formato reporte (4 secciones: sectores, velocidad, paladas)
- Tripulación inline con SVG click-to-assign
- Eliminar con confirmación

---

## 5. Sesión Diaria (GET /sesion/{id})

**Template:** `sesion.html`

### Wireframe

```
┌─────────────────────────────┐
│ Home / Registros / Sesión   │
├─────────────────────────────┤
│  Sesión del 15/06/2026      │
│  6 pruebas · 1 archivo      │
│  Entreno · Open Sénior       │
├─────────────────────────────┤
│  Métricas generales del entreno │
│  Dist.total real: 1198m      │
│  Tiempo total: 30:00        │
│  Tiempo parado: 5:00         │
│  Tiempo en mov.: 25:00       │
│  Vel.media mov: 8,5 km/h    │
│  Vel.máx día: 32,10 km/h    │
│  Ritmo medio: 7,06 min/km   │
├─────────────────────────────┤
│  Pruebas de velocidad       │
│  # │ Nom │ Dist │ Bar │ T  │
│  1 │ Pr1 │ 200m │ DB12│ 42s│
│  2 │ Pr2 │ 200m │ DB12│ 45s│
│  [Ver] [Eliminar]           │
├─────────────────────────────┤
│  Archivos CSV               │
│  - 15jun.csv subido 10:30   │
├─────────────────────────────┤
│  Editar día                 │
│  [Categoría] [Tipo]         │
│  [Guardar día] [Recalcular]  │
├─────────────────────────────┤
│  Eliminar sesión (rojo)     │
│  [Eliminar sesión completa] │
├──────┬──────┬──────┬───┬────┤
│ Home │Regis │Infor │Dep│ ⚙️ │
└──────┴──────┴──────┴───┴────┘
```

### Comportamiento

- Vista complementaria al detalle de prueba individual
- Acceso desde breadcrumb de `test.html` o desde `home.html` (link "Ver")
- Métricas agregadas pre-calculadas (`recalc_sesion_aggregates`)
- Tabla de pruebas con badges y botones de acción
- Editar día (cambiar categoria/tipo)
- Recalcular métricas (botón secundario)
- Eliminar sesión completa (cascade)

---

## 6. Informes (GET /informes)

**Template:** `informes.html`

### Wireframe

```
┌─────────────────────────────┐
│  Informes                   │
├─────────────────────────────┤
│                             │
│  ┌─ Subir CSV ────────────┐│
│  │  [Drag & drop CSV]     ││
│  │  o click para seleccionar│
│  └─────────────────────────┘│
│                             │
│  ┌─ Reportes ─────────────┐│
│  │ Informe_15jun.txt  [Ver]││
│  │                   [Desc]││
│  │ Informe_14jun.txt  [Ver]││
│  │                   [Desc]││
│  │ [← 1 2 3 →]            ││  ← paginación
│  └─────────────────────────┘│
│                             │
│  [Descargar todos CSVs]     │
│                             │
├──────┬──────┬──────┬───┬────┤
│ Home │Regis │Infor │Dep│ ⚙️ │
└──────┴──────┴──────┴───┴────┘
```

### Comportamiento

- Drag & drop o click para subir CSV
- Detección de duplicados → ofrecer reemplazar
- Lista de reportes con paginación (15 por página)
- Botón Ver → visor AJAX (modal)
- Botón Descargar → archivo .txt
- Botón "Descargar todos CSVs" → ZIP

---

## 7. Deportistas (GET /deportistas)

**Template:** `deportistas.html`

### Wireframe

```
┌─────────────────────────────┐
│  Deportistas                │
├─────────────────────────────┤
│                             │
│  ┌─ Nuevo deportista ──────┐│
│  │ [Nombre] [Apellido]     ││
│  │ [Categoría] [Foto]      ││
│  │ [Agregar]               ││
│  └─────────────────────────┘│
│                             │
│  ┌─ Importar CSV ──────────┐│
│  │ [Seleccionar archivo]   ││
│  └─────────────────────────┘│
│                             │
│  ┌─────────────────────────┐│
│  │ Foto │ Nombre │ Acciones││
│  │  👤  │ Ana G. │ [E][X] ││
│  │  👤  │ Luis M.│ [E][X] ││
│  │  👤  │ Marta  │ [E][X] ││
│  └─────────────────────────┘│
│                             │
├──────┬──────┬──────┬───┬────┤
│ Home │Regis │Infor │Dep│ ⚙️ │
└──────┴──────┴──────┴───┴────┘
```

### Comportamiento

- Alta individual con foto (resize WebP 40x40px)
- Importación masiva desde CSV
- Edición inline (POST /deportistas/{id}/edit)
- Eliminación con confirmación
- Placeholder con iniciales si no hay foto

---

## 8. Configuración (GET /config)

**Template:** `config.html`

### Wireframe — Menú principal

```
┌─────────────────────────────┐
│  Configuración              │
├─────────────────────────────┤
│                             │
│  [🚢 Barcos]               │
│  [🏷 Categorías]           │
│  [📋 Tipos]                │
│  [📏 Distancias]           │
│  [⏱ Umbral]               │
│  [📱 Telegram]             │
│                             │
├──────┬──────┬──────┬───┬────┤
│ Home │Regis │Infor │Dep│ ⚙️ │
└──────┴──────┴──────┴───┴────┘
```

### Wireframe — Barcos

```
┌─────────────────────────────┐
│  Barcos          [← Volver] │
├─────────────────────────────┤
│  ┌─ Nuevo barco ──────────┐│
│  │ [Nombre] [Display]     ││
│  │ [Filas] [Personas]     ││
│  │ [Crear]                ││
│  └─────────────────────────┘│
│                             │
│  DB12 │ Dragon 12p │ 5 fil │
│        [Editar] [Eliminar]  │
│  DB22 │ Dragon 22p │10 fil │
│        [Editar] [Eliminar]  │
└─────────────────────────────┘
```

### Wireframe — Categorías

```
┌─────────────────────────────┐
│  Categorías      [← Volver] │
├─────────────────────────────┤
│  [Nueva categoría]          │
│                             │
│  Open Sénior    [Editar][X] │
│  Open Veterano  [Editar][X] │
│  Femenino Sénior [Editar][X]│
│  ...                        │
└─────────────────────────────┘
```

### Wireframe — Tipos

```
┌─────────────────────────────┐
│  Tipos           [← Volver] │
├─────────────────────────────┤
│  [Nuevo tipo]               │
│                             │
│  Entreno       [Editar][X]  │
│  Competición   [Editar][X]  │
└─────────────────────────────┘
```

### Wireframe — Distancias

```
┌─────────────────────────────┐
│  Distancias     [← Volver]  │
├─────────────────────────────┤
│  [Nueva distancia]          │
│  [Metros] [Descripción] [Orden]│
│                             │
│  200m  │ 200 metros  │ 1    │
│  500m  │ 500 metros  │ 2    │
│  1000m │ 1000 metros │ 3    │
│  2000m │ 2000 metros │ 4    │
└─────────────────────────────┘
```

### Wireframe — Umbral

```
┌─────────────────────────────┐
│  Umbral          [← Volver] │
├─────────────────────────────┤
│  Velocidad parado:          │
│  [1.5] km/h                 │
│  (rango: 0.5 - 20.0)       │
│  [Guardar]                  │
└─────────────────────────────┘
```

### Wireframe — Telegram

```
┌─────────────────────────────┐
│  Telegram        [← Volver] │
├─────────────────────────────┤
│  Habilitado: [ON/OFF]      │
│  Token: [____________]      │
│  Chat ID: [___________]     │
│  [Guardar]                  │
└─────────────────────────────┘
```

---

## 9. Breadcrumbs

Implementado en `test.html`:

```
Home / Registros / Prueba #1
```

- `Home` → `GET /`
- `Registros` → `GET /registros`
- Último item: texto del título (no es link)

---

## 10. Transiciones y estados

### Loading states
- Calendario: sin loading (renderizado SSR)
- Tabla pruebas: server-side render directo
- Mapa: `setTimeout(invalidateSize, 200)` post-render
- ECharts: lazy load con `fetch /test/{id}/chart-data`

### Empty states
- Sin sesión seleccionada: empty state con link a /informes
- Sin pruebas en el día: "Esta sesión no tiene pruebas de velocidad detectadas. Solo se registró el GPS del entreno."
- Sin datos GPS: "Mapa no disponible — datos GPS no registrados"
- Sin tripulantes: dropdown "Sin resultados"
- Sin rankings: sección colapsable vacía

### Error states
- CSV inválido: "Solo se aceptan archivos CSV"
- CSV duplicado: ofrecer reemplazar
- Error guardando: toast o `alert("Error al guardar")`
- Error de conexión: `alert("Error de conexión")`
