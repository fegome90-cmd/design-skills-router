# Manual de mantenimiento para agentes

## Entrada y comprobación

El encargo es mantener el plugin, no diseñar un producto: no iniciar Q00. Identidad privada: `plugins_6af0bd3b7e3c81918ab86be10f68159e`. Leer inventario y release actuales con Plugin Creator. No comenzar desde un ZIP viejo sin verificar equivalencia. El número de versión canónico está en `plugin.json`.

Trabajar en una copia aislada. Conservar recibo del release, hashes y alcance autorizado. No escribir expedientes dentro del plugin. No importar SQLite/CSV/XLSX ni filas del catálogo externo. Los iconos y prompts existentes se preservan.

```sh
python3 -B skills/design-tree/scripts/doctor.py --format text
python3 -B skills/design-tree/scripts/doctor.py --state /ruta/externa/ledger.json --format json
python3 -B skills/design-tree/scripts/doctor.py --bundle /ruta/externa/bundle --format json
python3 -B -m unittest discover -s tests -v
```

El doctor es lectura: no crea .pyc, no repara archivos ni elimina locks. Códigos 0=sin hallazgos en controles ejecutados, 1=advertencias, 2=bloqueos, 3=fallo interno/control no completado. NOT_CHECKED nunca es aprobación. `model_coverage=STRUCTURAL_CHECKS_ONLY` no acredita semántica completa. Una espera humana legítima no es corrupción.

## Diagnostico

Cada hallazgo trae code, severity, scope, location, detail, next_action y manual_ref. Empezar por el primer bloqueo causal, no por regenerar hashes.

| Código/familia | Reparación segura | Comprobación |
|---|---|---|
| INVALID_JSON / MANIFEST_SCHEMA | Recuperar contenido válido y cotejarlo con la fuente | doctor y test_doctor |
| MANIFEST_DIVERGENCE | Sincronizar campos equivalentes; raíz OpenAI prevalece, no se fusiona | test_release y lectura del ZIP |
| FILE_MISSING / HASH_MISMATCH | Revisar el cambio o recuperar el archivo del release | Comparar SHA y luego preparar release |
| UNTRACKED_PACKAGE_FILE | Decidir si pertenece al paquete; retirar sólo lo no autorizado de la copia | Comparar inventario de entrega |
| PATH_ESCAPE / SYMLINK_FORBIDDEN | Eliminar la referencia insegura de la copia, no tocar su destino | Test negativo de rutas |
| BASELINE_DRIFT | Restaurar v0.4; no regenerar baseline-lock.json | runner verify-package |
| MODEL_INVALID / CONTRACT_INVALID | Corregir el dueño indicado, conservando el árbol | test_contracts + doctor |
| STATE_LOCK_PRESENT | Verificar escritor; no borrar lock automáticamente | Reintentar sólo tras resolución |
| STATE_INVALID / STATE_RECORD_STALE | Conservar original, diagnosticar contexto/evidencia | status, nueva propuesta o upgrade explícito |
| BUNDLE_INVALID | Recuperar archivos íntegros o exportar nuevamente desde fuente válida | doctor --bundle |

Los archivos ausentes en una **actualización parcial declarada** no prueban corrupción del plugin remoto. Validar el overlay aparte y comprobar después que el backend conservó los assets. No informar package PASS sobre una copia que no contiene esos bytes.

## Propiedad y receta por cambio

| Necesidad | Archivo canónico | No tocar |
|---|---|---|
| Corregir instrucciones operativas | SKILL.md, CLI.md o este manual según responsabilidad | Fuente v0.4, prompts y política de invocación |
| Añadir/modificar relación suplementaria | contracts.json | Alternativas del árbol o pins en inventory |
| Modificar lógica de gates | runner.py / assistance.py / contracts.py según causa | Recibos de proyectos reales |
| Doctor | diagnostics.py; CLI en doctor.py | Auto-reparación, red, ejecución de scripts externos |
| Regla, pin de fuente o rama canónica | **nueva versión del baseline** desde paquete editable/generador original | No editar tree-v0.4 en el lugar ni crear overrides |
| Versión de distribución | scripts/release.py prepare | Fuente de trabajo y baseline-lock.json |

### Texto o enlace no normativo

Editar sólo el documento dueño. Ejecutar `test_maintenance.py`; verificar links/rutas y que el texto no contradiga PROTOCOL o ASSISTANCE. Si cambia una obligación, deja de ser editorial: registrar impacto y prueba de política. No reescribir informes históricos como si probaran la versión nueva.

### Relación suplementaria

Leer la fuente exacta y su sección. Identificar origen, destino tipado, ámbito, condición y evidencia. Editar contracts.json; no copiar catálogo externo ni títulos del árbol. Añadir un test positivo y uno negativo antes de la lógica. Ejecutar:

```sh
python3 -B -m unittest discover -s tests -p test_contracts.py -v
python3 -B skills/design-tree/scripts/doctor.py --format json
```

Un complemento sigue optativo; recursos no son skills. Las nuevas obligaciones invalidan decisiones relevantes por policy_hash. Si necesitas cambiar candidate_commit del inventario, detener esta receta: requiere nueva versión del baseline, regeneración del visor y migración, fuera de esta entrega.

### Reparar runtime

Reproducir el error en fixture sintético. Escribir la aserción de comportamiento, observarla fallar y reparar la causa. Ejecutar el test específico y toda la suite. No reetiquetar una condición UNKNOWN, quitar una skill ni recalcular una aprobación para conseguir verde.

### Elegir o cambiar nivel

Consultar ASSISTANCE y CLI. Aprovechar el mensaje real; no preguntar otra vez por un nivel ya indicado. Confirmar estructura y mapa en bloque cuando corresponda. El mandato identifica fase, acciones y reservas; `grant-packet` calcula su huella después de editar el contenido. Registrar con `grant`. `revoke` detiene delegación y vuelve a manual sin borrar evidencia.

Al cambiar de nivel no fabricar aceptaciones previas. Volver a presentar decisiones provisionales afectadas bajo el mandato nuevo o pedir su confirmación individual. No modificar decisiones aceptadas independientes. `resume` vuelve a manual y requiere renovar mandato para continuar automático.

### Terminar o reabrir una fase

Preparar artefactos reales; `phase-prepare` genera paquete exacto y deja AWAITING_HUMAN. Presentar una síntesis, no miles de instancias. Detenerse. Guardar `phase-accept` sólo tras aceptación explícita. Para continuar, registrar autorización específica de la siguiente fase; puede provenir de la misma respuesta si cubre ambas acciones. Para cambios, `phase-reopen` usa un recibo dedicado, archiva paquetes y recibos anteriores y deja la fase y sus dependientes STALE. Revoca la delegación activa; registrar un mandato nuevo antes de revisar las decisiones. No sobreescribir la aceptación anterior en silencio.

### Recuperar un bloqueo

Distinguir evidencia pendiente de ruta no desarrollada. Para P03, aportar evidencia y reproponer P01 con la respuesta ahora sustentada; nueva confirmación o delegación válida abre P02. No forzar una aceptación directa de P03. Nativo/documental/gráfico continúan bloqueados hasta desarrollar sus contratos; un nuevo brief no instala esas capacidades.

### Migrar y hacer rollback

```sh
python3 -B skills/design-tree/scripts/runner.py upgrade-state --bundle /origen/0.1 --dry-run
python3 -B skills/design-tree/scripts/runner.py upgrade-state --bundle /origen/0.1 --output /destino/0.2-nuevo
python3 -B skills/design-tree/scripts/runner.py --state /otro/ledger.json resume --bundle /destino/0.2-nuevo
```

La migración explícita desde 0.1 **o 0.2** genera una copia nueva 0.3; no convierte verificaciones históricas en PASS.
No sobreescribir origen ni destino existente. Consultar PROTOCOL: recibos viejos son historia, todo lo nuevo comienza manual. Ante interrupción, no presentar un staging como bundle terminado. Evidencia versionada por archivo; no reutilizar un path con contenido diferente. Rollback de código no degrada expedientes: conservar 0.1, 0.2 y 0.3; elegir explícitamente cuál reabrir. Nunca perder decisiones posteriores.

## Preparar y publicar

```sh
python3 -B scripts/release.py prepare --version VERSION_SUPERIOR --output /ruta/externa/update.zip
```

Para un overlay con assets originales inaccesibles localmente, agregar `--retained-assets /ruta/externa/retained-assets.json`. Ese archivo contiene rutas exactas de assets y SHA-256 cotejadas con el release remoto; no otorga permiso para retener archivos desconocidos. La salida se identifica GUARDED_OVERLAY, no paquete standalone. Sin declaración explícita, assets ausentes bloquean.

Preparar no publica ni modifica fuente. Se normalizan fechas/permisos del ZIP y se incluyen hashes de cada archivo salvo el propio manifiesto de hashes. Repetir con mismos inputs debe dar el mismo SHA. El preparador no compensa un baseline alterado. No empaquetar credenciales, expedientes ni la database.

Antes de subir, ejecutar suite/doctor/validación del candidato y revisar diff. Volver a leer el release remoto. Si cambió, reconciliar; no cambiar sólo expected_release_id para forzar la escritura. Usar update_plugin con el mismo ID, archive local y expected_release_id. Omitir assets conservados en el overlay, sin delete_paths. Después leer versión, archivos cambiados, manifiestos y assets. Si lectura posterior falla, indicar guardado/no verificado; no repetir publicación a ciegas.

## Límites

Doctor y pruebas son consistencia local, no autenticación, calidad estética ni obediencia del agente. Los datos sintéticos no aprueban decisiones de Felipe. La activación real, ejecución de las recetas por otro agente y reducción de preguntas se informan separadas. Una publicación exitosa no demuestra funcionamiento dentro del host.


## Cobertura de fuentes de esta entrega

Se releyeron los documentos principales de 23 skills del conjunto asociado y la entrada/ámbito de una adicional (`write-swift`, ruta nativa bloqueada). Las otras 58 entradas siguen como no revisadas en esta entrega. Eso no acredita lectura exhaustiva de sus referencias auxiliares, ejecución de sus scripts ni calidad de sus resultados. `contracts.json` mantiene el detalle y los blobs observados. Las recetas estéticas y afirmaciones técnicas de esas fuentes no se elevan automáticamente a normas del router.

El recurso de formato de revisión de `better-interface` tiene una relación explícita y un blob fijado. Ningún script externo se ejecuta por recuperar ese documento. Otros apoyos deben consultarse cuando el criterio aplicable los requiera; sus contratos no están exhaustivamente descompuestos.


### Serialización de compatibilidad por el servicio

La publicación 0.2.0 mostró que Plugin Creator vuelve a generar `.codex-plugin/plugin.json`. La preparación preserva ahora el orden y escape ASCII observados de esa proyección, antes de calcular su SHA. No se excluye el archivo de la comprobación para ocultar deriva. Tras cada actualización, leer de nuevo el manifiesto generado y contrastarlo con la huella entregada. Si el servicio cambia su formato, corregir el empaquetado y publicar una versión superior; no declarar verificada una huella de bytes que ya cambió.

El JSON de `--retained-assets` tiene forma `{"assets/nombre.png": {"sha256": "hash de 64 caracteres"}}`. Los recibos que incluyen plugin_id/release_id se conservan aparte: no son el input directo de ese argumento.

### Prueba de activación con alcance explícito

El pack `tests/fixtures/host-routing-cases.json` aporta casos positivos,
negativos y límites de autoridad. `tests/test_host_cases.py` valida el pack,
pero no simula obediencia de un LLM ni una conversación independiente.
Guardar observaciones reales externamente con release_id/session_ref,
fecha, trazas y estado; registrar `UNVERIFIED` cuando no estén disponibles.
No abrir Q00 al mantener el plugin.

### Aprendizajes como propuestas, no autoediciones

Usar [LEARNING-CANDIDATE.md](LEARNING-CANDIDATE.md) sólo para defectos
reproducibles con dueño y evidencia antes/después. La instancia permanece
fuera del plugin en estado `PROPOSED`; no autoaplicar, no promover, no añadir
una skill instalada y no escribir expedientes de usuarios. La aprobación
humana del diff y el gate de publicación son decisiones diferentes.
Este procedimiento es documental: las pruebas verifican texto y trazas,
no la obediencia de otro agente ni disminución de consumo de contexto.


### Revisar resultados obligatorios

Antes de aprobar una fase, leer `contracts.json.verification_requirements`,
revisar métodos compatibles, evidencia y aplicabilidad. `verification` 
(OBSERVED/STATIC/NOT_VERIFIED) no expresa PASS. Los cuatro outcomes de
`design-tree-checks/1` se registran por check; FAIL/UNVERIFIED obligatorio
o N/A no respaldado impide cierre. Una nueva norma cambia `policy_hash` y
vuelve obsoletas sólo decisiones afectadas. No agregar checks universales
sobre las 82 referencias sin revisión individual.
