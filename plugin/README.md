# Design Skills Router

La versión vigente se consulta en `plugin.json`. Plugin privado para diseño UI web supervisado con el árbol v0.4, preservado sin cambios. Contiene una skill de entrada, inventario de 82 referencias, helper Python, doctor y manual de mantenimiento. No contiene la database externa, servidor ni ejecución automática de herramientas.

## Experiencia de asistencia en nuevos encargos

Si no existe un nivel elegido para un nuevo diseño web, el Router **propone `guided` una sola vez** dentro del encuadre inicial. La propuesta no crea delegaciones ni modifica el estado `manual`: sólo un mandato de la persona, vinculado a fase y alcance, habilita decisiones reversibles provisionales. El modo explícito del usuario prevalece y un mandato vigente no vuelve a preguntarse. El prompt de «próxima pregunta» se refiere al siguiente gate humano necesario, no a cada referencia del árbol.

- `manual`: confirmaciones por decisión pendiente.
- `guided`: se resuelven decisiones reversibles autorizadas; se consultan reservas/estrategia y gate de fase.
- `phase_auto`: progresa dentro de la fase autorizada; no abre la siguiente automáticamente.

Las pruebas locales miden el contrato, **no** preguntas hechas por otro modelo en ChatGPT. El archivo `PILOT.md` documenta cómo observar una sesión real sin fabricar trazas.

## Empezar

Seleccionar Design Skills Router e indicar el encargo y nivel. Ejemplo: «Automático por fase; conserva mi stack y detente al entregar la propuesta visual». El agente aprovecha lo ya resuelto, registra decisiones y evidencia y se detiene en gates; no produce el proyecto completo one-shot. Si se pide mantener el plugin, entra al doctor/manual, no a un cuestionario de diseño.

- [Instrucciones](skills/design-tree/SKILL.md)
- [Manual de agentes](skills/design-tree/references/MAINTENANCE.md)
- [Niveles de asistencia](skills/design-tree/references/ASSISTANCE.md)
- [Protocolo, datos y migración](skills/design-tree/references/PROTOCOL.md)
- [CLI](skills/design-tree/references/CLI.md)

```sh
python3 -B skills/design-tree/scripts/doctor.py --format text
python3 -B -m unittest discover -s tests -v
python3 -B skills/design-tree/scripts/runner.py verify-package
```

Python 3.10+ previsto, sólo biblioteca estándar. Los recibos humanos no están autenticados; el helper no controla herramientas externas. Referencias documentadas no son skills instaladas. Persistencia: exportación explícita, no memoria cloud. Cada prueba tiene su alcance; leer documentos no demuestra ejecución del host.

Las actualizaciones parciales conservan los assets originales mediante overlay protegido por release de origen. No instalar un overlay como si fuera una distribución completa; consultar su recibo de preparación. Evidencia histórica en docs/VERIFICATION.md corresponde a 0.1.0; los resultados de cada entrega se adjuntan por separado.


## Candidato 0.3.0 (sin publicación)

La extensión de outcome añade ledger `design-tree-ledger/0.3`, checks con
PASS/FAIL/N/A/UNVERIFIED y migración a copia. `verification` mantiene su
significado histórico de método. El árbol v0.4 y 82 referencias no cambian.
Se añaden pruebas de artefacto preparado y pack de evaluación del host
(`UNVERIFIED` hasta observar sesiones frescas). Candidatos de aprendizaje
siguen externos y no se autoaplican.
