# Pizarra autónoma (v1.4)

Abre `../release/design-router-pizarra-v1.4-offline.html` desde el disco. La v1.3 autónoma original queda en `release/` con su huella registrada en `evidence/`. Contiene el tema claro de Shoelace 2.20.1, los dos componentes que usa la pizarra y las fuentes Fraunces, IBM Plex Sans e IBM Plex Mono. Incluye los avisos de licencia en el documento y en `local-ui/licenses/`.

La vista local usa el SVG nativo de la pizarra. El botón **Motor draw.io** devuelve a esa vista en la variante autónoma. La descarga **Descargar diagrama** genera el archivo draw.io sin conexión. El enlace **diagrams.net** abre el editor en otra pestaña con conexión. Los enlaces a fuentes externas se conservan.

## Regenerar

```sh
python3 build_offline.py /ruta/design-router-pizarra-v1.4.html design-router-pizarra-v1.4-offline.html
```

El script usa solo la biblioteca estándar de Python, prueba los hashes de los recursos y requiere una ruta de salida distinta al HTML dorado. `ui-dependencies.json` registra las URLs de distribución, las versiones, los tamaños y los hashes.

El bundle reducido de Shoelace proviene de la distribución oficial de npm, con el SRI registrado en el manifiesto. Para rehacerlo, crea junto al directorio `cdn/components` un archivo `board-entry.js` con:

```js
import "./components/tooltip/tooltip.js";
import "./components/tag/tag.js";
```

Compílalo con esbuild 0.25.12:

```sh
esbuild cdn/board-entry.js --bundle --format=esm --target=es2022 --minify \
  --legal-comments=inline --outfile=local-ui/shoelace-2.20.1-board.js
```

Con Node, Playwright y Chromium disponibles, `node test-offline.cjs ../release/design-router-pizarra-v1.4-offline.html` comprueba componentes, fuentes, mapa, exportación y el uso sin solicitudes a internet.
