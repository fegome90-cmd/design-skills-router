## Candidato no publicado · 0.3.1 (2026-11-10)

- Experiencia conversacional por niveles: recomendar `guided` una sola vez sólo en diseños web nuevos sin nivel ni mandato vigente; sin conceder autoridad por defecto.
- `manual`, `guided` y `phase_auto` dejan de confundirse con una lista de preguntas: las decisiones reversibles autorizadas se procesan internamente y las reservas/gates siguen requiriendo revisión.
- Ocho escenarios UX etiquetados añadidos a los doce casos de evaluación preexistentes; dos tareas comparables de doce decisiones reversibles, una reserva y cambio de alcance.
- Scorecard de observación fuera del plugin distingue `USER_OBSERVED`, `TRACE_VERIFIED` y `UNVERIFIED`; sin cifras de preguntas fabricadas.
- Árbol v0.4, helper Python, fuente/contratos y derechos de publicación permanecen intactos. No se publica ni se instala el overlay como ZIP autónomo.

## Candidato no publicado · 0.3.0 (2026-11-10)

- Pruebas de release portables y ronda de comprobación sobre ZIP ya preparado.
- Evaluación de routing en host con casos etiquetados, sin simulación de LLM.
- Resultados de verificación normativos, política vinculada a nodos y nueva
  compatibilidad de ledgers 0.3, con migración conservadora de 0.1/0.2.
- Plantilla de aprendizaje PROPOSED que no modifica el plugin.
- Árbol v0.4 y assets actuales sin cambio intencional. Sin publicación.

# Changelog

## 0.2.1 · 2026-11-08

Corrige la serialización del manifiesto de compatibilidad regenerado por Plugin Creator. Su SHA coincide con los bytes esperados tras publicar; agrega regresión específica y mantiene intactos los contratos y el runtime de 0.2.0. Ver docs/VERIFICATION-0.2.1.md y el recibo remoto separado.

## 0.2.0 · 2026-11-08

Añade doctor, mantenimiento rápido y asistencia manual/guiada/automática por fase. Cierra huecos de vigencia de contexto, criterios, fuentes e inventario; valida recursos específicos y conserva historial al reabrir fases. Añade migración explícita y empaquetado reproducible. Conserva el baseline v0.4 y las 82 referencias sin incorporar la database externa.

La versión de paquete está en plugin.json. Los informes docs/VERIFICATION.md, docs/PLAN.md y docs/SPEC.md anteriores son documentos históricos del primer release, no promesas de la entrega actual. Ver docs/VERIFICATION-0.2.0.md para cobertura y límites.
