# Dragon Boat Analyzer — Specifications

Directorio de especificaciones del proyecto. Cada archivo documenta una parte del sistema y se versiona con el código en git.

## Archivos

- `SPEC.md` — Especificación principal del proyecto (visión general, navegación, secciones, modelo de datos, rutas, decisiones de diseño)
- `registros-detalle.md` — Rediseño de Registros (calendario + tabla interactiva) y Detalle de Test (7 bloques: navegación, métricas + editar, mapa GPS, gráfica, datos generales, tripulación interactiva SVG, eliminar prueba)

## Convenciones

- Idioma: español
- Formato: Markdown plano (sin frontmatter)
- Alcance: una spec por tema (ej: `navegacion.md`, `api.md`, `tripulacion.md`)
- Actualización: al inicio de cada sprint o cambio significativo en la arquitectura

## Cómo contribuir

1. Leer `SPEC.md` para contexto general del proyecto
2. Crear un nuevo archivo `.md` en esta carpeta para specs temáticas
3. Actualizar este `README.md` con el link al nuevo archivo
4. Versionar todo junto con el código (mismo commit o PR)
