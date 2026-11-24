# R01 · Dossier de investigación: registro compartido de herramientas

Fecha: 2026-11-24. Decisión vigente: alternativa A, handlers explícitos y prueba de paridad implementada, pendiente de cierre del PR. No autoriza merge ni publicación del plugin. Se conserva a continuación la investigación estática original (G1), cuyo resultado provisional sobre incorporar un registro fue `INCONCLUSIVE`; los experimentos G2 no fueron ejecutados.

## Encargo y alcance

Conforme al [spec R01](../units/R01-registro-compartido-de-tools.md), comparar el mecanismo actual con un registro mínimo y determinar si el cambio aporta valor. No incorporar herramientas de diseño nuevas, ni resolver R02, ni introducir un segundo runner. Pstack: investigación de solo lectura, foundational-thinking y laziness-protocol. No hubo delegación independiente EGM ni ejecución de servidores externos. Las fuentes son código leído mediante GitHub y documentación pública, no resultados de ejecución.

## Fuentes fijadas

| ID | Revisión | Evidencia |
|---|---|---|
| ROUTER | `e1aa16f2fe20540dd4de47704d169c4690e5c42a` | [PR #6](https://github.com/fegome90-cmd/design-skills-router/pull/6), merge comprobado en la sesión anterior; lectura de archivos a ese SHA. No se afirma que sea el HEAD actual. |
| OP | `4ca4e03177a6aa39673c53793745b9dc1e9eb84a` | [OpenPencil](https://github.com/open-pencil/open-pencil/tree/4ca4e03177a6aa39673c53793745b9dc1e9eb84a); [LICENSE](https://github.com/open-pencil/open-pencil/blob/4ca4e03177a6aa39673c53793745b9dc1e9eb84a/LICENSE) MIT. |
| K | `46031f169704b177858beacd897a2d81187798fb` | [Kalka](https://github.com/leyscore/kalka/tree/46031f169704b177858beacd897a2d81187798fb); [LICENSE](https://github.com/leyscore/kalka/blob/46031f169704b177858beacd897a2d81187798fb/LICENSE) MIT con atribución a ambos proyectos. |
| F | consulta 2026-11-24 | [Figma tools](https://developers.figma.com/docs/figma-mcp-server/tools-and-prompts/), documentación oficial de contratos, no código del servidor. |
| P | consulta 2026-11-24 | [Paper MCP](https://paper.design/docs/mcp), [integraciones oficiales](https://github.com/paper-design/agent-plugins). Contratos, no implementación del editor. |
| PI | rama main consultada 2026-11-24, no pin de commit | [paper-mcp.ts](https://github.com/try-works/pi-paper-design/blob/main/extensions/paper-mcp.ts), blob `d0f3cd4e437b3c0be85c11751d95299ee603ddbb`; [LICENSE](https://github.com/try-works/pi-paper-design/blob/main/LICENSE) blob `261eeb9e9f8b2b4b0d119366dda99c6fd7d35c64` Apache-2.0; [package.json](https://github.com/try-works/pi-paper-design/blob/main/package.json) blob `916c54a1ce1c76313c39ff92c3717d36695024f6` declara MIT. No copiar hasta resolver contradicción. |
| D | `6009dc3da00f3a95d3e288e721185af9fad61ef7` | [Doop](https://github.com/kgoedecke/doop/tree/6009dc3da00f3a95d3e288e721185af9fad61ef7); [LICENSE](https://github.com/kgoedecke/doop/blob/6009dc3da00f3a95d3e288e721185af9fad61ef7/LICENSE) AGPL-3.0, referencia conceptual sin copiar. |

## OpenPencil: mecanismo central

- [schema.ts](https://github.com/open-pencil/open-pencil/blob/4ca4e03177a6aa39673c53793745b9dc1e9eb84a/packages/core/src/tools/schema.ts): `defineTool` conserva nombre, descripción, esquema Valibot estricto, ejecución, capacidades, disponibilidad y exposición por interfaz. `parseToolArgs` rechaza entradas extra o inválidas. `mutates` se deriva de ejecución; `toolChangesDocument` distingue cambios de propiedades/documento de cambios de vista. `toolInputFor` proyecta argumentos según interfaz. No trasladar Valibot, FigmaAPI ni carga de fuentes a Python.
- [registry/index.ts](https://github.com/open-pencil/open-pencil/blob/4ca4e03177a6aa39673c53793745b9dc1e9eb84a/packages/core/src/tools/registry/index.ts): concatena CORE_TOOLS y EXTENDED_TOOLS; catálogo explícito, no escaneo mágico.
- [manifest.ts](https://github.com/open-pencil/open-pencil/blob/4ca4e03177a6aa39673c53793745b9dc1e9eb84a/packages/mcp/src/tool/manifest.ts): deriva descriptores y filtra exposición; agrega tools propias de MCP (documentos, settings, historial). `effect` describe cambios del documento, no todos los posibles efectos secundarios.
- [registration.ts](https://github.com/open-pencil/open-pencil/blob/4ca4e03177a6aa39673c53793745b9dc1e9eb84a/packages/mcp/src/tool/registration.ts): comprueba existencia del descriptor y política de registro; agrega document_id/page_id; deriva anotaciones MCP; limita salida y transforma imágenes; propaga el alcance de selección. Las anotaciones son informativas, no reemplazan autorización. Incluye opción de esquemas anunciados más compactos para clientes con carga diferida.
- [commands/tool.ts](https://github.com/open-pencil/open-pencil/blob/4ca4e03177a6aa39673c53793745b9dc1e9eb84a/packages/cli/src/commands/tool.ts): `list`, `describe`, `call` consumen el mismo catálogo filtrado. La CLI puede ejecutar sobre app o archivo; guarda cambios headless solo con opción explícita. No todos los comandos CLI corresponden a tools MCP.
- [WebMCP policy](https://github.com/open-pencil/open-pencil/blob/4ca4e03177a6aa39673c53793745b9dc1e9eb84a/src/app/automation/webmcp/policy.ts): desactiva por defecto ante modo inválido; filtra según exposición, mutación y modo.
- [options.test.ts](https://github.com/open-pencil/open-pencil/blob/4ca4e03177a6aa39673c53793745b9dc1e9eb84a/packages/mcp/tests/server/options.test.ts): pruebas escritas para catálogo registrado, anotaciones, exclusiones, argumentos inesperados, scope y rutas. Leídas, no ejecutadas.

## Kalka: diferencias observadas entre los commits estudiados

No atribuir una diferencia a innovación exclusiva del fork sin comparar el ancestro común; aquí se comparan snapshots.

- [schema.ts](https://github.com/leyscore/kalka/blob/46031f169704b177858beacd897a2d81187798fb/packages/core/src/tools/schema.ts), [registry.ts](https://github.com/leyscore/kalka/blob/46031f169704b177858beacd897a2d81187798fb/packages/core/src/tools/registry.ts) y [manifest.ts](https://github.com/leyscore/kalka/blob/46031f169704b177858beacd897a2d81187798fb/packages/mcp/src/tool/manifest.ts): misma idea de registro y metadatos, añade `output` JSON/file y `returnsFile`.
- [registration.ts](https://github.com/leyscore/kalka/blob/46031f169704b177858beacd897a2d81187798fb/packages/mcp/src/tool/registration.ts): `applyPolicy` conserva política actual, añade/elimina registros al cambiar y recalcula tras handshake. Filtra según capacidad del cliente (elicitation/sampling). Permite resultado inline o URL para archivos. Guardar esta idea para R02/R09; no copiar un servidor de larga vida para nuestro stdio.
- [decisions.ts](https://github.com/leyscore/kalka/blob/46031f169704b177858beacd897a2d81187798fb/packages/mcp/src/tool/decisions.ts): preguntas contextuales por operaciones concretas. La eliminación de una colección usada contempla continuar sin formulario en clientes incompatibles; NO copiar ese fallback. En el router una acción reservada permanece bloqueada si falta confirmación.
- [html/read.ts](https://github.com/leyscore/kalka/blob/46031f169704b177858beacd897a2d81187798fb/packages/core/src/tools/html/read.ts): `get_html` conserva IDs por elemento, referencia imágenes por hash y marca truncamiento con longitud total; límite 16.000 caracteres. Relevante para R04/R10, no requisito R01.

## Figma y Paper

Figma separa `get_metadata` (árbol ligero), `get_design_context` (contexto profundo), `get_screenshot` y `get_variable_defs`. Distingue herramientas remotas y desktop. `use_figma` permite escribir e inspeccionar, por lo que su clasificación es general, no una autorización para ejecuciones arbitrarias. Aplicación: contexto progresivo, operaciones especializadas, disponibilidad explícita, sin introducir ejecución arbitraria en R01.

Paper documenta un proxy CLI stdio que anuncia herramientas aunque Desktop esté cerrado; la ejecución real requiere Desktop. Su cliente Pi de terceros obtiene `tools/list`, convierte los esquemas anunciados y registra las tools con prefijo `paper_`; reenvía texto e imágenes. Inyecta reglas breves durante la sesión y guía completa solo durante dos turnos iniciales tras conexión; luego consulta `get_guide` cuando corresponda. Es una referencia para contexto bajo demanda, no prueba de que esta estrategia sea mejor en nuestro G5. Reintento de sesión no debe convertirse en reintento ciego de una escritura. No copiar código PI hasta resolver licencia.

## Doop: paridad explícita sin registro universal

[agentToolParity.test.ts](https://github.com/kgoedecke/doop/blob/6009dc3da00f3a95d3e288e721185af9fad61ef7/tests/agentToolParity.test.ts) usa cliente MCP conectado por transporte in-memory y compara el catálogo real con el conjunto del agente residente. Clasifica equivalencias, funciones ya cubiertas por contexto y brechas. Prueba también que las excepciones no queden obsoletas. Es un patrón de test aplicable independientemente del diseño de registro. AGPL: reimplementar desde requisitos propios, no copiar código. [toolLoads.ts](https://github.com/kgoedecke/doop/blob/6009dc3da00f3a95d3e288e721185af9fad61ef7/server/toolLoads.ts) delimita carga, lectura, presupuesto y escritura por llamada. Fuera de R01.

## Router: comparación estática

Fuentes: [mcp_server.py](https://github.com/fegome90-cmd/design-skills-router/blob/e1aa16f2fe20540dd4de47704d169c4690e5c42a/plugin/skills/design-tree/scripts/mcp_server.py), [runner.py](https://github.com/fegome90-cmd/design-skills-router/blob/e1aa16f2fe20540dd4de47704d169c4690e5c42a/plugin/skills/design-tree/scripts/runner.py), [cli.py](https://github.com/fegome90-cmd/design-skills-router/blob/e1aa16f2fe20540dd4de47704d169c4690e5c42a/packages/cli/src/design_skills_router/cli.py).

| Tool MCP | CLI | Ruta común y diferencia |
|---|---|---|
| next_node() | context-next | context_command('next'); obtiene estado y frontier. |
| open_node(node_id) | context-open NODE | context_command('open'); puede persistir paquete de contexto y aumentar revisión; no es solo lectura estricta. |
| search_context(node_id, query) | context-search NODE --query QUERY | context_command('search'); puede reconstruir índice derivado SQLite; no registra un paquete nuevo en el ledger por una búsqueda. |
| submit_evidence(node_id, expected_revision, proposal) | propose NODE --file FILE | Ambas usan Router.propose y save_state. MCP se limita a nodos del piloto G5 y exige revisión esperada por el cliente y evidencia absoluta canónica dentro de evidence/ junto al ledger, sin que ese directorio sea un enlace simbólico. CLI genérica también admite nodos fuera del piloto bajo los gates del runner; lee la revisión de inicio de la llamada y la usa al guardar, sin exigir revisión explícita del cliente, y conserva su propio contrato de evidencia. |

`context_command` comprueba `expected_revision` antes de `Router.propose` en MCP; `save_state` protege la escritura concurrente en ambas rutas. No son garantías idénticas. Una propuesta confirmada por persona no es lo mismo que el registro `AWAITING_HUMAN`. El runner sigue siendo autoridad. La CLI Typer construye argv para el parser portable, mientras MCP llama a la función Python directamente. No igualar la totalidad de las CLI y MCP, ni eliminar las restricciones deliberadas del transporte.

Evidencia de pruebas existentes: [test_node_context.py](https://github.com/fegome90-cmd/design-skills-router/blob/e1aa16f2fe20540dd4de47704d169c4690e5c42a/plugin/tests/test_node_context.py) contiene test stdio del conjunto exacto de cuatro tools, rechazo de borrador sin permiso, revisión anterior y propuesta incompleta, aceptación como AWAITING_HUMAN; también prueba índice reconstruible. [test_installed_cli.py](https://github.com/fegome90-cmd/design-skills-router/blob/e1aa16f2fe20540dd4de47704d169c4690e5c42a/packages/cli/tests/test_installed_cli.py) cubre instalación, ayuda, JSON, errores y ejecución fuera del checkout. No se observó ejecución de una matriz completa de paridad en esta sesión.

## ADR-R01 provisional

| Alternativa | Ventaja | Costo/riesgo |
|---|---|---|
| A: handlers explícitos + matriz de paridad con excepciones | No cambia arquitectura; detecta deriva observada; conserva firmas y contratos. | Es necesario mantener la matriz cuando cambien operaciones. |
| B: definición interna mínima + adaptadores | Catálogo y metadatos de operaciones comunes; reduce repetición si crecen las tools. | Añade un concepto, puede duplicar esquemas FastMCP/Typer y confundir efectos con permisos; riesgo de convertirlo en segundo dispatcher. |

Preferencia provisional: A como primer incremento comprobable. Si B demuestra reducción de duplicación o defectos al modelar una incorporación simulada de R03, adoptar B de forma mínima. No decidir por similitud con OpenPencil. No introducir Pydantic/Valibot/TypeScript como dependencia nueva por este estudio. No modificar tree-v0.4. Diferenciar efectos de ledger, índice derivado, archivos y artefacto de diseño. R02 definirá permisos y control por llamada; R09 definirá evidencia visual.

## G2: experimentos pendientes, no ejecutados

1. Revalidar HEAD actual del router y pins de fuentes; checkout aislado, sin cambios a main. Leer las reglas vigentes.
2. Construir wheel/sdist e instalar en entornos separados base y [mcp]. Con cliente stdio capturar `tools/list`, argumentos, tipos, required y resultados. No inferir esquemas desde Python.
3. Usar el fixture sintético G5 descrito en el spec R01, con copias independientes del mismo ledger. Comparar cuatro operaciones y estados observables. Probar primer open (paquete persistido) y segundo open (sin cambio si paquete idéntico); search con índice perdido; borrador sin permiso; propuesta válida AWAITING_HUMAN; revisión obsoleta y rutas fuera de evidence/. Separar diferencias intencionales de defectos. Comparar semántica, no formato textual. Capturar hash/revisión antes y después.
4. Añadir a una copia desechable de A y B una operación de lectura sintética equivalente a R03, sin incorporarla al catálogo productivo. Medir definiciones tocadas, esquemas duplicados, dependencias, pruebas que detectan deriva de nombre/campo/handler y preservación del contrato instalado. Registrar líneas y archivos modificados, no fijar conteos a priori. En OP, ejecutar un caso equivalente usando tool list/describe/call y MCP si el runtime está disponible. Si no, NOT_RUN.
5. Ejecutar pruebas G5, CLI instalada, suite plugin y doctor según baseline actual. Revisión independiente EGM con evidencias reales y decisión GO/ADAPT/NO_GO. Si A cumple y B no demuestra valor, cerrar sin registry nuevo. Si B aporta valor, pedir autorización de implementación y congelar plan separado. No ejecutar R02 por inercia.

Resultado de esta sesión: investigación estática y ADR provisional. Paridad ejecutada, tests upstream, prototipo comparativo, juicio independiente y decisión final: NOT_RUN. En la sesión original de investigación no se realizaron cambios en GitHub. La incorporación posterior de este documento al PR borrador no modifica esos resultados.

## Decisión operativa posterior al dossier

El operador decidió el 24-11-2026 que los experimentos A/B no sean requisito para esta fase de desarrollo. Seleccionamos A: handlers explícitos, runner existente y prueba de paridad. B queda como opción futura, no como trabajo pendiente de R01. Se conserva el texto histórico del estudio; la versión vigente del contrato es el spec R01.

La prueba checkout-level packages/cli/tests/test_mcp_parity.py usa una copia temporal del paquete CLI instalado (en la verificación histórica, instalado desde un wheel), pins sintéticos, dos expedientes independientes y un cliente MCP stdio real. La revisión posterior verifica primero la igualdad del contrato instalado con el checkout y adapta solo los git_blob de las fuentes sintéticas. No altera el runtime. El 24-11-2026 se ejecutó en macOS, Python 3.12.16 y MCP 1.30.0:

| Control | Resultado observado |
|---|---|
| Build wheel/sdist | PASS |
| Prueba de paridad G5 | 1/1 PASS |
| Suite plugin | 209/209 PASS |
| Suite CLI con MCP | 12/12 PASS |
| CLI base sin MCP | 11 PASS, 1 omitida por extra ausente |
| Recursos portables | 20/20 idénticos entre wheel y sdist |
| Doctor y verify-package | Exit 0; baseline_verified=true |

No se ejecutó A/B ni se probó el código externo en runtime. Las cifras son históricas, de las pruebas ejecutadas localmente sobre el runtime sin cambios y la prueba original; la revisión independiente y los checks del HEAD actualizado se consultan en el [PR #7](https://github.com/fegome90-cmd/design-skills-router/pull/7). No representan por sí solas el resultado de revisiones posteriores, un merge del PR ni una mejora del juicio visual del agente.
