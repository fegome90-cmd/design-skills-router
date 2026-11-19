# Autoría del árbol v0.4

El árbol canónico del paquete está en `../plugin/skills/design-tree/references/tree-v0.4/`. Ahí están `tree.json`, `rules.json`, `skill-inventory.json`, `criterion-map.json`, el visor distribuido `index.html` y su documentación original. Para cambiar el modelo, edita esos datos en una copia de trabajo del plugin y reconstruye el visor desde las fuentes.

`original/` conserva los 24 archivos complementarios de [design-decision-tree-v0.4.zip](https://chatgpt.com/library?file_id=libfile_fde3_f-52e62977a6e88191987c64e762896b9a_11107b86ea008191bab113dfcc32deba&account_id=personal), incluidos el constructor `build.py`, el expansor `model.py`, el visor `viewer.js`, su hoja `styles.css`, las pruebas y la evidencia histórica. Los siete archivos compartidos con el plugin coinciden byte por byte y se toman de la copia canónica. El ZIP original tiene SHA-256 `f1b03407ad1ec38fbe90d8570f53089c75500f5a8883ccb385b8a7d135160142`.

## Reconstruir y verificar

Desde esta carpeta:

```sh
python3 build.py --verify-original --check regressions --output release/index.html
node --check original/viewer.js
```

El constructor prepara las fuentes y los datos en un directorio temporal. `--verify-original` valida el manifiesto histórico y exige que el visor generado coincida con el visor distribuido. Para trabajar con otro checkout, usa `--baseline /ruta/al/tree-v0.4`. Si editaste fuentes o datos deliberadamente, omite `--verify-original` para construir la variante.

La reconstrucción verificada produjo las huellas del release original:

| Archivo | SHA-256 |
| --- | --- |
| `tree.json` | `0cf76c1833d7aec023a3f939924af11e3caa7ff837ada1d208f6453f1e22a793` |
| `index.html` | `591257cf413b7380e2ad7f2e72377aa69882c72651e785d7f9e816ef2284a1b8` |

Pasaron las 12 comprobaciones de regresión y la comprobación de sintaxis de `viewer.js`. Las pruebas históricas del modelo y navegador se incluyen en `original/tests/`. Para volver a ejecutarlas usa `--check model` con pytest y Beautiful Soup, o `--check browser` con Playwright y Chromium. Los resultados de navegador guardados en `original/evidence/` corresponden al ZIP histórico.
