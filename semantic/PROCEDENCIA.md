# Fuentes de investigación y formatos editables

Las versiones de esta carpeta describen capas de investigación del Design Skills Router. El plugin 0.3.1 y su árbol canónico 0.4 se distribuyen por separado. La pizarra v1.3 incluye las vistas de investigación, la simulación de selección v1.2 y el mapa del código del plugin. El plan MCP vigente es `Plan_MCP_Design_Router.md` y se conserva con la documentación principal del proyecto.

| Capa | Uso |
| --- | --- |
| Auditoría semántica de la pizarra v0.3 | Antecedente de los cambios v0.6. Conserva decisiones y riesgos documentales de ese momento. |
| Relaciones v0.5 | Última red editable de relaciones y fichas funcionales identificada en la carpeta del proyecto. TriG y draw.io sirven para inspeccionar y editar este modelo de investigación. |
| Cambios propuestos v0.6 | 15 expedientes de remediación organizados en seis etapas. Sirven para consultar pendientes y su contexto. |
| Mapa funcional v1.0 | Catálogo de 28 funciones y 47 skills usado en la pizarra posterior. El CSV y el informe aportan formatos para consulta y revisión. |

## Datos editables ubicados en la pizarra

Los siguientes objetos JSON se compararon con el HTML v1.3 y son estructuralmente idénticos. Se mantienen en el código fuente de la pizarra.

| Archivo original | Datos en `board/src/` | ID en el HTML |
| --- | --- | --- |
| `router_skill_relations_v05.json` | `board/src/relaciones/datos.json` | `semanticDataset` |
| `design-router-cambios-propuestos-v0.6.json` | `board/src/propuestas/datos.json` | `changeBoardData` |
| `design-router-mapa-funcional-v1.0.json` | `board/src/mapa-funcional/datos.json` | `capabilityMapData` |

La exportación draw.io v0.6 conserva los mismos bytes que el XML de `changeDrawioData`. El archivo se incluye para abrirlo directamente en un editor de diagramas.

## Validaciones

- TriG v0.5 parseado en modo estricto con Serd. Tiene 5.437 declaraciones, 782 en el catálogo, 4.508 en propuestas y 147 en relaciones documentadas. El grafo de aprobación humana quedó sin declaraciones.
- XML draw.io válido en ambos archivos. Relaciones v0.5 tiene 289 celdas mxGraph y cambios v0.6 tiene 50. Quedó fuera de esta revisión la importación a diagrams.net.
- JSON de auditoría válido, con 47 registros, y CSV válido, con 83 filas de datos. Los archivos seleccionados referidos en los manifiestos de v0.5 y v1.0 coincidieron con sus hashes originales.
- Estas comprobaciones cubren los archivos y su consistencia, sin validar activación del plugin ni criterios de calidad de un diseño.

## Procedencia

Salvo los dos archivos de auditoría v0.3, que estaban en la raíz, las fuentes corresponden a la carpeta `Design Systems/Tooling/Design_Skills_Router`.

| Archivo | Descripción | Fuente | SHA-256 |
| --- | --- | --- | --- |
| `auditoria-v0.3/design-router-auditoria-semantica-v0.3.md` | Hallazgos P1-01–P1-07 y justificación de los 47 registros. Referencia directa de las propuestas v0.6. | [v0](https://chatgpt.com/library?file_id=libfile_fde3_f-a629f5162244819195f92b9890dc1ef2_11107b86ea008191bab113dfcc32deba&account_id=personal) | `c39bd249e6486ee79500e754a7805d432648975a5f0811400f386537ff11a938` |
| `auditoria-v0.3/design-router-auditoria-semantica-v0.3-matriz.json` | Matriz semántica de 47 registros y 14 comprobaciones estructurales. | [v0](https://chatgpt.com/library?file_id=libfile_fde3_f-788f63bd03e08191bcd43abda0669972_11107b86ea008191bab113dfcc32deba&account_id=personal) | `46a6f8a4a1f1fe7df95cb68a6cfcf8ac9e9637dd2ee5567f90ddca0b1228c94b` |
| `relaciones-v0.5/router-skill-relations-v0.5.trig` | Grafo RDF/TriG editable de investigación y procedencia. | [v0](https://chatgpt.com/library?file_id=libfile_fde3_f-b4f32397252c819196219302ac06977f_11107b86ea008191bab113dfcc32deba&account_id=personal) | `7637f8e25ea117c237aa4338e8bf9f4976116034b36234a76c683a733db04c45` |
| `relaciones-v0.5/design-router-relaciones-skills-v0.5.drawio` | Diagrama editable de relaciones entre skills. | [v0](https://chatgpt.com/library?file_id=libfile_fde3_f-d835ee33d9f08191a2d292c9e4c86aa4_11107b86ea008191bab113dfcc32deba&account_id=personal) | `2127ea99c82b6d15da6730f17dc849f4b12fdb489076d4dbf807e8e9f626011c` |
| `relaciones-v0.5/Design_Skills_Router_Relaciones_v0.5_README.md` | Modelo y límites de la red funcional. | [v0](https://chatgpt.com/library?file_id=libfile_fde3_f-9331b157e0f4819196a0d1bf993b53ad_11107b86ea008191bab113dfcc32deba&account_id=personal) | `f4ab0b6e78841d6af4c8e1c220dfd67898806cff1877f37f52e628d98d669e46` |
| `relaciones-v0.5/Auditoria_Design_Skills_Router_Grafo_v0.5_2026-11-17.md` | Alcance y hallazgos de la reauditoría v0.5. | [v0](https://chatgpt.com/library?file_id=libfile_fde3_f-e9b0ffe8ee808191abde0bea2e1a5a05_11107b86ea008191bab113dfcc32deba&account_id=personal) | `145efadaf2b643794c2b01d13ced488bd0130d4d499c611af5d250a89295b1e8` |
| `propuestas-v0.6/design-router-cambios-propuestos-v0.6.drawio` | Diagrama editable de las seis capas de propuestas. | [v0](https://chatgpt.com/library?file_id=libfile_fde3_f-b03c1e9327ec819192372e23071c9d96_11107b86ea008191bab113dfcc32deba&account_id=personal) | `67831aca584a13bc2bb9531acfa36ef926361d3f09e7f6f79cae31b9800ad81c` |
| `propuestas-v0.6/Design_Router_Cambios_Propuestos_v0.6_README.md` | Interpretación de los 15 expedientes y su frontera de autoridad. | [v0](https://chatgpt.com/library?file_id=libfile_fde3_f-a8d7d7dc73fc8191b3ac8b5fff61f029_11107b86ea008191bab113dfcc32deba&account_id=personal) | `336fbeecaded02b2281c93e77c35446a8b86ae8a575ccea060a274dc4bb3319c` |
| `mapa-funcional-v1.0/design-router-mapa-funcional-v1.0.csv` | 83 contribuciones de 47 skills sobre 28 funciones, ordenables en una planilla. | [v0](https://chatgpt.com/library?file_id=libfile_fde3_f-25f738f575788191a152cf69eb0307ea_11107b86ea008191bab113dfcc32deba&account_id=personal) | `cf9cdc252ae79db14bce18714aae21521101992488923342d0512582cddc15d9` |
| `mapa-funcional-v1.0/design-router-mapa-funcional-v1.0-informe.md` | Directorio y matriz funcional documentada, con criterio de alcance y límites. | [v0](https://chatgpt.com/library?file_id=libfile_fde3_f-d9c11f3b806c8191957d68d220a03608_11107b86ea008191bab113dfcc32deba&account_id=personal) | `e5a3205fabdca2a10a0cb5d6e31e7aeb030ed67c0cfde4a3e9a2498c66ad6a04` |
