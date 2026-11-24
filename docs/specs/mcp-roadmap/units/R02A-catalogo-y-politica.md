# R02A — Catálogo y política por operación

Estado: implementado y verificado localmente. No integrado ni publicado.
Base: e1aa16f2fe20540dd4de47704d169c4690e5c42a (main).
Gate de publicación: R01 (#7) integrado, revisión y CI del HEAD correspondiente.
El roadmap v0.2 y la rama preparatoria citados en el encargo no estaban
disponibles en los checkouts inspeccionados; el contrato de esta unidad
es el ancla del operador. No reconstruye R01 ni las unidades posteriores.

## Procedencia del port

OpenPencil, commit [4ca4e03177a6aa39673c53793745b9dc1e9eb84a](https://github.com/open-pencil/open-pencil/tree/4ca4e03177a6aa39673c53793745b9dc1e9eb84a), MIT.
Aviso íntegro en plugin/NOTICE.md; cabecera de atribución en tool_catalog.py.

| Fuente | Lógica adaptada |
| --- | --- |
| packages/core/src/tools/schema.ts | defineTool, ToolDef, ToolCapability, ToolExecution; mutación y capacidades declarativas |
| packages/core/src/tools/registry/index.ts | registro explícito de definiciones |
| packages/mcp/src/tool/metadata.ts | ToolDescriptor |
| packages/mcp/src/tool/policy.ts | parseDisabledTools, isToolEnabled, applyToolPolicy |
| packages/mcp/src/tool/manifest.ts | proyección de descriptores desde el registro |
| packages/mcp/src/tool/registration.ts | filtrado y metadatos/annotations al registrar |
| packages/mcp/tests/tool/scope.test.ts | caso de una herramienta denegada y otra permitida, adaptado a dos operaciones analyze |

No se trasladan las funciones del editor, su motor gráfico ni su sistema
de evaluación. El test upstream de parseToolDescriptor no se incorpora:
los descriptores se construyen internamente y no se reciben del cliente.

## Contrato de ejecución

Una sola tabla inmutable de cuatro operaciones. Los efectos derivan de las
mutaciones declaradas. El runner existente ejecuta los handlers y aplica
la política antes de acceder al expediente y el índice por la ruta
context_command. La CLI histórica propose también sirve propuestas humanas:
lee el expediente para identificar G5 y comprueba la política antes de
validar el expediente o leer el payload, sin mutar nada en caso de rechazo.
Los métodos directos del runner también comprueban la política; CLI y MCP
conservan sus contratos públicos. Las comprobaciones de dominio existentes
no se sustituyen. No se cambian mandatos, recibos ni fases.

Configuración del operador en el entorno del proceso:
DESIGN_ROUTER_DISABLED_TOOLS=search_context (lista de nombres separados
por comas). Ausente o cadena vacía: ninguna restricción adicional.
Se eliminan espacios alrededor de nombres y se deduplican. Nombres
desconocidos, comodines, diferencias de mayúsculas y elementos vacíos
intermedios se rechazan; no se ignoran errores silenciosamente.
Una llamada no puede elegir su propia política mediante argumentos.
El operador debe controlar el proceso y su entorno; no es una frontera
de seguridad frente a un agente con acceso arbitrario a la shell.

El registro MCP se filtra al arrancar y las ejecuciones se vuelven a
comprobar en el runner. El catálogo no pretende reflejar revocaciones de
mandatos en vivo en esta unidad (R02C). Las propuestas humanas no G5
conservan su comportamiento. No se agrega un dispatcher ni servidor.

## Reproducción

Desde el checkout, usando Python 3.12, uv y entornos virtuales aislados:

```sh
B="$(mktemp -d)"
B="$(cd "$B" && pwd -P)"
mkdir -p "$B/tmp"
export TMPDIR="$B/tmp"
python -B packages/cli/build.py --out-dir "$B/dist" --allow-network
python -m venv "$B/base"
"$B/base/bin/python" -m pip install "$B"/dist/*.tar.gz
"$B/base/bin/python" -c 'import importlib.util; assert importlib.util.find_spec("mcp") is None'
"$B/base/bin/python" -B -m unittest discover -s packages/cli/tests -p test_installed_cli.py -v
python -m venv "$B/extra"
wheels=("$B"/dist/*.whl)
"$B/extra/bin/python" -m pip install "${wheels[0]}[mcp]"
"$B/extra/bin/python" -B -m unittest discover -s plugin/tests
"$B/extra/bin/python" -B -m unittest discover -s packages/cli/tests -v
"$B/extra/bin/python" -B plugin/skills/design-tree/scripts/doctor.py --format json
"$B/extra/bin/python" -B plugin/skills/design-tree/scripts/runner.py verify-package
```

Las pruebas de integración crean expedientes y fuentes sintéticas y usan
una copia desechable de la instalación para adaptar únicamente los pines
al fixture. El cliente usa MCP stdio real, no mocks. La resolución
canónica del directorio temporal en macOS evita aliases de /tmp y /var
sin debilitar las restricciones de rutas del servidor.

## Resultados locales observados

Python 3.12.16, design-skills-router 0.3.1, MCP SDK 1.30.0.
Se construyeron wheel y sdist; instalación base desde sdist y extra desde
wheel en entornos nuevos. Primera iteración: plugin 215/215, CLI+MCP 14/14, CLI base 11/11.
Doctor exit 0, cero hallazgos; verify-package baseline true, 82 entradas,
3660 nodos expandidos. Las cuatro pruebas iniciales de política fallaron
antes del port; posteriormente se extendieron a seis pruebas verdes.
La suite de integración contiene tres pruebas nuevas:

- Con analyze autorizado, search_context no anunciado ni invocable;
  open_node entrega cinco secciones y conserva la paridad.
- Se comparan bytes/existencia del expediente e índice antes y después
  de los rechazos, tanto con índice ausente como existente.
- Política inválida rechazada en ambos adaptadores, contrato original de
  las cuatro operaciones y propuesta válida AWAITING_HUMAN.

Además, el ejecutable original del wheel instalado (sin adaptar pines)
se probó mediante CLI y un cliente stdio real: tools/list devolvió
next_node, open_node y submit_evidence; llamada directa a search_context
devuelve Unknown tool: search_context. La CLI devuelve
TOOL_DISABLED:search_context con exit 2.

El manifiesto de distribución se actualiza solo para los archivos tocados;
el baseline canónico v0.4 no cambia. CI de R02A no ejecutada: no hay PR.

## Revisión independiente de la primera iteración

Codex gpt-6.2-astra, razonamiento alto, en modo filesystem read-only,
sobre 916e93f8b8cdedba4e8ac1155625fac30d779372: sin bypass de ejecución
G5 deshabilitada identificado; tres P2 (orden del guard de propose,
capacidades de lectura de next_node y efectos de resubmission).
Se añadieron dos regresiones: antes del fix, el payload ausente produjo
FileNotFoundError en vez del rechazo esperado y la metadata omitía lecturas.
Los cambios de seguimiento corrigen los tres hallazgos, sin cambiar gates
ni el comportamiento humano fuera del piloto. La metadata enumera
también los efectos condicionales de historial, invalidación, candidatos
y vinculación de rutas de evidencia. El guard histórico de propose
necesita leer el expediente para discriminar G5 de propuestas no piloto.

Verificación posterior a los fixes: plugin 217/217; CLI+MCP 14/14;
CLI base 11/11; doctor exit 0, sin hallazgos; baseline intacto.
Wheel y sdist reconstruidos e instalados. La prueba instalada incluye
un JSON deliberadamente inválido bajo submit_evidence deshabilitada,
que se rechaza por política antes de parsearlo.
El HEAD de seguimiento requiere revisión independiente/CI antes del PR.
