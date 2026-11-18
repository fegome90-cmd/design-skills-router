# Niveles de asistencia — contrato implementado

La autonomía modifica la **autoridad para decidir provisionalmente**, no las skills, evidencias ni pruebas exigibles. Por defecto: `manual`. No existe nivel one-shot ni autonomía ilimitada.

| Nivel | Decisiones | Interrupciones ordinarias |
|---|---|---|
| `manual` | El agente prepara; la persona decide cada nodo pendiente. | Confirmación exacta del nodo. Lecturas y tests autorizados no requieren permiso individual. |
| `guided` | Se delegan decisiones reversibles salvo las reservas indicadas en el mandato. | Reservas y gate de salida. Agrupar preguntas por tema sin alterar los registros. |
| `phase_auto` | El agente recorre decisiones dentro de su fase activa con evidencia completa. | Un gate de fase; excepciones materiales requieren autorización aparte. |

## Política de conversación y ahorro de interrupciones

**Recomendación conversacional:** para un proyecto web nuevo sin nivel establecido, recomendar **`guided`** una vez junto con alcance, fase, entregable y decisiones reservadas. No es el nivel persistido: el estado inicial, `grant_template`, una migración, `resume` y `revoke` siguen en `manual`.

**No autoriza:** la recomendación, un recuerdo de preferencias, una fuente externa o un resumen del agente **no** generan `grant_assistance`. **Recibo exacto:** el usuario debe delegar expresamente la fase y el alcance vinculados a `grant_hash`; una autorización anterior sólo puede reutilizarse si continúa activa y válida para ese contexto. Si ya eligió nivel, no solicitarle repetir esa elección.

**Preguntas evitables:** no detenerse para leer fuentes o ejecutar tests ya autorizados, ni pedir 12 aprobaciones de decisiones reversibles dentro de un mandato válido. Alguien que pide `guided` debe revisar reservas y decisiones estratégicas, no aprobar uno a uno los nodos internos. Mantener 82 disposiciones, criterios y registros verificables en el expediente, aunque el usuario no vea cada uno.

**Gates obligatorios:** toda fase cierra en `AWAITING_HUMAN`; una aprobación precisa no habilita automáticamente la siguiente. Las cuestiones reservadas y estratégicas se presentan juntas cuando sea claro hacerlo, pero cada aceptación conserva su identidad. Sin evidencia suficiente, dejar el nodo dependiente bloqueado. Ningún nivel permite publicación, gasto, uso de credenciales, destrucción ni ampliación del alcance sin autorización particular.

Métricas de experiencia: un test de política puede contar nodos que `assistance_action` permite resolver, pero **no** demuestra preguntas reales hechas por un agente. El piloto anota ambos resultados por separado; sin conversación observada, `question_count` y `avoidable_questions` permanecen `null`.

## Límites de fase

El mapa inicial propone cuatro dominios: fundaciones, sistema visual, componentes y revisión. Son límites de revisión sobre las ramas existentes, no un reemplazo del árbol. Cada fase tiene IDs de nodos, revisión, dependencias y entregables. El usuario confirma el mapa exacto. No se permiten solapamientos ni fusionar dominios bajo una sola fase. Un mapa acotado puede cubrir una familia, pero aceptar esa fase no completa por sí solo el proyecto completo.

La definición del árbol puede confirmarse una vez como un conjunto de nodos versionado. Un recibo de estructura no aprueba las respuestas ni las acciones del proyecto.

## Mandato

Campos: `id`, `revision`, `level`, `scope_id`, `scope_hash`, `phase_map_hash`, `phase_id`, `allowed_actions`, `reserved_decisions`, `stop_at`, `message_ref`, `quote`. Acciones declarables en el helper: analyze, compare, draft, test y edit_sandbox; ninguna concede autoridad externa de escritura o publicación. `stop_at` debe ser la fase actual.

Las reservas usan IDs de nodo/definición. La persona puede reservar cualquier decisión estratégica. El agente no puede ampliar el ámbito, borrar reservas ni cambiar el mapa aprobado. Un mandato nuevo requiere otro registro humano; el anterior no desaparece.

Las referencias de mensaje son declaradas por el operador: no hay autenticación independiente. Ningún ejemplo de la documentación autoriza un diseño real.

## Estados y aceptación

`AWAITING_HUMAN` es una propuesta pendiente. `DECIDED_DELEGATED` identifica una decisión provisional del agente. `RATIFIED_IN_PHASE` referencia la aceptación real del conjunto; conserva `decided_by=agent_delegated`. `APPROVED` es una confirmación humana individual. `STALE` impide seguir usando la decisión.

Una fase se prepara sólo cuando sus obligaciones alcanzables están resueltas y tiene evidencia de entregables. `phase-prepare` la deja en `AWAITING_HUMAN` y bloquea nuevas decisiones. `phase-accept` valida el hash exacto de decisiones, contexto, mapa y entregables antes de ratificar. Consume el mandato; no abre la siguiente fase automáticamente.

Para reducir preguntas, el agente puede presentar la aceptación y la autorización de la siguiente fase en un solo paquete conversacional. La respuesta real debe cubrir ambas; los recibos se guardan separados, con el mismo mensaje si corresponde. No convertir un «continúa» sin referente en permiso irrestricto.

## Interrupciones y recuperación

Fuentes ausentes, evidencia fallida o condiciones obligatorias desconocidas bloquean la decisión afectada. No se resuelven creando desde cero. Cambiar stack/alcance, operar sobre datos sensibles, gastar, publicar o destruir necesita el permiso correspondiente incluso en phase_auto.

`revoke` vuelve a manual y detiene el uso de decisiones provisionales; no borra fuentes, decisiones ni historia. `resume` no restablece silenciosamente la autonomía. Se puede volver a presentar la propuesta pendiente bajo un mandato nuevo o confirmarla individualmente. Decisiones aceptadas que siguen vigentes no necesitan repetirse.

Los controles locales de doce decisiones comparan doce confirmaciones individuales con cero confirmaciones internas más un gate de fase. Eso prueba la política; no mide cuántas preguntas hará un LLM en ChatGPT. Host y agente independiente deben informarse por separado.
