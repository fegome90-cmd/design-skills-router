# Pizarra de escritorio

Prototipo web de Design Skills Router a partir del documento **react-refactor-borrador** de Kalka. Conserva la estructura de tres regiones, la barra superior de 74 px en escritorio, la marca de ruta y la paleta clara del lienzo. El carril compacto queda visible con o sin panel contextual. La paleta oscura y la composición del dashboard se adaptaron a los contrastes y a la densidad de las referencias.

## Ejecutar

Desde esta carpeta, con Node 20.19+ de la rama 20 o Node 22.12+:

```sh
npm ci
npm run dev -- --port 4184
```

Vite sirve en `127.0.0.1`. Para servir la compilación final, ejecuta `npm run build` y luego `npm run preview -- --port 4184`. Elige un puerto libre si ya hay una instancia.

## Interacciones

- El carril navega entre Chat, Dashboard, Proyectos, Biblioteca y Configuración. Cada sección ofrece sus propios recursos. El botón inferior del carril o Ctrl/Cmd+B abre y cierra el panel.
- En escritorio, arrastra el borde del panel o enfócalo y usa las flechas. El ancho se limita a 240–320 px. El ancho, el plegado de escritorio y el tema se guardan en este navegador.
- En pantallas estrechas, el panel se abre como diálogo y se cierra con Escape. El carril y el encabezado conservan su posición.
- Chat permite buscar, cambiar de hilo, iniciar conversaciones y añadir mensajes en la pestaña actual. Las respuestas preescritas están identificadas como parte de un ejemplo. Añadir un mensaje nunca genera una respuesta.
- El dashboard cambia métricas y gráfico al elegir 7, 30 o 90 días. Cada fila abre un detalle de proyecto de ejemplo. La biblioteca abre documentos breves de la misma demostración.

## Componentes y licencias

| Fuente | Versión y licencia | Uso |
| --- | --- | --- |
| [shadcn/ui](https://github.com/shadcn-ui/ui/blob/main/LICENSE.md) | Registro Base Nova, CLI 4.23.0, MIT | Componentes en `src/components/ui`. Composición de dos niveles de [sidebar-09](https://ui.shadcn.com/blocks/sidebar) y estructura de tarjetas, gráfico y tabla de [dashboard-01](https://ui.shadcn.com/blocks/dashboard). |
| [Base UI](https://base-ui.com/) | 1.9.0, MIT | Primitivas de interacción, diálogo para pantallas estrechas y grupos de controles. |
| [Lucide](https://lucide.dev/license) | 1.75.0, ISC | Iconos del carril y de las acciones. |
| [react-resizable-panels](https://github.com/bvaughn/react-resizable-panels) | 4.24.0, MIT | Arrastre y redimensionamiento por teclado a través de Resizable de shadcn/ui. |
| [Recharts](https://github.com/recharts/recharts) | 3.11.0, MIT | Gráfico de actividad que se carga al abrir Dashboard. |
| [React](https://react.dev/), [Vite](https://vite.dev/) y [Tailwind CSS](https://tailwindcss.com/) | 19.3.1, 8.3.8 y 4.3.5 respectivamente, MIT | Estado y renderizado, compilación y estilos. |

Las fuentes IBM Plex Sans y Fraunces vienen del paquete local de la pizarra bajo SIL OFL 1.1. Los avisos de fuentes y shadcn/ui se incluyen en [public/licenses](public/licenses). La compilación añade en `dist/licenses/dependencies.txt` las licencias y avisos de las dependencias de producción del lockfile, incluida class-variance-authority (Apache-2.0).

## Verificar

```sh
npm run lint
npm run typecheck
npm run build
npx playwright install chromium
npm test
```

Oxlint revisa JavaScript, TypeScript y TSX del prototipo. Las reglas de Hooks y sus dependencias se comprueban como errores. `npm run typecheck` comprueba los tipos.

Las pruebas abren el puerto 4183. `DESKTOP_TEST_PORT` permite usar otro puerto. `DESKTOP_SCREENSHOTS` indica una carpeta donde se guardan capturas de Chat y Dashboard en ambos temas.

## Verificaciones antes de un commit

Desde la raíz del repositorio, instala las dependencias del prototipo, el navegador de Playwright CLI y el hook con `pre-commit` 4.4 o posterior:

```sh
npm ci --prefix board/desktop-demo
npm --prefix board/desktop-demo exec -- playwright-cli install-browser chrome-for-testing
pre-commit install --config board/desktop-demo/.pre-commit-config.yaml --allow-missing-config
```

Al hacer un commit con archivos de `board/desktop-demo` en el índice, el hook ejecuta Oxlint, Impeccable sobre el código de `src` y una prueba de humo con Playwright CLI. Los errores del detector bloquean el commit y los avisos se muestran. La prueba abre el dashboard en un servidor local temporal y comprueba el cambio al período semanal. La suite completa sigue disponible con `npm test`.

Para ejecutar los tres controles manualmente desde la raíz:

```sh
pre-commit run --config board/desktop-demo/.pre-commit-config.yaml --all-files
```
