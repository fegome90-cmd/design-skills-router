# Roadmap MCP

Índice de las unidades del roadmap MCP. Una unidad está **integrada** cuando su contrato vive en [`units/`](units/) y el PR que la implementa se fusionó. Está **planificada** cuando otros documentos del repositorio la citan, pero todavía no tiene contrato aquí.

La columna "Lo que dicen las fuentes" cita los documentos que mencionan cada unidad. No amplía su alcance: el alcance de una unidad planificada lo fija su contrato cuando se escriba.

Esta tabla es una fuente de definiciones para `scripts/check-docs.py`, que comprueba que cada ID de `docs/` esté definido.

| Unidad | Estado | Lo que dicen las fuentes |
|---|---|---|
| [R01](units/R01-registro-compartido-de-tools.md) | Integrada (PR #7) | Contrato compartido de tools: paridad entre la CLI instalada y el MCP stdio. Investigación en el [dossier R01](research/R01-dossier-v0.1.md). |
| R02 | Planificada, sin contrato | "R02 definirá permisos y control por llamada" ([dossier R01](research/R01-dossier-v0.1.md#adr-r01-provisional)). "El siguiente PR será R02, seguido por R03" ([contrato R01](units/R01-registro-compartido-de-tools.md#secuencia-de-trabajo)). |
| R02A | Planificada, sin contrato | "Actualizar R02A. Integrar sus commits sobre la nueva base y aplicar los controles" ([plan de calidad](../calidad/plan-ci-calidad.md#orden-de-integración)). |
| R02B | Planificada, sin contrato | "Retomar R02B y R02C" ([plan de calidad](../calidad/plan-ci-calidad.md#orden-de-integración)). |
| R02C | Planificada, sin contrato | "Retomar R02B y R02C" ([plan de calidad](../calidad/plan-ci-calidad.md#orden-de-integración)). |
| R03 | Planificada, sin contrato | "El siguiente PR será R02, seguido por R03" ([contrato R01](units/R01-registro-compartido-de-tools.md#secuencia-de-trabajo)). El dossier usa una incorporación simulada de R03 como caso de estudio ([dossier R01](research/R01-dossier-v0.1.md#g2-experimentos-pendientes-no-ejecutados)). |
| R04 | Planificada, sin contrato | La lectura HTML de Kalka es "relevante para R04/R10, no requisito R01" ([dossier R01](research/R01-dossier-v0.1.md#kalka-diferencias-observadas-entre-los-commits-estudiados)). |
| R09 | Planificada, sin contrato | "R09 definirá evidencia visual" ([dossier R01](research/R01-dossier-v0.1.md#adr-r01-provisional)). |
| R10 | Planificada, sin contrato | La lectura HTML de Kalka es "relevante para R04/R10, no requisito R01" ([dossier R01](research/R01-dossier-v0.1.md#kalka-diferencias-observadas-entre-los-commits-estudiados)). |
