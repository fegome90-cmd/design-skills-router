# Pizarra de escritorio

Es el único front de Design Skills Router y el destino de la migración de la pizarra v1.3, que está congelada. Las convenciones para trabajar aquí están en [AGENTS.md](AGENTS.md).

Prototipo web de Design Skills Router a partir del documento **react-refactor-borrador** de Kalka. Conserva la estructura de tres regiones, la barra superior de 74 px en escritorio, la marca de ruta y la paleta clara del lienzo. El carril compacto queda visible con o sin panel contextual. La paleta oscura y la composición del dashboard se adaptaron a los contrastes y a la densidad de las referencias.

## Ejecutar

Desde esta carpeta, con Node 22.22.2+, 24.15+ o 26+:

```sh
npm ci
npm run dev -- --port 4184
```

Vite sirve en `127.0.0.1`. Para servir la compilación final, ejecuta `npm run build` y luego `npm run preview -- --port 4184`. Elige un puerto libre si ya hay una instancia.

`npm run build` también genera `dist/standalone/design-router-desktop.html`, una versión autónoma en un solo archivo. Ábrela directamente en el navegador, sin servidor ni red: los scripts, los estilos, las fuentes y el mapa del plugin van dentro del HTML. Para generar solo esa salida, usa `npm run build:standalone`.

## Interacciones

- El carril navega entre Chat, Dashboard, Proyectos, Biblioteca, Mapa del plugin y Configuración. Cada sección ofrece sus propios recursos. El botón inferior del carril o Ctrl/Cmd+B abre y cierra el panel.
- En escritorio, arrastra el borde del panel o enfócalo y usa las flechas. El ancho se limita a 240–320 px. El ancho, el plegado de escritorio y el tema se guardan en este navegador.
- En pantallas estrechas, el panel se abre como diálogo y se cierra con Escape. El carril y el encabezado conservan su posición.
- Chat permite buscar, cambiar de hilo, iniciar conversaciones y añadir mensajes en la pestaña actual. Las respuestas preescritas están identificadas como parte de un ejemplo. Añadir un mensaje nunca genera una respuesta.
- El dashboard cambia métricas y gráfico al elegir 7, 30 o 90 días. Cada fila abre un detalle de proyecto de ejemplo. La biblioteca abre documentos breves de la misma demostración.
- El Mapa del plugin lee el grafo versionado en [release/design-router-mapa-fuentes.json](../../release/design-router-mapa-fuentes.json). El panel contextual busca por nodo, archivo, símbolo o alias y filtra por grupo; la búsqueda se conserva al cambiar de sección. Cada nodo tiene un enlace directo `#router-node-<ID>`, y Atrás y Adelante recorren los nodos visitados. La vista muestra la ubicación en el código, la fuente, el flujo del nodo y la lista de relaciones. El flujo dibuja lo que llega al nodo y lo que sale de él; con más de 12 vecinos por lado agrupa las relaciones por tipo y grupo con su conteo, sin descartar ninguna. Un clic en un vecino lo abre; la lista de relaciones es la alternativa accesible con teclado y lector de pantalla. **Exportar JSON** descarga el grafo completo.

## Componentes y licencias

| Fuente | Versión y licencia | Uso |
| --- | --- | --- |
| [shadcn/ui](https://github.com/shadcn-ui/ui/blob/main/LICENSE.md) | Registro Base Nova, CLI 4.23.0, MIT | Componentes de `src/components/ui` que UI SDK no ofrece (Badge, Card, Chart, Empty, Sidebar y Table). Composición de dos niveles de [sidebar-09](https://ui.shadcn.com/blocks/sidebar) y estructura de tarjetas, gráfico y tabla de [dashboard-01](https://ui.shadcn.com/blocks/dashboard). |
| [UI SDK](https://ui-sdk.dev) | 0.1.0-beta.12, Apache-2.0 | Primitivas de interacción, diálogo para pantallas estrechas, grupos de controles, paneles redimensionables y herramientas para agentes (WebMCP). |
| [Lucide](https://lucide.dev/license) | 1.75.0, ISC | Iconos del carril y de las acciones. |
| [Recharts](https://github.com/recharts/recharts) | 3.11.0, MIT | Gráfico de actividad que se carga al abrir Dashboard. Excepción registrada a la regla de componentes. |
| [Cytoscape.js](https://github.com/cytoscape/cytoscape.js) | 3.35.0, MIT | Lienzo complementario del Mapa del plugin: recibe una proyección, se dibuja a zoom 1 desde 634 px útiles y usa los tokens CSS. Las listas dirigidas son la vista completa y accesible. Excepción registrada a la regla de componentes. |
| [React](https://react.dev/), [Vite](https://vite.dev/) y [Tailwind CSS](https://tailwindcss.com/) | 19.3.1, 8.3.8 y 4.3.5 respectivamente, MIT | Estado y renderizado, compilación y estilos. |

Las fuentes Geist Sans y Geist Mono son copias de las publicadas por Vercel en `geist` 1.9.2, bajo SIL OFL 1.1; su procedencia está en [src/assets/fonts/PROCEDENCIA.md](src/assets/fonts/PROCEDENCIA.md). Los avisos de Geist y shadcn/ui se incluyen en [public/licenses](public/licenses). La compilación añade en `dist/licenses/dependencies.txt` las licencias y avisos de las dependencias de producción del lockfile, incluida class-variance-authority (Apache-2.0).

## Verificar

```sh
npm run lint
npm run typecheck
npm run build
npx playwright install chromium
npm test
```

Oxlint revisa JavaScript, TypeScript y TSX del prototipo. Las reglas de Hooks y sus dependencias se comprueban como errores. `npm run typecheck` comprueba los tipos.

`npm test` compila primero la versión autónoma. Las pruebas del Mapa se ejecutan dos veces: contra el servidor y contra el HTML autónomo abierto desde `file://` con la red desactivada, donde fallan si la página pide cualquier recurso externo. Las pruebas abren el puerto 4183. `DESKTOP_TEST_PORT` permite usar otro puerto. `DESKTOP_SCREENSHOTS` indica una carpeta donde se guardan capturas de Chat y Dashboard en ambos temas.

## Verificaciones antes de un commit

Instala Python 3, Gitleaks y `pre-commit` 4.4 o posterior. Desde la raíz del clon, instala las dependencias del prototipo y el navegador de Playwright CLI, y activa el hook del repositorio:

```sh
npm ci --prefix board/desktop-demo
npm --prefix board/desktop-demo exec -- playwright-cli install-browser chrome-for-testing
git config --local core.hooksPath .githooks
```

El hook ejecuta el escáner de seguridad en cada commit. Si el commit cambia `board/desktop-demo` y quedan archivos del prototipo en el índice, invoca `pre-commit` y exige que su configuración siga en el índice. Cuando hay archivos aplicables, se ejecutan Oxlint, Impeccable sobre el código de `src` y una prueba de humo con Playwright CLI. Los errores del detector bloquean el commit y los avisos se muestran. La prueba abre el dashboard en un servidor local temporal y comprueba el cambio al período semanal. La suite completa sigue disponible con `npm test`.

Para ejecutar los tres controles manualmente desde la raíz:

```sh
pre-commit run --config board/desktop-demo/.pre-commit-config.yaml --all-files
```
