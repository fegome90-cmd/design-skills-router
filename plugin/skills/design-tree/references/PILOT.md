# Contrato del piloto

Versión del paquete: consultar plugin.json. Árbol: v0.4, conservado byte por byte. Expediente actual: design-tree-ledger/0.3. Soporte: UI web supervisada; no se completaron las rutas nativa/documental/gráfica.

La skill coordina decisiones con fuentes originales, el helper registra evidencia y gates, y el doctor comprueba consistencia local. No hay servidor, almacenamiento cloud, instalación de 82 skills ni interceptación de herramientas externas.

El inventario conserva 82 referencias; sólo un subconjunto tiene preguntas asociadas. Releer una fuente no integra automáticamente todos sus criterios. Consultar contracts.json para saber qué relaciones se verificaron y qué fuentes permanecen pendientes. Las versiones fijadas no sustituyen verificar APIs actuales antes de una integración real.

Estructura, decisiones del proyecto y permiso de ejecución son distintos. ASSISTANCE.md define manual, guided y phase_auto; todos conservan cobertura y gates. Un agente puede decidir provisionalmente dentro de un mandato; aceptar una fase corresponde a una persona y al paquete exacto. No hay one-shot de proyecto.

Los recibos son declaraciones del operador, no identidad autenticada. Los hashes detectan deriva, no vuelven inalterable un fichero accesible al agente. Recibir bytes no demuestra comprensión ni pertinencia. Las pruebas locales no prueban calidad visual o comportamiento de otro LLM.

Un expediente cubre un requisito atómico de componente. Para más requisitos, mantener sesiones identificadas y enlazar sus resultados; no hay agregador global que certifique toda una aplicación. Guardar/exportar explícitamente fuera del plugin; otra conversación necesita ese archivo. Una recuperación empieza manual.

Sin fuentes: bloquear la decisión dependiente. Sin Python: VALIDATOR_NOT_RUN y sólo borrador conversacional. Sin render: NOT_VERIFIED. No convertir estos límites en éxito. Publicación e instalación requieren autoridad independiente; permission_to_execute permanece false.

Mantenimiento: MAINTENANCE.md. Formatos y compatibilidad: PROTOCOL.md. Comandos: CLI.md. La auditoría original del árbol se conserva en tree-v0.4/AUDIT.md, no prueba esta versión del helper.

## Evaluación de activación en host (separada de tests del helper)

Los doce casos etiquetados están en `tests/fixtures/host-routing-cases.json`. Un resultado
`UNVERIFIED` significa que **no** se obtuvo una traza de conversación nueva;
leer esta skill en la sesión que está haciendo la auditoría **no** certifica
que un agente independiente active y respete sus gates.

Para ejecutar un caso desde una sesión fresca, guardar un registro **fuera del plugin**:
`{case_id, release_id, host, session_ref, observed_at, trace_refs, result, reason}`.
`trace_refs` enumera evidencias reales de activación, lecturas, operaciones y
punto de detención (no una etiqueta fabricada por el evaluador). Evaluar
por separado descubrimiento, selección de skill, lectura de referencias,
invocación del helper y cumplimiento del gate. Sólo registrar `PASS` con
trazas concordantes y `FAIL` con una contradicción observada. Sin runner de
host disponible, mantener `UNVERIFIED` y no afirmar ahorro real de preguntas
ni de tokens. Ningún resultado de prueba del host equivale a permiso de
publicación o edición del plugin.

## Evaluación UX de interrupciones (separar política y experiencia)

El dolor reportado por el usuario es contestar muchas preguntas derivadas de las referencias del árbol: **`USER_OBSERVED`** (funciona, pero exige demasiadas interrupciones). Es evidencia de uso cualitativo; sin una transcripción observada **no** conocemos una cifra real de preguntas ni podemos certificar ahorro de tokens. La ausencia de trazas se marca **`UNVERIFIED`**, no borra ese feedback.

Para comparar políticas se usan dos tareas equivalentes con **12 decisiones reversibles**, una decisión reservada y un gate de fase. El helper puede demostrar la diferencia de permisos entre `manual`, `guided` y `phase_auto`; **no mide preguntas reales** pronunciadas por un LLM. Una modificación de alcance crea un nuevo gate y no hereda autorización. Los escenarios `ux_scenarios` y `policy_budget` viven en `tests/fixtures/host-routing-cases.json` y siguen separados de los 12 casos originales.

Una observación de host real se documenta **fuera del plugin**, sólo con autorización para conservarla y sin copiar chats privados automáticamente. Campos mínimos:

`{case_id, level, release_id, user_or_trace_source, scope, observed_at, question_count, avoidable_questions, pending_strategic_questions, node_decisions_recorded, phase_gate_respected, result, trace_refs}`

- `user_or_trace_source=USER_OBSERVED`: descripción comunicada por la persona; sin conteo inferido.
- `user_or_trace_source=TRACE_VERIFIED`: evidencia de sesión nueva con preguntas y gates auditables.
- `result=UNVERIFIED`: faltan trazas o verificaciones para esa afirmación; usar `null` para contadores desconocidos, nunca 0.
- `question_count`: preguntas reales en la conversación; `avoidable_questions`: repeticiones o solicitudes de aprobación para acciones ya autorizadas; `node_decisions_recorded`: decisiones realmente conservadas en el expediente, no inferidas de silencios.
- `phase_gate_respected`: `true`/`false` sólo si el gate fue observado; de otro modo `null`.

Seis casos mínimos en host cuando esté disponible: petición sin nivel; `manual`, `guided` y `phase_auto` explícitos; recuperación de expediente; y mantenimiento. En los tres niveles se verifica que no se salte el gate, que no se pregunte por decisiones ya resueltas y que el resultado de tarea sea útil. La ejecución sintética no sustituye esa observación.

## Resultados de verificación en 0.3

`proposal.verification` sigue describiendo el método histórico
(OBSERVED/STATIC/NOT_VERIFIED), no un veredicto. Las obligaciones expresas
provienen exclusivamente de `contracts.json.verification_requirements` y
se evalúan como `PASS`, `FAIL`, `NOT_APPLICABLE` o `UNVERIFIED` en
`proposal.verification_results`. Un resultado obligatorio FAIL, sin evidencia
o sin prueba compatible no permite preparar, aceptar ni conservar como vigente
una fase. Sin obligaciones revisadas no se inventan controles universales.
La recepción de bytes o un test de helper no prueban observación de host.
