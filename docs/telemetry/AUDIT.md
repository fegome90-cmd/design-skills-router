# Telemetría global · auditoría, contratos y límites

Esta auditoría documenta la arquitectura, los contratos y la verificación del
subsistema opt-in de telemetría. El despliegue en producción queda fuera del
alcance de este repositorio.

> **Registros históricos:** [HARDENING-2026-11-18](HARDENING-2026-11-18.md) y
> [REAUDIT-2026-11-18](REAUDIT-2026-11-18.md) son registros inmutables de las
> rondas locales de endurecimiento previas a la publicación pública. Sus
> referencias a ramas/commits internos, el tope anterior de 200 eventos en
> outbox, los conteos previos de pruebas y las notas sobre `release/` o estado
> sin remoto quedan sustituidos por este documento y por
> [`telemetry/README.md`](../../telemetry/README.md).

## 1. Alcance auditado

| Componente | Estado en el repositorio |
| --- | --- |
| Plugin `design-tree` | Versión `0.3.1`, árbol canónico `tree-v0.4`, 82 skills inventariadas y contrato estricto de «sin red» en `runner.py`. |
| Pizarra HTML | Versión `v1.4` (con instrumentación opt-in en `release/design-router-pizarra-v1.4*.html` y `.preview/`) junto a `v1.3` congelada sin telemetría. |
| Subsistema `telemetry/` | Colector HTTP + SQLite WAL en biblioteca estándar Python, contrato opt-in, wrapper CLI, outbox del tablero, adaptador de host y dashboard estático. |

## 2. Principios del contrato y alternativas descartadas

El subsistema se diseñó para ser **opt-in**, **sin dependencias externas** y
**estrictamente verificable** sobre eventos reales:

- **OFF por defecto y validación explícita (`telemetry/contract.py`)**: exige
  habilitación explícita, presupuestos de timeout/tamaño y HTTPS fuera de
  loopback; rechaza credenciales en la URL y campos sensibles (prompts, rutas
  locales, texto libre).
- **Sin runtime externo obligatorio**: no depende de un servidor Fastify/Node,
  PostgreSQL desplegado ni de un Collector OpenTelemetry para funcionar en un
  entorno local o de CI; el esquema SQLite sigue siendo portable a PostgreSQL si
  el volumen exige múltiples réplicas.

## 3. Mapa de eventos y puntos de instrumentación

| Evento | Dónde se observa realmente | Evidencia | Límite |
| --- | --- | --- | --- |
| `router.invoked` | CLI: wrapper de proceso `telemetry/observe.py` tras una ejecución exitosa. Tablero: cada acción de evaluación del simulador (ruta, función, alcance, dominio, permiso, aplicabilidad). | Código de salida 0 + comando; `window.__minimalRouterPreview`. | Una invocación directa de `runner.py` no pasa por el wrapper. El plugin no puede instrumentarse por dentro sin romper su contrato de “sin red”. |
| `decision.node_visited` | CLI clásico y Typer a través de `observe.py`, al consultar `node`. | Comando exitoso y respuesta JSON de hasta 1 MiB. | La pizarra usa `nodesByFunction` para calcular selecciones y no registra visitas. |
| `decision.branch_selected` | CLI: comando `propose`, leyendo `selected` del archivo de propuesta y `node_id` del argumento. | Propuesta aceptada por el runner (salida 0). | No se emite en `confirm`; la rama se elige al proponer. |
| `skill.selected` | Tablero: contribuciones `support.read`/`support.write` de `resolveSelection`. | IDs estables del catálogo. | El CLI **no** lo emite: `packet.skills` es una lista de candidatas del nodo, no una selección algorítmica. Nunca es ejecución. |
| `skill.execution_started` | Sólo un host que controla la invocación, mediante `telemetry/host_adapter.py`. | Context manager alrededor de la llamada real; `source=host` obligatorio. | No hay host integrado en este repositorio. Cero eventos hasta que exista uno. |
| `skill.execution_completed` | Igual que el anterior, al salir sin excepción. | Context manager. | Sin `started` previo el colector rechaza el evento. |
| `skill.execution_failed` | Igual que el anterior, al salir con excepción. | Context manager. | Sin `started` previo el colector rechaza el evento. |

### Por qué no se instrumentó dentro de `runner.py`

`plugin/tests/test_portability.py::test_export_has_no_external_network_behavior`
prohíbe `urlopen(` e `import requests` en `runner.py`. El plugin se distribuye
como skill portable y declara “No network”. Añadir HTTP allí habría violado un
contrato probado. La frontera correcta es el proceso: el wrapper conserva
stdout, stderr y código de salida byte a byte.

## 4. Arquitectura implementada

```
CLI runner.py  ──(subprocess, sin red)──►  telemetry/observe.py
                                                │  eventos con IDs estables
                                                ▼
Tablero HTML  ──(fetch opt-in)──────────►  Colector HTTP (Python stdlib)
                                                │  SQLite WAL, un escritor
                                                ▼
                                        /v1/metrics + dashboard
```

- **Colector**: `telemetry/collector.py`, `ThreadingHTTPServer` + SQLite.
- **Store**: `telemetry/store.py`; eventos crudos aceptados como fuente de
  verdad; agregados calculados en consulta.
- **Contrato**: `telemetry/contract.py`; lista blanca de eventos y campos.
- **Cliente CLI**: `telemetry/client.py` + outbox local acotada.
- **Wrapper**: `telemetry/observe.py`; no modifica el plugin.
- **Tablero**: `board/src/telemetria/telemetria.js`, activado sólo si hay
  endpoint configurado.
- **Dashboard**: `telemetry/dashboard.html`, servido por el colector.
- **Adaptador de host**: `telemetry/host_adapter.py`, para ejecuciones reales
  cuando exista un host que las controle.

### Por qué SQLite y no Prometheus/OTel/PostgreSQL

| Alternativa | Decisión | Motivo |
| --- | --- | --- |
| Prometheus | Rechazada | Scrape muestreado, retención y cardinalidad operativa; no acredita eventos exactos ni históricos de selección/ejecución. |
| OpenTelemetry SDK/Collector | Rechazada para el mínimo | Añade dependencias de SDK/exportación y requiere desplegar un Collector externo para un problema de conteo exacto. |
| PostgreSQL dedicado | Rechazada para el mínimo | Requiere desplegar y operar un servidor de base de datos; el router no tiene backend permanente. El esquema es portable a PostgreSQL si el volumen lo exige. |
| SQLite central | **Elegida** | Cero dependencias, persistencia real, transacciones, idempotencia, consultas exactas y pruebas de concurrencia. Un proceso, un archivo. |

Límite explícito: SQLite es un almacén de un solo escritor. Para varias réplicas
del colector haría falta PostgreSQL (o un servicio equivalente). No se afirma
escalabilidad horizontal.

## 5. Reglas de contabilización

1. **Invocación**: un `router.invoked` aceptado. En CLI, sólo tras código de
   salida 0. En tablero, una acción de evaluación; los renders no cuentan.
   Incluye comandos de mantenimiento (`init`, `confirm`, etc.), por eso no es
   sinónimo de “evaluación”.
2. **Evaluación**: subconjunto de invocaciones: tablero o CLI `node`/`status`.
   Se informa separado de “invocaciones” para no mezclar lecturas del árbol con
   comandos de mantenimiento.
3. **Selección de skill**: una por `(evaluation_id, skill_id)`, sólo desde el
   tablero (`resolveSelection`). Un `skill.selected` repetido con otro
   `event_id` se descarta por índice único semántico. Las candidatas de
   `packet.skills` no cuentan.
4. **Visita de nodo**: una por `(evaluation_id, node_id)`, sólo desde CLI
   `node` (packet inspeccionado). El tablero no infiere visitas.
5. **Rama**: una por `(evaluation_id, node_id, branch_id)`, desde CLI
   `propose`.
6. **Precedencia**: los eventos de evaluación requieren un `router.invoked`
   previo con el mismo `evaluation_id`, en la base o antes en el mismo lote.
7. **Ejecución iniciada**: una por `execution_id`, sólo `source=host`.
8. **Completada/fallida**: una por `execution_id`, y sólo si existe el
   `started` correspondiente con el mismo `skill_id` e `instance_id`. Un
   terminal contradictorio se descarta como duplicado.
9. **Reintentos**: `event_id` es la clave de idempotencia; además hay índices
   semánticos para que un reintento con otro `event_id` no infle.
10. **Evaluaciones repetidas**: cada acción del usuario produce un
    `evaluation_id` nuevo; repetir la misma consulta cuenta como otra evaluación.
11. **Múltiples skills**: se emiten eventos separados; el total de selecciones
    puede superar el total de evaluaciones.
12. **Ejecuciones incompletas**: un `started` sin cierre queda como iniciado; no
    se inventa un resultado.
13. **Muestreo**: no se usa. Los agregados salen de eventos aceptados, no de
    trazas muestreadas.

## 6. Protección de datos

- Lista blanca estricta de campos por evento. Cualquier campo desconocido se
  rechaza; los nombres sensibles (`prompt`, `message`, `email`, `user_id`,
  `path`, `ip`, `reason`, etc.) tienen código propio.
- Sólo se envían IDs estables (`skill_id`, `node_id`, `branch_id`, `route`,
  `scope`, `function_id`), versiones, `command`, timestamps y un UUID de
  instalación aleatorio.
- No se guardan prompts, resúmenes, evidencia, rutas de archivo, URLs, correos,
  IPs, user-agent ni cookies.
- El colector no registra la IP del cliente; el logging HTTP está silenciado por
  defecto y, si se activa, no incluye dirección ni cuerpo.
- No hay identidad de usuario ni `distinct_id`. El UUID de instalación sólo
  evita colisiones y permite probar múltiples instancias; no se usa para
  segmentar personas.
- El tablero no envía nada si no hay endpoint configurado. La variante offline
  sigue siendo offline por defecto.

### Exposición del colector

- Por defecto escucha en `127.0.0.1`. Si se configura un host no loopback sin
  token, el proceso **se niega a arrancar**; el modo anónimo expuesto requiere
  `--allow-anonymous-writes` explícito.
- El token se compara con `hmac.compare_digest`; las escrituras exigen
  `Content-Type: application/json`, cuerpo máximo de 64 KiB y lote máximo de
  100 eventos.
- Las escrituras están acotadas por velocidad: tope global de eventos
  validados por ventana de 60 s (`--max-events-per-minute`, default 6000). El
  exceso recibe `429 RATE_LIMITED` con `Retry-After` y no se cuenta; `429` es
  retryable para ambos clientes (no está en su conjunto de rechazo
  permanente), así que el lote queda en la outbox y se reintenta.
- Como contrapartida visible, `data_quality` en `/v1/metrics` expone
  `instances`, `max_events_per_instance` y `possibly_inflated` (heurística de
  concentración: una instalación con ≥5000 eventos en la ventana). El
  dashboard lo muestra. Rotar `instance_id` evade la señal: es visibilidad,
  no atribución.
- Los errores de SQLite se aíslan como `503 STORE_UNAVAILABLE`; los errores
  internos como `500 INTERNAL_ERROR`, sin trazas ni detalles al cliente.
- CORS `*` sigue disponible como opt-in explícito (`--cors-origin '*'`, sólo
  redes controladas); un token embebido en un tablero público es visible para
  cualquier visitante: para exposición real, usa TLS/reverse proxy y
  restricciones de red, no un token de cliente público.
- Residuales aceptados: sigue sin haber prueba de legitimidad del escritor
  (un portador del token puede inflar contadores despacio dentro del tope);
  el header `Host` no se valida (una lectura por DNS rebinding expone los
  agregados sin PII; no se valida para no romper un reverse-proxy en
  loopback); el dashboard lleva `frame-ancestors 'self'` y no puede
  incrustarse en iframes de otro origen.
- Las lecturas `/v1/metrics` y `/` son agregados sin PII y no llevan token.
  Si el panel no debe ser público, protégelo en la red.

## 7. Límites no verificables en este entorno

- **Ejecución real de skills**. El host puede reportarla mediante
  `host_adapter.py`. Para estos eventos, `observed` indica que el subtipo aparece en
  la ventana. `observed_zero_events` indica cero eventos de ese subtipo en la
  ventana cuando el colector ya recibió al menos un inicio de ejecución.
  `schema_supported_no_emitter` indica que aún falta esa evidencia histórica.
- La observación del CLI requiere `observe.py` con telemetría habilitada.
  El runner clásico es el predeterminado y `--exec design-skills-router`
  ejecuta el Typer instalado. Las invocaciones directas quedan fuera del conteo.
- **Host/LLM**: no se observa si el host obedece la selección, si instala una
  skill o si ejecuta otra distinta.
- **Despliegue global**: no hay servicio desplegado ni credenciales. Las pruebas
  usan un colector local efímero.
- **Pizarra publicada**: `release/design-router-pizarra-v1.3.html` conserva su
  SHA-256 dorado congelado sin instrumentación. La pizarra publicada
  `release/design-router-pizarra-v1.4*.html` y las compilaciones de `.preview/`
  incluyen la instrumentación opt-in de telemetría.
- **PR remoto**: la evidencia de esta auditoría procede de pruebas locales.

## 8. Verificación ejecutada

| Comando | Resultado |
| --- | --- |
| `python3 -B -m unittest discover -s telemetry/tests` | 125 pruebas OK. Incluyen recuperación entre procesos, permisos de colas existentes, validación del acuse HTTP y reintento de una respuesta 422 truncada. |
| `node --test tests/telemetry-board.test.cjs` | 40 pruebas OK. Cubren el límite compartido de 1.000 eventos, compatibilidad con colas anteriores, revocación en pestañas abiertas, acuses y reintento tras 429. |
| `npm run test:telemetry:e2e` | Pizarra y dashboard en Chromium, colector HTTP con SQLite, revocación entre pestañas y selección de ventana ante respuestas fuera de orden. |
| `npm test` | 8 pruebas del núcleo + 11/11 del contrato semántico sobre v1.4. |
| `npm run test:golden` | 11/11 del contrato semántico y prueba offline sobre v1.3 congelada. |
| `npm run test:preview` | 11/11 semánticas, 7/7 mapa, 13/13 Playwright y offline sin solicitudes HTTP. |
| `(cd plugin && python3 -B -m unittest discover -s tests)` | 186 pruebas OK. |
| `python3 -B tools/verify_sources.py` | 238 propios, 2.096 externos, 71 del plugin y pizarra v1.3 verificados (requiere checkout completo con `vendor/`). |
| `python3 -B plugin/skills/design-tree/scripts/doctor.py --format json` | `exit_code=0`, sin hallazgos, paquete `CHECKED`. |
| Colector real + wrapper CLI | 2 invocaciones, 2 evaluaciones, 1 nodo, 0 selecciones CLI; ejecuciones en `schema_supported_no_emitter`. |

## 9. Estado de entrega

| Categoría | Contenido |
| --- | --- |
| **Observado** | El router no observa ejecuciones reales sin un host integrado y el plugin prohíbe acceso a red dentro de `runner.py` (`test_portability.py`). |
| **Implementado** | Colector SQLite + HTTP, contrato opt-in, wrapper CLI, cliente de tablero, outbox, adaptador de host, dashboard, pruebas y documentación. |
| **Probado** | Idempotencia, concurrencia, persistencia, multi-instancia, rechazo de campos sensibles, emparejamiento de ejecuciones, wrapper real y tablero real. |
| **No verificable aquí** | Ejecución real de skills sin host integrado; invocaciones directas de `runner.py` sin wrapper; despliegue global; verificación en un PR remoto. |

## 10. Comandos de reproducción

Sin dependencias externas (Python 3.10+ y Node.js 18+):

```sh
python3 -B -m unittest discover -s telemetry/tests -v
node --test tests/telemetry-board.test.cjs
npm test
(cd plugin && python3 -B -m unittest discover -s tests)
python3 -B plugin/skills/design-tree/scripts/runner.py verify-package
python3 -B plugin/skills/design-tree/scripts/doctor.py --format json
python3 -B tools/verify_sources.py  # requiere checkout completo con vendor/
```

Pruebas de navegador (requieren `npm ci` y `npx playwright install chromium`):

```sh
npm run test:golden
npm run test:preview
npm run test:telemetry:e2e
```
