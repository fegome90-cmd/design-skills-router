# Auditoría posterior a los fixes · v0.4

Fecha: 8 de noviembre de 2026. Objeto: `index.html`, fuente canónica, inventario, criterios y expansión por contexto.

## Dictamen

**VISOR: comprobaciones ejecutadas satisfactorias. DISEÑO DEL ROUTER: todavía incompleto para asegurar cobertura universal. RUNTIME: no implementado ni evaluado.**

El resultado no se promueve a plugin. Las confirmaciones humanas permanecen pendientes. Revisión realizada por el mismo agente que reparó el artefacto; no se presenta como evaluación independiente o ciega.

## Pruebas realizadas

- Regresión contra v0.3: 10 de 12 comprobaciones fallaron antes de la reparación; 12 de 12 pasan en v0.4. La v0.3 permanece intacta (SHA-256 original conservado en build-metrics.json).
- Suite del modelo: **25 pruebas**, incluyendo **8 controles negativos**. Detectan autoaprobación, eliminación de una skill, evaluación cruzada de candidatos, escrituras en modo auditoría, pérdida de cobertura, regla inexistente, referencia inexistente y ciclo de plantilla.
- Visor: **72 comprobaciones** en Chromium. Navegación por nodo, teclado, padre, hash, fichas con fuentes, 14 accesos de rama, igualdad entre expansión Python/JavaScript, límites de textos SVG y ausencia de errores de consola.
- Anchuras: 320, 390, 768 y 1440 píxeles CSS, antes y después de expandir. La anchura del documento coincide con la del viewport. Antes del cambio, v0.3 alcanzaba 456 px a 320 y 390 px.
- Se probó una combinación de ajustes de espaciado de texto y un viewport de 720 px como sondeo de reflow. **No es una prueba de zoom real al 200 %.** Se comprobó la preferencia reduced-motion, no una animación externa.
- Los resultados de modelo, regresión y navegador tienen cobertura diferente y parcialmente solapada; no sumar sus cifras como una única tasa de calidad.

## Resultado frente a los hallazgos anteriores

| Hallazgo | Estado | Reparación / límite |
|---|---|---|
| SEM-01: conservar identidad y proyectos existentes perdían cobertura | CORREGIDO ESTRUCTURALMENTE | D00 contiene D01 y D10 como ramas obligatorias. E03/E04/E05/E07 expanden F00 con contexto y permisos propios. No es una prueba de obediencia de un LLM. |
| SEM-02: dirección de arte y microtipografía no descompuestas | CORREGIDO EN EL ALCANCE | ART01–ART05 y TY01–TY03, con criterios y alternativas. No se afirma descomposición exhaustiva de cada frase de todas las skills. |
| SEM-03: cobertura incompleta | PARCIAL | 82 disposiciones explícitas y better-interface asignada. Sólo 24 skills tienen preguntas de diseño asociadas; 18 condicionales no están desarrolladas y 3 pertenecen a otras rutas. |
| SEM-04: medio sólo si faltaba stack | CORREGIDO / RUTAS ESPECIALIZADAS ABIERTAS | ENV00 siempre se revisa. Nativo/documental/gráfico quedan explícitamente bloqueados para no sustituirlos con web. Faltan sus subárboles especializados. |
| SEM-05: evaluación desligada del candidato | CORREGIDO EN LA ESPECIFICACIÓN | Cada candidato expande ADOPT con su candidate_key y contexto. Identidad, versión y requisito son obligatorios. Unknown no equivale a Verified. No hay autoridad de ejecución. |
| SEM-06: capacidades que coexisten como XOR | CORREGIDO | R11 separa lista y arrastre; M03 separa capacidades de movimiento. R01 se aplica a requisitos atómicos de cada componente. |
| SEM-07: trazabilidad demasiado general | PARCIAL | 25 grupos de reglas con categoría, sección y adaptación. La revisión de metadatos y contenido de todas las fuentes no es exhaustiva. |
| UI-01: desbordamiento móvil | CORREGIDO EN CHROMIUM | La indentación ya no se acumula por anidación. Pruebas de expansión a cuatro anchuras. |
| UI-02: abrir ramas sólo mostraba ficha | CORREGIDO | Navegación real de rama, ficha separada y enlaces por ID. |

## Problemas encontrados durante esta reparación

### P1 · Cobertura de conocimiento todavía parcial

Hay 24 skills vinculadas a preguntas; 18 condicionales sin desarrollo, 3 de rutas especializadas, 14 referencias de gobernanza y 23 exclusiones propuestas. **Disposición visible no equivale a integración ni justifica automáticamente excluir una skill.** Las razones heredadas de algunas exclusiones son genéricas y sus contratos deben revisarse antes de ratificarlas. Las filas están visibles y pendientes, no ocultas ni aprobadas.

### P1 · Aplicabilidad aún no completamente formalizada

El modelo conserva condiciones expresadas en lenguaje natural y ámbitos `context-dependent`. Esto sirve para discutir el árbol, pero todavía no determina por sí solo qué subconjunto de criterios es obligatorio para cada encargo. Antes de activar un router habrá que traducir esos criterios a condiciones comprobables, resolver solapamientos y conservar la decisión humana. No debe afirmarse que este HTML garantiza que un agente no omita trabajo.

### P1 · Rutas especializadas y contratos de invocación pendientes

Nativo, documentos, presentaciones y gráfica no tienen el mismo detalle que UI web. Además, el inventario conserva estados de metadatos por revalidar, incluidos contratos de invocación explícita. Los pins son los heredados de la investigación, no una comparación completa con main actual. Si el encargo activa una capacidad pendiente, la salida correcta es bloqueo explícito, no una solución web sustituta.

### P2 · Expansión global excesivamente larga

La fuente comparte definiciones, pero materializa 3.660 instancias al desplegar toda la raíz: a 390 px la prueba registró una altura de documento de **824.360 px** y 32.520 elementos DOM. No produce desbordamiento horizontal, pero resulta poco práctica para lectura global. La navegación por rama evita esa lectura masiva. Queda pendiente decidir si se elimina la expansión global o se limita con una confirmación específica; no se ocultan ramas silenciosamente.

### Incidencias adicionales ya corregidas

La primera proyección v0.4 dejaba la raíz fuera del área visible del diagrama en tamaños estrechos. Se cambió a un nivel por vista, raíz anclada arriba y navegación explícita para profundizar. Se detectó además recorte de una etiqueta superior de dos líneas; se aumentó el margen y se comprobaron los límites de textos SVG. El subcatálogo de capacidades estaba inicialmente tipado como “todas”; se corrigió a una decisión por requisito atómico para no exigir adoptar todo el catálogo.

## Límites y entorno

Browser conectado sólo expone lectura de pestañas en este chat; no se usó el navegador personal. Pruebas con Playwright y Chromium ya instalados en el contenedor, utilizando el contenido exacto del HTML. `file://` fue rechazado por política del navegador; no se desactivó ni se alteró. La carga de HTML provisto mediante `set_content` permite probar el render, pero **no acredita apertura directa del archivo en el dispositivo de Felipe**.

No se probaron Safari/iOS real, lectores de pantalla, zoom real 200 %, Firefox, persistencia de decisiones, ejecución de agentes, admisión/instalación de skills ni todos los enlaces externos. No se ejecutaron las librerías de componentes mencionadas por el catálogo. No se modificaron GitHub, Library ni un plugin existente.

## Fuentes de investigación utilizadas

- `my-skills`, pin 5211aae8843eca4966d2aee828513582a04a7c8f: contratos del orquestador, arte, tipografía, color, layout, tokens y handoff recuperados en la conversación; nueva lectura del contrato y microtipografía en esta reparación.
- `emilkowalski/skills`, pin 5206a950b715e0cabe7043ea0b2304332b91494e: catálogo y revisión de movimiento, según fuentes recuperadas y guía en Library.
- `jakubkrehel/skills`, pin 157da62016338e8693dcff93d47154a9e36f2157: better-interface revisada de nuevo; responsabilidades de dominios contrastadas con la investigación.
- Library: `sistema-skills-diseno-revision-y-arquitectura.md` y `guia-pick-ui-library-y-12-herramientas.md`.

El mapa de secciones identifica una adaptación de trabajo. Las reglas locales están etiquetadas router-policy; no se atribuyen a los autores externos. No se presentan heurísticas como normas universales.
