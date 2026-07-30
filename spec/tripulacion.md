# Especificación: Tripulación y Asignaciones

## 1. Modelo de datos

### crew_members

| Campo | Tipo | Constraints |
|-------|------|-------------|
| id | INTEGER | PK |
| nombre | VARCHAR(100) | NOT NULL |
| apellido | VARCHAR(100) | NOT NULL |
| categoria | VARCHAR(50) | nullable |
| photo_path | VARCHAR(255) | nullable |
| created_at | DATETIME | DEFAULT now |

### crew_assignments

| Campo | Tipo | Constraints |
|-------|------|-------------|
| id | INTEGER | PK |
| test_metric_id | INTEGER | FK → test_metrics.id, ondelete=CASCADE |
| crew_member_id | INTEGER | FK → crew_members.id |
| role | VARCHAR(20) | "tambor" / "remero" / "timonel" |
| side | VARCHAR(10) | nullable, "estribor" / "babor" |
| row_number | INTEGER | nullable, 1..10 |
| | | UNIQUE(test_metric_id, role, side, row_number) |

---

## 2. CRUD Deportistas

### Alta individual (POST /deportistas/add)

**Form data:**
- `nombre` (str, obligatorio)
- `apellido` (str, obligatorio)
- `categoria` (str, opcional)
- `photo` (UploadFile, opcional)

**Foto:**
- Se redimensiona a WebP 40x40px
- Se guarda como `{member_id}.webp` en `data/photos/`
- Si no hay foto: placeholder con iniciales

### Edición (POST /deportistas/{id}/edit)

Mismos campos que alta. Si se sube nueva foto, reemplaza la anterior.

### Eliminación (POST /deportistas/{id}/delete)

- Elimina foto (webp, jpg, png)
- Elimina el registro de la DB
- Cascade: elimina crew_assignments asociados

### Importación masiva (POST /deportistas/import)

**Formato CSV:**
```csv
nombre,apellido,categoria
Ana,García,Open Sénior
Luis,Martínez,
```

- Columnas aceptadas: `nombre`/`Nombre`, `apellido`/`Apellido`, `categoria`/`Categoria`
- Crea un tripulante por fila válida
- Ignora filas sin nombre o apellido

---

## 3. Asignación en test (SVG interactivo)

### Configurador inline

El configurador de tripulación vive en `test.html`, no en página separada.

**Layout del card:**
- Título "Tripulación" + badge del barco (`.badge.db12` verde, `.badge.db22` naranja)
- Subtítulo: "Haz clic en la cabeza de cada palista para asignarlo"
- SVG inline + contador `X / N asignados`
- Botones: "Limpiar" (con confirm) + "Guardar"

### SVG del barco

Dos partials Jinja2:
- `boat_hull_db12.svg.j2` — 5 filas (12 palistas), viewBox "0 0 1177 340"
- `boat_hull_db22.svg.j2` — 10 filas (22 palistas), viewBox "0 0 1718 359"

Color principal: púrpura (#7c2a78).

Los partials contienen círculos `.seat-marker` (invisibles) con atributos:
- `data-role`: "tambor" / "remero" / "timonel"
- `data-side`: "estribor" / "babor" / null
- `data-row`: número de fila

### Seat markers por barco

| Barco | Tambor | Remeros estribor | Remeros babor | Timonel | Total |
|-------|--------|------------------|---------------|---------|-------|
| DB12 | 1 | 5 | 5 | 1 | 12 |
| DB22 | 1 | 10 | 10 | 1 | 22 |

### Interacción click-to-assign

1. Click en la cabeza → dropdown posicionado en `position: fixed` a nivel body (z-index: 99999)
2. Dropdown contiene: header "SELECCIONAR TRIPULANTE", input búsqueda, lista filtrada, contador
3. Búsqueda type-ahead con normalización NFD + eliminación de combining chars
4. Tripulantes ya asignados a OTRO puesto: opacity 0.35 + "asignado" label + pointer-events: none
5. Navegación teclado: ArrowUp/ArrowDown/Enter/Escape
6. Click fuera del dropdown → cierra

### Orden de tripulantes

`list_crew_by_frequency()` en repo.py:
- LEFT JOIN con crew_assignments + COUNT + GROUP BY + ORDER BY COUNT DESC
- Los más usados aparecen primero en el dropdown

### Labels por defecto (asiento vacío)

| Rol | Label |
|-----|-------|
| Tambor | "Tambor" |
| Timonel | "Timonel" |
| Remero estribor | "E{row}" (E1…E10) |
| Remero babor | "B{row}" (B1…B10) |

### Visualización del tripulante asignado

- Con foto: `<image>` con clip-path circular, oculta placeholder e iniciales
- Sin foto: iniciales (1ª letra nombre + 1ª letra apellido) en #334155, bold, #e2e8f0
- Label debajo del círculo: solo `member.nombre` (sin apellido)

---

## 4. Guardar asignaciones

### Endpoint JSON (POST /test/{id}/crew/json)

**Body:**
```json
{
  "assignments": [
    {"crew_member_id": 1, "role": "remero", "side": "estribor", "row_number": 1},
    {"crew_member_id": 2, "role": "tambor", "side": null, "row_number": null}
  ]
}
```

**Lógica:** reemplaza todas las asignaciones existentes por las nuevas (DELETE + INSERT en transacción)

**Respuesta:** `{"ok": true}` (200) o error (500)

### Endpoint form (POST /test/{id}/crew)

Legacy: recibe campos `slot_{role}_{side}_{row}` del form HTML.
Redirige a `/test/{id}#tripulacion`.

---

## 5. Warnings en Home

### Lógica de warnings

Para cada sesión diaria, se aggregate sobre todas sus pruebas:

```python
total_palistas = sum(asignados_en_cada_prueba)
has_timonel = any(timonel_en_cualquier_prueba)
```

**Warnings generados:**
- `{"type": "crew", "label": "falta asignar tripulación"}` — si `total_palistas == 0`
- `{"type": "timonel", "label": "falta timonel"}` — si `not has_timonel and pruebas`

### Visualización

- Warning de tripulación: icono muñeco paleando tachado + "falta asignar tripulación"
- Warning de timonel: icono de timón tachado + "falta timonel"
- Solo aparecen si la sesión tiene pruebas

---

## 6. Contador de asignaciones

- `document.getElementById('assigned-count')` se actualiza en cada asignación
- Cuenta claves no vacías en el mapa `assignments`
- Se muestra como `X / N asignados`

---

## 7. Limpiar todo

- `window.limpiarTodo()` con `confirm("¿Limpiar todas las asignaciones?")`
- Vacía mapa de asignaciones
- Resetea cada seat: placeholder visible, image/initials ocultos, label default
- NO guarda automáticamente (el usuario debe hacer click en "Guardar")

---

## 8. Eliminar prueba

### Endpoint (POST /test/{id}/delete)

**Lógica:**
1. Borra la prueba (TestMetric)
2. Cascade por FK: crew_assignments, gps_data (SET NULL)
3. Si la sesión queda vacía → cascade: csv_uploads, gps_data
4. Si csv_upload.kept=True → borra archivo en disco

**Confirmación:** `onsubmit="return confirm('¿Eliminar esta prueba?')"`

**Redirección:** `/registros` (302)

---

## 9. Vista de sesión diaria (sesion.html)

### Endpoint (GET /sesion/{id})

`sesion.html` es una vista complementaria al detalle de prueba individual. Muestra:

**Header:**
- Título: "Sesión del dd/MM/YYYY"
- Subtítulo: "{num_pruebas} pruebas · {num_archivos} archivos · {tipo} · {categoria}"

**Métricas generales del entreno (7 stat-cards):**
- Distancia total real (con nominal como sub) — en metros
- Tiempo total (duración GPS)
- Tiempo parado (sin moverse)
- Tiempo en movimiento (remando)
- Vel. media en mov. (km/h)
- Vel. máxima del día (km/h)
- Ritmo medio (min/km)

**Tabla de pruebas de velocidad:**
- Columnas: #, Nombre, Distancia (badge), Barco (badge), Tiempo (duration), Paladas, Tripulación
- Tripulación: emoji 🧑‍🦱 si tiene, 🚫 si está vacía
- Click en fila → `/test/{id}` (con `event.stopPropagation()` en botones)
- Botones: Ver, Eliminar (con confirm)

**Archivos CSV del día:**
- Lista con filename, fecha de upload, fecha de datos (metadata_date)

**Editar día:**
- Form `POST /sesion/{id}` con selects de categoria y tipo
- Botón "Recalcular métricas" → `POST /sesion/{id}/recalcular`

**Eliminar sesión completa:**
- Form `POST /sesion/{id}/delete` con confirm "Esta acción no se puede deshacer"
- Borra la sesión + cascade (csv_uploads, gps_data, test_metrics, crew_assignments, archivos físicos)

### Sesiones CRUD endpoints

| Método | Ruta | Acción |
|--------|------|--------|
| GET | `/sesion/{id}` | Vista de sesión |
| POST | `/sesion/{id}` | Actualizar tipo/categoría |
| POST | `/sesion/{id}/delete` | Eliminar sesión completa |
| POST | `/sesion/{id}/recalcular` | Recalcular agregados |
