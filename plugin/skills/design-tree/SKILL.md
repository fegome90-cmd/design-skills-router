---
name: design-tree
description: "Use when Felipe explicitly selects Design Skills Router for a supervised UI web design project, the design supermarket, or maintenance, diagnosis and updates of this plugin. Do not activate for unrelated coding or backend work."
disable-model-invocation: true
---

# Diseño y mantenimiento guiados por el árbol

## Mantenimiento del plugin

Si pide auditar, diagnosticar, modificar o actualizar **este plugin**, leer [MAINTENANCE](references/MAINTENANCE.md) y usar el doctor. **No iniciar Q00**, no pedir un proyecto de diseño. Resolver la ruta real del paquete y recuperar el release vigente antes de actualizar. No crear otro plugin ni importar la database del catálogo externo.

## Proyecto de diseño

Leer [PILOT](references/PILOT.md) y [ASSISTANCE](references/ASSISTANCE.md). El árbol canónico está en `references/tree-v0.4/`; no reconstruirlo de memoria ni convertirlo en un flujo lineal. Los tres niveles conservan las mismas obligaciones de fuentes, alternativas, criterios y evidencia.

Resolver la ubicación real del paquete. Usar `python3 -B scripts/runner.py` y consultar [CLI](references/CLI.md). El expediente vive fuera del plugin. Sin helper ejecutable: `VALIDATOR_NOT_RUN`; sólo preparar propuestas conversacionales, no fingir transiciones ni implementar producción.

Si falta un encargo, preguntar por el proyecto o pantalla; no inventarlo. Recuperar primero el expediente indicado. No usar recuerdos del chat como persistencia. `resume` comprueba los bytes y vuelve a manual; renovar una delegación sólo desde autorización humana explícita.

## Experiencia de los tres niveles (contrato conversacional)

- **Inicio sin nivel explícito:** al recibir un nuevo **encargo de diseño web** y no haber nivel indicado ni mandato vigente, **recomendar `guided` una sola vez**, dentro de un único encuadre breve con alcance, fase, entregable y decisiones reservadas. Pedir consentimiento para el mandato concreto antes de delegar. La recomendación **no cambia** `assistance_level=manual` ni autoriza decisiones: el helper requiere recibo humano exacto.
- **Nivel explícito:** si el usuario ya eligió `manual`, `guided` o `phase_auto`, usarlo sin pedir que escoja de nuevo; `guided` y `phase_auto` necesitan un mandato real para ese alcance y fase. No tratar una frase del asistente, una preferencia guardada ni un «ok» ambiguo como recibo.
- **Mandato vigente:** si hay delegación activa y válida para fase, alcance, reserva y acciones, reutilizarla sin solicitar una segunda elección del nivel o confirmación para cada lectura, prueba o decisión reversible autorizada. Los cambios de contexto que invaliden el mandato vuelven al gate humano.
- **Reanudación:** después de `resume`, migración o `revoke`, continuar en `manual` y solicitar una delegación nueva únicamente si se quiere recuperar autonomía; no reiniciar el cuestionario sobre hechos y decisiones todavía vigentes en el expediente.
- **Interrupciones y gates:** en `manual` presentar cada decisión pendiente con alternativas concretas; en `guided` resolver provisionalmente las reversibles cubiertas y preguntar sólo por reservas/estratégicas y cierre de fase; en `phase_auto` avanzar hasta el paquete de fase autorizado. Agrupar cuestiones estratégicas relacionadas en un intercambio compacto, sin fusionar recibos, omitir registros, saltarse pruebas o aceptar fases automáticamente. Gastos, publicación, destrucción, credenciales y cambios de alcance requieren permisos propios.

El `defaultPrompt` heredado habla de «la próxima pregunta»: en `guided` y `phase_auto`, entenderla como el **siguiente gate humano necesario**, no como instrucción de interrogar sobre cada nodo; nunca contradecir una petición explícita de modo manual. La presentación del plugin permanece intacta por contrato.

El árbol contiene 82 referencias, **no 82 preguntas obligatorias para la persona**. Recuperar el contexto documentado primero y no volver a preguntar lo que ya está decidido o respaldado. Los 3 niveles cambian la frecuencia de interrupciones, no la cobertura, procedencia, verificaciones o autoridad del contrato.

## Encuadre único, no ochenta preguntas

Distinguir estructura, decisiones del proyecto y permisos de ejecución. El usuario puede confirmar una estructura exacta como conjunto y aceptar un mapa de fases. Una fase contiene un resultado revisable y un límite; no puede abarcar todos los dominios de un proyecto para eludir gates.

Aprovechar instrucciones ya explícitas. Presentar en un único encuadre nivel, alcance, fase, entregable y reservas. `manual` consulta cada decisión pendiente; `guided` conserva reservas acordadas; `phase_auto` decide provisionalmente dentro de la fase. No pedir permiso por cada lectura ni añadir «¿continúo?» entre operaciones autorizadas. Las actualizaciones intermedias son informativas.

Un mandato se registra con el mensaje real, su cita, nivel, ámbito, fase y punto de parada. No fabricar recibos humanos ni elevar autonomía al recuperar un archivo. Confirmar estructura no aprueba propuestas; delegar no es aceptar el resultado. La aceptación de una fase no autoriza por sí sola la siguiente.

## Recorrer decisiones

1. Consultar `status`, `node` y sus condiciones. Una decisión elige una respuesta; `all` conserva todas las ramas. No quitar skills por conveniencia ni por cambiar de nivel.
2. Recuperar las skills originales y apoyos exigibles por sus commits fijados usando herramientas autorizadas. Guardar bytes, referencia, commit y SHA Git blob; un hash no prueba comprensión. No sustituir una fuente ausente por memoria. Leer es `REFERENCE_ONLY`, no permiso para ejecutar la skill ni instalar sus dependencias.
3. Registrar para todas las alternativas, skills, criterios y relaciones exigibles: decisión, razones resumidas, descartes y evidencia. Mostrar muestras cuando la decisión sea visual. No revelar razonamiento privado. Separar normas, heurísticas, convenciones y preferencias; no transformar opiniones de autores en normas universales.
4. En manual o ante una reserva, `propose` espera confirmación de esa propuesta exacta. Con un mandato válido, `delegate` registra `DECIDED_DELEGATED`: puede fundamentar el trabajo provisional de la fase, pero nunca se presenta como aprobación humana.
5. Conservar recursos del proyecto, evaluar capacidades nativas y bibliotecas pertinentes antes de crear una pieza. Cada candidato conserva componente, requisito, fuente y versión. Una sesión cubre un requisito atómico; no declarar completa una aplicación por cerrar sólo un componente.
6. Al terminar la fase, preparar un paquete con artefacto, decisiones relevantes, fuentes y descartes, pruebas, límites y bloqueos. `phase-prepare` deja `AWAITING_HUMAN`. Detenerse. No atravesar al siguiente dominio.
7. Tras observar la aceptación real, `phase-accept` ratifica el paquete exacto sin crear recibos individuales ficticios. Una respuesta que acepte y autorice explícitamente la fase siguiente puede respaldar dos registros separados desde el mismo mensaje; nunca inferir el segundo de un «ok» ambiguo.

## Cobertura, cambios y cierre

Mantener las 82 disposiciones visibles; no son 82 skills instaladas ni todos sus criterios están formalizados. Una entrada aplicable sin revisión y una exclusión contradictoria impiden cierre. La aceptación del inventario puede formar parte del paquete de fase, pero sus filas y evidencias siguen siendo comprobables.

Un cambio relevante de hechos, fuente, propuesta o contrato invalida sus decisiones afectadas. Las propuestas y recibos previos quedan en historia. Datos desconocidos no son falsos ni «no aplica». Si falta información recuperable, aportar evidencia y reproponer la pregunta padre; no forzar una hoja bloqueada. Una ruta no desarrollada sigue bloqueada.

Cambios de stack o alcance, gastos, destrucción, publicación y acceso sensible requieren autoridad correspondiente; el modo automático no la crea. El helper no ejecuta esas acciones ni controla herramientas externas. En auditoría, conservar fuentes del proyecto sin cambios.

Al pausar, exportar el expediente y entregar próximos gates y bloqueos. Guardar en Library, Drive o GitHub requiere autorización específica. No hay persistencia cloud automática. No afirmar ejecución de host, accesibilidad, calidad o autenticación por pasar tests estructurales. El [doctor](references/MAINTENANCE.md#diagnostico) informa cada ámbito por separado.
