# Design Skills Router

Lee la guía que corresponda al encargo.

| Encargo | Empieza por |
| --- | --- |
| Entender qué hace el Router y qué está planificado | [Contexto](docs/agent/CONTEXT.md) |
| Cambiar una regla, un contrato o un límite entre componentes | [Arquitectura](docs/agent/ARCHITECTURE.md) |
| Editar una vista, rastrear una decisión o localizar una prueba | [Mapa de código](docs/agent/CODEMAP.md) |
| Cambiar un subcomando o su ayuda | [Mantenimiento del plugin](plugin/AGENTS.md) y [pruebas del CLI](docs/agent/RUNTIME.md#comprobar-el-cli-del-plugin) |
| Recuperar o migrar un expediente | [Persistencia y migración](plugin/skills/design-tree/references/CLI.md#persistencia-y-migración) |
| Explorar relaciones entre archivos y símbolos | [Graphify](docs/agent/CODEMAP.md#grafo-de-código-con-graphify) |
| Configurar los lenguajes, reconstruir o comprobar el repositorio | [Operación y verificación](docs/agent/RUNTIME.md) |

El punto de entrada del repositorio es [README.md](README.md). Para mantenimiento del plugin, sigue [plugin/AGENTS.md](plugin/AGENTS.md). Para un encargo de diseño, sigue [design-tree](plugin/skills/design-tree/SKILL.md). Interpreta las rutas de código de estas guías desde la raíz del repositorio.

## Code Review Rules

Reglas para revisar pull requests en este repositorio. Asigna la severidad según el impacto real del caso, no por la regla: un defecto en código de producción o en una prueba que protege un contrato pesa más que uno en un ejemplo o en una herramienta auxiliar. Señala un hallazgo solo cuando el diff lo muestre, y cita archivo y línea.

### Equivalencia que también pasaría con resultados vacíos

Una prueba compara dos resultados (por ejemplo, CLI frente a MCP, o antes frente a después) sin comprobar que alguno contenga datos. Si los dos lados devuelven una lista vacía, `None` o un error equivalente, la prueba pasa y el contrato queda sin proteger: un fallo que rompa ambos transportes a la vez no se detecta.

Evidencia: un `assertEqual(a, b)` o una igualdad entre resultados sin ninguna aserción previa sobre el contenido, la longitud o un campo concreto de alguno de ellos. No aplica cuando el vacío es precisamente el resultado esperado y la prueba lo afirma de forma explícita.

### Rechazo sin comprobar el estado antes y después

Una prueba verifica que una operación se rechaza (código de error, excepción o mensaje) pero no comprueba que el rechazo deje intacto el estado persistente: el ledger, el índice, los archivos o la revisión. Un rechazo que escribe a medias pasa la prueba y corrompe el expediente.

Evidencia: una aserción de error sin una captura del estado anterior (bytes, hash o revisión) comparada con el estado posterior. No aplica a operaciones que no tienen estado persistente.

### Afirmación de un spec que el código citado no cumple

Un documento de `docs/specs/` afirma un contrato, un nombre, una regla de rechazo o una cobertura de pruebas que el código o la prueba que cita no implementa. Quien siga el spec confiará en una protección que no existe y aprobará cambios que la rompen.

Evidencia: una frase del spec que no coincide con el código citado en el mismo PR o en `main`, por ejemplo un error que el código lanza con otro código, una prueba que no hace la comprobación descrita o un paso de CI que no ejecuta lo que el spec dice. Indica el archivo y la línea de ambos lados.

### E/S de texto con codificación implícita

Un `open`, `read_text`, `write_text`, `tempfile` o `subprocess` en modo texto que no indica `encoding`. En un sistema que no usa UTF-8, los textos con tildes del repositorio se leen o escriben mal, o la operación falla. `scripts/check-encoding.py` y el workflow `python-quality.yml` ya lo bloquean en CI; señálalo solo si un cambio lo elude, por ejemplo con el marcador `check-encoding: ignore` sin un motivo válido o con una ruta que la guardia no cubre.

Evidencia: la llamada de texto sin `encoding`, o un marcador `ignore` cuyo motivo no explica por qué la API no abre texto.
