# Dragon Boat Analyzer — Specifications

Directorio de especificaciones del proyecto. Cada archivo documenta una parte del sistema y se versiona con el código en git.

## Archivos

### Principales

- `SPEC.md` — Especificación principal (visión general, navegación, modelo de datos, decisiones de diseño, estructura)
- `registros-detalle.md` — Registros + Detalle de Test (calendario, sesión del día, ECharts interactivo, mapa GPS, tripulación SVG, datos generales formato reporte)

### Por funcionalidad

- `navegacion.md` — Wireframes de cada pantalla, bottom nav, breadcrumbs, estados vacíos
- `api.md` — Todos los endpoints HTML y JSON con request/response schemas
- `tripulacion.md` — CRUD deportistas, asignación inline SVG, warnings, vista de sesión diaria
- `informes.md` — Upload CSV, análisis de tramos, gráficas (PNG + ECharts), reportes, backfill
- `configuracion.md` — Barcos, Categorías, Tipos, Distancias, Umbral, Telegram

### Base de datos

- `dragonboat.dbml` — Diagrama de base de datos (DBML)
- `dragonboat.sql` — SQL DDL generado desde DBML

## Convenciones

- Idioma: español
- Formato: Markdown plano (sin frontmatter)
- Alcance: una spec por tema
- Actualización: al inicio de cada sprint o cambio significativo en la arquitectura
- Los specs deben reflejar la implementación REAL, no estado aspiracional

## Stack técnico (resumen)

- **Backend:** Python 3.12 + FastAPI + Jinja2
- **DB:** SQLite WAL + SQLAlchemy 2.0 ORM
- **Frontend:** HTML + CSS (`base.css`) + vanilla JS
- **Gráficas web:** ECharts 5 (vendored en `static/vendor/`)
- **Gráficas PDF:** matplotlib
- **Mapa GPS:** Leaflet.js (CDN) con polilíneas coloreadas por velocidad
- **Procesamiento:** pandas, numpy, scipy

## Cambios recientes (2026-07)

- Reemplazo de Plotly por ECharts (vendored, sin CDN)
- Nuevo endpoint `GET /test/{id}/chart-data` con series 25Hz
- Edición de prueba ahora oculta por defecto (botón "Editar prueba ▾")
- Mapa GPS con polilínea coloreada por velocidad (gradiente 6 stops)
- Vista de sesión diaria (`sesion.html`) con métricas agregadas
- Columnas pre-calculadas: `sectores_detalle` y `paladas_detalle` en `test_metrics`
- Script de backfill: `dragonboat.tools.backfill_sectores_paladas`
- Nuevas secciones de config: Distancias, Umbral
- Datos generales en formato reporte (4 splits D/4, velocidad, paladas)

## Cómo contribuir

1. Leer `SPEC.md` para contexto general del proyecto
2. Crear un nuevo archivo `.md` en esta carpeta para specs temáticas
3. Actualizar este `README.md` con el link al nuevo archivo
4. Versionar todo junto con el código (mismo commit o PR)
