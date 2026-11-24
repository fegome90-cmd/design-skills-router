# R01 · Registro compartido de tools

Estado: `PROPOSED`. Fase: Fundamentos. Dependencia: R00, piloto G5 integrado técnicamente mediante el [PR #6](https://github.com/fegome90-cmd/design-skills-router/pull/6). Base comprobada al abrir la rama: `e1aa16f2fe20540dd4de47704d169c4690e5c42a`. El ensayo de utilidad del contexto completo no alcanzó el umbral; la generalización sigue pendiente.

Fuente prioritaria: OpenPencil (`OP`), Router (`ROUTER`). Fuentes y hallazgos fijados en el dossier R01 que acompaña este PR. Permiso objetivo: Mantenimiento/contratos; no tool de diseño nueva.

## Problema y objetivo

Las cuatro tools actuales llaman al runner. Crecer sin contrato explícito puede crear divergencias de esquemas, errores o permisos entre interfaces.

Comparar el registro explícito actual con un catálogo mínimo de definiciones inspirado en OpenPencil. Comprobar si el código actual ya satisface la paridad y medir costo de cambio antes de añadir una abstracción.

## Contrato candidato

Entrada: Inventario de operaciones actuales, esquemas MCP observados por tools/list, comandos CLI equivalentes, permisos y casos de error.

Salida: ADR con alternativa A (mantener handlers explícitos con pruebas de paridad) y B (registro común mínimo); matriz de paridad y decisión GO/NO_GO. Si B gana, un registro interno, sin nuevas tools públicas.

El contrato es semántico; la implementación y nombres públicos no se congelan hasta G2/G3 del protocolo de trabajo que se incluye abajo. Respetar las reglas de `AGENTS.md`, `docs/agent/ARCHITECTURE.md` y `plugin/skills/design-tree/references/MAINTENANCE.md`. Reutilizar estructuras y errores vigentes cuando existan equivalentes.

## Investigación requerida

- Fijar fuente, licencia, símbolos, dependencias y pruebas originales. Separar documentación de código observado y ejecución. Para origen propietario, limitarse a contrato público y pruebas permitidas.
- Estudiar el código actual del router y comprobar si la capacidad ya existe. Comparar mecanismo original con solución mínima y registrar `GO`, `ADAPT`, `NO_GO` o `INCONCLUSIVE` en el dossier y ADR R01.
- Si corresponde un PR funcional, fijar contrato y rutas en plan independiente, escribir pruebas de comportamiento y ejecutar las verificaciones de este documento.

## Criterios de aceptación específicos

- [ ] Con fixtures equivalentes, `next_node`, `open_node`, `search_context` y `submit_evidence` tienen paridad semántica CLI/MCP en sus operaciones comunes. Las diferencias legítimas de contrato, incluida la revisión explícita y la restricción de rutas del MCP, quedan documentadas y probadas; no se equiparan artificialmente.
- [ ] El listado MCP conserva las cuatro tools, argumentos, tipos, obligatoriedad, nombres y semántica del baseline.
- [ ] Una prueba detecta un cambio incompatible en la definición o un handler ausente. No confundir metadatos de exposición con permiso.
- [ ] El paquete base continúa sin instalar MCP; wheel y sdist con extra [mcp] incluyen las mismas fuentes portables.

## STOP y exclusiones

Si un test de paridad sobre el código actual resuelve el problema con menos costo que un registro nuevo, cerrar R01 sin añadir infraestructura.

Fuera de alcance: No añadir herramientas nuevas, política de permisos R02, otro runner, dispatcher genérico, HTTP, catálogo externo ni dependencia TypeScript.

## Entregable y cierre

Dossier de investigación con fuentes fijadas, alternativa seleccionada y evidencia. Si la decisión es GO y se autoriza implementar, ampliar este PR R01 con las pruebas de aceptación, verificación instalada/compatibilidad aplicable, licencia y revisión independiente. Si no se implementa, registrar decisión NO_GO o bloqueo y la consecuencia para las dependencias. No iniciar otra unidad por inercia.

## Plan de estudio inicial de R01 (solo lectura)

Objetivo del estudio: contrastar las alternativas y completar el ADR antes de implementar. El PR borrador conserva el punto de partida y no autoriza cambios de runtime ni merge.

1. Leer las fuentes exactas del router en el HEAD vigente, `runner.py`, `mcp_server.py`, `cli.py`, `test_node_context.py`, `test_installed_cli.py` y el workflow G5 del checkout vigente. Inventariar las cuatro rutas, sus esquemas, validaciones y restricciones (en particular el path check de submit_evidence). Separar dominio de transporte.
2. Usar OpenPencil `4ca4e03177a6aa39673c53793745b9dc1e9eb84a`. Leer [schema.ts](https://github.com/open-pencil/open-pencil/blob/4ca4e03177a6aa39673c53793745b9dc1e9eb84a/packages/core/src/tools/schema.ts), [registry/index.ts](https://github.com/open-pencil/open-pencil/blob/4ca4e03177a6aa39673c53793745b9dc1e9eb84a/packages/core/src/tools/registry/index.ts), [manifest.ts](https://github.com/open-pencil/open-pencil/blob/4ca4e03177a6aa39673c53793745b9dc1e9eb84a/packages/mcp/src/tool/manifest.ts) y [commands/tool.ts](https://github.com/open-pencil/open-pencil/blob/4ca4e03177a6aa39673c53793745b9dc1e9eb84a/packages/cli/src/commands/tool.ts) completos. Seguir imports hasta `defineTool`, los registros `CORE_TOOLS`/`EXTENDED_TOOLS`, validación Valibot, proyección de esquemas y ejecución real. Buscar pruebas por símbolos, no asumir rutas adicionales. Distinguir CLI de herramientas MCP/WebMCP/AI.
3. Armar una matriz por tool: nombre, firma, esquema JSON del MCP, comando CLI, handler de dominio, validación, permiso, errors, side effects y payload. Registrar dónde se definen dos veces y si hay deriva efectiva. Si las diferencias son legítimas (p. ej., rutas de evidencia), dejarlas explícitas.
4. Comparar A: cuatro handlers explícitos + pruebas de contrato compartido, y B: un catálogo interno mínimo de definiciones + adaptadores. Dibujar ambos recorridos, identificar tipos, punto de autorización y líneas/archivos que cambiarían. No portar Valibot ni el registro de un editor completo a Python.
5. Si se dispone de un checkout/runtime aislado, medir listado y ejecución CLI/MCP sobre fixture F01 (lectura y propuesta en copias independientes), y probar el mecanismo original en un caso pequeño. Si no existe runtime, marcar NOT_RUN y no adjudicar equivalencia experimental.
6. Entregar `ADR-R01` con decisión y costo: número de definiciones/validaciones duplicadas, dependencias nuevas, riesgo de ruptura, capacidad de agregar R03 sin duplicar política. Si A cumple, no agregar un registry solo para parecerse a OpenPencil. Si B demuestra beneficio, redactar plan de implementación mínimo con firmas y rutas exactas antes de ampliar este PR con código autorizado.

### Matriz de prueba inicial

| Caso | CLI | MCP | Resultado esperado |
|---|---|---|---|
| F01 fase válida | `context-next` | `next_node` | Mismo conjunto de nodos y revisión. |
| F01 nodo G5 | `context-open E05__LAY01` | `open_node` | Mismos cinco cuerpos y permisos. |
| F01 consulta jerarquía | `context-search` | `search_context` | Mismas secciones recuperadas bajo el nodo. |
| F01 sin draft | `propose` | `submit_evidence` | Rechazo, sin escritura del ledger. |
| F01 con draft y evidence válida | `propose` | `submit_evidence` | `AWAITING_HUMAN`; no APPROVED. |
| Revisión obsoleta | comportamiento vigente a localizar | `expected_revision` anterior | Rechazo equivalente en la operación de dominio; identificar diferencia de interfaz si CLI aún no recibe la revisión. |
| Evidencia fuera de evidence/ | comportamiento vigente a documentar | `submit_evidence` | Rechazo MCP; mantener restricción legítima. |

La revisión de cada caso requiere salida observada. No afirmar que la tabla ya pasó. Reusar pruebas vigentes si prueban la misma conducta y verificar instalación real. Para R01 una mejora de juicio visual no es requisito; sí lo son paridad y ausencia de regresiones.

## Gates e invariantes de esta unidad

Este documento es una adaptación autocontenida del spec R01 del paquete de trabajo v0.1. No importa las otras unidades ni modifica los contratos vigentes. La apertura de este PR es un espacio de trabajo; no equivale a `READY_TO_IMPLEMENT`, aprobación de un ADR o permiso de merge.

| Gate | Evidencia de salida |
|---|---|
| G0 | HEAD, reglas del repositorio y dependencia R00 comprobados. |
| G1 | Dossier con fuentes, licencias y lectura estática. Las pruebas upstream no ejecutadas se registran como NOT_RUN. |
| G2 | Matriz real CLI/MCP y comparación A/B, con fixtures, comandos, resultados y decisión GO/ADAPT/NO_GO/INCONCLUSIVE. |
| G3 | ADR revisado de manera independiente, alcance y plan de implementación aprobados. Si no hay revisor disponible, registrar NOT_RUN. |
| G4 | Pruebas de comportamiento, regresión, empaquetado y verificación en el HEAD exacto. |
| G5 | Evaluación de mantenibilidad y paridad. R01 no presume una mejora de juicio visual. |
| G6 | Diff acotado, revisión independiente, checks aplicables y autorización separada de merge. |

- El runner conserva la autoridad de fase, mandato, revisión y transición. Exposición o anotaciones MCP no son permisos.
- Mantener Python >=3.10 y extra `[mcp]` opcional. No agregar dependencias para copiar la arquitectura de OpenPencil.
- No modificar el baseline v0.4, el expediente canónico ni sus hashes para adaptar pruebas. No introducir otro dispatcher ni publicar el plugin.
- Distinguir efectos sobre el expediente, el índice derivado, archivos y el diseño: `open_node` puede persistir contexto y `search_context` puede reconstruir SQLite. No etiquetarlos indiscriminadamente como lectura sin efectos.
- Preservar `AWAITING_HUMAN`, el control de revisión y las restricciones de rutas. Ningún adaptador concede confirmación humana.
- No introducir archivos privados, credenciales, capturas autenticadas o copias de código AGPL. Resolver licencias dudosas antes de reutilizar.
- Mantener las pruebas originales de OpenPencil y Kalka como referencia; una inspección estática no demuestra ejecución.

### Fixture F01 y método

Usar un expediente sintético G5 opt-in con los cinco pasajes fijados, dos mandatos independientes (analyze-only y analyze+draft) y una captura PNG sintética válida con SHA-256. Reutilizar el fixture existente de `plugin/tests/test_node_context.py` cuando cumpla esas condiciones. Partir de copias independientes del mismo estado para cada ruta; comparar resultado semántico, revisión, hashes y estado del expediente antes/después. Incluir primer open, open repetido, pérdida del índice derivado, propuesta incompleta, revisión obsoleta, ruta fuera de evidence/ y propuesta válida. No afirmar equivalencia cuando el CLI no expone el mismo argumento.

Para simular crecimiento en A/B, agregar una operación sintética de lectura con contrato equivalente a R03 únicamente en copias desechables. No exponer R03 como herramienta productiva. Comparar definiciones/archivos tocados, dependencias, divergencias detectables por tests y cambios del paquete instalado. Predefinir métricas y casos antes de medir; no seleccionar B por cantidad de código ni asumir que A debe ganar.

### Verificación prevista

Desde la raíz del checkout, confirmar primero los comandos vigentes en `AGENTS.md` y las guías que enlaza. Como base:

```sh
python3 -B -m unittest discover -s plugin/tests -v
python3 -B -m unittest discover -s packages/cli/tests -v
python3 -B plugin/skills/design-tree/scripts/doctor.py --format json
python3 -B plugin/skills/design-tree/scripts/runner.py verify-package
```

Construir wheel y sdist con `packages/cli/build.py` según el README y reproducir el recorrido de `.github/workflows/g5-pilot.yml` con la CLI instalada y un cliente MCP stdio real. Usar entornos aislados base y con extra MCP. Registrar salida, código de retorno, versión y SHA probado; no declarar PASS por leer un test. El plan de implementación detallado (Superpowers) se fija después del experimento. Aplicar pstack por unidad verificable y EGM para revisión independiente solo con sesiones reales; sin aislamiento, marcar NOT_RUN.

### Decisión y estado

Alternativas A y B abiertas. Preferencia provisional A, sin aprobación. Investigación estática documentada; experimento, ADR final, implementación, pruebas instaladas y revisión independiente: NOT_RUN. El PR no habilita R02.
