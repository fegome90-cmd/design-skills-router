# R01 · Contrato compartido de tools

Estado: protección de paridad implementada; pendiente de revisión del PR. Fase: Fundamentos. Dependencia: R00, piloto G5 integrado mediante el PR #6, commit e1aa16f2fe20540dd4de47704d169c4690e5c42a.

Fuentes: [dossier R01](../research/R01-dossier-v0.1.md). El operador decidió el 24-11-2026 que los experimentos A/B no sean requisito para esta fase: seleccionar una solución coherente, implementar y verificar el comportamiento real. El cambio no modifica el árbol canónico ni autoriza merge.

## Problema y decisión

Las cuatro tools MCP ya reutilizan el runner. La CLI instalada y el MCP stdio ofrecen distintas entradas de transporte para las mismas operaciones de dominio. Un registro nuevo no es necesario para preservar esa semántica en la base actual.

Adoptar la alternativa A: conservar handlers explícitos y añadir una prueba de contrato ejecutable desde el checkout. Inspiración: la prueba de paridad de Doop, con una implementación propia, y los contratos centralizados de OpenPencil. No se incorpora código de terceros ni otro dispatcher. Reconsiderar el registro común cuando una nueva capacidad muestre duplicación efectiva; no se exige construir B para avanzar.

## Contrato

| MCP | CLI | Operación y efecto |
|---|---|---|
| next_node() | context-next | Consulta fase, revisión y nodos pendientes. |
| open_node(node_id) | context-open NODE | Recupera pasajes y permisos; puede persistir un paquete y aumentar la revisión. |
| search_context(node_id, query) | context-search NODE --query QUERY | Busca secciones; puede reconstruir el índice derivado sin cambiar el ledger. |
| submit_evidence(node_id, expected_revision, proposal) | propose NODE --file FILE | Presenta una propuesta mediante Router.propose; queda AWAITING_HUMAN. |

Las diferencias de frontera son deliberadas: MCP exige revisión esperada y evidencia en evidence/; la CLI genérica utiliza la revisión leída al comenzar y conserva sus reglas de evidencia. No forzar paridad de firmas ni debilitar estas restricciones. La autorización permanece en el runner.

## Prueba de aceptación

La prueba checkout-level vive en packages/cli/tests/test_mcp_parity.py. Reutiliza el fixture G5 sintético del plugin y copia el paquete instalado a un directorio temporal; solo sustituye los pins de fuentes por los del fixture. Ejecuta el código Typer de esa copia y conecta un cliente MCP real al proceso stdio. Usa dos ledgers independientes con el mismo estado inicial y los mismos bytes de evidencia. No altera el paquete instalado, el árbol v0.4 ni el proyecto del usuario.

- El catálogo anunciado por tools/list conserva exactamente los cuatro nombres, campos, tipos y campos obligatorios.
- Next, open y search devuelven resultados estructurados equivalentes. Open prepara cinco secciones, aumenta una revisión al persistir por primera vez y no modifica el ledger al repetirse. Search reconstruye SQLite sin modificar el ledger.
- Un nodo fuera del piloto, un borrador sin permiso y una propuesta incompleta se rechazan. Un expected_revision obsoleto y una ruta fuera del proyecto se rechazan en MCP. Ningún rechazo altera el ledger.
- Con permiso de borrador, ambos transportes obtienen la misma propuesta y revisión, en AWAITING_HUMAN, sin autoaprobación.
- El extra MCP sigue siendo opcional. En instalación base se omite únicamente la prueba que requiere el SDK.

## Verificación y límites

Ejecutar las pruebas desde el checkout en un entorno aislado, con la CLI instalada desde el wheel y extra [mcp]:

~~~sh
python -B -m unittest discover -s plugin/tests
python -B -m unittest discover -s packages/cli/tests -v
python -B plugin/skills/design-tree/scripts/doctor.py --format json
python -B plugin/skills/design-tree/scripts/runner.py verify-package
~~~

Construir wheel y sdist con packages/cli/build.py según README; comprobar la instalación base sin MCP y la igualdad de los recursos portables. El workflow G5 existente ejecuta la suite CLI desde el checkout. En un sdist aislado la prueba de paridad no se distribuye porque depende del fixture del repositorio.

## Secuencia de trabajo

1. G0/G1: base comprobada y código de referencia documentado.
2. G2/G3: decisión A; no construir una alternativa B desechable. La prueba de paridad sustituye la comparación de prototipos.
3. G4: ejecución de pruebas reales, build, instalación y regresiones.
4. G5/G6: revisión independiente cuando exista un revisor real, CI del HEAD y autorización separada para merge. Una revisión no ejecutada permanece NOT_RUN.

R01 no añade tools de diseño, dependencia de TypeScript, política de permisos R02, servidor HTTP ni cambios al baseline. El siguiente PR será R02, seguido por R03. Para observar diseños, usar primero un proveedor de canvas existente, Kalka cuando esté disponible, sin crear un editor propio. Mantener cada unidad verificable y no convertir la prueba de utilidad en requisito A/B de cada PR.

No publicar ni fusionar automáticamente. No tratar el resultado técnico como prueba de mejora del juicio visual del agente.
