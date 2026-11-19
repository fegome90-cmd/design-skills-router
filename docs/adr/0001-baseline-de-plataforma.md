# Baseline de plataforma

## Status

accepted

## Contexto

La protección clásica de `main` ya exigía el check `Secrets and private paths` y aplicaba las restricciones a los administradores, pero no requería pull requests ni resolución de conversaciones: un push directo podía entrar sin revisión y los threads de revisión no bloqueaban el merge. Esas decisiones vivían en la configuración de GitHub, fuera del repositorio.

## Decisión

Se adopta un baseline de plataforma compuesto por:

- un ruleset `pr-gate` sobre la rama por defecto, con la regla `pull_request`: pull request obligatorio, 0 aprobaciones, resolución de threads obligatoria y los tres métodos de merge habilitados;
- `delete_branch_on_merge` habilitado;
- licencia MIT para el contenido propio, con las licencias de terceros preservadas por componente;
- `SECURITY.md` con reporte privado de vulnerabilidades y alcance por componente;
- plantilla de pull request y este glosario.

La protección clásica no se modifica: sigue exigiendo el check con `strict` y mantiene `enforce_admins`.

## Considered Options

- **Mutar la protección clásica por GraphQL**: se descartó porque la API de rama no expone un campo separado para "requerir pull request" —el bloque de revisiones con 0 aprobaciones lo implica— y un PUT completo del template de la skill borraría el check requerido y `enforce_admins`. Se prefirió un ruleset para aislar la regla sin mutar la protección clásica.
- **Ruleset con `deletion` y `non_fast_forward`**: se descartó porque la protección clásica ya cubre esos bloqueos y duplicarlos agrega superficie.
- **CODEOWNERS con revisión obligatoria de code owners**: se descartó porque, con un solo mantenedor y `enforce_admins`, la rama quedaría inmergeable por pull request.
- **`release.yml`**: se descartó porque el historial tiene un solo pull request mergeado y el changelog se mantiene a mano.
- **Vendorizar la skill de Netresearch**: se descartó porque es una skill de operaciones de plataforma, no de diseño, y no aporta nodos al árbol del router.

## Consequences

- El push directo a `main` deja de ser posible: todo cambio entra por pull request.
- Los threads de revisión, incluidos los de bots, bloquean el merge hasta resolverse.
- La licencia MIT no relicencia `vendor/`; cada componente conserva su licencia.
- Los metadatos de licencia del `package.json` de la raíz, de `board/desktop-demo/package.json`, de `pyproject.toml` y de `plugin/.codex-plugin/plugin.json` quedan pendientes. El `package.json` de la raíz y el del plugin llegan con el pull request #2; el del demo existe en `main` y todavía no declara licencia.
- La API agregó `require_extra_approval_for_unattributed_changes: true` al ruleset; con 0 aprobaciones no tiene efecto.
- Reversión: leer el ruleset con `GET`, cambiar `enforcement` a `disabled` y enviar el objeto completo con `PUT` (el endpoint reemplaza el recurso, así que un payload parcial puede vaciarlo); `PATCH` del repositorio con `{"delete_branch_on_merge":false}`; y restauración del comentario y del thread por separado. La protección clásica no requiere reversión.
