# Arquitectura

| Componente | Responsabilidad y fuente |
| --- | --- |
| Modelo canónico y runtime | `plugin/skills/design-tree/references/tree-v0.4/tree.json` contiene el modelo declarativo. `plugin/skills/design-tree/scripts/runner.py` carga y verifica el baseline, expande el modelo y calcula los nodos activos y sus paquetes. |
| Contratos suplementarios | `plugin/skills/design-tree/references/contracts.json` declara relaciones condicionadas que `plugin/skills/design-tree/scripts/contracts.py` valida y evalúa. |
| Pizarra y simulador | `board/build.py` incrusta las fuentes de las vistas. El simulador usa `board/src/simulador/politica.json`. `tools/build.py` coordina el ensamblado de los HTML y el mapa. |
| Mapa navegable | `map/assemble_map.py` combina el árbol y las relaciones revisadas, comprueba referencias de archivo y símbolos, y genera el grafo que se incrusta con `map/view.py`. |
| Investigación y fuentes fijadas | `semantic/PROCEDENCIA.md` documenta los datos editables. `docs/skills.md` registra las revisiones de las skills. El índice de rutas vive en `vendor/index.json` del checkout completo. |
| Telemetría global | `telemetry/` contiene el contrato opt-in, el colector SQLite, el wrapper del CLI, el adaptador de ejecuciones y el dashboard. El plugin permanece sin red; la observación del CLI ocurre en el límite del proceso. Las reglas y límites están en `docs/telemetry/AUDIT.md`. |

## Fronteras de cambio

El árbol v0.4 tiene una huella verificada por `Router.verify_baseline` y sigue la política de mantenimiento de `plugin/skills/design-tree/references/MAINTENANCE.md`. Para una rama o regla canónica nueva, ese manual exige una nueva versión del baseline. Los expedientes se guardan fuera del plugin, según `plugin/AGENTS.md`.

Para una vista, empieza en las fuentes de la pizarra. Para una decisión en ejecución, usa el runner y sus contratos. Para ubicar archivos concretos, consulta el [mapa de código](CODEMAP.md).

## Expedientes y evidencia portable

El expediente conserva la referencia de evidencia que participa en los hashes de las propuestas. Al registrar una ruta relativa nueva, el runner guarda su ubicación en `artifact_paths`. Al recuperar un bundle, `resume` vincula esas referencias a los archivos de evidencia del bundle. Así, cambiar de directorio de trabajo conserva la identidad de la propuesta y el acceso a los mismos bytes.

`init` crea expedientes 0.3. `export` opera sobre un expediente 0.3 y `upgrade-state` recibe un bundle 0.1 o 0.2. Para un expediente antiguo suelto o para recuperar evidencia registrada antes de la vinculación de rutas, consulta [persistencia y migración](../../plugin/skills/design-tree/references/CLI.md#persistencia-y-migración).
