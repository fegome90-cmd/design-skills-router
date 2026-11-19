# Design Skills Router · Pizarra de cambios propuestos v0.6

Fecha: 2026-11-17. Estado: PROPUESTAS. **No son aprobaciones ni cambios del plugin**.

## Qué cambia en la interfaz

Se parte del archivo existente `design-router-pizarra-relaciones-v0.5.html` y se mantienen sus dos vistas: **Capas** y **Relaciones entre skills**. Se agrega la tercera vista **Cambios propuestos**, con 15 expedientes divididos entre seis etapas. Cada expediente muestra antes/después, prioridad, dueño G0–G7, IDs canónicos, skills relacionadas, pruebas y gates. También se proponen cuatro paquetes de trabajo F1–F4, sin convertirlos en una ejecución lineal obligatoria.

## Archivo y exportaciones

- `design-router-pizarra-cambios-propuestos-v0.6.html` — HTML principal con datos y lógica embebida. Requiere navegador; mantiene fallback SVG y no depende de Shoelace/CDN para el panel de cambios.
- `design-router-cambios-propuestos-v0.6.drawio` — XML editable por capas y dependencias de investigación, no un flujo automatizado.
- `design-router-cambios-propuestos-v0.6.json` — esquema `design-router-proposal-board/0.6` con las propuestas y criterios.
- `qa_router_changeboard_v06_results.json` — evidencia de pruebas en navegador y límites.

## Hallazgos fuente

P1-01 elegibilidad; P1-02 clasificación; P1-03 web/nativo; P1-04 doble orquestador; P1-05 infraestructura; P1-06 permisos/invocación/aprendizaje; P1-07 procedencia. Derivados de `design-router-auditoria-semantica-v0.3.md` y de contratos G0–G7. La clasificación del roadmap no altera el archivo canónico `tree-v0.4`, `contracts.json` ni la versión publicada del plugin.

## Interpretación

- **AHORA** describe el riesgo detectado; no asegura que el runtime real lo esté ejecutando.
- **PROPUESTA** describe comportamiento deseado no implementado.
- **Archivos** son candidatos a modificaciones futuras, no fueron escritos en esta tarea.
- Las relaciones de dependencia indican secuencia de revisión; no generan automáticamente permisos de ejecución.
- No se ha hecho QA de activación real del plugin. Las pruebas de esta entrega son de la interfaz y el XML.

Para incorporar los cambios efectivamente se requerirá diseño tipado, versiones fijadas, fixtures negativos, auditoría, aceptación humana del diff y autorización de actualización por separado.
