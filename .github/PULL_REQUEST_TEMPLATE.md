## Resumen

<!-- Qué cambia, por qué y qué queda fuera del alcance. -->

## Verificación

Marcá lo que corriste y anotá el resultado, no solo el tilde. Si un comando no existe en la base de este PR, indicá qué verificación hiciste en su lugar.

- [ ] `python3 -B tools/build.py` y `git status --short` limpio
- [ ] `npm test`
- [ ] `(cd plugin && python3 -B -m unittest discover -s tests)`
- [ ] `python3 -B -m unittest discover -s telemetry/tests` (si toca `telemetry/`)
- [ ] `./scripts/check-secrets.sh staged`
- [ ] Cambio visual: `npm run test:browser`

## Procedencia

- [ ] Sin archivos de `vendor/` salvo justificación explícita
- [ ] Sin rutas absolutas de la máquina local
- [ ] Si cambia `vendor/index.json`, `docs/skills.md` o un manifiesto: commit fijado, SHA-256 y licencia citados

## Límites

<!-- Qué no se pudo verificar y por qué. -->
