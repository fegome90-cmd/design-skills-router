# Verificación y auditoría residual · Design Skills Router 0.2.1

Fecha: 8 de noviembre de 2026. Ejecución inline con Superpowers. Revisión propia, no independiente.
Base de ejecución: 0.1.3, release pluginrel_6af0c2f4065881918655a7dca673abcf. Se publicó 0.2.0 y la lectura posterior detectó normalización del manifiesto de compatibilidad; esta corrección 0.2.1 se prepara contra pluginrel_6af0f9576e408191b88527e403cb19aa. Esta entrega no importa la database externa.

## Implementado

Doctor de sólo lectura, entrada de mantenimiento en design-tree, AGENTS y manual operativo, contratos suplementarios, hechos con evidencia, tres niveles de asistencia, mapa de fases y aceptación humana de paquetes exactos. Exportación transaccional, migración explícita 0.1→0.2 hacia copia nueva, recuperación en manual y preparador reproducible de releases. El árbol v0.4, inventario, reglas, visor y sus huellas originales permanecen idénticos.

## Pruebas observadas

- Suite completa por unittest discovery: **127 tests, 0 fallos, 0 errores, 0 omitidos**, en Python 3.13.5.
- El escenario web sintético tiene **93 registros, 45 elecciones de ramas y cuatro paquetes de fase**. Sus selecciones esperadas son literales, no calculadas por el evaluador de vigencia. Se detiene en cada gate; sólo recibos sintéticos de usuario aceptan paquetes. El cierre llega a ready_for_human_handoff=true, con permission_to_execute=false. Alterar la evidencia vuelve a bloquearlo.
- La prueba de presupuesto compara 12 decisiones reversibles en una misma fase: el evaluador exige 12 decisiones manuales o permite las 12 delegadas más el gate final. **No mide preguntas de un LLM ni una conversación real.**
- El doctor prueba JSON roto, tipos inválidos, deriva de bytes, rutas inseguras, symlinks, bloqueo de expediente y ausencia de escrituras de contenido/entradas. Desactiva bytecode antes de importar módulos.
- Regresiones: referencias del inventario inventadas, criterio o snapshots de fuente eliminados, cambio de alcance, evidencia de hechos cambiada, recurso equivocado, política de recurso cambiada, auditoría que pretendía escribir y reapertura que perdía historial. Casos rojos y verdes conservados fuera del plugin.
- Migración: copia nueva manual, original intacto, dry-run, corrupción, formato desconocido, destino ocupado, escape de rutas y fallo de escritura sin salida parcial. No genera aprobaciones nuevas.
- Manual: ruta de mantenimiento antes de Q00, comandos reales desde otro directorio, diagnóstico de pin incompatible y cambio editorial de relación. **No es prueba de descubribilidad por un agente independiente.**
- Sintaxis de todos los archivos Python comprobada con grammar feature_version 3.10; **runtime Python 3.10, Windows y macOS no probados**.

Las comprobaciones se solapan. No se suman como una puntuación global de calidad ni prueban calidad estética/accesibilidad del resultado de diseño.

## Cobertura de fuentes y contratos

Se releyeron 23 documentos principales SKILL.md y la entrada/ámbito más secciones de write-swift; esa ruta nativa continúa bloqueada. Las 58 entradas restantes conservan NOT_REVIEWED_THIS_RELEASE. Referencias auxiliares no exhaustivas. Los siete contratos efectivos son seis delegaciones de better-interface y su recurso review-format.md fijado por blob; otros vínculos no se inventan ni importan del catálogo. Las fuentes originales se consultan, no se instalan/ejecutan.

Las recetas rígidas o afirmaciones técnicas de las fuentes siguen subordinadas al encargo, la evidencia y las adaptaciones contextuales del árbol; no se promueven como normas universales.

## Empaquetado y conservación

Se conserva el mismo ID/nombre/audiencia, los prompts, la invocación explícita y el árbol. No hubo repositorio GitHub ni Library modificados. Los tres iconos originales se preservan por overlay remoto: la descarga binaria del archivo actual no estaba accesible en el contenedor. El ZIP de actualización se identifica como **GUARDED_OVERLAY**, no como paquete autónomo. Sus hashes de assets retenidos proceden del release consultado; las lecturas posteriores de inventario/manifiesto no se presentarán como comparación local de esos bytes.

La publicación y su lectura posterior se documentan en un recibo separado. Este informe se redacta antes de publicar y no afirma activación de host.

## Corrección posterior a publicación 0.2.0

El servicio regeneró `.codex-plugin/plugin.json` con orden/escape diferentes, aunque su significado era equivalente. Eso desalineó la huella entregada. Una regresión específica reprodujo el problema y el preparador ahora conserva la serialización observada antes de calcular hashes. No se eliminó ese archivo de la verificación. La suite completa final pasó 127 tests. La lectura remota del nuevo release debe confirmar nuevamente los bytes declarados; el resultado se registra aparte.

## Límites y problemas residuales

1. **HOST_NOT_VERIFIED:** no se ha observado la skill activarse en una conversación nueva ni un LLM obedecer los gates. Los tests son del helper, CLI, datos y empaquetado.
2. **Autoridad supervisada:** los recibos son referencias declaradas por el operador; no autentican al humano. Un agente con acceso para reescribir el paquete o estado puede evadirlo. No hay interceptación global de herramientas, servidor ni permisos de producción concedidos por el helper.
3. **Cobertura parcial de conocimiento:** no se han descompuesto exhaustivamente las 82 skills ni todas sus referencias. Nativo, documentos, presentaciones y gráfica mantienen bloqueos. El catálogo externo sigue separado.
4. **Un requisito atómico por expediente:** no hay agregador de cumplimiento de toda una aplicación. El mapa de fases por defecto agrupa los dominios del árbol; se acepta explícitamente y no expresa una arquitectura universal de proyectos.
5. **Fuentes y evidencias versionadas:** exportar historia exige conservar archivos inmutables por versión. Si el mismo path representa dos hashes históricos, se bloquea en vez de perder evidencia. El rollback de código no revierte ni elimina el expediente nuevo.
6. **Rendimiento:** el árbol aún expande 3.660 instancias. Se elimina trabajo repetido dentro de una lectura síncrona con caché efímera; la siguiente lectura vuelve a comprobar evidencia. No se afirma un benchmark general ni se modificó el visor.
7. **Concurrencia externa:** cambios del filesystem durante una lectura no constituyen un snapshot transaccional de fuentes. La integridad se revalida en nuevas operaciones; no es una frontera de seguridad frente a escritores maliciosos.

## Reproducir

Desde el paquete completo instalado (no desde un overlay sin los assets retenidos):

```sh
python3 -B -m unittest discover -s tests -v
python3 -B skills/design-tree/scripts/doctor.py --format json
python3 -B skills/design-tree/scripts/runner.py verify-package
```

Para recuperar: consultar CLI.md y MAINTENANCE.md. No usar recibos sintéticos de tests para proyectos reales.
