# Contexto

## Qué reúne el repositorio

Design Skills Router reúne un plugin que guía decisiones de diseño, una pizarra que permite inspeccionar el árbol y su relación con el código, y telemetría opt-in. Sirve a quien investiga rutas de diseño y a quien mantiene el plugin o la pizarra. El repositorio reúne la pizarra v1.4 (con v1.3 congelada), el plugin 0.3.1 y el árbol canónico v0.4, según `README.md` y `plugin/.codex-plugin/plugin.json`.

## Cómo leer las capas

- Una **declaración** define un nodo del árbol. Una **ocurrencia** es su aparición expandida en un recorrido concreto. `map/README.md` explica cómo buscarlas y rastrear su implementación.
- Las fichas y relaciones de investigación expresan estados distintos. Consulta `semantic/PROCEDENCIA.md` para identificar las propuestas y la evidencia de cada versión.
- El [catálogo de skills](../skills.md) registra las revisiones que usa cada inventario. Sus fuentes fijadas y el índice JSON están en `vendor/` del checkout completo.

## Trabajo planificado

El [piloto G5](../../plugin/skills/design-tree/references/CLI.md#piloto-g5-de-contexto-por-nodo) ofrece un MCP local para una decisión de auditoría web. El [plan MCP](../Plan_MCP_Design_Router.md) describe la ampliación a otros recorridos. El [contrato R01](../specs/mcp-roadmap/units/R01-registro-compartido-de-tools.md) fija la paridad CLI/MCP y el [dossier R01](../specs/mcp-roadmap/research/R01-dossier-v0.1.md) registra la investigación y la decisión.

El [plan de calidad en CI](../specs/calidad/plan-ci-calidad.md) convierte los defectos hallados en R01 en controles automáticos: codificación explícita en Python, documentación verificable y reglas para los revisores.
