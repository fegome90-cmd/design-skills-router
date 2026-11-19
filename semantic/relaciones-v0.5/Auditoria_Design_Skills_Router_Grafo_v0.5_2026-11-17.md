# Reauditoría posterior a fixes — Design Skills Router / Grafo v0.5

**Fecha:** 17-11-2026  
**Tipo:** auditoría técnica de un artefacto de investigación (HTML/JSON/TriG/draw.io/ZIP).  
**Dictamen:** **APTO para investigación y navegación supervisada, con reservas. NO apto para ejecutar selección automática de skills ni promocionar al router canónico.**

## 1. Matriz de hallazgos R-01 a R-08

| Ref. | Prioridad original | Resultado v0.5 | Evidencia / reserva |
|---|---|---|---|
| R-01: web confundida con nativo bloqueado | P1 | **Corregido en el grafo** | `mobile-native → G5/G7` y `apple-design → G7/G3` son capacidades web evaluables. `S05` sigue BLOCKED; Swift/Expo siguen pendientes. Test positivo y negativos contra falsas habilitaciones. |
| R-02: 29 fuentes sin pins | P1 | **Pins corregidos; metadatos parcialmente pendientes** | 29 commits de 40 hex, blobs Git cotejados y `SKILL.md` leído al commit. Ninguna URL `blob/main` en nodos ni aristas. Cinco skills de Vercel carecen de licencia declarada/acreditada: no suponer derechos; dependencias requieren verificación por proyecto. |
| R-03: ausencia de función/ICOM por nodo | P1 | **Modelo experimental añadido** | 111 perfiles por skill + 41 perfiles de nodo visual, campos de función, entradas, controles, salidas, mecanismos y evidencias. RDF tiene clases `Capability`, `Function`, `DecisionNode`, `Input`, `Output`, `Control`, `Mechanism`, `EvidenceRequirement`. Los procedimientos todavía son propuestas no ratificadas, no un motor de reglas. |
| R-04: red ilegible en móvil | P1 | **Corregido en Chromium** | Altura real de `#semanticScroll`: 320×680=461 px; 320×760=541 px; 390×844=625 px. El modo grafo oculta encabezados secundarios en móvil y conserva acceso a capas. No hay overflow global. Safari/iOS físico no probado. |
| R-05: contador 0 con siete líneas | P2 | **Corregido** | Filtrar `alimenta` en panorama muestra siete aristas y contador «7 enlaces dibujados». `coordina` también coincide (7). |
| R-06: relaciones sin fuente/condición | P2 | **Trazabilidad explícita; hipótesis sin verificar** | 20 relaciones sin referencia directa original y 25 sin condición original mantienen flags de brecha; todas aportan fuentes de sus extremos fijadas y condición explícita o `NO FORMALIZADA`. Ninguna de las 157 propuestas acredita por sí misma una dependencia ni habilita ejecución. 45 enlaces `main` corregidos. |
| R-07: motor HTML no usa mxGraph | P2 | **Parcial / límite reconocido** | `.drawio` XML nativo genera 111 vértices, 171 aristas, metadata de evidencia y endpoints válidos; la descarga fue probada byte a byte. **HTML sigue en SVG local**, sin motor mxGraph; importación real a diagrams.net NO_VERIFIED. No afirmar cumplimiento completo de esta exigencia. |
| R-08: exclusiones propuestas mostradas como definitivas | P2 | **Corregido** | Estado `proposed-exclusion`, flag `PENDING_HUMAN`, rótulo «EXCLUSIÓN PROPUESTA». Ninguna exclusión se convirtió en ratificada. |

## 2. Alcance de pruebas y resultados

| Bloque | Resultado | Qué acredita |
|---|---:|---|
| Pruebas focalizadas de v0.5 | **58/58 PASS** | Consistencia de datos, clasificación web, pins, perfiles, RDF, navegación, contadores, XML y tamaños de pantalla en Chromium |
| Regresión adaptada de la batería anterior | **35/35 PASS** | Vista por etapas, fichas, filtros, búsqueda, alternancia de modos, descargas y ausencia de errores JavaScript, sin regresiones en esos escenarios |
| Validación de contrato y mutaciones negativas | **11/11 PASS** | El validador acepta el modelo conservado y detecta 10 errores deliberados: fuente no fijada, rutas, clasificación, permisos, aristas, contadores y fichas faltantes |

Estas baterías se solapan; no hay una tasa única de rendimiento o conformidad. La revisión fue realizada en el mismo entorno de trabajo, sin un auditor humano independiente, Safari real ni prueba con lector de pantalla.

## 3. Comprobación de procedencia y modelo

- Skills únicas: **111 = 82 del inventario canónico + 29 nuevas** (sin duplicar 18 registros que aparecían en ambas listas).
- Relaciones: **171 = 14 documentadas + 157 propuestas**. Se añadieron 2 asociaciones de capacidades web; todas las propuestas son explícitamente `eligibleForAutomaticRouting=false`.
- Funciones: **152 = 111 perfiles de skill + 41 nodos visuales**; están en el grafo `proposed` y no ratificadas.
- Grafo RDF: tres contextos con datos (`catalogue`, `documented`, `proposed`) y `human_approved` vacío; **5437 triples** contados tras parseo. 
- Licencias: 24/29 con licencia identificada por texto de skill o licencia del repositorio; 5/29 con estado explícito `NOT_DECLARED_IN_SKILL`. No se instalaron dependencias, no se descargaron ejecutables y no se concedieron permisos.
- Los cuatro archivos históricos v0.4 mantienen las huellas SHA-256 de la auditoría anterior; se generó v0.5 como copia distinta.

## 4. Evidencia observada de interfaz

| Viewport Chromium | Antes (según auditoría v0.4) | v0.5 (`#semanticScroll`) |
|---|---:|---:|
| 320×680 | 117 px; otra secuencia alcanzaba 86 px | **461 px** |
| 320×760 | 197 px | **541 px** |
| 390×844 | la auditoría anterior reportó 254 px tras una secuencia | **625 px** |
| 1440×900 | visor v0.4 con ~241 px en escenario comparable | **493 px** |

La métrica es altura visible del panel del grafo, **no** porcentaje WCAG ni garantía de legibilidad de todas las tarjetas simultáneamente. Se desplazó el grafo horizontal/verticalmente y se retuvo el zoom, en vez de imponer el ajuste completo al ancho de 320 px.

## 5. Límites abiertos que bloquean promoción a producción

1. **R07 parcialmente pendiente:** se necesita biblioteca mxGraph/maxGraph real en la vista HTML o una aceptación explícita de que SVG + exportación draw.io satisface el formato solicitado; se requiere prueba de importación en diagrams.net, no solo XML correcto.
2. **R03 sigue siendo investigación:** la clasificación de capacidades y las entradas/salidas IDEF0 son propuestas; faltan revisión de expertos, reglas de elegibilidad operacionales, contraejemplos y pruebas de agentes en host.
3. **R06 relación semántica:** las 157 relaciones propuestas permanecen hipótesis. Tener las URL de ambos `SKILL.md` no demuestra que la relación esté formulada por los autores.
4. **Licencias/dependencias:** cinco fuentes con licencia no acreditada y toda dependencia de ejecución pendiente de inspección por proyecto.
5. **Plataformas:** solo se probó Chromium local sin CDN; falta Safari/iOS real, zoom efectivo, teclado a gran escala y lector de pantalla.
6. **Router publicado:** no se ejecutó `doctor` sobre el release remoto, ni se modificó plugin, árbol v0.4, permisos, Library preexistente o decisiones históricas.

## 6. Criterio de cierre

**Cierre autorizado aquí:** correcciones sobre una copia documental v0.5 y reauditoría técnica con evidencia. **No autorizado ni realizado:** promoción de nuevas skills, cambios a `contracts.json`, cambios de baseline y publicación del plugin. Un «PASS» de la pizarra no es aprobación del router.
