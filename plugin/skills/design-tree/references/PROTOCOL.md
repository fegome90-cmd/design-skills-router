# Protocolo local y propiedad de datos

Este documento cierra las decisiones A01–A07 del plan. Describe validación local, no autenticación ni control global de herramientas. Código de referencia: `runner.py`, `contracts.py`, `assistance.py`, `migration.py`.

## Propiedad

| Dato | Dueño | Cambio permitido |
|---|---|---|
| Preguntas, alternativas, reglas y pins de skills | baseline v0.4 | Nueva versión de baseline; nunca override en contracts. |
| Relaciones adicionales y revisión de fuentes | contracts.json | Cambio revisado y nueva política; no duplica el árbol. |
| Hechos y evidencias de un proyecto | expediente externo | Actualización explícita, revisión creciente e invalidación relevante. |
| Nivel y límite de autonomía | mandato humano | Recibo específico; sin incremento implícito. |
| Prompts, iconos y audiencia | manifiestos vigentes | Preservar salvo autorización específica. |

## Relación tipada

`contracts.json` usa `schema=design-tree-contracts/0.2`, `baseline.tree_hash`, `relations`, `resources` y `source_reviews`. Una relación tiene `id`, `from_skill`, `target:{kind,id}`, `type`, `required`, `scope`, `applies_to`, `when`, `source:{url,commit,section}`, `provenance` y `evidence_status`.

`kind` es skill o resource. Tipos: delegates_to, requires_skill, routes_to, optional_companion, uses_resource. Ámbitos de operación: reference, product, preparation, verification, host. Una revisión de la fuente distingue lo leído de lo indexado; el estado no acredita ejecución. Una relación opcional no puede ser required=true. Una relación obligatoria activa exige revisión explícita, evidencia y el dominio correspondiente; los ciclos de prerrequisitos/delegaciones obligatorias se rechazan.

Los pasos internos de una skill permanecen en el original; el router no fabrica otra máquina de ejecución. En este release, las relaciones activas son las seis delegaciones de better-interface y su recurso review-format.md, fijado por Git blob. Otros requisitos no se inventan por similitud de tags. Las fuentes y apoyos que no se revisaron completamente permanecen señalados.

## Hechos y tabla de verdad

Hecho: `state=PRESENT|ABSENT|UNKNOWN`, `scope=project|component|requirement|host`, `subject`, `revision` entero creciente, `applies_to` (IDs o `*`), `evidence` y `value` cuando está PRESENT. `evidence_refs` se deriva de los archivos registrados. Un dato ausente del JSON no prueba ausencia del mundo.

Predicado: `{fact,op,value}` con eq, in o exists; in requiere lista. Eq e in comparan tipos exactos: true no equivale a 1. PRESENT con evidencia permite comparar; ABSENT con evidencia da FALSE; UNKNOWN, clave no disponible o evidencia insuficiente dan UNKNOWN.

| AND | TRUE | FALSE | UNKNOWN |
|---|---|---|---|
| TRUE | TRUE | FALSE | UNKNOWN |
| FALSE | FALSE | FALSE | FALSE |
| UNKNOWN | UNKNOWN | FALSE | UNKNOWN |

Conjunción vacía: TRUE. Un complemento expresamente no seleccionado es OPTIONAL_NOT_SELECTED, incluso con condición desconocida. Una operación fuera de ámbito es OUT_OF_OPERATION. Una relación sólo indexada no se vuelve obligación verificada: queda UNKNOWN al resultar candidata. UNKNOWN bloquea sólo sus resultados dependientes.

## Expediente 0.3

Conserva identidad de proyecto, scope, medium web, mode design/audit, revision, tree_hash, inventory_hash, structures, structure_sets, records, sources, candidates, facts, inventory_proposal/confirmation, grants, phase_map/hash/receipt, phases, active_phase_id, active_grant_id e history. Los campos normativos no se sustituyen por booleans de permiso.

Una propuesta conserva summary, selected, alternatives, skill_reviews, criterion_reviews, relation_reviews, evidence, candidate, verification y permission. Cada relación obligatoria se registra como `{relation_id,status:SATISFIED,reason,evidence_refs}`. No se permite omitir alternativas ni justificar con referencias inexistentes. OBSERVED/STATIC/NOT_VERIFIED describen evidencia, no una certificación global. `permission_to_execute` siempre es false.

El binding separa estructura, política, contexto, proyecto y autoridad. Contexto incluye scope y hechos relevantes con revisiones/evidencias; comentarios y fechas de lectura no invalidan por sí solos. En cada comprobación se reabren las evidencias y se revalida la propuesta completa. El memo interno sólo existe durante una lectura síncrona; nunca sobrevive a otra operación ni a una mutación.

`relation_reviews` no autentica que un juicio sea correcto. El operador debe aportar fuentes originales y la persona revisar la selección. Tampoco un SHA prueba comprensión. Para políticas de invocación, ausencia de una interpretación fijada al blob exacto queda UNKNOWN, nunca false inferido por regex; INVOKE continúa prohibido.

## Compatibilidad y migración

| Formato | Lectura diagnóstica | Ejecución/mutación actual |
|---|---|---|
| 0.1 válido | Inspección de bundle y dry-run | Sólo upgrade explícito hacia copia 0.3. |
| 0.2 válido | Diagnóstico, exportación íntegra y migración explícita | No operar sobre runtime 0.3 sin migración. |
| 0.3 válido | Doctor/status/resume | Operaciones actuales, con outcomes. |
| Corrupto/parcial/desconocido | Hallazgo y rechazo | Ninguna transformación automática. |

La migración conserva un `legacy_snapshot` completo como historia, copia/reubica evidencia verificada y conserva fuentes sin elevar su política. Inicia manual con nuevos records, grants, structures y phases vacíos: ninguna aprobación antigua valida obligaciones nuevas. Este release elige conservadoramente reabrir todas las decisiones migradas; no aplica una equivalencia no demostrada.

Exportación y migración preparan en staging junto al destino, validan y renombrarán sólo la salida íntegra. Destinos ocupados se rechazan; fallo de escritura elimina el staging y no publica una salida parcial. Un reintento conserva el original. Si un mismo path histórico aparece con hashes distintos, exportar se bloquea: guardar evidencia en archivos versionados inmutables, no sobrescribirla.

Rollback de código conserva ambos expedientes: no se ejecuta un runtime antiguo sobre estado 0.3 ni se borra trabajo reciente. Volver a una copia 0.1 es una decisión explícita; no constituye downgrade automático. La publicación de código anterior puede necesitar un número superior según el backend.


## Recursos y recuperación de fase

Una relación `uses_resource` exige `resource_id` y `resource_path` en su revisión. La ruta tiene que estar en `proposal.evidence` y en `evidence_refs`, y sus bytes deben coincidir con el `sha256` o `git_blob` de la definición del recurso. No basta citar otro archivo legible. La huella de política incluye los recursos de las relaciones aplicables.

Reabrir una fase conserva una copia íntegra del paquete y recibo previos en el historial, revoca el mandato activo y deja la fase y sus dependientes como STALE. Sus decisiones retiradas permanecen como historia; para reanudar hay que registrar un mandato nuevo. Una aceptación anterior no se sobreescribe silenciosamente ni se inventa para las propuestas revisadas.

Elegir auditoría mediante ENV02 impide propuestas de escritura también en ramas hermanas del encargo. No se cambia `mode` por detrás de una aprobación que ya está ligada a él. Para cambiar de intención hay que revisar explícitamente la pregunta correspondiente.


## Resultados normativos (nuevo en ledger/0.3)

`proposal.verification_results` utiliza el schema `design-tree-checks/1`
con `checks: [{id,result,method,scope,environment,observed_at,evidence_refs,reason}]`.
`environment` requiere `runtime`, `version` y `platform`; `observed_at`
es timestamp RFC3339 con zona. El resultado es PASS / FAIL /
NOT_APPLICABLE / UNVERIFIED. Métodos admisibles y ámbito: STATIC_REVIEW y
LOCAL_TEST → helper; BROWSER_OBSERVATION → browser; DEVICE_OBSERVATION →
device; HOST_OBSERVATION → host. No se permite elevar una prueba local al host.

La lista `contracts.json.verification_requirements` es la única propietaria
de `required`, `applies_to`, `scope`, `allowed_methods`, `when`, permisos de
N/A y justificación. Los datos del agente jamás amplían autoridad. El esquema
se valida y las obligaciones que afecten un nodo se vinculan a `policy_hash`.
Los predicados reutilizan la tabla trivalente: FALSE respaldado puede
justificar N/A si política lo permite; UNKNOWN exige evidencia antes de cierre.
Un campo opcional sin resultado no se convierte en obligatorio.

La propuesta registra honestamente FAIL/UNVERIFIED para diagnóstico, pero
un chequeo obligatorio pendiente o fallido no puede ser ratificado ni cerrar
fase. Reconsultar estado, preparar/aceptar fase y verificar vigencia releen
artefactos y obligaciones. Las comprobaciones no autentican a la persona ni
conceden ejecución externa.

Migración desde ledgers 0.1/0.2: `upgrade-state` hacia una copia 0.3 nueva;
conservar historia y evidencia originales, reiniciar manual y no convertir
OBSERVED/STATIC históricos a PASS. Una versión anterior del helper rechaza
0.3. No mutar un expediente antiguo en su lugar ni mezclarlo con uno nuevo.
