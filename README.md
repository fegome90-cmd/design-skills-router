# Design Skills Router

Design Skills Router ayuda a elegir qué skills consultar para una tarea de diseño y a explicar por qué se propone cada una.

Abre [la pizarra autónoma v1.4](release/design-router-pizarra-v1.4-offline.html) después de descomprimir el repositorio. Desde **Mapa del plugin** puedes seguir una decisión hasta el archivo, símbolo y línea que la implementan. La [pizarra v1.4 con referencias web](release/design-router-pizarra-v1.4.html) y la [pizarra v1.3 original congelada](release/design-router-pizarra-v1.3.html) también están disponibles en `release/`.

Este repositorio reúne la pizarra v1.4 (con v1.3 congelada), el plugin 0.3.1 con su árbol v0.4 y el colector opt-in de telemetría. El [catálogo](docs/skills.md) registra las revisiones de las skills referenciadas. Las copias espejo de fuentes en `vendor/` y el asistente experimental en `assist/` no se publican en este repositorio; aquí la verificación del paquete se realiza con `runner.py verify-package` y `doctor.py`.

## Ejemplo de selección

«Quiero auditar cómo se distribuye el contenido de una pantalla y si se entiende qué elemento es el más importante».

Para una auditoría con ese alcance, el router propone **G5**, el especialista en composición, cuadrícula y jerarquía visual. La selección reúne tres tareas en modo de **solo lectura**:

- Revisar la coherencia visual de la pantalla.
- Comprobar la accesibilidad de la interfaz.
- Examinar cómo responde el diseño ante casos extremos, como un título demasiado largo.

El resultado es una propuesta de revisión. La persona a cargo decide qué comprobaciones llevar a cabo.

## Prototipo de escritorio

El [prototipo React](board/desktop-demo/README.md) incluye un espacio de trabajo con navegación, conversaciones de ejemplo y un dashboard interactivo. La guía del prototipo explica cómo ejecutarlo y comprobarlo localmente.

## Dónde trabajar

| Para | Punto de entrada |
| --- | --- |
| Cambiar una vista o el simulador | [Fuentes HTML, CSS, JS y JSON por vista](board/README.md). Las reglas del simulador están en [politica.json](board/src/simulador/politica.json). |
| Seguir el flujo real del plugin | [Skill de entrada](plugin/skills/design-tree/SKILL.md), [CLI Python](plugin/skills/design-tree/scripts/runner.py), [expansión de decisiones](plugin/skills/design-tree/scripts/tree_model.py) y [contratos](plugin/skills/design-tree/scripts/contracts.py). |
| Localizar decisiones y reglas | [tree.json](plugin/skills/design-tree/references/tree-v0.4/tree.json) y [rules.json](plugin/skills/design-tree/references/tree-v0.4/rules.json). El [constructor del visor](decision-authoring/README.md) permite regenerar el HTML histórico. Para experimentar con cambios usa una copia del árbol. El plugin comprueba la huella de su versión canónica. |
| Editar relaciones semánticas | [Grafo JSON de la pizarra](board/src/relaciones/datos.json), [TriG y draw.io](semantic/relaciones-v0.5/) y [mapa de funciones](board/src/mapa-funcional/datos.json). [Procedencia por versión](semantic/PROCEDENCIA.md). |
| Consultar la revisión de una skill | [Catálogo de 111 skills](docs/skills.md) con las revisiones de la pizarra y del inventario del plugin. |
| Rastrear una decisión al código | [Guía de navegación](map/README.md), [generador](map/assemble_map.py), [vista navegable](map/view.py) y [380 nodos con 1.411 enlaces](release/design-router-mapa-fuentes.json). Las rutas del mapa se resuelven bajo `plugin/`. |
| Mantener el plugin | [Manual](plugin/skills/design-tree/references/MAINTENANCE.md), [manifiesto](plugin/.codex-plugin/plugin.json), [pruebas](plugin/tests/) y [herramienta de release](plugin/scripts/release.py). |
| Reproducir los hallazgos v1.1 | [Auditoría histórica](history/v1.1/README.md), HTML original y anotado, pruebas negativas, informe y capturas. |
| Revisar el futuro MCP | [Plan de integración](docs/Plan_MCP_Design_Router.md). El servidor queda como trabajo posterior. |
| Medir uso global del árbol y las skills | [Telemetría](telemetry/README.md), [auditoría y límites](docs/telemetry/AUDIT.md). El colector es opt-in y no observa ejecuciones sin un host que las reporte. |

## Cómo leer los inventarios

El árbol contiene 239 declaraciones que se expanden a 3.660 apariciones en diferentes recorridos. El inventario original contiene 82 skills. La capa de investigación añade 47 fichas candidatas, 18 compartidas con ese inventario. El grafo reúne 111 identidades y 171 relaciones, 14 documentadas y 157 propuestas. El índice mantiene el estado de cada nodo y distingue las revisiones fijadas por el plugin y por la pizarra. La skill instalable de entrada es `design-tree`. El inventario y las propuestas sirven para inspección y selección supervisada.

## Reconstruir y comprobar

Desde la raíz, con Python 3.10 o posterior y Node.js 18 o posterior:

```sh
python3 -B tools/build.py
python3 -B tools/build.py --output-dir .preview
python3 -B decision-authoring/build.py --verify-original --check regressions
(cd plugin && python3 -B -m unittest discover -s tests)
python3 -B plugin/skills/design-tree/scripts/runner.py verify-package
npm test
npm run test:telemetry
git status --short
```

La reconstrucción local no requiere conexión. `python3 -B tools/build.py` regenera la pizarra v1.4, su variante autónoma, el mapa de fuentes en `release/` y `map/tree_data.json` sin modificar las versiones congeladas. La pizarra v1.3 original conserva el SHA-256 `c07323286b8cf2c285049527c676f19f2d3016fadf078ac47a40e41683eb119e`. La variante autónoma contiene las fuentes y los componentes Shoelace que usa la interfaz. El diagrama usa SVG local y se exporta como draw.io. El enlace al editor externo requiere conexión. La instrumentación opt-in de telemetría se compila tanto en `release/design-router-pizarra-v1.4*.html` como en `.preview/`.

Para comprobar el paquete y entender el alcance de la verificación de las fuentes fijadas, consulta [operación y verificación](docs/agent/RUNTIME.md#reproducir-las-versiones-fijadas).

Para volver a ejecutar las pruebas de interfaz en Chromium, instala las dependencias de desarrollo y el navegador:

```sh
npm ci
npx playwright install chromium
npm run test:golden
npm run test:browser
npm run test:offline
npm run test:preview
npm run test:telemetry:e2e
node tests/sidebar-preference.cjs .preview/design-router-pizarra-v1.4.html
```

Con un Chromium existente, puedes especificar su binario en `PLAYWRIGHT_CHROMIUM_EXECUTABLE`. Registros históricos de la línea base v1.3: [pruebas Chromium](evidence/chromium.log), [apertura autónoma sin solicitudes HTTP](evidence/offline-chromium.log) y [pruebas del plugin](evidence/repo-unit.log).

## Cómo colaborar

Este repositorio público reúne las propuestas y revisiones de personas y agentes.

- Para proponer un cambio o informar un problema, abre un [issue](https://github.com/fegome90-cmd/design-skills-router/issues). Describe el caso concreto, el resultado esperado y cómo se podría comprobar.
- Para entregar un cambio, abre un [pull request](https://github.com/fegome90-cmd/design-skills-router/pulls) hacia `main`. Enlaza el issue cuando exista y resume qué cambió, cómo lo probaste y qué queda por verificar.

## Seguridad de las contribuciones

El hook comprueba el contenido preparado en Git antes de cada commit. Busca claves de API, material de clave privada y rutas personales de macOS. También bloquea nombres de archivos sensibles, incluso si el archivo está vacío. Para documentar variables de entorno, usa un `.env.example` con valores vacíos.

### Activar el hook en cada clon

Instala Python 3 y [Gitleaks](https://github.com/gitleaks/gitleaks/releases/tag/v8.30.1). La comprobación de GitHub usa Gitleaks 8.30.1. Desde la raíz del clon:

```sh
git config --local core.hooksPath .githooks
git config --local --get core.hooksPath
```

El segundo comando debe mostrar `.githooks`. Después de preparar los archivos con `git add`, puedes comprobarlos con `./scripts/check-secrets.sh staged`. Si se bloquea el commit, retira del índice el archivo privado o sustituye la credencial por una referencia a una variable de entorno, y vuelve a preparar los cambios.

GitHub Actions ejecuta **Secrets and private paths** al recibir un push o un pull request. Para comprobar localmente los commits alcanzables desde `HEAD`, ejecuta `./scripts/check-secrets.sh history`.

Si ya publicaste una credencial, revócala en el proveedor antes de sanear el historial. Para avisar al mantenedor, usa el [reporte privado de seguridad](https://github.com/fegome90-cmd/design-skills-router/security/advisories/new) e indica el archivo y el commit. Omite el valor de la clave.

En el PR que introduce el escáner, el workflow identifica el commit de base inicial y verifica las huellas SHA-256 de los tres archivos de política antes de ejecutarlos. En los PR posteriores usa la política del commit base de cada PR.
