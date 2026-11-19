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
| `observe.py` | Observa el runner clásico o el ejecutable instalado de Design Skills Router. |
| `host_adapter.py` | Context manager para hosts que sí ejecutan skills. |
| `dashboard.html` | Vista compacta de métricas reales. |

## Arranque local

```sh
python3 -B -m telemetry.collector --db var/telemetry.sqlite3 --port 8787
```

Abre <http://127.0.0.1:8787/>. Mientras el colector carezca de eventos históricos
de ejecución de un host, el dashboard muestra `schema_supported_no_emitter`.

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

Desde la raíz del repositorio, inicializa un expediente si aún no existe y
activa la telemetría para la sesión de terminal:

```sh
python3 -B plugin/skills/design-tree/scripts/runner.py --state /ruta/ledger.json \
  init --project-id demo --scope "Proyecto de prueba"

export DESIGN_ROUTER_TELEMETRY=1
export DESIGN_ROUTER_TELEMETRY_URL=http://127.0.0.1:8787
```

Para observar el **runner clásico**:

```sh
python3 -B telemetry/observe.py -- --state /ruta/ledger.json node Q00
```

Para observar el **CLI Typer instalado**, invoca su ejecutable por nombre
(si está en `PATH`) o pasa la ruta completa de su entorno virtual:

```sh
python3 -B telemetry/observe.py --exec design-skills-router -- --state /ruta/ledger.json node Q00
```

`--exec` usa el intérprete del propio ejecutable. Para un archivo Python que
deba ejecutarse con el intérprete del observador, usa `--runner ruta/runner.py`.
Los argumentos después de `--` pasan intactos al CLI. La observación es
explícita por invocación: si llamas directamente a cualquiera de los dos CLI,
el colector no recibe eventos de ese comando.

El observador reenvía stdout y stderr durante la ejecución y conserva el código
de salida. Ambos CLI usan la fuente `cli` y generan los mismos eventos:

- Un `node` exitoso emite una invocación y, si su respuesta es un packet JSON
  válido de hasta 1 MiB, una visita al nodo. Una respuesta mayor se muestra
  completa y solo cuenta la invocación. Las skills del packet son candidatas.
- `propose` emite una invocación y la rama elegida cuando el archivo de propuesta
  contiene `selected`.
- `status` y los demás comandos exitosos emiten una invocación. La ayuda y los
  comandos que terminan con error no se cuentan.

### Variables

| Variable | Requerida | Efecto |
| --- | --- | --- |
| `DESIGN_ROUTER_TELEMETRY` | sí, exactamente `1` | Activa. Sin esto, todo es no-op. |
| `DESIGN_ROUTER_TELEMETRY_URL` | sí | `https://…` o `http://` sólo loopback. Sin credenciales, path, query ni fragmento. |
| `DESIGN_ROUTER_TELEMETRY_TOKEN` | no | Bearer para escrituras. |
| `DESIGN_ROUTER_TELEMETRY_TIMEOUT` | no | 0.1–5 s; default 0.5. |
| `DESIGN_ROUTER_TELEMETRY_STATE` | no | Directorio de instancia/outbox. |

Una URL inválida desactiva el envío. Ante un fallo transitorio, como un
`429` o `503`, el cliente guarda los eventos en el directorio de estado,
en `collectors/<sha256-del-endpoint>/outbox-*.jsonl`. Al volver a usar ese
endpoint, reintenta sus pendientes antes de enviar los eventos nuevos. Cada
colector admite hasta 100 archivos de 100 eventos. Al alcanzar el límite,
el cliente puede descartar el archivo más antiguo. Un rechazo permanente se
guarda en `rejected-*.jsonl` junto a la cola de ese colector. Varios procesos
pueden compartir el directorio. Mientras uno reenvía un lote, los demás
pueden guardar los suyos. Al compactar la cola, el cliente escribe el lote en
un archivo nuevo para que un acuse tardío de la versión anterior sólo retire
el archivo que esa versión llegó a enviar. Si pierde el permiso de lectura
sobre un archivo y el directorio permite moverlo, lo aparta en cuarentena y
continúa con los lotes siguientes.

Ambos clientes confirman la entrega cuando el colector devuelve HTTP 202
con el esquema `design-router-telemetry/1` y la suma de `accepted` y
`duplicates` coincide con el tamaño del lote. Una respuesta HTML o un acuse
incompleto deja el lote pendiente.

Al actualizar, los archivos antiguos en la raíz del directorio de estado
quedan disponibles para inspección local. Como esos archivos carecen de
destino registrado, el cliente no los reenvía automáticamente.

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

El límite se comparte entre las pestañas del mismo origen que escriben al
mismo colector. Los eventos nuevos se guardan por separado y la pizarra
también recupera las colas anteriores en fragmentos. Ambas versiones pueden
coexistir durante una actualización. Al comparar ambos formatos para aplicar
el límite, la pizarra usa la fecha del evento. Un empate conserva el evento del
formato anterior. Si el navegador agota la cuota de almacenamiento, conserva
lo que ya está guardado. Cuando aún quedan cupos dentro del límite de 1.000,
la pestaña productora mantiene en memoria la parte inicial de la evaluación
que cabe en esos cupos y puede enviarla mientras siga abierta. Con los 1.000
cupos ocupados, un evento nuevo sólo desplaza a otro tras guardarse. Ante un
HTTP 429, una pestaña abierta programa su reintento
según `Retry-After`.

La cola de la pizarra y los rechazos pertenecen a la URL de ingesta
configurada, incluida su ruta y consulta. Si cambias de
colector, los pendientes esperan hasta que vuelvas a usar el original. Las
colas antiguas sin destino permanecen en el navegador para inspección local.
Con la telemetría desactivada, el cliente tampoco crea un ID de instalación.
`DesignRouterTelemetry.configure(null)` desactiva los envíos en las pestañas
que usan esa configuración compartida. Las páginas con un endpoint explícito
en `window.DESIGN_ROUTER_TELEMETRY` se rigen por ese valor.

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
