# Verificación del plugin · 0.1.0

Fecha: 8 de noviembre de 2026. Base: árbol v0.4, sin cambios. Alcance: plugin privado de skills para un piloto supervisado de UI web. Este informe describe la verificación local previa al registro; no es una evaluación independiente de obediencia del modelo.

## Resultado local

- **49 pruebas automatizadas aprobadas** con `python3 -m unittest discover -s tests -v`.
- **27 comprobaciones de paquete y arranque satisfactorias**: manifiesto, YAML, rutas, fuente v0.4, recuperación de Q00, negativa a avanzar sin confirmación y conservación del estado tras el rechazo.
- **7 archivos del baseline conservados byte por byte**, verificados con SHA-256: árbol, reglas, inventario, correspondencia de criterios, auditoría, README y visor.
- Una skill descubrible: `design-tree`. Las 82 entradas originales son referencias y disposiciones, no 82 skills instaladas.
- El helper únicamente lee fuentes/evidencias locales y escribe el expediente o su exportación. No instala dependencias, llama modelos, publica ni modifica código de proyecto.

Las 27 comprobaciones se solapan parcialmente con las 49 pruebas; no sumarlas como una tasa global de calidad. El registro remoto y su lectura posterior se documentan en un recibo de entrega separado.

## Evidencia de regresiones reales

El primer intento del ejecutor falló por ausencia de implementación; ese fallo de arranque no se cuenta como evaluación conductual. Las pruebas de portabilidad posteriores reprodujeron tres fallos: exportación sin integridad utilizable y ausencia de recuperación compatible. Se corrigieron y volvieron a ejecutar.

Una prueba adicional demostró que omitir las decisiones por criterio no bloqueaba una propuesta; se añadió el control. En la revisión final se reprodujeron cinco fallos más: referencias inventadas de skills, referencias inventadas de criterios, referencias con tipo incorrecto, skills declaradas aplicables sin revisión y exclusiones que contradicen revisiones activas. Todos se corrigieron antes del último resultado satisfactorio.

Los registros rojos y el último resultado verde permanecen en `evidence/`. Los mensajes de aprobación y archivos de fuentes usados en pruebas son **sintéticos**: no aprueban decisiones reales de Felipe y no acreditan la recuperación de las 82 fuentes originales.

## Comportamientos comprobados

Una propuesta no abre sus hijos hasta recibir un registro humano separado dirigido a su huella exacta. Una decisión abre sólo el hijo seleccionado; una apertura ALL mantiene todos sus hijos. No se admite omitir alternativas, skills ni criterios del nodo. Las revisiones deben apuntar a archivos o recibos de fuente registrados.

Cambios en evidencia, fuentes o decisiones invalidan la vigencia; la auditoría sólo acepta alcance de lectura. Los candidatos mantienen su identidad de componente, requisito, fuente y versión. Las rutas bloqueadas no se convierten a web. El expediente evita sobreescrituras concurrentes por revisión y se guarda por reemplazo atómico.

Exportar, mover la carpeta, borrar los archivos originales y recuperar el expediente conserva los hashes de las propuestas y la frontera pendiente. Una exportación alterada es rechazada. La exportación puede contener información privada y no debe publicarse.

## Límites de seguridad y autoridad

**El recibo humano no está autenticado.** El helper verifica su forma y correspondencia con una propuesta, no que el mensaje exista realmente en la conversación. El agente debe citar el mensaje observado y la persona supervisa. Quien puede reescribir el paquete o el expediente puede eludir sus controles: no es una barrera de seguridad del host.

**Recibir bytes no demuestra comprensión.** Los hashes comprueban que el archivo coincide con el blob esperado informado por el conector; el código no autentica GitHub ni verifica semánticamente la lectura. La pertinencia de una fuente y la calidad del juicio requieren revisión.

**No controla herramientas externas.** No hay bloqueo global del entorno, firma de aprobaciones ni servidor. `permission_to_execute` permanece falso: aprobar decisiones no publica ni autoriza ejecución irrestricta.

## Pendientes para el uso real

- Activación de la skill en una conversación nueva: NOT_RUN antes del registro.
- Evaluación con un LLM independiente y escenarios de presión: NOT_RUN. No hubo herramienta de subagentes disponible; las pruebas Python no sustituyen esa evaluación.
- Cobertura completa de los criterios de las 82 fuentes y contratos de invocación: pendiente, heredada de v0.4. No se promovieron exclusiones silenciosamente.
- Las fuentes originales no se redistribuyen: se consultan por demanda con sus commits fijados. Si faltan, la propuesta dependiente queda bloqueada.
- Soporte desarrollado: UI web supervisada. Nativo, presentaciones, documentos y gráfica mantienen sus bloqueos.
- Un expediente evalúa un requisito atómico de componente. La composición de varios expedientes no cuenta con un verificador global de producto.
- Persistencia: archivos exportables, no almacenamiento cloud automático ni memoria garantizada entre chats.
- Visor: se conserva el HTML ya revisado en v0.4; no se repitieron pruebas visuales en esta entrega porque sus bytes no cambiaron.

## Reproducción

Desde la raíz del paquete:

```sh
python3 -m unittest discover -s tests -v
python3 skills/design-tree/scripts/runner.py verify-package
```

Las pruebas usan la biblioteca estándar de Python. La validación adicional de los manifiestos utilizó PyYAML en el entorno de desarrollo; el helper no lo requiere. Consultar `evidence/package-validation.json`, `evidence/cli-smoke.json` y `evidence/green-tests.txt`.
