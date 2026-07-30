# Especificación: Configuración

## 1. Estructura general

Menú de configuración accesible desde `GET /config`.
Template: `config.html` (se renderiza con `section` para mostrar la sección activa).

```
GET /config            → menú principal
GET /config/barcos     → CRUD barcos
GET /config/categorias → CRUD categorías
GET /config/tipos      → CRUD tipos
GET /config/distancias → CRUD distancias
GET /config/umbral     → Umbral velocidad parado
GET /config/telegram   → Config Telegram
```

**Orden del menú principal (en `config.html`):**
1. 🚢 Barcos
2. 🏷️ Categorías
3. 🧪 Tipos
4. 📏 Distancias
5. 🟢🔴 Umbral parado / movimiento
6. 🤖 Telegram Bot

Cada item es un `<li onclick="window.location='/config/...'">` con nombre + meta.

---

## 2. Barcos (/config/barcos)

### Modelo de datos

**Tabla `boats`:**

| Campo | Tipo | Constraints |
|-------|------|-------------|
| id | INTEGER | PK |
| name | VARCHAR(10) | UNIQUE, NOT NULL |
| display_name | VARCHAR(50) | NOT NULL |
| num_rows | INTEGER | NOT NULL |
| total_persons | INTEGER | NOT NULL |

### Barcos seed

| name | display_name | num_rows | total_persons |
|------|-------------|----------|---------------|
| DB12 | Dragon Boat 12 personas | 5 | 12 |
| DB22 | Dragon Boat 22 personas | 10 | 22 |

### Endpoints

| Método | Ruta | Acción |
|--------|------|--------|
| GET | `/config/barcos` | Lista barcos |
| POST | `/config/barcos` | Crear barco |
| POST | `/config/barcos/{id}/delete` | Eliminar barco |

**POST /config/barcos — form data:**
- `name` (str, obligatorio): nombre único
- `display_name` (str, obligatorio): nombre para mostrar
- `num_rows` (int, obligatorio): número de filas
- `total_persons` (int, obligatorio): total de personas

---

## 3. Categorías (/config/categorias)

### Modelo de datos

**Tabla `categories`:**

| Campo | Tipo | Constraints |
|-------|------|-------------|
| id | INTEGER | PK |
| name | VARCHAR(100) | UNIQUE, NOT NULL |
| created_at | DATETIME | DEFAULT now |

### Categorías seed

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

### Endpoints

| Método | Ruta | Acción |
|--------|------|--------|
| GET | `/config/categorias` | Lista categorías |
| POST | `/config/categorias` | Crear categoría |
| POST | `/config/categorias/{id}/edit` | Editar categoría |
| POST | `/config/categorias/{id}/delete` | Eliminar categoría |

**POST /config/categorias — form data:**
- `name` (str, obligatorio): nombre único

**Uso:** Se usa en selector de tipo "competición" de cada prueba.

---

## 4. Tipos de prueba (/config/tipos)

### Modelo de datos

**Tabla `test_types`:**

| Campo | Tipo | Constraints |
|-------|------|-------------|
| id | INTEGER | PK |
| name | VARCHAR(20) | UNIQUE, NOT NULL |
| created_at | DATETIME | DEFAULT now |

### Tipos seed

1. Entreno
2. Competición

### Endpoints

| Método | Ruta | Acción |
|--------|------|--------|
| GET | `/config/tipos` | Lista tipos |
| POST | `/config/tipos` | Crear tipo |
| POST | `/config/tipos/{id}/edit` | Editar tipo |
| POST | `/config/tipos/{id}/delete` | Eliminar tipo |

**POST /config/tipos — form data:**
- `name` (str, obligatorio): nombre único

**Uso:** Se usa en selector de tipo de cada prueba. Reemplaza la lista hardcodeada "entreno"/"competición".

---

## 5. Distancias (/config/distancias)

### Modelo de datos

**Tabla `distancias`:**

| Campo | Tipo | Constraints |
|-------|------|-------------|
| id | INTEGER | PK |
| metros | INTEGER | UNIQUE, NOT NULL |
| descripcion | VARCHAR(50) | NOT NULL |
| orden | INTEGER | NOT NULL, default 0 |

### Distancias seed

| metros | descripcion | orden |
|--------|-------------|-------|
| 200 | 200 metros | 1 |
| 500 | 500 metros | 2 |
| 1000 | 1000 metros | 3 |
| 2000 | 2000 metros | 4 |

### Endpoints

| Método | Ruta | Acción |
|--------|------|--------|
| GET | `/config/distancias` | Lista distancias |
| POST | `/config/distancias` | Crear distancia |
| POST | `/config/distancias/{id}/edit` | Editar distancia |
| POST | `/config/distancias/{id}/delete` | Eliminar distancia |

**POST /config/distancias — form data:**
- `metros` (int, obligatorio): metros (único)
- `descripcion` (str, obligatorio): descripción
- `orden` (int, obligatorio): orden de visualización

**Uso:** Se usa en rankings, filtros, y selector de distancia de cada prueba.

---

## 6. Umbral de velocidad parado (/config/umbral)

### Modelo de datos

Almacenado en tabla `app_settings` (key-value):

| key | value | Descripción |
|-----|-------|-------------|
| `umbral_velocidad_parado` | `"1.50"` | Velocidad en km/h por debajo de la cual se considera "parado" |

### Endpoint

| Método | Ruta | Acción |
|--------|------|--------|
| GET | `/config/umbral` | Muestra formulario |
| POST | `/config/umbral` | Guardar umbral |

**POST /config/umbral — form data:**
- `umbral` (float): rango 0.5 - 20.0

**Uso:** Se usa en el análisis GPS para clasificar segmentos de movimiento/parado.

---

## 7. Telegram (/config/telegram)

### Estado actual

- Toggle on/off
- Token del bot
- Chat ID destino
- **Deshabilitado**: stub que imprime en consola

### Endpoint

| Método | Ruta | Acción |
|--------|------|--------|
| GET | `/config/telegram` | Muestra formulario |

**Campos:**
- Habilitado: toggle on/off
- Token del bot de Telegram
- Chat ID destino

**Comportamiento futuro:**
- Si habilitado: envía notificación al subir CSV con resumen de tiempos
- Si deshabilitado: stub que imprime en consola

---

## 8. Tabla AppSetting

### Modelo de datos

**Tabla `app_settings`:**

| Campo | Tipo | Constraints |
|-------|------|-------------|
| key | VARCHAR(64) | PK |
| value | VARCHAR(255) | NOT NULL |
| updated_at | DATETIME | DEFAULT now |

**Settings actuales:**
- `umbral_velocidad_parado`: velocidad parado (km/h)

### Repo functions

- `get_setting(key)` → value o None
- `set_setting(key, value)` → upsert
