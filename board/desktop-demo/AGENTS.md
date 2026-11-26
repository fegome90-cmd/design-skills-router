# Pizarra de UI SDK

Esta carpeta es el único front de Design Skills Router. La pizarra v1.3 en HTML plano (`board/src/`) está congelada y se migra aquí vista por vista. Para migrar una vista, léela en `board/src/` como referencia y constrúyela en esta app. No crees otra app de interfaz.

## Antes de usar UI SDK

Sigue la skill `ui-sdk` si está instalada y lee `node_modules/@ui-sdk/react/docs/llms.txt`. Para construir un componente nuevo, busca también por encabezado en `node_modules/@ui-sdk/react/docs/core.md` y lee `rendering.md`, junto a ese archivo. La documentación instalada corresponde a la versión fijada en `package.json`.

## Componentes

Una sola forma de construir la interfaz:

1. **Si UI SDK tiene la pieza, se usa UI SDK**, importada directo desde `@ui-sdk/react/<componente>`. No escribas envoltorios para piezas de UI SDK. Las variantes se marcan en la propia pieza con `data-variant` (`solid`, `destructive` o `ghost`; sin atributo es el contorno por defecto) y `data-size` (`sm`, `icon` o `icon-sm`), y su estilo vive en `src/styles.css`.
2. **Si UI SDK no la tiene, se usa un componente de shadcn/ui** (ecosistema de Vercel) en `src/components/ui/`: hoy `badge`, `card`, `chart`, `empty`, `sidebar` y `table`. Sus partes interactivas usan UI SDK por dentro. `class-variance-authority`, `clsx` y `tailwind-merge` (`cn`) solo se usan en esa carpeta.
3. **Íconos:** `lucide-react`. Vercel no publica un paquete oficial de íconos.
4. **Excepciones registradas:**
   - `recharts`, solo para el gráfico de actividad del Dashboard, a través del Chart de shadcn/ui.
   - `cytoscape`, solo para el lienzo del flujo del nodo en `src/node-flow.tsx`. Recibe la proyección de `flowProjection` (`src/graph.ts`), nunca el JSON completo. Se dibuja a zoom 1 cuando caben tres columnas (desde 634 px útiles; `src/node-flow-layout.ts`). Las listas dirigidas de la tarjeta Relaciones son la vista completa y accesible; la navegación y el foco siguen en React. Sus colores salen de los tokens CSS.

Cualquier otra librería de componentes, o una nueva excepción, necesita la aprobación del responsable del proyecto. Las secciones del carril se declaran en `src/app.tsx` (`appSections`) y `src/preferences.ts` (`destinations`). Cada sección aporta su contenido al panel contextual y su vista. El hash de la URL es la fuente de verdad de la sección activa.

## Estilos

- Usa los tokens definidos en `:root` de `src/styles.css` (`--background`, `--foreground`, `--muted`, `--border`, `--radius`, etc.). No fijes colores: el tema oscuro (clase `.dark`) y la densidad compacta (`data-density="compact"`) redefinen esos tokens.
- Estiliza las piezas de UI SDK por su `data-slot` y sus atributos de estado (`data-open`, `data-selected`, `data-pressed`…), como indica `node_modules/@ui-sdk/react/docs/styling-and-animation.md`.
- La tipografía es **Geist Sans** para textos y títulos y **Geist Mono** para código. Los archivos están en `src/assets/fonts/` con su [procedencia](src/assets/fonts/PROCEDENCIA.md). No las cargues desde la red.

## Agente UI y WebMCP

- `src/agent.ts` crea el agente y registra las herramientas WebMCP con una sola función `allow`. Marca con `data-agent-confirm` cualquier control destructivo: el paso espera a la persona tanto en el cajón del agente como por WebMCP.
- Marca con `data-agent-hidden` los paneles que el agente no debe inspeccionar, como el propio cajón del agente.
- Los flujos de ejemplo están en `src/components/agent-drawer.tsx`. El agente solo opera componentes de UI SDK; los enlaces y el marcado propio no aparecen en su snapshot.

## HTML autónomo

`npm run build` genera también `dist/standalone/design-router-desktop.html`, que se abre desde `file://` sin red. Todo lo que agregues tiene que poder ir dentro de ese archivo:

- nada de CDN, `fetch` a la red ni recursos cargados desde otra URL;
- los datos se importan en el código, como el grafo de `release/design-router-mapa-fuentes.json`;
- un worker o un WASM nuevo tiene que poder inlinearse; compruébalo con `npm test`.

## Verificar

Desde esta carpeta, antes de entregar un cambio:

```sh
npm run lint
npm run typecheck
npm run test:unit
npm test
npm run check:design
npm run check:browser
```

`npm test` compila el HTML autónomo y ejecuta Playwright contra el servidor de desarrollo y contra ese archivo con la red desactivada. Además de las pruebas, revisa capturas en escritorio, móvil y tema oscuro: las pruebas comprueban el comportamiento, no la apariencia.
