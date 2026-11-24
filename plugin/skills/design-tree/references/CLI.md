# CLI — expediente 0.3, Python 3.10+

Usa sólo biblioteca estándar. Comandos desde la raíz del paquete con `python3 -B skills/design-tree/scripts/runner.py`. Resolver la ruta real desde el host; nunca suponer instalación. Estado, fuentes y evidencias van fuera del plugin. JSON por stdout; gates rechazados salen con código 2. No hay red, instalación ni ejecución de producción.

## Inspección e inicio

```sh
python3 -B skills/design-tree/scripts/runner.py verify-package
python3 -B skills/design-tree/scripts/doctor.py --format json
python3 -B skills/design-tree/scripts/runner.py --state /proyecto/ledger.json init --project-id mi-web --scope 'Una pantalla; no publicar' --medium web --mode design
python3 -B skills/design-tree/scripts/runner.py --state /proyecto/ledger.json node Q00
python3 -B skills/design-tree/scripts/runner.py --state /proyecto/ledger.json status
```

`verify-package` sólo comprueba el baseline; doctor abarca el paquete. `node` es lectura, no aprobación ni consulta automática de la fuente externa. La sesión inicia manual. `--mode audit` sólo permite propuestas read_only. Las rutas especializadas conservan sus bloqueos.

## Recibos humanos — nunca copiar como autorizaciones

Formato: `{role:"user",kind,target_hash,message_ref,quote}`. Los valores deben venir de un mensaje humano observado que acepte el objeto exacto mostrado. `kind` distingue structure, structure_set, project, inventory, phase_map, delegation, phase o reopen. El helper comprueba forma y binding, no autentica identidad ni comprende las palabras. Un ejemplo, una respuesta del agente o una instalación no son autorizaciones.

## Confirmar estructura y límites sin repetir preguntas

```sh
python3 -B skills/design-tree/scripts/runner.py phase-template > /proyecto/phase-map-proposal.json
python3 -B skills/design-tree/scripts/runner.py structure-manifest --nodes ALL > /proyecto/structure-proposal.json
```

Son propuestas, no estados. No imprimir miles de IDs en el chat: conservar el archivo exacto y presentar una síntesis con sus límites. El usuario puede confirmar ambos conjuntos en un encuadre.

`configure --file` recibe un objeto JSON con los campos `phase_map` y `receipt`. El recibo apunta al hash del mapa. Si falta alguno de los dos campos, el comando termina con código 2 e indica ambos nombres. `structure-set --file` recibe `{node_ids,receipt}` y usa el hash de structure-manifest. Los contenidos originales se conservan; no simular una aprobación por nodo.

```sh
python3 -B skills/design-tree/scripts/runner.py --state /proyecto/ledger.json configure --file /proyecto/confirmed-map.json
python3 -B skills/design-tree/scripts/runner.py --state /proyecto/ledger.json structure-set --file /proyecto/confirmed-structure.json
```

Para una única estructura activa: `structure Q00 --file receipt.json` conserva el formato anterior. Estructura confirmada no acepta respuestas del proyecto.

## Mandato por fase

```sh
python3 -B skills/design-tree/scripts/runner.py --state /proyecto/ledger.json grant-template foundations --level phase_auto > /proyecto/grant-template.json
```

Tomar `grant`, sustituir message_ref/quote por la autorización real y fijar allowed_actions y reserved_decisions según el encargo. Guardar sólo ese objeto en grant.json. Recalcular el paquete después de editarlo:

```sh
python3 -B skills/design-tree/scripts/runner.py --state /proyecto/ledger.json grant-packet --file /proyecto/grant.json > /proyecto/grant-packet.json
python3 -B skills/design-tree/scripts/runner.py --state /proyecto/ledger.json grant --file /proyecto/authorized-grant.json
```

El segundo archivo tiene `{grant,receipt}` con kind delegation y target_hash exacto del paquete. No usar los textos REPLACE_WITH como aprobación. Niveles: manual/guided/phase_auto. Reservas: IDs de nodo o definición. La fase debe estar autorizada y sus dependencias aceptadas. No se activa por preferencia del agente.

## Fuentes

Recuperar el original por repositorio/ruta/commit del paquete de nodo usando conector compatible. Guardar bytes completos y SHA Git blob devuelto por la fuente. No confundir SHA de commit, tree o blob. El comando source es recepción local, no lectura semántica ni invocación.

```sh
python3 -B skills/design-tree/scripts/runner.py --state /proyecto/ledger.json source --skill ID_SKILL --file /proyecto/sources/archivo.md --commit SHA_COMMIT --git-blob SHA_BLOB --source-ref REFERENCIA_REAL
```

Los apoyos requeridos por un criterio también se consultan y registran como evidencia. Metadatos desconocidos permanecen UNKNOWN; sólo se permite REFERENCE_ONLY. Actualizar un pin canónico requiere otra versión del baseline, no editar un contrato suplementario.

### Piloto G5 de contexto por nodo

Crea un expediente nuevo de auditoría web con `init --mode audit --context-pilot`. Configura la fase y registra un mandato asistido que cubra las acciones `analyze` y `draft`. El piloto aplica a la decisión `E05__LAY01`. Para un encargo acotado, el mapa de fase puede incluir esa decisión y sus resultados `E05__LAY01_1`, `E05__LAY01_2` y `E05__LAY01_3` en la familia `visual`. Los ancestros conservan sus comprobaciones habituales.

```sh
design-skills-router --state /proyecto/ledger.json context-next
design-skills-router --state /proyecto/ledger.json context-open E05__LAY01
design-skills-router --state /proyecto/ledger.json context-search E05__LAY01 --query jerarquia
```

Registra las dos fuentes del nodo con `source`. `context-open` devuelve las secciones obligatorias del cuerpo, el contexto vigente y un `context_id`. `section_ids.skills` identifica el pasaje principal de cada skill. `section_ids.criteria` identifica todos los pasajes asignados al criterio en `rules.json`. Para `layout`, son cuatro pasajes de `better-layout`. El índice `ledger.json.context.sqlite3` se crea junto al expediente, requiere SQLite con FTS5 y se puede reconstruir desde las fuentes registradas.

Si el índice pierde filas, la siguiente consulta lo regenera desde esas fuentes. Ante `CONTEXT_INDEX_UNAVAILABLE`, conserva el expediente y aparta el índice después de cerrar los procesos del router. Vuelve a ejecutar `context-open` para regenerarlo.

Para `propose`, incluye `context_id`, `verification: OBSERVED` y una evidencia PNG con su SHA-256. Cada entrada de `skill_reviews` cita su `section_id`. Cada entrada de `criterion_reviews` cita la lista completa de `section_ids` de su regla. Ambas registran una `observation`, vinculan la captura en `evidence_refs` y conservan la justificación. Si el paquete preparado es anterior a este contrato, ejecuta `context-open` otra vez antes de presentar una propuesta nueva. Las propuestas ya registradas se comprueban según su paquete original.

Una sección ausente, un paquete de otro contexto o una captura con datos incompletos impiden presentar la decisión. El expediente guarda en cada propuesta los hashes de su paquete, incluso al reabrir la fase. El mandato del piloto autoriza análisis y borrador. La decisión de G5 requiere `confirm`, también si un expediente anterior trae una decisión delegada que sigue sin ratificar. Si el expediente anterior conserva el paquete original, el runner lo adjunta al registro al confirmar o reabrir. El runner vuelve a comprobar la evidencia al ratificar, incluidos los datos del PNG, el hash y el vínculo con las secciones. La procedencia de la captura y la pertinencia del juicio se revisan con la persona.

Si una fase anterior ya esperaba aceptación con una decisión delegada de G5, usa `phase-reopen` con un recibo humano para volver a preparar la fase. El expediente conserva el paquete anterior como historial.

Con la CLI instalada con el extra `[mcp]`, ejecuta `design-skills-router --state /proyecto/ledger.json mcp` como servidor local stdio. Las herramientas `next_node`, `open_node`, `search_context` y `submit_evidence` usan ese expediente. `submit_evidence` requiere `expected_revision` y rutas absolutas bajo `/proyecto/evidence/`. Presenta una propuesta pendiente de aprobación. El host conserva su propia observación de qué contenido incorporó al contexto del modelo.

## Propuesta y decisión

Objeto de propuesta:

- summary, selected (hijo elegido, null en all/result).
- alternatives: todas las ramas con node_id, disposition SELECTED/REJECTED o REQUIRED para all, reason.
- skill_reviews: todas las skills con skill_id, status APPLIED/REVIEWED_NOT_APPLICABLE, rationale, evidence_refs y use REFERENCE_ONLY.
- criterion_reviews: todas las reglas con rule_id, disposition APPLIED/NOT_APPLICABLE, reason, evidence_refs.
- relation_reviews: obligaciones del nodo con relation_id, status SATISFIED, reason y evidence_refs. Ninguna obligación puede desaparecer por nivel de asistencia.
- evidence: archivos reales con path, sha256 y note; references sólo a estas rutas o recibos de fuente registrados.
- candidate: cuando aplica, candidate_key, component_id, requirement_id, candidate_source, candidate_version.
- verification OBSERVED/STATIC/NOT_VERIFIED y permission read_only/write (descripción del trabajo, no permiso nuevo).

```sh
python3 -B skills/design-tree/scripts/runner.py --state /proyecto/ledger.json propose Q00 --file /proyecto/proposal.json
# Manual/reservado: esperar al usuario antes de confirm.
python3 -B skills/design-tree/scripts/runner.py --state /proyecto/ledger.json confirm Q00 --file /proyecto/human-decision.json
# Sólo con mandato delegado válido, en lugar de fingir confirmación humana:
python3 -B skills/design-tree/scripts/runner.py --state /proyecto/ledger.json delegate Q00
```

No ejecutar las dos alternativas como receta automática. La segunda deja DECIDED_DELEGATED, no APPROVED. Una corrección del contexto invalida decisiones afectadas; no reciclar recibos.

## Inventario y hechos

`inventory` muestra el catálogo sin modificar el expediente. `inventory --file propuesta.json` registra una propuesta pendiente de revisión humana. El archivo debe contener una lista JSON con una entrada por skill y los campos `skill_id`, `disposition`, `reason` y `evidence_refs`. Los valores admitidos para `disposition` son APPLICABLE, NOT_APPLICABLE, DEFERRED y GOVERNANCE_ONLY. Cada evidencia debe existir. La huella de la propuesta vincula cada referencia con su ruta lógica y el SHA-256 de sus bytes. Si una referencia de fuente identifica varios archivos, asígnales referencias distintas antes de presentar el inventario. Los expedientes anteriores conservan sus filas. Para renovar una confirmación cuya huella no incluía evidencia, vuelve a presentar las filas con `inventory --file` y solicita aceptación de la nueva huella.

Si el archivo contiene `null`, el CLI devuelve `INVENTORY_COVERAGE_REQUIRED` con código 2 y conserva el expediente. Si el propio expediente contiene una raíz JSON distinta de un objeto, el error es `STATE_OBJECT_REQUIRED`.

`confirm-inventory` usa un recibo inventory. Alternativamente, la propuesta de inventario forma parte del gate exacto de una fase y se ratifica con él; no necesita una segunda pregunta conversacional.

`fact ID --file fact.json` recibe el esquema de PROTOCOL: estado, ámbito, sujeto, revisión, IDs afectados y evidencia. Cambiar un hecho relevante invalida lo afectado; comentario y fecha no se usan como causas globales por sí solos. No reescribir scope en el JSON manualmente. Un cambio mayor de alcance requiere nuevo mandato y revisión explícita.

## Gate de fase

Archivo de entregables: lista de evidencias `{path,sha256,note}`. Las notas identifican qué entregable representan; se revisa su pertinencia con el humano.

```sh
python3 -B skills/design-tree/scripts/runner.py --state /proyecto/ledger.json phase-prepare foundations --file /proyecto/deliverables.json
# Detenerse: presentar artefacto, síntesis, decisiones, fuentes, pruebas y pendientes.
python3 -B skills/design-tree/scripts/runner.py --state /proyecto/ledger.json phase-accept foundations --file /proyecto/human-phase.json
```

La respuesta AWAITING_HUMAN bloquea cambios hasta aceptar o reabrir. El recibo phase acepta el hash del paquete exacto. No crea aprobaciones humanas por nodo. Para continuar: nuevo grant explícito de la próxima fase. Puede registrarse desde la misma respuesta si el usuario aceptó el cierre y autorizó ese siguiente alcance.

Si una fase ya estaba en AWAITING_HUMAN al actualizar el runner y su paquete contiene una huella de inventario anterior que sólo cubría las filas, vuelve a presentar esas mismas filas con `inventory --file`. Ejecuta `phase-prepare ID --file` con los entregables originales. El runner conserva las decisiones y archiva el paquete anterior. Revisa la evidencia del inventario y el nuevo paquete antes de emitir un recibo humano `phase` para la nueva huella y ejecutar `phase-accept`. Si cambian las filas, los entregables o las decisiones, utiliza el procedimiento de reapertura.

En un mapa acotado, la fase activa permite resolver a mano los prerrequisitos de sus propios nodos, incluida la rama seleccionada de un prerrequisito. Las fases futuras se habilitan al recibir su mandato y sólo mientras sus dependencias sigan vigentes.

Para reabrir: el target_hash del recibo reopen es el digest canónico de `{phase_id,gate_packet_hash,reason}` del estado actual. `phase-reopen ID --reason ... --file receipt.json`. Se archivan los paquetes previos, se revoca el mandato activo y la fase y sus dependientes quedan STALE. Registrar un mandato nuevo antes de volver a proponer; no borrar el historial. `revoke --reason ...` vuelve a manual sin perder fuentes.

## Persistencia y migración

```sh
python3 -B skills/design-tree/scripts/runner.py --state /proyecto/ledger.json export --output /salida/bundle-nuevo
python3 -B skills/design-tree/scripts/runner.py --state /recuperado/ledger.json resume --bundle /salida/bundle-nuevo
python3 -B skills/design-tree/scripts/runner.py upgrade-state --bundle /origen/bundle-0.1 --dry-run
python3 -B skills/design-tree/scripts/runner.py upgrade-state --bundle /origen/bundle-0.1 --output /salida/bundle-0.3
```

Bundles pueden contener datos privados; nunca publicar automáticamente. La recuperación valida evidencia, reubica rutas, no sobreescribe estado y vuelve a manual. La migración conserva 0.1 o 0.2 como historia y abre obligaciones nuevas; no transfiere aprobaciones. Evidencia debe guardarse versionada, no sobrescribir rutas cuyos hashes ya aparecen en historia.

Escrituras usan revisión y reemplazo atómico. Un lock existente bloquea: identificar al escritor, nunca borrarlo automáticamente. El helper no ejecuta pruebas de producto, instala dependencias ni publica aunque un estado esté listo para revisión final.

Al registrar evidencia nueva, una ruta relativa queda vinculada al archivo del directorio de trabajo donde se usó por primera vez en ese expediente. Las operaciones posteriores pueden ejecutarse desde otro directorio. Para un expediente anterior que aún conserve rutas relativas sin vincular, exporta desde el directorio original y recupera el bundle con `resume`.


### Evidencia de un recurso exigido

Además de `relation_id`, `status: SATISFIED`, `reason` y `evidence_refs`, una revisión `uses_resource` lleva `resource_id` y `resource_path`. Incluir ese archivo en `evidence` con SHA-256 observado. El helper contrasta sus bytes con el SHA-256 o Git blob del recurso; una nota sobre otro archivo no satisface esa obligación.


### Compatibilidad de verificación y migración

`init` crea expedientes `design-tree-ledger/0.3`. Si tienes un **bundle 0.1 o 0.2**, usa `upgrade-state --bundle ORIGEN --dry-run` para consultar el informe y `upgrade-state --bundle ORIGEN --output COPIA_NUEVA` para escribir el bundle 0.3. Después, usa `resume` con un expediente de destino nuevo. Las aprobaciones anteriores quedan en el historial.

Si sólo tienes un **expediente suelto 0.1 o 0.2**, esta versión requiere el bundle de origen para migrarlo. `export` y `status` requieren un expediente 0.3. Recupera el bundle del respaldo o expórtalo con la versión de origen que creó el expediente, si dispone de esa operación.

Cada proposal con obligaciones aplicables registra
`verification_results` con schema `design-tree-checks/1`. Consultar
PROTOCOL.md para resultados, método, scope, evidencia y política de N/A.
Los errores `CHECK_RESULTS_INVALID` y `CHECK_REQUIRED_PENDING` son bloqueos,
no permisos para editar el expediente manualmente.
