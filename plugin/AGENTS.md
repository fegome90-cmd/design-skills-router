# Design Skills Router — mantenimiento

Identidad: `plugins_6af0bd3b7e3c81918ab86be10f68159e`, privado. La versión vigente la declara `plugin.json`.

**Mantenimiento del plugin:** leer [MAINTENANCE](skills/design-tree/references/MAINTENANCE.md), ejecutar el doctor y reparar únicamente lo autorizado. No iniciar Q00 ni pedir un brief de producto.

Para cambiar el CLI, consulta el [contrato de comandos y expedientes](skills/design-tree/references/CLI.md) y sus [pruebas de regresión](tests/test_cli.py).

**Proyecto de diseño:** leer [design-tree](skills/design-tree/SKILL.md). Elegir nivel y límites desde la instrucción real; no asumir automático. No one-shot.

```sh
python3 -B skills/design-tree/scripts/doctor.py --format json
python3 -B -m unittest discover -s tests -v
python3 -B scripts/release.py prepare --version VERSION_SUPERIOR --output /ruta/externa/update.zip
```

Árbol, reglas, inventario, mapa de criterios y visor v0.4 tienen dueño inmutable. No editar `baseline-lock.json` para ocultar deriva. Relaciones adicionales: `skills/design-tree/references/contracts.json`. Estado: fuera del plugin. No importar la database externa.

No cambiar iconos, prompts, audiencia o ID. Publicar es una acción separada con `expected_release_id`, seguida de lectura remota. Los recibos son declaraciones del operador, no autenticación. Las pruebas con fixtures no demuestran obediencia de un LLM.
