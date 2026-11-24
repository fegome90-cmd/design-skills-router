# Plan del MCP para Design Skills Router

**Propuesta para decisión · 17 de noviembre de 2026**  
**Base comprobada:** pizarra 1.3, política de selección 1.2, plugin 0.3.1 y árbol 0.4.  
**Objetivo del primer piloto:** desde un chat, obtener la misma propuesta de especialistas y apoyos que en la pizarra, y poder inspeccionar el nodo que justifica la recomendación.

## Evolución del runner MCP

Este documento conserva el plan inicial del piloto. El contrato del MCP stdio G5 y su paridad con la CLI instalada se documentan en [R01](specs/mcp-roadmap/units/R01-registro-compartido-de-tools.md), con la investigación y decisión de implementación en el [dossier R01](specs/mcp-roadmap/research/R01-dossier-v0.1.md).

## La experiencia que queremos probar

Felipe escribe «Audita el layout de esta pantalla». El host interpreta «auditoría» y «layout» usando el catálogo del router. La herramienta recibe la ruta, el alcance del escenario y el dominio G5. Devuelve G5 (layout, grilla y jerarquía), las funciones aplicables y los apoyos agrupados según su efecto. El agente puede explicar por qué dejó fuera la revisión de movimiento y qué fuente tendría que consultar antes de avanzar. Si Felipe escribe solo «audita la interfaz», la herramienta devuelve una pregunta para delimitar el dominio. El modelo formula esa pregunta en español, usando los nombres de las disciplinas.

Una segunda consulta responde «¿Qué respalda esa ruta?». Muestra la relación entre función y definición del árbol, y permite abrir el criterio o el código que lo consulta. Si la pregunta es «¿cuál es el siguiente paso de *mi proyecto*?», se necesita un expediente concreto. Esa capacidad corresponde a la ampliación del piloto.

## Qué podemos reutilizar

| Fuente comprobada en el HTML o el plugin | Uso propuesto |
|---|---|
| `capabilityMapData` | Catálogo de rutas, funciones, especialistas, contribuciones, efectos y referencias a nodos. Las 28 funciones contienen 53 referencias a 32 nodos distintos. Todos existen en el grafo 1.3. |
| `minRouteData` y `selection.js` | Política de selección mínima. Centralizar selección de funciones, resolución de especialistas, clasificación de apoyos, aplicabilidad y validación. |
| `routerNodeData` | Índice de 380 nodos y 1.411 relaciones. Permite consultar una definición, alternativa, archivo o símbolo y distinguir el tipo de vínculo. |
| `tree.json`, `runner.py` y expediente del plugin | Árbol canónico y estado del proyecto. `Router.packet`, `Router.active` y `Router.frontier` permiten consultar qué se presenta, qué está activo y qué falta resolver. |

Hay un detalle que cambia la arquitectura. En la v1.3, el selector lee botones activos y campos del DOM. Incluso la validación usa la visibilidad de un control. La lista genérica de especialistas de `visual-qa` omite G2, mientras que la política de auditoría sí lo habilita. Parsear los nombres de las funciones o recorrer aristas del grafo perdería esa regla.

## Arquitectura propuesta

Usar el HTML entregado como referencia verificable. Congelar su huella y capturar entradas y salidas por la interfaz en Chromium. Luego extraer a un módulo JavaScript puro las reglas hoy mezcladas con los controles. El módulo acepta un objeto de entrada y el catálogo versionado. La pizarra y el servidor MCP consumen la misma implementación. Chromium queda en las pruebas de paridad. Un cambio de política se construye, se prueba y se distribuye una sola vez para ambos consumidores.

Para el piloto propongo un adaptador pequeño en TypeScript/Node y el SDK oficial de MCP. El host traduce lenguaje natural a identificadores del catálogo. El servidor valida esos identificadores y calcula la ruta de forma determinista. El resultado lleva versión del esquema, versiones de catálogo y política, y huella del paquete que reúne datos y código. La huella actual de `minRouteData` identifica solo la política embebida.

La primera versión puede ser de solo lectura y sin persistencia del servidor. El estado explícito de cada llamada incluye la selección y, cuando proceda, las revisiones de aplicabilidad de ese contexto. Al cambiar ruta, alcance, función o dominio se usa la revisión correspondiente. El cliente conserva esas revisiones durante la interacción. Una invocación idéntica debe producir el mismo resultado independientemente del usuario o de llamadas anteriores.

## Contrato mínimo

Estos nombres son propuestas para el nuevo MCP. Las pruebas fijarán los esquemas antes de congelar la interfaz.

| Herramienta | Entrada | Resultado |
|---|---|---|
| `resolver_ruta` | Ruta, alcance, función si el alcance es individual, dominio opcional y revisiones opcionales vinculadas al contexto | Especialistas, funciones solicitadas y efectivas, apoyos con su efecto y permiso, referencias de fuente y de árbol, validación y pregunta pendiente si corresponde. |
| `consultar_router` | Una variante explícita: consultar catálogo, buscar por término o leer nodo por ID | Opciones válidas para construir una consulta, o una ficha con ID de definición, ID de ocurrencia si se proporcionó, criterio, archivo, símbolo o JSON Pointer y vecinos tipados. Limitar los vecinos por página y devolver cursor si quedan más. |

El catálogo debe poder descubrirse desde el chat. La salida debe incluir texto breve y datos en `structuredContent` con esquema. Los nombres de skill y los IDs de nodo pertenecen a espacios distintos. La respuesta conserva la relación explícita `función → nodos`. Un ID desconocido devuelve un error de entrada. Un dominio legítimamente ausente devuelve un resultado de negocio con la pregunta pertinente. Una combinación conocida pero incompatible devuelve el conflicto y las opciones que permiten corregirlo.

**Ejemplo de llamada propuesta**

```json
{"ruta":"auditoria","alcance":"scenario","dominio":"G5"}
```

**Resultado esperado para esa entrada:** especialista `G5`; funciones `visual-qa`, `accessibility` y `stress-test`; permiso efectivo de solo lectura. El catálogo vincula `visual-qa` a `QA01`, `accessibility` a `AC01` y `TY03`, y `stress-test` a `LAY01` y `QA01`. Se conserva la relación por función aunque un mismo nodo aparezca dos veces. La contribución analítica de `break-ui` se distingue de su contribución de prototipado, prohibida en esta auditoría. Una propuesta puede ser útil aunque el expediente siga incompleto. Se mantienen separados validez, completitud, aprobación y ejecución.

**Autoridad del piloto:** las herramientas pueden recomendar una skill y devolver su fuente fijada. Para afirmar que fue consultada o ejecutada se requiere evidencia del host. Una respuesta incorrecta del modelo sobre la intención puede producir una ruta coherente para la tarea equivocada: por eso también se prueba la interpretación del encargo y la pregunta de aclaración en conversaciones reales.

## Etapas y criterios de salida

| Etapa | Entrega | Cuándo avanzar |
|---|---|---|
| 1. Fijar referencia | Huellas de HTML, catálogo, grafo y política. Fixtures con entradas, respuestas del navegador y referencias de nodo. | Los casos críticos se reproducen en el HTML congelado. Cada diferencia futura tiene una referencia independiente del código extraído. |
| 2. Extraer el selector | Núcleo compartido y adaptador de la pizarra. Dominio requerido y permisos calculados con datos explícitos. | El núcleo y el HTML reproducen las salidas observadas. Se conservan las 11 pruebas previas del selector y las 7 de navegación del mapa. |
| 3. Exponer las dos herramientas | Servidor local, catálogo consultable, respuestas estructuradas y validación de entradas. | Un cliente MCP descubre y llama ambas herramientas. Pasa la comparación con la referencia, incluida la alternancia de contextos y dos clientes simultáneos. |
| 4. Piloto privado en ChatGPT | Endpoint MCP remoto mediante Streamable HTTP y conexión de prueba. | En chats nuevos se observa selección correcta de herramienta, argumentos coherentes, pregunta útil ante ambigüedad y explicación fiel de la fuente. Registrar llamada y resultado por caso. |
| 5. Decidir la ampliación | Con el piloto observado, elegir entre seguir solo con recomendaciones, añadir una ficha visual o integrar avance de proyecto. | Para avance real, probar primero una lectura del expediente con `packet` y `frontier`, incluidos prerrequisitos, estado pendiente e invalidación. Toda futura mutación debe respetar la revisión del expediente y los recibos del runner. |

Una ficha visual dentro de ChatGPT podría abrir el nodo devuelto y mostrar alternativas como en la pizarra. Propongo evaluarla después de que las dos herramientas funcionen desde texto. El alojamiento, la identidad del proyecto y la persistencia del expediente son decisiones de la etapa que efectivamente los necesite.

## Casos que deciden si el piloto sirve

| Entrada o recorrido | Observación exigida |
|---|---|
| Auditoría sin dominio | Ningún especialista ni apoyo propuesto. Una pregunta concreta para delimitar el dominio. |
| Auditoría focalizada `visual-qa/G2` | Resuelve G2 por la política específica de auditoría. |
| Auditoría de escenario G5 | Devuelve solo G5 como especialista. Los apoyos de motion-review quedan fuera. |
| Tipografía con función `accessibility` sin dominio explícito | Usa G3 según la política contextual. La presencia de un selector visible en el HTML no exige una pregunta. |
| Auditoría `motion-review/G5` | Informa que la función está fuera del dominio elegido y explica qué selección ajustar. |
| G2 → G5 → G2 con justificaciones distintas | Cada contexto recupera sus decisiones. Una exclusión contradictoria o sin razón queda señalada en el expediente. |
| Consulta de `E03__F00` | Identifica la ocurrencia solicitada y su definición F00. La consulta documental no atribuye actividad a un proyecto. |
| Pedido en lenguaje natural en ChatGPT | El host llama la herramienta apropiada, transmite el dominio correcto y presenta la propuesta como propuesta. Medir los errores de interpretación por separado de los errores del selector. |

## Fuentes utilizadas

- [Pizarra v1.3 revisada](https://chatgpt.com/library?file_id=libfile_fde3_f-082eba08a9488191a179ad98e3f7c56f_11107b86ea008191bab113dfcc32deba&account_id=personal)
- [Código del release, mapa y pruebas](https://chatgpt.com/library?file_id=libfile_fde3_f-7b5dbd67ab0c8191b430df2ac14fa0d6_11107b86ea008191bab113dfcc32deba&account_id=personal)
- [MCP, herramientas y salida estructurada](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)
- [MCP, recursos identificados por URI](https://modelcontextprotocol.io/specification/2025-11-25/server/resources)
- [OpenAI, servidores MCP para plugins, herramientas e interfaz opcional](https://developers.openai.com/plugins/build/mcp-server)
