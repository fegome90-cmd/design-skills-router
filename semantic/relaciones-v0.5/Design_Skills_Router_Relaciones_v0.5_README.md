# Design Skills Router · Red funcional de skills v0.5

**Fecha:** 17-11-2026  
**Objeto:** correcciones y reauditoría de la pizarra de relaciones v0.4.  
**Estado:** artefacto de investigación funcional, **NO** plugin publicado, **NO** enrutador automático ni nuevo baseline. El árbol canónico `tree-v0.4` queda intacto.

## Abrir

1. Abre `design-router-pizarra-relaciones-v0.5.html` en un navegador moderno.
2. Selecciona **Relaciones entre skills** para explorar G0–G7 y especialistas.
3. **Ficha funcional** (en filtros) muestra propósito, entradas, controles, mecanismo, salidas y evidencia de los 41 nodos visuales de la pizarra.
4. Selecciona una skill para consultar su ficha FBS/IDEF0 propuesta, condiciones y fuente fijada.
5. **.drawio** exporta el grafo como XML nativo de mxGraph; el archivo `design-router-relaciones-skills-v0.5.drawio` está incluido en este paquete. El diagrama HTML sigue implementado en SVG/JavaScript local: **no** es el motor nativo draw.io.
6. **JSON** exporta el grafo completo con procedencia, funciones, capacidades, clasificación y condiciones.

## Diferencias principales de v0.4

- Clasificación por capacidad y medio: `mobile-native` se asigna a G5/G7 y `apple-design` a G7/G3 para sus funciones **web**, sin desbloquear la rama nativa `S05`.
- **29 candidatas** nuevas fijadas a commit Git de 40 caracteres, blob SHA de su `SKILL.md` y URL inmutable; se conserva metadato de licencia y dependencias o su incertidumbre explícita. En cinco skills de Vercel, la licencia no estaba declarada en el SKILL.md y no se pudo acreditar un LICENSE común del repositorio; **verificar antes de usar o redistribuir**.
- **171 relaciones**, 14 documentadas y 157 propuestas. Se añadieron dos relaciones que reflejan capacidades web complementarias. Las **157 propuestas** permanecen no ejecutables: una fuente `SKILL.md` no demuestra automáticamente la relación propuesta.
- Fuentes fijas también en las conexiones: se corrigieron 45 URL heredadas apuntando a `main`.
- **111 fichas de función de skills** y **41 fichas de nodos de la pizarra** con estructura IDEF0/FBS de carácter **propuesto**; se representan también en RDF/TriG. No están ratificadas, ni constituyen un selector semántico ejecutable.
- Mejor espacio útil en modo grafo: navegador a 320×680 → **461 px** de altura de red; a 390×844 → **625 px**. En 1440×900 → **493 px**. Los filtros móviles se repliegan y el zoom no fuerza una vista ilegible tras redimensionar.
- El contador incluye todas las aristas **dibujadas**; `alimenta` muestra siete enlaces y contador siete.
- Las etiquetas `OUT_OF_DESIGN_SCOPE_PROPOSED` se visualizan como **Exclusión propuesta**, sin inventar aprobación.

## Principios conservados

- **G0** coordina; **G1–G7** deciden en sus dominios según las fuentes del proyecto y permisos humanos. El modelo no concede privilegios a skills externas.
- `S05` (nativo) y `S06` (documental) no quedan habilitadas por un grafo informativo.
- Fuente de una skill, hipótesis de relación, relación documentada, aceptación humana y permiso de ejecución son conceptos distintos.
- El espacio `human_approved` de RDF está vacío deliberadamente.

## Archivos

| Archivo | Función |
|---|---|
| `design-router-pizarra-relaciones-v0.5.html` | Visualización interactiva sin necesidad de servidor para el modo SVG de respaldo |
| `router_skill_relations_v05.json` | Grafo tipado y contratos funcionales versionados |
| `router-skill-relations-v0.5.trig` | Grafo RDF con fuentes, relaciones documentadas/propuestas, funciones y aprobación vacía |
| `design-router-relaciones-skills-v0.5.drawio` | Diagrama editable con nodos/aristas y atributos de evidencia |
| `Auditoria_Design_Skills_Router_Grafo_v0.5.md` | Reauditoría y limitaciones verificadas |
| `router-skillgraph-v05-qa.json` | Pruebas focalizadas funcionales, semánticas y Chromium |
| `router-skillgraph-v05-negative-qa.json` | Validaciones del contrato y diez mutaciones negativas |
| `qa_v05_legacy/regression_v05.log` | Reejecución adaptada de los 35 tests anteriores |
| `build_router_skillgraph_v05.py`, `patch_router_skillgraph_html_v05.py` | Fuentes reproducibles de transformación, basadas en los archivos históricos v0.4 |
| `reaudit_router_skillgraph_v05.py`, `validate_router_skillgraph_v05.py` | Scripts de auditoría independientes del runtime del plugin |

## Validaciones y límites

- 58/58 comprobaciones específicas, 35/35 de regresión y 11/11 de contratos/controles negativos; tienen solapamientos, **no** se suman como 104 evidencias independientes.
- RDF/TriG parseable, XML `.drawio` bien formado; descarga de navegador reproduce los mismos bytes.
- No se verificó importación real en `app.diagrams.net`, motor mxGraph en el HTML, Safari/iOS nativo, lector de pantalla real, asistencia de agentes en host, decisiones humanas o ejecución del router en producción.
- No ejecutar automáticamente ninguna skill ni promover este grafo al baseline. Para cambios normativos, usar nueva versión del baseline y las pruebas/gates del plugin publicados.
