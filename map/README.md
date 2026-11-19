# Mapa del código y del árbol de decisiones

Abre `release/design-router-pizarra-v1.4.html` y pulsa **Mapa del plugin**. La ficha inicial es Q00. Sigue «Presentar paquete de nodo» o el enlace a Router.packet en «Consultado desde código Python» para ver dónde el runner presenta la decisión. Desde Q00 también puedes seguir la alternativa F00 (proyecto nuevo) o E01 (proyecto existente).

En **Buscar nodos** escribe un ID, un nombre de archivo o un símbolo. Con el filtro **Archivos del plugin**, busca `runner.py` para entrar por el archivo y elegir uno de sus métodos. La dirección de una ficha termina en `#router-node-<ID>`. La búsqueda por el ID de una ocurrencia, por ejemplo `E03__F00`, lleva a su definición compartida.

## Fuentes y alcance

Plugin `design-skills-router` 0.3.1, release `pluginrel_6af336537e808191831d72799b60bf4b`. La pizarra v1.4 (junto con la v1.3 congelada) representa el árbol canónico 0.4 y el código del paquete instalado. El propio mapa funcional de la pizarra conserva el simulador de selección mínima v1.2.

Cada uno de los 24 archivos representados tiene un ID estable derivado de su ruta, su SHA-256 y vínculos a las declaraciones o símbolos que contiene. Las fichas de Python indican clase o función y línea del release. Las declaraciones JSON usan JSON Pointer. En el visor HTML y los documentos se indica la función o sección que corresponde. «Ver fuente» en una ficha de símbolo muestra el fragmento pertinente; la copia completa del release está en `plugin/`.

Las 239 declaraciones reúnen 52 decisiones, 37 grupos de ramas obligatorias, 123 resultados y 27 instancias de plantilla. El expansor de Python genera 3.660 ocurrencias. El grafo distingue alternativas, prerrequisitos, lecturas, ubicación física y conexiones de implementación. Las etiquetas también identifican pasos que dependen de una nueva invocación del host. Una relación documental no acredita ejecución ni aprobación.

## Verificación

Desde la raíz del paquete, estos comandos reconstruyen el grafo y la pizarra.

```sh
python3 -B tools/build.py
python3 -B -m unittest discover -s plugin/tests -q
node tests/router-v12.semantic.cjs release/design-router-pizarra-v1.4.html
```

La fuente de los datos declarativos está en el plugin. Los archivos runtime.json y context.json describen las relaciones de implementación revisadas para este release. El ensamblador comprueba los hashes de los archivos del manifiesto, resuelve símbolos Python y punteros JSON y valida ambos extremos de cada relación. Para ver o procesar el grafo completo usa `release/design-router-mapa-fuentes.json`.

Las pruebas de navegador requieren Node, Playwright y Chromium. Si usas un binario del sistema, define PLAYWRIGHT_CHROMIUM_EXECUTABLE con su ruta.

```sh
node tests/map-test.cjs release/design-router-pizarra-v1.4.html
node tests/router-v12.playwright.cjs release/design-router-pizarra-v1.4.html
```

En `evidence/`, chromium.log conserva los 7 casos del mapa y las 11 regresiones de la pizarra, unit.log registra las 171 pruebas del plugin y cli-trace.json documenta las 12 invocaciones con un expediente temporal. El CLI rechazó correctamente dos propuestas prematuras, conservó el estado y pudo exportarlo y recuperarlo. La activación conversacional de las skills desde ChatGPT queda fuera de esta evidencia.
