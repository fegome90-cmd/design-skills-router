# Plan · Controles permanentes de calidad en CI

Estado: aprobado con ajustes el 24-11-2026. Pendiente de ejecución.

Origen: la revisión del PR #7 (R01) encontró defectos que ningún control automático detectaba. Había E/S de texto sin codificación explícita, aserciones que pasaban con resultados vacíos, rechazos sin verificar el estado y documentación que no coincidía con el código. Este plan convierte esos hallazgos en controles permanentes, para no depender solo de revisores que podrían volver a omitirlos.

## Decisiones

| Tema | Decisión |
|---|---|
| Versión del plugin | Se mantiene 0.3.1 durante el desarrollo y se incrementa en el próximo release. |
| Guardia estática de codificación | Script AST propio, solo con la biblioteca estándar. No se incorporan Ruff ni Semgrep: la regla `PLW1514` de Ruff detectó 9 de 157 llamadas y sigue en preview. |
| Guardia dinámica de codificación | `EncodingWarning` como error en todas las suites y en los subprocesos que hereden el entorno. |
| Enlaces y anclas | lychee en modo offline con fragmentos. Se probó y detecta archivos y anclas rotos, también con tildes, sin falsos positivos. |
| Documentos alcanzables e IDs del roadmap | Script propio, porque no hay herramienta estándar para esto. |
| Prefijos del roadmap | `R` y `F`, con sufijo de letra opcional (`R02A`, `R02B`, `R02C`): `\b[RF]\d{2}[A-Z]?\b`. |
| Revisores semánticos | Sección `## Code Review Rules` en el `AGENTS.md` raíz, que leen Codex y CodeRabbit, y un `.coderabbit.yaml` mínimo. |
| Mutation testing | Diferido. La candidata es Cosmic-Ray, aplicado módulo por módulo. |

## Hechos de partida

Inventario estático, sin revisar todavía caso por caso:
- 157 llamadas de E/S de texto sin `encoding`, en 144 líneas distintas de 31 archivos.
- Por tipo de llamada: 76 `read_text`, 61 `write_text`, 15 `subprocess(text=True)`, 4 `tempfile` y 1 `.open`.
- Por carpeta, en llamadas: `plugin` 91, `telemetry` 37, `decision-authoring` 14, `map` 7, `history` 6, `packages` 1 y `tests` 1.
- Las 14 de `decision-authoring/original/` (con `SHA256SUMS.txt`) y las 6 de `history/` son material congelado. Se excluyen de la corrección y de la guardia.

Otros hechos verificados:
- Con `-W error::EncodingWarning`, hoy fallan 67 pruebas del plugin.
- `plugin/PACKAGE-HASHES.json` lo validan `diagnostics.py`, `tools/verify_sources.py` y `map/assemble_map.py`. `release.py prepare` no lo regenera en el sitio.
- El workflow G5 solo ejecuta `test_node_context.py` y `packages/cli/tests`.
- Para reproducir un locale que no es UTF-8 hace falta `LC_ALL=C PYTHONUTF8=0 PYTHONCOERCECLOCALE=0`.
- Estado de la documentación en `main`: 0 enlaces rotos y 1 documento sin enlace entrante, `docs/adr/0001-baseline-de-plataforma.md`.
- Los IDs `R` y `F` se definen en `board/src/*/datos.json` y en documentos de unidades del roadmap.

## Orden de integración

1. **Cerrar R01 (PR #7).** Consolida la base revisada. Está en `71a513a` con CI en verde; el merge lo decide el operador.
2. **PR A · Calidad de Python.** Guardia AST, codificación explícita, hashes y CI.
3. **PR B · Calidad documental.** Enlaces, referencias, documentos alcanzables y reglas de revisión.
4. **Actualizar R02A.** Integrar sus commits sobre la nueva base y aplicar los controles.
5. **Retomar R02B y R02C.**

Cada PR va en su propia rama, partiendo de `main` después de fusionar el anterior. Cuando los workflows hayan demostrado ser estables, se propondrá, con una autorización aparte, añadirlos como checks obligatorios de `main`. Crear un workflow no basta para que sus fallos bloqueen el merge.

## PR A · Calidad de Python

### Preflight
- Inventariar los archivos con `git ls-files '*.py'`, que incluye `tests/`, `map/` y `board/`.
- Declarar las exclusiones con su motivo: `decision-authoring/original/` y `history/` por ser material congelado, y cualquier código de terceros que se encuentre.
- Revisar caso por caso el recuento y conciliar llamadas, líneas y archivos.
- Para cada uno de los 15 `subprocess(text=True)`, comprobar qué codificación produce realmente el proceso hijo (git, node, Python u otro) antes de imponer UTF-8. Si no es UTF-8, se usa la codificación correcta o se leen bytes.

### Commit 1 · Guardia
`scripts/check-encoding.py` vive en la raíz, fuera de `plugin/`, para no alterar el manifiesto. Su prueba va en `tests/`.

Detecta, cuando falta `encoding` (por nombre o por posición) o cuando vale `encoding=None`:
- `open`, `io.open`, `Path.open`, `read_text`, `write_text` y `fileinput` en modo texto;
- `tempfile.TemporaryFile`, `NamedTemporaryFile` y `SpooledTemporaryFile` en modo texto, sin falsos positivos con `mkstemp`, `mkdtemp`, `TemporaryDirectory` ni `gettempdir`;
- `subprocess.run`, `Popen`, `check_output` y `call` con `text=True` o `universal_newlines=True`.

Solo excluye los modos binarios literales; un modo no literal se trata como texto. Cubre los archivos del inventario, salvo las exclusiones declaradas. Su prueba incluye casos positivos, negativos, `encoding=None`, los `tempfile` que no abren archivos y un modo no literal.

CI queda en rojo hasta el commit 2, y así se indica en el PR.

### Commit 2 · Corrección
- Añadir `encoding='utf-8'`, o la codificación verificada en el preflight, editando a mano o con AST. Sin sed.
- No tocar modos binarios, `newline` ni `ensure_ascii`.
- No modificar `tree-v0.4/*` ni `baseline-lock.json`. Si aparece otro archivo inmutable, se detiene el trabajo y se consulta.

### Commit 3 · Hashes y CI
- Regenerar `plugin/PACKAGE-HASHES.json` en el sitio con `release.encoded()` y `read_bytes()`, sin subir la versión.
- Reconstruir el wheel y el sdist. `_portable/*` debe ser idéntico byte a byte a su fuente.
- Workflow `python-quality.yml`, con `contents: read`, acciones fijadas por SHA y `persist-credentials: false`. Pasos:
  - la guardia AST;
  - `plugin/tests`, `packages/cli/tests` (wheel con `[mcp]`), `telemetry/tests` y `tests/`, con `PYTHONWARNDEFAULTENCODING=1` y `PYTHONWARNINGS=error::EncodingWarning`, para que el control llegue también a los subprocesos Python que heredan el entorno;
  - la suite CLI con `LC_ALL=C PYTHONUTF8=0 PYTHONCOERCECLOCALE=0`. Con ese locale, la codificación del sistema de archivos es ASCII y POSIX no puede pasar argumentos no ASCII a un subproceso. Por eso `scripts/run-cli-tests-locale-c.py` excluye, por ID y con su motivo, las tres pruebas que los usan a propósito; esas pruebas siguen ejecutándose en los pasos UTF-8. El fallo es idéntico en `main` (`926a225`). Si una exclusión deja de existir, el script falla.
- Los fallos ajenos a la codificación que aparezcan se informan, pero no se corrigen en este PR.
- Enlazar este plan desde `docs/agent/CONTEXT.md`, una vez fusionado el #7, para evitar conflictos en ese archivo.

### Verificación
- Todas las suites: normales, con la advertencia como error y con locale C.
- `doctor.py`, `runner.py verify-package` y `tools/verify_sources.py`.
- Igualdad de `_portable` con sus fuentes y `git diff --check`.

Queda fuera de este PR `release/design-router-mapa-fuentes.json`, que ya está desactualizado y no tiene prueba.

## PR B · Calidad documental

### Enlaces y anclas
- Workflow `docs.yml` con `lycheeverse/lychee-action` fijada por SHA, en modo offline con fragmentos, y con el mismo endurecimiento que el resto.
- Excluye `vendor/`, `release/` y `node_modules/`.

### Documentos alcanzables e IDs
`scripts/check-docs.py`, solo con la biblioteca estándar. Su prueba va en `tests/`.

- **Alcanzabilidad.** Cada `.md` de `docs/` debe ser alcanzable siguiendo enlaces desde puntos de entrada reconocidos: `README.md`, `AGENTS.md` y `docs/agent/*.md`. Un grupo de documentos huérfanos que se enlazan entre sí no pasa. Las excepciones se listan con su motivo.
- **IDs.** Cada ID que encaje con el patrón y aparezca en `docs/**` debe estar definido en una fuente reconocida:
  - un `"id"` de `board/src/*/datos.json`;
  - el nombre de archivo de una unidad del roadmap (`docs/specs/**/units/<ID>-*.md`);
  - una tabla de definiciones declarada de forma explícita en el script.

  Una mención en la primera columna de cualquier otra tabla no cuenta como definición.
- Ignora los bloques de código y lee los archivos con `utf-8-sig`.
- Pruebas: documento huérfano, ciclo de huérfanos, ID no definido, ID definido en cada fuente reconocida, ID que solo aparece en una tabla no reconocida y bloque de código ignorado.
- Enlazar `docs/adr/0001-baseline-de-plataforma.md` desde una guía de `docs/agent/`.

Notas de implementación (25-11-2026):
- Sobre `f4e4479`, la documentación citaba 8 IDs sin definición reconocida: R02, R02A, R02B, R02C, R03, R04, R09 y R10, con 20 menciones en total. Son unidades planificadas sin contrato. La tabla declarada es la de [`docs/specs/mcp-roadmap/README.md`](../mcp-roadmap/README.md). Cada fila cita literalmente el documento que menciona la unidad y no le atribuye alcance. Los `id` `R01` y `F00` de `board/src/*/datos.json` son nodos de la pizarra, no unidades; el plan los admite igualmente como fuente.
- `lycheeverse/lychee-action` v2.9.0 descarga el binario de lychee sin verificar su checksum. La acción queda fijada por SHA y la versión de lychee por número (`v0.24.2`); el binario descargado no se verifica.

### Reglas de revisión
- En el `AGENTS.md` raíz, una sección `## Code Review Rules` con subtítulos `###`. Cada regla describe el daño, porque Codex en GitHub solo marca P0 y P1:
  1. una comparación de equivalencia que también pasaría si ambos resultados estuvieran vacíos;
  2. un rechazo que no comprueba el estado antes y después;
  3. una afirmación de un spec que el código citado no cumple;
  4. E/S de texto sin `encoding`, como recordatorio de un control que ya hace CI.
- `.coderabbit.yaml` con `path_instructions` para `**/tests/**` y `docs/**`, sin repetir `AGENTS.md`, y un `custom_check` en `warning` para la regla "spec frente a código". Solo contiene instrucciones de revisión.
- Validar `.coderabbit.yaml` contra el esquema oficial de CodeRabbit. Confirmar que el plan contratado admite `custom_checks`; si no lo admite, se omite ese check.
- Probar cada regla con tres PR o casos de ensayo: uno defectuoso, uno correcto y uno al que la regla no aplica. Registrar qué marcó cada bot.

### Verificación
- `check-docs.py` y lychee pasan sobre la base tras enlazar el ADR.
- El esquema de `.coderabbit.yaml` es válido.
- Resultados de los casos de ensayo de los bots.

## Fuera de alcance
- Ruff y Semgrep.
- Mutation testing.
- Cambios de versión del plugin.
- Aplicar el plan a R02, que se hace en el paso 4 del orden de integración.

## Riesgos

| Riesgo | Mitigación |
|---|---|
| Imponer UTF-8 a un proceso hijo que emite otra codificación | Verificar cada `subprocess` en el preflight |
| Añadir `encoding` a una apertura binaria, que provoca `ValueError` | Edición con AST o a mano, más la suite completa |
| Deriva de los hashes o de `_portable` | Regenerar en el sitio y pasar doctor y verify-package |
| Fallos preexistentes que aparecen al ejecutar la suite completa | Informarlos sin ampliar el alcance |
| Falsos positivos o negativos en los IDs | Fuentes de definición reconocidas y prefijos explícitos |
| Reglas de revisión que los bots no aplican | Casos de ensayo y empezar en `warning` |
| Un workflow que falla pero no bloquea el merge | Proponerlo después como check obligatorio, con autorización aparte |
