# Telemetría global · operación mínima

Contadores exactos y persistentes para el árbol de decisiones y las skills del
Design Skills Router. No es una plataforma de analítica general.

## Componentes

| Archivo | Función |
| --- | --- |
| `contract.py` | Contrato de eventos, configuración opt-in y validación. |
| `store.py` | SQLite WAL, idempotencia semántica, agregados exactos. |
| `collector.py` | HTTP mínimo: `POST /v1/events`, `GET /v1/metrics`, `GET /`, `/healthz`. |
| `client.py` | Cliente opt-in con outbox local acotada. |
| `observe.py` | Wrapper del CLI del plugin; no modifica el plugin. |
| `host_adapter.py` | Context manager para hosts que sí ejecutan skills. |
| `dashboard.html` | Vista compacta de métricas reales. |

## Arranque local

```sh
python3 -B -m telemetry.collector --db var/telemetry.sqlite3 --port 8787
```

Abre <http://127.0.0.1:8787/>. El dashboard no inventa datos: si no hay eventos,
lo dice; si no hay emisor de ejecuciones, muestra `schema_supported_no_emitter`.

### Opciones del colector

| Flag | Default | Uso |
| --- | --- | --- |
| `--db` | `var/telemetry.sqlite3` | Archivo persistente. |
| `--host` | `127.0.0.1` | `0.0.0.0` sólo detrás de TLS/proxy. |
| `--port` | `8787` | Puerto. |
| `--token` | `DESIGN_ROUTER_TELEMETRY_COLLECTOR_TOKEN` | Exige `Authorization: Bearer` en escrituras. Obligatorio si el host no es loopback, salvo `--allow-anonymous-writes`. |
| `--cors-origin` | `loopback` (o `DESIGN_ROUTER_TELEMETRY_CORS`) | Política de origen cruzado para navegadores: `loopback` (sólo orígenes localhost), `none`, una URL de origen explícita, o `*` (cualquier sitio web puede escribir; sólo redes controladas). |
| `--max-events-per-minute` | `6000` (o `DESIGN_ROUTER_TELEMETRY_MAX_EVENTS_PER_MINUTE`) | Tope global de eventos validados por ventana fija de 60 s (alineada, no deslizante). Mínimo 100 (un lote completo): un tope menor dejaría lotes mayores en reintento perpetuo. El exceso recibe `429` con `Retry-After` y los clientes lo reintentan; nunca se cuenta. |
| `--verbose` | apagado | Logging sin IP ni cuerpos. |
| `--allow-anonymous-writes` | apagado | Permite escrituras sin token en un listener no loopback. Sólo con control de red. |

Las lecturas `/v1/metrics` y `/` no llevan token: son agregados sin PII. Si el
panel no debe ser público, protégelo en el proxy de red. Un token enviado al
tablero queda visible en el navegador; úsalo para CLI/host y controla las
escrituras del tablero en la red, no como secreto de un cliente público.

El colector rechaza escrituras sin `Content-Type: application/json`, cuerpos
mayores de 64 KiB y lotes de más de 100 eventos, y acota la velocidad con un
tope global de eventos por minuto (`429 RATE_LIMITED` con `Retry-After`;
retryable para ambos clientes, nunca contado). Los errores de SQLite se
devuelven como `503 STORE_UNAVAILABLE`, sin trazas, y el dashboard lleva
`frame-ancestors 'self'` (no puede incrustarse en iframes de otro origen).

Sigue sin haber prueba de legitimidad del escritor: un portador del token
puede inflar contadores despacio (rotando `instance_id` evade la señal). Como
contrapartida visible, `data_quality` en `/v1/metrics` expone `instances`,
`max_events_per_instance` y `possibly_inflated` (heurística de concentración:
una instalación que aporta ≥5000 eventos en la ventana). El colector asume
confianza local o una red controlada.

Residuales conocidos: el header `Host` no se valida (una lectura por DNS
rebinding expone los agregados sin PII; no se valida para no romper un
reverse-proxy en loopback) y las lecturas de `/v1/metrics` y `/` no llevan
token.

## Instrumentar el CLI

El plugin no tiene red por contrato. Inicializa primero un expediente (si aún no existe) y luego usa el wrapper:

```sh
python3 -B plugin/skills/design-tree/scripts/runner.py --state /ruta/ledger.json \
  init --project-id demo --scope "Proyecto de prueba"

DESIGN_ROUTER_TELEMETRY=1 \
DESIGN_ROUTER_TELEMETRY_URL=http://127.0.0.1:8787 \
python3 -B telemetry/observe.py -- --state /ruta/ledger.json node Q00
```

El wrapper reenvía todos los argumentos, conserva stdout/stderr/código de salida
y sólo agrega eventos después de un resultado exitoso. Comandos observados:

- `node`: invocación + nodo visitado. **No** emite `skill.selected`: las
  skills del packet son candidatas, no una selección algorítmica.
- `status`: invocación.
- `propose`: invocación + rama elegida.
- Cualquier otro comando exitoso: invocación con `command`.

Una ejecución directa de `plugin/skills/design-tree/scripts/runner.py` no se
cuenta. Es un límite deliberado.

### Variables

| Variable | Requerida | Efecto |
| --- | --- | --- |
| `DESIGN_ROUTER_TELEMETRY` | sí, exactamente `1` | Activa. Sin esto, todo es no-op. |
| `DESIGN_ROUTER_TELEMETRY_URL` | sí | `https://…` o `http://` sólo loopback. Sin credenciales, path, query ni fragmento. |
| `DESIGN_ROUTER_TELEMETRY_TOKEN` | no | Bearer para escrituras. |
| `DESIGN_ROUTER_TELEMETRY_TIMEOUT` | no | 0.1–5 s; default 0.5. |
| `DESIGN_ROUTER_TELEMETRY_STATE` | no | Directorio de instancia/outbox. |

La configuración falla cerrada: si está activada pero la URL es inválida, no se
envía nada. Los fallos de red no cambian el comando observado; los lotes no
entregados quedan en `outbox-*.jsonl`. La outbox compacta: cada archivo
almacena hasta 100 eventos (un lote POST), de modo que el máximo de 100
archivos representa hasta 10.000 eventos (~5.000 corridas `node`); al
superarlo se descarta el archivo más antiguo. La compactación no preserva
estrictamente el orden de entrega entre archivos: los agregados son
insensibles al orden y el store deduplica por `event_id`. Un lote rechazado
de forma permanente (`400`, `413`, `415`, `422`) se mueve a `rejected-*.jsonl`
y no bloquea los lotes posteriores. Un `429` del tope por minuto es retryable:
el lote queda en la outbox y se reintenta.

## Instrumentar el tablero

El tablero carga `board/src/telemetria/telemetria.js` al final. Sin endpoint, no
hace nada. Para activarlo en el navegador:

```js
DesignRouterTelemetry.configure('http://127.0.0.1:8787');
location.reload();
```

O antes de cargar:

```js
window.DESIGN_ROUTER_TELEMETRY = { endpoint: 'http://127.0.0.1:8787' };
```

Emite `router.invoked` y `skill.selected` por cada acción de evaluación. **No**
emite `decision.node_visited`: `nodesByFunction` es un lookup de la selección,
no una visita al packet. No emite ejecuciones. Un outbox en `localStorage`
acotado a 1000 eventos (~330-1000 evaluaciones, ~372 KiB) reintenta si el
colector cae —al superarlo conserva los 1000 eventos más recientes; si un corte
divide la evaluación más antigua, el colector pone en cuarentena los eventos
huérfanos al reintentar—; no es la fuente de verdad.

La instrumentación opt-in se ensambla en las fuentes, en `.preview/` y en la
pizarra publicada `release/design-router-pizarra-v1.4*.html`. El HTML dorado
congelado `release/design-router-pizarra-v1.3.html` conserva su SHA-256 sin
modificaciones ni telemetría.

## Instrumentar un host que ejecuta skills

Sólo si el host controla realmente la invocación:

```python
from telemetry.client import client_from_env
from telemetry.host_adapter import observe_execution

client = client_from_env()
with observe_execution(client, "emilkowalski/skills/break-ui"):
    host.invoke_skill("break-ui")
```

El colector rechaza un `completed`/`failed` sin `started` previo. Sin host
integrado, los contadores de ejecución permanecen en cero y así se muestran.

## Consultas

```sh
curl 'http://127.0.0.1:8787/v1/metrics?window=all'
curl 'http://127.0.0.1:8787/v1/metrics?window=30d&limit=50'
curl 'http://127.0.0.1:8787/v1/metrics?since=2026-11-01T00:00:00Z'
```

Campos principales:

- `totals.invocations`, `totals.evaluations`.
- `totals.skills_selected`, `totals.nodes_visited`, `totals.branches_selected`.
- `totals.executions_started/completed/failed`.
- `skills[]`, `skills_executed[]`, `nodes[]`, `branches[]`, `routes[]`, `daily[]`.
- `observability` distingue `observed`, `observed_zero_events` y
  `schema_supported_no_emitter`.
- `data_quality.sampling = false`; `data_quality.instances`,
  `max_events_per_instance` y `possibly_inflated` exponen la señal de
  concentración por instalación (heurística, no prueba de inflado).

Histórico crudo, si hace falta auditar:

```sh
sqlite3 var/telemetry.sqlite3 \
  "SELECT occurred_at, name, skill_id, node_id, evaluation_id FROM events ORDER BY occurred_at;"
```

## Pruebas

```sh
python3 -B -m unittest discover -s telemetry/tests -v
node --test tests/telemetry-board.test.cjs
```

Cubren: contrato y campos sensibles, configuración OFF/ON, idempotencia,
emparejamiento de ejecuciones, precedencia de invocación, concurrencia,
persistencia tras reinicio, múltiples instancias, outbox con compactación,
evicción y cuarentena, tope por minuto (429 retryable), señal de concentración,
aislamiento de errores, exposición del colector, wrapper real del CLI y eventos
del tablero.
