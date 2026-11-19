# Mapa de código

| Si el cambio afecta a… | Empieza por | Verificación relacionada |
| --- | --- | --- |
| Un nodo, sus alternativas o su expediente | `plugin/skills/design-tree/scripts/runner.py` en `Router.packet`, `Router.active` y `Router.frontier`. Para la expansión de instancias, consulta `plugin/skills/design-tree/scripts/tree_model.py`. | Suite en `plugin/tests/`. El doctor comprueba el paquete y `verify-package` comprueba el baseline. |
| Un subcomando, su ayuda o sus errores | [runner.py](../../plugin/skills/design-tree/scripts/runner.py), función `main`. El [manual del CLI](../../plugin/skills/design-tree/references/CLI.md) describe los argumentos y el formato de los archivos de entrada. | [test_cli.py](../../plugin/tests/test_cli.py) invoca el proceso y comprueba la ayuda, stdout, stderr, el código de salida y los cambios en el expediente. |
| Las rutas de evidencia, la exportación o la recuperación | `Router.bind_evidence_paths` en el runner conserva la ubicación del archivo. [migration.py](../../plugin/skills/design-tree/scripts/migration.py) inspecciona, exporta y migra bundles. | [Portabilidad](../../plugin/tests/test_portability.py), [migración](../../plugin/tests/test_migration.py) y el caso de cambio de directorio en `test_cli.py`. |
| Una vista o su navegación | `board/README.md` orienta por vista. `board/src/board.template.html` contiene la estructura común. | Reconstruye el HTML antes de ejecutar `tests/router-v12.semantic.cjs`. |
| Las reglas del simulador de selección | `board/src/simulador/selection-core.cjs` expone `resolveSelection(input, { catalog, policy })`. Recibe ruta, alcance, función, dominio, permiso y revisiones del contexto activo. `selector.js` gestiona el DOM, la memoria de cada contexto y la descarga. `board/build.py` incrusta el módulo en el script del simulador. | `npm run test:core` ejecuta las pruebas de las reglas en Node.js. `npm run test:preview` comprueba la pizarra recién ensamblada. |
| Una decisión que apunta al código equivocado | `map/README.md`, `map/assemble_map.py` y `map/view.py`. | `tests/map-test.cjs` comprueba la vista del mapa en Chromium. |
| Una relación o propuesta de investigación | `semantic/PROCEDENCIA.md` y `board/src/relaciones/datos.json`. | Comprueba procedencia y estado de la relación antes de cambiar su ficha. |
| Una referencia a una skill | `docs/skills.md` registra la revisión. | En el checkout completo, `tools/verify_sources.py` verifica las fuentes fijadas. |
| Contadores de uso del router y las skills | `telemetry/contract.py`, `telemetry/store.py` y `telemetry/collector.py`. El CLI se observa con `telemetry/observe.py`; el tablero con `board/src/telemetria/telemetria.js`. | `npm run test:telemetry` y `npm run test:telemetry:e2e`. Límites en [auditoría](../telemetry/AUDIT.md). |

Consulta [operación y verificación](RUNTIME.md) para los comandos y sus requisitos.

## Consultar el selector desde Node.js

Desde la raíz del repositorio, simula una auditoría de escenario en G5. `reviews` recoge las revisiones del contexto activo por dominio, con registros `{ status, reason }`.

```sh
node <<'JS'
const { resolveSelection } = require('./board/src/simulador/selection-core.cjs');
const catalog = require('./board/src/mapa-funcional/datos.json');
const policy = require('./board/src/simulador/politica.json');

const { owners, selectedFunctions, permit, validation, completeness } = resolveSelection({
  route: 'auditoria',
  scope: 'scenario',
  domain: 'G5',
  permit: 'sandbox',
  reviews: { G7: { status: 'not_applicable', reason: 'La auditoría se limita a layout.' } }
}, { catalog, policy });
console.log({ owners, selectedFunctions, permit, validation, completeness });
JS
```

El resultado propone `G5` y limita el permiso simulado a `read`. `validation` informa los errores y `completeness` indica si la cobertura es completa y enumera los dominios pendientes. La respuesta también incluye `support.read` y `support.write` con los apoyos, y `nodesByFunction` con los IDs de los nodos por función seleccionada.

## Grafo de código con Graphify

Desde la raíz del router, genera el grafo con Graphify 0.9.26. La extracción estructural se ejecuta localmente y usa `.graphifyignore` para excluir las copias fijadas, el historial y los artefactos generados.

```sh
graphify extract . --code-only
graphify cluster-only . --no-label
```

Consulta el grafo desde la misma raíz.

```sh
graphify explain 'Router'
graphify path 'assemble_map.py' 'tree_model.py'
```

Una vez generado, abre el informe (`graphify-out/GRAPH_REPORT.md`) o el visor interactivo (`graphify-out/graph.html`). `graphify-out/` contiene las salidas locales y la caché. El visor carga vis-network desde un CDN. Las consultas de consola usan el JSON local.

Confirma las relaciones `INFERRED` en el código antes de usarlas como evidencia. Para los datos declarativos, estilos y plantillas, usa los puntos de entrada de la tabla y el [mapa de decisiones del plugin](../../map/README.md).
