# Auditoría funcional, semántica y de interfaz · Design Skills Router v1.1

**Fecha:** 17 de noviembre de 2026  
**Artefacto:** `design-router-pizarra-seleccion-minima-v1.1.html`  
**SHA-256 del original:** `9136c45f41d8c3f0f0f896477fbb7150060114daf046d609a79b382b8ba32317`  
**Veredicto:** **APTO COMO PIZARRA EXPERIMENTAL CON ADVERTENCIAS; NO APTO PARA PROMOCIÓN A POLÍTICA EJECUTABLE.**

## Alcance y método

Lectura del modelo, del HTML y del código JavaScript que incluye. Contraste con los contratos reales de `design-process-orchestrator` y las rutas del árbol `v0.4`. Replicación de las tres pruebas originales; cinco tests negativos nuevos con Playwright/Chromium; comprobaciones de foco, overflow, contraste de muestras, integridad de ZIP y hashes. El HTML original, los expedientes y el plugin quedan **sin cambios**. La copia anotada es un artefacto separado de auditoría.

## Evidencia de ejecución

| Prueba | Observación | Interpretación |
| --- | --- | --- |
| Suite original `test_min_route_v11_smoke.py` | **3/3 PASS** (6,0 s) | Confirma ejemplos básicos, integridad de datos y móvil; no cubre las contradicciones nuevas |
| Cinco pruebas negativas | **5/5 FAIL** (4,9 s) | Cada prueba reproduce un comportamiento incorrecto que la suite original omitía |
| Auditoría → G2, modo función | **Owners `[]`** | La selección de dominio es inoperante para ese escenario |
| Auditoría → G5, escenario completo | **Owners `[G5,G7]`** | Fuga funcional de especialista de movimiento |
| N/A sin razón y exportación | Descarga con `not_applicable` sin razón ni campo de validación | Registro incompleto/contradictorio sin control de consistencia |
| Cambio de select de aplicabilidad | Foco queda en `BODY` | Falla operativa de navegación por teclado |
| Contraste de muestras | 17 muestras medidas con ratio ≥ 4,5:1 | **No** equivale a conformidad WCAG global |
| Viewports | 320, 390, 768, 1440 CSS px sin desbordamiento horizontal del documento | No prueba zoom real ni lectura accesible a 200 % |
| Integridad | 7/7 archivos del manifest con bytes y SHA coincidentes; ZIP sin error | Empaquetado íntegro, no necesariamente reproducible desde fuentes |
| Apertura directa `file://` | `ERR_BLOCKED_BY_ADMINISTRATOR` | Límite del entorno de pruebas, **no** un fallo adjudicado al HTML |

Las cinco pruebas fallidas son **pruebas de regresión negativas** intencionadas: muestran defectos y deben pasar cuando se implementen las correcciones. No reportar 5/5 como «pruebas superadas».

## Hallazgos y reparaciones propuestas

### SEM-01 · P1 · Auditoría focalizada pierde el dominio seleccionado

**Observado:** Auditoría → Solo función → G2: el selector muestra G2, pero los especialistas propuestos quedan vacíos ([])

**Esperado:** Al elegir un dominio de auditoría, derivar la función de evaluación al especialista de ese dominio o mantener un bloqueo visible y justificado.

**Causa/localización:** `resolveOwner() · ownersSelected() · renderDomain()`.

**Corrección propuesta:** Usar un dominio de auditoría explícito y resolver sus capacidades; no usar el owner predeterminado de una función genérica.

**Evidencia:** `probe_negative.json#audit_function_G2`.

### SEM-02 · P1 · El escenario de auditoría activa un especialista no solicitado

**Observado:** Auditoría → Todas las funciones → G5: resultado [G5, G7]; con G2 el resultado es [G2, G7].

**Esperado:** Un ámbito focalizado en G5 o G2 no debe arrastrar automáticamente G7 por una subfunción genérica de motion-review.

**Causa/localización:** `functionsSelected() · resolveOwner() · ownersSelected()`.

**Corrección propuesta:** Filtrar funciones por el dominio elegido antes de resolver los owners; separar auditoría global de auditoría focalizada.

**Evidencia:** `evidencia_A01_auditoria_G5_G7.png`.

### STATE-03 · P1 · La exportación conserva N/A inválidos sin declarar invalidez

**Observado:** Se puede exportar G4 como not_applicable sin razón, o el owner requerido como not_applicable con contradicción, sin estado validation.

**Esperado:** Bloquear exportación como registro listo o exportar borrador con validación formal e identificación de conflictos.

**Causa/localización:** `checkReview() · renderCoverage() · exportSelection()`.

**Corrección propuesta:** Incorporar validateSelection() pura que produzca errores, y separar borrador de registro válido.

**Evidencia:** `probe_negative.json#audit_export_conflict`.

### TRACE-04 · P1 · El expediente omite la selección explícita de dominio

**Observado:** selected_domain no se incluye; en una auditoría focalizada que no resuelve owner, la elección de G2 se pierde.

**Esperado:** Registrar dominio, contexto de aplicación, versión de política y estado de validación independientemente de proposed_owners.

**Causa/localización:** `exportSelection()`.

**Corrección propuesta:** Agregar selected_domain y policy_version/hash al contrato de exportación; probar serialización y readback.

**Evidencia:** `probe_negative.json#audit_export_conflict`.

### UX-05 · P1 · Se pierde el foco del teclado al cambiar la aplicabilidad

**Observado:** Al modificar un select o justificación, renderCoverage() reemplaza toda la grilla; document.activeElement pasa a BODY.

**Esperado:** Conservar foco y cursor en el control correspondiente, y anunciar de forma no intrusiva la actualización.

**Causa/localización:** `renderCoverage() · listener change de minCoverage`.

**Corrección propuesta:** Actualizar únicamente la fila afectada o restaurar foco por identificador estable y posición de selección.

**Evidencia:** `probe_a11y.json`.

### MODE-06 · P2 · Modo de G0 inferido por función, no por contexto de proyecto

**Observado:** El perfil de «elegir fuente» siempre anuncia Lightweight; otros perfiles Subgraph sin identificar greenfield, fuentes existentes o permiso.

**Esperado:** Marcar modo ilustrativo o solicitar contexto pertinente antes de proponer modo real; G0 decide según intención y trabajo.

**Causa/localización:** `profile() · policy.profiles`.

**Corrección propuesta:** Separar necesidad funcional y modo; inferencia de modo solo desde hechos con evidencia.

**Evidencia:** `design-router-seleccion-minima-v1.1-modelo.json#profiles`.

### VIS-07 · P2 · Los primeros diez apoyos ocultan intervenciones de escritura

**Observado:** El renderer ordena todas las consultas antes de las escrituras y corta all.slice(0,10): componentes oculta 5 intervenciones, movimiento oculta 8, auditoría oculta 1.

**Esperado:** Mostrar apoyos agrupados por función y efecto o ofrecer un contador con expansión sin esconder el tipo de intervención.

**Causa/localización:** `renderMain() · all.slice(0,10)`.

**Corrección propuesta:** No truncar por orden de inventario sin un criterio; listar efectos por separado y permitir expandir.

**Evidencia:** `min_route_v11.js:L48-L56`.

### POLICY-08 · P2 · La simulación de sandbox aparece en modo de auditoría read-only

**Observado:** minPermit permite sandbox aunque el perfil vigente es «Audit · read-only». No se ejecuta escritura, pero el relato visual es inconsistente.

**Esperado:** Cuando mode=Audit, desactivar la opción de sandbox y conservar permisos read-only; registrar la causa.

**Causa/localización:** `minPermit · profile()`.

**Corrección propuesta:** Hacer el permiso de simulación dependiente de modo; nunca usarlo como autorización real.

**Evidencia:** `probe_negative.json#audit_scenario_G5_sandbox`.

### MAINT-09 · P2 · El ZIP no incluye fuentes de construcción editables

**Observado:** El paquete integra el HTML compilado y test, pero no incluye build_min_route_v11.py, min_route_v11.js ni min_route_v11.css.

**Esperado:** Conservar fuente, comando de build y hashes para reproducir una versión posterior sin editar manualmente el HTML monolítico.

**Causa/localización:** `Empaquetado y trazabilidad`.

**Corrección propuesta:** Incluir sources/ y prueba de build determinista en el próximo release de pizarra.

**Evidencia:** `unzip -l design-router-seleccion-minima-v1.1.zip`.

### A11Y-10 · P2 · Lectura en pantallas pequeñas requiere evaluación específica

**Observado:** Textos informativos de 9–11 CSS px; el check de ancho a 320 px no verifica por sí solo zoom 200%, reflow ni lector de pantalla.

**Esperado:** Evaluar legibilidad y escalado real, foco, recorrido por teclado y tecnologías asistivas con contenidos largos.

**Causa/localización:** `min_route_v11.css`.

**Corrección propuesta:** Revisar escala de texto y ejecutar pruebas de 200% zoom, reflow y teclado completo; no afirmar conformidad por solo contraste.

**Evidencia:** `probe_contrast.json + probe_a11y.json`.

## Orden recomendado de reparación

1. Resolver **SEM-01 y SEM-02** con una ruta de auditoría derivada exclusivamente del dominio elegido, y casos negativos «auditoría tipográfica» y «auditoría layout».
2. Resolver **STATE-03 y TRACE-04** creando `validateSelection()` y una exportación que incluya ámbito elegido, validez, conflictos, y huella de política. Se puede seguir descargando borradores, pero deben identificarse como inválidos cuando corresponda.
3. Resolver **UX-05** manteniendo foco/posición durante cambios de aplicabilidad; probar teclado real y edición repetida de justificaciones.
4. Desacoplar **MODE-06** del nombre de ruta y eliminar la contradicción de sandbox **POLICY-08**.
5. Completar **VIS-07** con la lista y prioridad de apoyos por efecto; recuperar fuentes editables **MAINT-09** y probar escalado y lectura **A11Y-10**.

**Regla conservada:** la función determina el especialista G1–G7 aplicable; G0 coordina; una referencia externa no autoriza instalación, escritura ni aceptación de fase. No modificar el baseline v0.4 ni el plugin v0.3.1 como parte de esta auditoría.

## Límites

No se ha probado el host real seleccionando skills, ni Safari/iPhone, VoiceOver, lectores de pantalla, zoom real al 200 %, ni la activación efectiva de dependencias externas. Tampoco hay revisión externa independiente: esta auditoría y sus tests los elaboró el mismo agente.

## Fuentes normativas consultadas

- W3C WCAG 2.2, **SC 1.4.3 Contrast Minimum**: https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html
- W3C WCAG 2.2, **SC 1.4.4 Resize Text**: https://www.w3.org/WAI/WCAG22/Understanding/resize-text.html
- W3C WCAG 2.2, **SC 1.4.10 Reflow**: https://www.w3.org/WAI/WCAG22/Understanding/reflow.html
- `fegome90-cmd/my-skills` a commit `5211aae8843eca4966d2aee828513582a04a7c8f`: `design-process-orchestrator` y sus `execution-contracts`.
- Plugin instalado `design-tree` / `tree-v0.4` y `ASSISTANCE.md`; son fuentes de reglas, no pruebas de comportamiento del host.
