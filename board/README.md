# Fuentes de la pizarra v1.4

Desde la raíz del repositorio, ejecuta `python3 -B tools/build.py --output-dir .preview` para compilar una vista previa sin tocar `release/`, o `python3 -B tools/build.py` para regenerar la pizarra `v1.4` (`release/design-router-pizarra-v1.4.html`, `release/design-router-pizarra-v1.4-offline.html`), el mapa de fuentes y `map/tree_data.json`. La compilación usa la biblioteca estándar de Python y no necesita red.

## Qué editar

| Vista | Archivos |
| --- | --- |
| Estructura, navegación y etiquetas comunes | `src/board.template.html` |
| Capas y exportación del árbol visual | `src/capas/` |
| Relaciones entre skills | `src/relaciones/` |
| Cambios propuestos y exportación draw.io | `src/propuestas/` |
| Ficha de revisión individual | `src/revision-individual/` |
| Comparar skills | `src/comparacion/` |
| Revisiones pendientes | `src/revisiones-pendientes/` |
| Mapa funcional | `src/mapa-funcional/` |
| Simulador de selección mínima | `src/simulador/` |
| Telemetría opt-in del tablero | `src/telemetria/` |

Cada vista tiene sus propios estilos, JavaScript y datos. La hoja `src/capas/base.css` también contiene estilos compartidos. El ensamblador (`board/build.py`) incrusta las fuentes que identifica cada marcador `@@BOARD:ruta@@`, añade el simulador con la huella SHA-256 de su política y agrega el cliente opt-in de `src/telemetria/`.

## Ensamblado y versiones congeladas

`tools/build.py` importa `board/build.py` para generar la base HTML en un directorio temporal, acopla el mapa del plugin y la variante autónoma, y verifica que las pizarras históricas congeladas (`release/design-router-pizarra-v1.2.html` y `release/design-router-pizarra-v1.3.html`) conserven intactas sus huellas SHA-256.

Para comprobar únicamente el ensamblado base sin escribir dentro del repositorio:

```sh
python3 -B board/build.py --output /tmp/design-router-pizarra-base.html
```

Para la suite completa de verificación semántica, navegador y telemetría, consulta [operación y verificación](../docs/agent/RUNTIME.md#comprobar-un-cambio).
