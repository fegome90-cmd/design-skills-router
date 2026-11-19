# Hardening de telemetría · 2026-11-18

Base auditada: `98d1b25` (`feat/global-telemetry`). Las correcciones de este
informe viven en el commit de hardening de la misma rama. No se modificó
`main`, no se reescribió historial y no se regeneró `release/`.

## G1 · Estado inicial reproducido

| Comprobación | Resultado |
| --- | --- |
| Rama / HEAD | `feat/global-telemetry` / `98d1b25` |
| Checkpoint ajeno | `b82ef46` |
| Worktrees | principal + dos worktrees preexistentes en `895533c` |
| Cambios sin confirmar | `.gitignore` y `assist/README.md` ajenos a este encargo; preservados |
| Diff de telemetría | 30 archivos, separado del checkpoint |
| `unittest telemetry/tests` | 51 OK |
| `node --test tests/telemetry-board.test.cjs` | 7 OK |
| `plugin/tests/test_portability.py` | 5 OK |
| `(cd plugin && python3 -B -m unittest discover -s tests)` | 179 OK |

## Hallazgos

No se encontró un P0 (corrupción silenciosa de totales ya aceptados, pérdida de
la base o ejecución remota de código). Sí se encontraron defectos P1 de
semántica, integridad, recuperación y aislamiento.

### P1-01 · Candidatas del packet contadas como skills seleccionadas

- **Archivo:** `telemetry/observe.py`, rama `node` de `observe()`.
- **Observado:** el wrapper emitía un `skill.selected` por cada entrada de
  `packet.skills`. Esa lista son candidatas asociadas al nodo, no una selección
  algorítmica. Inflaba el ranking de selecciones con skills que el router nunca
  eligió.
- **Reproducción:** `node Q00` real generaba `skill.selected` para
  `design-process-orchestrator` sin que existiera una selección de tablero.
- **Corrección:** se eliminó la emisión. `skill.selected` queda reservado a
  `resolveSelection` del tablero.
- **Regresión:** `test_node_emits_invocation_and_visit_but_not_candidate_skills`
  y `test_real_node_and_status_are_counted_without_candidate_skills`.

### P1-02 · Nodos inferidos contados como visitados

- **Archivo:** `board/src/telemetria/telemetria.js`, `buildEvaluationEvents`.
- **Observado:** el tablero emitía `decision.node_visited` desde
  `selection.nodesByFunction`. Ese mapa es un lookup derivado de la selección,
  no una visita al packet. Producía visitas que nunca ocurrieron.
- **Reproducción:** una selección `visual-qa` emitía `QA01` sin abrir ningún
  packet.
- **Corrección:** el tablero ya no emite `decision.node_visited`. La visita se
  cuenta sólo cuando el CLI ejecuta `node` y lee un packet real.
- **Regresión:** `evaluation events contain only observable board selections` y
  el E2E de tablero, que ahora exige ausencia de `decision.node_visited`.

### P1-03 · Eventos de evaluación aceptados sin invocación previa

- **Archivo:** `telemetry/store.py`, `_insert`.
- **Observado:** un `skill.selected`, `decision.node_visited` o
  `decision.branch_selected` se aceptaba con un `evaluation_id` inventado y sin
  `router.invoked`. El resultado era `skills_selected=1` con
  `evaluations=0`.
- **Reproducción:** `POST /v1/events` con un solo `skill.selected` devolvía
  `202 accepted` y el agregado mostraba una selección huérfana.
- **Corrección:** los eventos de evaluación exigen un `router.invoked` con el
  mismo `evaluation_id`, ya persistido o anterior en el mismo lote. Si falta,
  el lote se rechaza con `422 INVOCATION_NOT_RECORDED`.
- **Regresión:** `test_evaluation_scoped_events_require_a_prior_invocation` y
  `test_invocation_must_precede_evaluation_events_in_the_batch`.

### P1-04 · Ejecuciones aceptadas desde fuentes que no son host

- **Archivo:** `telemetry/contract.py`, `validate_event`; defensa adicional en
  `telemetry/store.py`.
- **Observado:** un cliente `source=cli` podía emitir `skill.execution_started`
  y `skill.execution_completed`; el colector las aceptaba y contaba. Eso
  permitía declarar ejecuciones que ningún host observó.
- **Reproducción:** dos POST con `source=cli` y el mismo `instance_id`
  producían `executions_started=1`, `executions_completed=1`.
- **Corrección:** los tres eventos de ejecución exigen `source=host`. El
  contrato responde `400 EXECUTION_SOURCE_MUST_BE_HOST`; el store aplica la
  misma regla si se lo usa directamente.
- **Regresión:** `test_execution_events_require_host_source` y
  `test_store_rejects_non_host_execution_even_if_called_directly`.

### P1-05 · Un lote envenenado bloqueaba toda la outbox

- **Archivo:** `telemetry/client.py`, `_post`, `flush_spool`.
- **Observado:** si el primer archivo `outbox-*.jsonl` recibía un rechazo
  permanente (por ejemplo `422 EXECUTION_NOT_STARTED`), `flush_spool` cortaba el
  bucle y todos los lotes posteriores quedaban bloqueados indefinidamente.
- **Reproducción:** dos archivos de spool; el primero con un `completed` huérfano
  y el segundo con una invocación válida. El segundo nunca se enviaba.
- **Corrección:** se distingue `ok`, `retry` y `reject`. Un rechazo permanente se
  mueve a `rejected-*.jsonl` y el bucle continúa; un fallo retryable conserva la
  outbox y corta. El lote actual rechazado también se cuarentena.
- **Regresión:** `test_permanent_rejection_is_quarantined_without_blocking_later_batches`
  y `test_current_batch_rejected_is_quarantined_not_retried`.

### P1-06 · Errores de SQLite rompían el handler HTTP

- **Archivo:** `telemetry/collector.py`, `do_GET` y `do_POST`.
- **Observado:** un `sqlite3.OperationalError` no capturado cerraba la conexión
  sin respuesta (`RemoteDisconnected`) y dejaba un traceback en stderr. Un
  bloqueo temporal o un fallo de disco no producía un error JSON manejable.
- **Reproducción:** store falso que lanza `database is locked`; POST y GET
  terminaban en conexión cerrada.
- **Corrección:** se devuelve `503 STORE_UNAVAILABLE` para errores de SQLite y
  `500 INTERNAL_ERROR` para errores internos, sin detalles ni trazas al cliente.
- **Regresión:** `test_store_failure_is_isolated_as_json_503` y
  `test_unexpected_store_failure_is_isolated_as_json_500`.

### P1-07 · Un fallo inesperado de telemetría cambiaba el exit code del CLI

- **Archivo:** `telemetry/observe.py`, `main`.
- **Observado:** el bloque de telemetría sólo capturaba
  `ContractError/ValueError/OSError`. Un `RuntimeError` en `client.flush()`
  producía traceback y exit 1 aunque el comando observado hubiera terminado 0.
- **Reproducción:** cliente falso cuyo `flush` lanza `RuntimeError`; el wrapper
  salía 1.
- **Corrección:** la frontera de telemetría captura `Exception` y preserva
  stdout, stderr y el código de salida del comando.
- **Regresión:** `test_unexpected_telemetry_failure_does_not_change_exit_or_output`.

### P1-08 · El adaptador de host podía romper la invocación real

- **Archivo:** `telemetry/host_adapter.py`.
- **Observado:** sólo capturaba `ValueError/OSError`; un error inesperado del
  cliente de telemetría se propagaba y podía reemplazar el resultado o la
  excepción de la skill.
- **Corrección:** `__enter__` y `__exit__` capturan `Exception`. La telemetría
  nunca altera la llamada del host.
- **Regresión:** `test_unexpected_telemetry_error_does_not_break_the_host_call`.

### P1-09 · Colector expuesto sin autenticación

- **Archivo:** `telemetry/collector.py`, `validate_exposure`, `make_server`,
  `main`.
- **Observado:** `--host 0.0.0.0` sin token arrancaba y aceptaba escrituras
  anónimas. Cualquiera en la red podía inflar contadores.
- **Corrección:** un listener no loopback exige token. El modo anónimo expuesto
  requiere `--allow-anonymous-writes` explícito. El binding por defecto sigue
  siendo `127.0.0.1`.
- **Regresión:** `test_non_loopback_listener_requires_token_or_explicit_override`
  y `test_cli_refuses_non_loopback_without_token`.

### P2-01 · Comparación de token no constante

- **Archivo:** `telemetry/collector.py`.
- **Corrección:** `hmac.compare_digest` sobre bytes. No se agregó una prueba de
  timing (no es estable en CI); sí sigue pasando la prueba funcional de token.

### P2-02 · Content-Type no validado

- **Archivo:** `telemetry/collector.py`, `do_POST`.
- **Corrección:** sólo `application/json` (con charset opcional). Otro tipo
  devuelve `415 CONTENT_TYPE_MUST_BE_JSON`.
- **Regresión:** `test_content_type_must_be_json`.

### P2-03 · Etiquetas semánticas ambiguas en el dashboard

- **Archivo:** `telemetry/dashboard.html`.
- **Observado:** `router.invoked` se etiquetaba “Evaluación iniciada” aunque
  incluye comandos de mantenimiento; nodos y selecciones no aclaraban su origen.
- **Corrección:** “Invocación exitosa registrada”, nota de nodos sólo CLI, nota
  de selecciones sólo tablero y línea de semántica en Procedencia. La tabla de
  ejecuciones distingue “sin emisor” (`schema_supported_no_emitter`) de “emisor
  presente, cero ejecuciones” (`observed_zero_events`), y el E2E cubre ambos
  estados y el error de consulta.

### P2-04 · Pérdida silenciosa al superar el límite de outbox

- **Archivo:** `telemetry/client.py`.
- **Estado:** aceptado y documentado. La outbox se acota a 100 archivos para no
  crecer sin límite; al superarlo se descarta el más antiguo. No se corrigió
  porque no hay un destino durable alternativo sin introducir otro backend.
  Es una pérdida explícita de telemetría bajo una caída prolongada, no una
  corrupción de contadores aceptados.

### P2-05 · Documentación desalineada

- **Archivos:** `docs/telemetry/AUDIT.md`, `telemetry/README.md`.
- **Corrección:** se eliminó la afirmación de que el CLI contaba selecciones y
  de que el tablero contaba visitas; se documentó la precedencia de invocación,
  la cuarentena de outbox y la exposición del colector.

## Pruebas de la corrección

| Suite | Resultado |
| --- | --- |
| `python3 -B -m unittest discover -s telemetry/tests` | 67 OK |
| `node --test tests/telemetry-board.test.cjs` | 7 OK |
| `npm run test:telemetry:e2e` | tablero 4 eventos, sin nodos inferidos; dashboard OK |
| `npm run test:preview` | 11/11 semánticas, 7/7 mapa, 11/11 Playwright, offline sin HTTP |
| `plugin/tests/test_portability.py` | 5 OK |
| `(cd plugin && python3 -B -m unittest discover -s tests)` | 179 OK |
| `npm test` | 7/7 núcleo + 11/11 semánticas |
| `tools/verify_sources.py` | 238 propios, 2.096 externos, 71 del plugin y pizarra v1.3 |

## Veredicto

**GO CON RESTRICCIONES.** El código queda apto para integrarse en la rama con
las correcciones aplicadas y las suites verdes: 67 pruebas de telemetría, 7 de
tablero, E2E de tablero/dashboard, 179 del plugin, 11/11 semánticas, 7/7 mapa,
11/11 Playwright, offline sin HTTP y fuentes verificadas. No queda apto para exposición
pública sin TLS/proxy, token y control de red; y los contadores de ejecución
seguirán en cero hasta que exista un host que use `host_adapter.py`.
Despliegue, merge, remote y PR son acciones pendientes de autorización.
