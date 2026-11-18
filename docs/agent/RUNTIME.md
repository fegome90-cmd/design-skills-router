# Operación y verificación

## Configuración en la raíz

- Python 3.10 o posterior. `pyproject.toml` declara el mínimo del repositorio. Los scripts y las pruebas se ejecutan directamente con `python3` y la biblioteca estándar.
- Node.js 18 o posterior. `package.json` declara el mínimo y `package-lock.json` fija las versiones de las dependencias. Las pruebas visuales requieren Playwright y Chromium. El [README](../../README.md#reconstruir-y-comprobar) documenta su instalación y el uso de un binario existente.
- `.editorconfig` define la codificación y el estilo de espacios para los manifiestos npm y las fuentes HTML, CSS, JavaScript y JSON editables de `board/src/`.

## Abrir la pizarra en localhost

Desde la raíz del repositorio, genera y sirve una vista previa de las fuentes editables.

```sh
python3 -B tools/build.py --output-dir .preview
python3 -m http.server 8000 --bind 127.0.0.1 --directory .preview
```

Abre la [pizarra autónoma](http://127.0.0.1:8000/design-router-pizarra-v1.4-offline.html). Después de editar una fuente, vuelve a ejecutar el primer comando y recarga la pizarra. La vista previa conserva los archivos históricos de `release/`. Para detener el servidor, pulsa `Ctrl+C` en la terminal donde lo iniciaste.

## Comprobar un cambio

Ejecuta los comandos desde la raíz del repositorio. `npm run test:core` prueba las reglas del simulador en Node.js. `npm run test:preview` reconstruye `.preview/` y ejecuta la suite semántica y las pruebas Chromium del mapa, el simulador y el HTML autónomo sobre esa vista previa. `npm test` ejecuta las pruebas del núcleo y la suite semántica de `release/`. `npm run test:browser` y `npm run test:offline` también usan los HTML v1.4 de `release/`. `npm run test:golden` comprueba que la v1.3 original sigue pasando su suite semántica y la prueba autónoma en Chromium (requiere `npm ci` y Playwright/Chromium).

Para comprobar solo el contrato semántico de la vista previa, genera el HTML y pásalo directamente a la prueba.

```sh
python3 -B tools/build.py --output-dir .preview
node tests/router-v12.semantic.cjs .preview/design-router-pizarra-v1.4.html
```

Para las pruebas de navegador, pasa el HTML de `.preview/` a `tests/map-test.cjs` y `tests/router-v12.playwright.cjs`. Para la variante autónoma, usa `offline/test-offline.cjs` con el archivo `.preview/design-router-pizarra-v1.4-offline.html`.

`node tests/sidebar-preference.cjs .preview/design-router-pizarra-v1.4.html` comprueba la preferencia de los paneles laterales al cambiar de vista y recargar.

`python3 -B tools/build.py` escribe la pizarra v1.4, su variante autónoma, el mapa de fuentes en `release/` y `map/tree_data.json`. Nunca reescribe la v1.2 ni la v1.3: el build falla si alguna de las dos cambia. Usa `--output-dir .preview` para reconstruir sin modificar esos archivos. La actualización del catálogo de fuentes requiere el checkout completo. Allí, `python3 -B tools/index_skills.py` escribe `vendor/index.json` y `docs/skills.md`.

## Comprobar el CLI del plugin

Desde la raíz del repositorio, consulta la ayuda y ejecuta las regresiones del CLI. La suite usa expedientes temporales.

```sh
python3 -B plugin/skills/design-tree/scripts/runner.py --help
python3 -B plugin/skills/design-tree/scripts/runner.py configure --help
python3 -B -m unittest discover -s plugin/tests -p test_cli.py
```

La verificación del CLI está completa cuando `unittest` descubre pruebas de [test_cli.py](../../plugin/tests/test_cli.py), ejecuta al menos una y todas pasan. Para revisar un cambio, contrasta el código de salida, stdout, stderr y el estado del expediente en disco con el [contrato del comando](../../plugin/skills/design-tree/references/CLI.md).

Para comprobar el plugin completo, ejecuta su suite y el diagnóstico del paquete.

```sh
(cd plugin && python3 -B -m unittest discover -s tests)
python3 -B plugin/skills/design-tree/scripts/doctor.py --format json
```

Consulta el [manual de mantenimiento](../../plugin/skills/design-tree/references/MAINTENANCE.md) para los límites de cambio del plugin.

## Reproducir las versiones fijadas

En este checkout, `python3 -B plugin/skills/design-tree/scripts/runner.py verify-package` comprueba la identidad del árbol canónico. El [diagnóstico del paquete](#comprobar-el-cli-del-plugin) comprueba su manifiesto. El SHA-256 de `release/design-router-pizarra-v1.3.html` está en el [README](../../README.md#reconstruir-y-comprobar). Las pruebas de la pizarra comprueban la compilación de las fuentes editables.

`python3 -B tools/verify_sources.py` se ejecuta en el checkout completo, donde están `vendor/my-skills-manifest.json`, el manifiesto externo y las copias de las fuentes fijadas. Allí comprueba conjuntamente esas copias, el manifiesto del plugin y la huella del HTML v1.3 original.

`python3 -B decision-authoring/build.py --verify-original --check regressions` reproduce el visor histórico y escribe por defecto `decision-authoring/release/index.html`. La evidencia en `evidence/` corresponde al release que registra.
