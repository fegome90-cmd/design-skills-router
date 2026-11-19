# Auditoría semántica · Design Skills Router / pizarra v0.3
**Fecha:** 17 de noviembre de 2026  ·  **Alcance:** 47 fichas externas de diez repositorios.  ·  **Modo:** auditoría documental de solo lectura.  ·  **Estado:** propuesta, no ejecución.

## Dictamen
**NO APTO para transformar el mapeo visual v0.3 directamente en reglas automáticas del plugin.** Sí es un inventario válido de hipótesis de ubicación con fuentes recuperadas. Las skills G0–G7 de `fegome90-cmd/my-skills` conservan la rectoría metodológica; el árbol v0.4 y los gates del host conservan la autoridad de decisión y autorización. Las externas son apoyos; consultar una skill no otorga permiso para ejecutarla.

**Resultado por relación:** 47 examinadas; 15 conservables con su alcance; 8 requieren condiciones corregidas; 9 requieren reubicación; 5 necesitan separar subfunciones; 7 deben seguir diferidas; 3 son meta-ruteadores que no deben incorporarse como decisiones propias. 15 observaciones prioritarias, 16 moderadas y 16 sin objeción en la posición funcional propuesta. Estas cifras son una *clasificación de auditoría*, no tasa de efectividad ni pruebas de agentes.

**Procedencia:** 18 skills de Emil ya constaban entre las 82 referencias; 29 candidatos adicionales. El plugin publicado comprobado por lectura de metadatos es **0.3.1** (`pluginrel_6af336537e808191831d72799b60bf4b`), no la versión de la pizarra.

## Hallazgos que impiden promocionar el mapa

### P1-01 — No existe contrato ejecutable de autoridad y elegibilidad para estos 47 enlaces
La ubicación gráfica define `owner`, `anchor` y `target` como cadenas, pero no demuestra aplicabilidad, permisos, exclusiones o reglas de precedencia en el runtime. El `contracts.json` publicado solo contiene relaciones suplementarias de la revisión `better-interface`, no estos 47 contratos. **No copiar las 47 fichas directamente** al contrato canónico.
### P1-02 — Clasificación por capa confunde consulta, implementación y verificación
Los cuadros X32, X35, X36, X41 y X42 describen *implementación/escritura*, pero aparecen en «Validación». X34 es exploración sin escritura y X40 es un glosario. La etapa visual no sustituye los permisos ni la semántica del nodo M01/M02/M03/MOV02/MOV04.
### P1-03 — Inventario heredado contradice descripciones de dos skills web
`mobile-native` trata fricciones de **sitios web vistos en el teléfono**; `apple-design` aplica criterios de Apple *a la web*. La clasificación del baseline puede relacionarlas con `S05` nativo bloqueado. Separar capacidad web (G5/G7, G3 cuando aplique) de la ruta nativa `S05`, que **permanece bloqueada**. Para cambiar el árbol se necesita versión nueva del baseline, no un override silencioso.
### P1-04 — Riesgo de doble orquestación y de sobrescritura de sistema visual
X02 Impeccable tiene múltiples comandos e inicialización con launcher y hooks; X06 UI UX Pro Max contempla generación/persistencia del sistema; X16 Uizze UI Design contiene su propio selector de workflows. Consultar una especialidad sí; activar el workflow completo sin gate puede competir con G0 y sustituir decisiones existentes de G1–G7.
### P1-05 — Infraestructura, publicaciones y credenciales fuera del flujo visual
X07, X08 y X33 son servicios de deploy/CLI/costes, no validación estética. Mantener como diferidos, fuera de QA01, con autoridad externa propia. X09–X12 pertenecen a rutas nativas/documentales aún sin contrato.
### P1-06 — Manual invocation, permisos de escritura y aprendizaje
`ask-emil`, `prototype`, `pick-ui-library`, `review-animations`, `learn-taste` declaran `disable-model-invocation: true`. Los constructores y herramientas adversariales requieren escritura autorizada incluso cuando se vean dentro de una auditoría. `learn-taste` necesita correcciones expresas del usuario y aprobación *antes* de escribir reglas; no instalar ni autopromocionar.
### P1-07 — Evidencia de procedencia insuficiente para reproducir contratos nuevos
Las 47 fichas enlazan a `blob/main`. Esta auditoría contrastó los SKILL.md actuales y registró su **Git blob SHA**; eso permite identificar bytes, **no fija por sí solo el commit de procedencia ni revisa dependencias/scripts auxiliares**. Los 18 del baseline conservan un commit heredado; los 29 candidatos nuevos necesitan pin, licencia, dependencias y revisión de seguridad antes de pasar a una rama canónica.

## Matriz de las 47 decisiones
La columna «Nodos propuestos» usa IDs del árbol canónico donde existen; G0–G7 son roles rectores de `my-skills`, no IDs del JSON canónico. Una relación propuesta no es una delegación demostrada.

| ID | Skill | Resolución | Prioridad | Nodos propuestos | Criterio de auditoría |
|---|---|---|---|---|---|
| X01 | [uizze-ui](https://github.com/uizze/uizze/blob/main/skills/uizze-ui/SKILL.md) | Excluir de la ejecución | OK | Q00 | Envoltorio Uizze duplica el enrutamiento. Mantener solo como documentación de catálogo. |
| X02 | [impeccable](https://github.com/pbakaus/impeccable/blob/main/skill/SKILL.src.md) | Descomponer por subfunción | P1 | P01, ART01, TY01, K01, L01, V01, M01, QA01 | 23 comandos con context launcher binario y hooks. No delegar gobierno ni ejecutar setup automáticamente; mapear cada comando. |
| X03 | [ask-emil](https://github.com/emilkowalski/skills/blob/main/skills/ask-emil/SKILL.md) | Excluir de la ejecución | OK | GOV00 | Ask Emil enruta skills de su propio repositorio; compite con G0 y es de invocación explícita. |
| X04 | [design](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/blob/main/.claude/skills/design/SKILL.md) | Excluir de la ejecución | OK | GOV00 | Design agrega múltiples subskills y formatos; no permitir segundo router ni apertura de rutas ajenas. |
| X05 | [ui-radar](https://github.com/uizze/uizze/blob/main/skills/ui-radar/SKILL.md) | Corregir condiciones | P2 | ART01, ART05 | Consulta útil de patrones. Quitar máximo arbitrario de 3; las referencias mínimas provienen del contrato local de diseño, no del autor. |
| X06 | [ui-ux-pro-max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/blob/main/.claude/skills/ui-ux-pro-max/SKILL.md) | Descomponer por subfunción | P1 | ART01, T01, TY01, K01, L01, V01 | Usar consultas específicas por dominio. El modo de generación/persistencia de design-system no tiene autoridad para reemplazar G1–G7. |
| X07 | [deploy-to-vercel](https://github.com/vercel-labs/agent-skills/blob/main/skills/deploy-to-vercel/SKILL.md) | Mantener diferida | OK | ENV02 | Despliegue Vercel fuera de ruta de diseño; requiere permiso de publicación independiente. |
| X08 | [vercel-cli-with-tokens](https://github.com/vercel-labs/agent-skills/blob/main/skills/vercel-cli-with-tokens/SKILL.md) | Mantener diferida | OK | ENV02 | CLI con tokens y cambios de entorno ajenos a auditoría visual; nunca tomar credenciales del router. |
| X09 | [react-native-skills](https://github.com/vercel-labs/agent-skills/blob/main/skills/react-native-skills/SKILL.md) | Mantener diferida | P2 | S05 | React Native es nativo; S05 no desarrollado. G0 coordina bloqueo, no asume diseño nativo. |
| X10 | [animate-expo](https://github.com/emilkowalski/skills/blob/main/skills/animate-expo/SKILL.md) | Mantener diferida | P2 | S05 | Animate Expo usa Reanimated y APIs nativas. No activar M03 web por similitud nominal. |
| X11 | [write-swift](https://github.com/emilkowalski/skills/blob/main/skills/write-swift/SKILL.md) | Mantener diferida | P2 | S05 | Write Swift es lenguaje de implementación nativo; no pertenece al núcleo G0. |
| X12 | [slides](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/blob/main/.claude/skills/slides/SKILL.md) | Mantener diferida | P2 | S06 | Slides requeriría contrato editorial/presentaciones; no habilita por sí sola S06. |
| X13 | [frontend-design](https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md) | Conservar con límites | OK | D07, ART01 | Consulta de dirección visual solo para identidad nueva o rediseño expresamente autorizado. |
| X14 | [design-taste-frontend](https://github.com/Leonxlnx/taste-skill/blob/main/skills/taste-skill/SKILL.md) | Conservar con límites | P2 | ART02, ART03 | Taste impone reglas de maquetación/animación fuertes; permitir solo si compatibles con producto e identidad y con escritura autorizada. |
| X15 | [hallmark](https://github.com/Nutlope/hallmark/blob/main/skills/hallmark/SKILL.md) | Conservar con límites | P2 | D07, ART05 | Hallmark restringe proyectos existentes salvo invocación explícita; no aceptar tema aleatorio sobre marca cerrada. |
| X16 | [ui-design](https://github.com/uizze/uizze/blob/main/skills/ui-design/SKILL.md) | Descomponer por subfunción | P2 | ART01, L01 | UI Design tiene workflows propios. Consultar playbook acotado, no activar segunda orquestación ni sustituir tokens. |
| X17 | [image-to-ui](https://github.com/uizze/uizze/blob/main/skills/image-to-ui/SKILL.md) | Conservar con límites | OK | LAY01, ART05 | Image to UI aplica a fidelidad 1:1 con imagen de referencia; requiere render comparativo, no rediseño libre. |
| X18 | [brand](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/blob/main/.claude/skills/brand/SKILL.md) | Conservar con límites | P2 | D01, ART01 | Brand consulta identidad y voz; no modificar marca autorizada por regla externa. |
| X19 | [banner-design](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/blob/main/.claude/skills/banner-design/SKILL.md) | Descomponer por subfunción | P2 | ART02, S06 | Hero web puede evaluarse en ART02; formatos de banner/print deben usar ruta especializada, hoy bloqueada. |
| X20 | [prototype](https://github.com/emilkowalski/skills/blob/main/skills/prototype/SKILL.md) | Conservar con límites | OK | ART05 | Prototype exige invocación explícita, comparación con mismo contenido y autorización para crear variantes. |
| X21 | [mobile-native](https://github.com/emilkowalski/skills/blob/main/skills/mobile-native/SKILL.md) | Corregir condiciones | P1 | LAY01, M03 | Mobile-native trata web en teléfonos. El baseline la clasifica junto a S05 nativo: conflicto de ámbito que requiere baseline nuevo. |
| X22 | [composition-patterns](https://github.com/vercel-labs/agent-skills/blob/main/skills/composition-patterns/SKILL.md) | Conservar con límites | OK | V01, RC01 | Composition Patterns solo en React y para API de componentes en alcance. |
| X23 | [design-system](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/blob/main/.claude/skills/design-system/SKILL.md) | Conservar con límites | P2 | V01 | Design System de Pro Max usa otra convención de capas; G6 decide arquitectura y compatibilidad DTCG local. |
| X24 | [ui-styling](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/blob/main/.claude/skills/ui-styling/SKILL.md) | Corregir condiciones | P2 | RC01, R01 | UI Styling presupone shadcn/Radix/Tailwind; bloquear cambio de stack y verificar Base UI o el incumbente. |
| X25 | [pick-ui-library](https://github.com/emilkowalski/skills/blob/main/skills/pick-ui-library/SKILL.md) | Conservar con límites | OK | R01, A10 | Pick UI Library ya inventariada y sujeta a invocación explícita. Toda opción pasa ADOPT por candidato. |
| X26 | [ask-sonner](https://github.com/emilkowalski/skills/blob/main/skills/ask-sonner/SKILL.md) | Conservar con límites | OK | R02, A10 | Ask Sonner después de decidir Sonner por contrato; no equivale a permiso para instalarlo. |
| X27 | [stageshow](https://github.com/benjitaylor/skills/blob/main/stageshow/SKILL.md) | Reubicar | P1 | ART02 | Stageshow crea escenas de producto ficticias; nunca validar funcionamiento real. Quitar anclaje IMPLEMENT de G6. |
| X28 | [anti-ui-slop](https://github.com/uizze/uizze/blob/main/skills/anti-ui-slop/SKILL.md) | Corregir condiciones | P2 | QA01 | Anti UI Slop es un control complementario. No imponer estética universal ni activar MCP/credenciales sin permiso. |
| X29 | [make-interfaces-feel-better](https://github.com/jakubkrehel/make-interfaces-feel-better/blob/main/skills/make-interfaces-feel-better/SKILL.md) | Descomponer por subfunción | P2 | TY02, V01, QA01 | Jakub reúne tipografía, superficies, iconos y motion; la propiedad decisoria sigue en cada G especialista. |
| X30 | [web-design-guidelines](https://github.com/vercel-labs/agent-skills/blob/main/skills/web-design-guidelines/SKILL.md) | Corregir condiciones | P1 | AC01, QA01 | Web Design Guidelines descarga reglas actuales. Fijar contenido/fecha/hash antes de comparar; file:line no certifica accesibilidad. |
| X31 | [react-best-practices](https://github.com/vercel-labs/agent-skills/blob/main/skills/react-best-practices/SKILL.md) | Conservar con límites | OK | V01, QA01 | React Best Practices solo optimiza código React/Next; no gobierna dirección estética ni exige Next.js. |
| X32 | [react-view-transitions](https://github.com/vercel-labs/agent-skills/blob/main/skills/react-view-transitions/SKILL.md) | Reubicar | P1 | M03, MOV01, MOV04 | React View Transitions construye movimiento. El trigger es necesidad/soporte, no un audit de QA genérico. |
| X33 | [vercel-optimize](https://github.com/vercel-labs/agent-skills/blob/main/skills/vercel-optimize/SKILL.md) | Mantener diferida | P1 | ENV02 | Vercel Optimize mide costes/caché en deploy. No clasificar como QA01 de interfaz visual. |
| X34 | [find-animation-opportunities](https://github.com/emilkowalski/skills/blob/main/skills/find-animation-opportunities/SKILL.md) | Reubicar | P2 | M01 | Find Animation Opportunities es exploración previa y no modifica código; no colocarlo como test de aceptación. |
| X35 | [remove-animations](https://github.com/emilkowalski/skills/blob/main/skills/remove-animations/SKILL.md) | Reubicar | P1 | M02 | Remove Animations edita código. En modo auditoría solo propuesta, nunca ejecutar por QA01. |
| X36 | [animate](https://github.com/emilkowalski/skills/blob/main/skills/animate/SKILL.md) | Reubicar | P1 | M03 | Animate construye transiciones. Condicionar a M01 afirmativo, intervención autorizada y alternativas reduced-motion. |
| X37 | [review-animations](https://github.com/emilkowalski/skills/blob/main/skills/review-animations/SKILL.md) | Conservar con límites | OK | MOV04, QA01 | Review Animations es revisión; invocación explícita y resultados con evidencia. |
| X38 | [improve-animations](https://github.com/emilkowalski/skills/blob/main/skills/improve-animations/SKILL.md) | Conservar con límites | OK | MOV04, QA01 | Improve Animations es auditoría y planes read-only; la ejecución posterior es otra acción. |
| X39 | [animation-performance](https://github.com/emilkowalski/skills/blob/main/skills/animation-performance/SKILL.md) | Conservar con límites | OK | MOV04, QA01 | Diagnóstico de jank con métricas si las hay; no inferir FPS de recetas. |
| X40 | [animation-vocabulary](https://github.com/emilkowalski/skills/blob/main/skills/animation-vocabulary/SKILL.md) | Reubicar | P2 | M03 | Animation Vocabulary solo traduce términos; es referencia consultiva, no prueba de QA. |
| X41 | [choreograph](https://github.com/emilkowalski/skills/blob/main/skills/choreograph/SKILL.md) | Reubicar | P1 | M03 | Choreograph coordina movimientos y puede cambiar implementación; requiere gate de escritura. |
| X42 | [gestures](https://github.com/emilkowalski/skills/blob/main/skills/gestures/SKILL.md) | Reubicar | P1 | MOV02, M03 | Gestures construye drag/swipe/hold; no disparar como validación read-only. |
| X43 | [apple-design](https://github.com/emilkowalski/skills/blob/main/skills/apple-design/SKILL.md) | Corregir condiciones | P1 | M03, TY02 | Apple Design traduce principios al navegador; baseline la clasifica como nativa. No habilita S05; G3 decide tipografía. |
| X44 | [emil-design-eng](https://github.com/emilkowalski/skills/blob/main/skills/emil-design-eng/SKILL.md) | Conservar con límites | OK | M03, QA01 | Emil Design Eng es respaldo cuando no existe skill de motion más específica, no agente rector. |
| X45 | [break-ui](https://github.com/emilkowalski/skills/blob/main/skills/break-ui/SKILL.md) | Corregir condiciones | P1 | LAY01, QA01 | Break UI puede crear toggle y fixtures adversariales: solo sandbox autorizado; no editar producción en auditoría. |
| X46 | [learn-taste](https://github.com/emilkowalski/skills/blob/main/skills/learn-taste/SKILL.md) | Corregir condiciones | P1 | QA01 | Learn Taste requiere invocación explícita, correcciones reales y aprobación de cada regla; sin autopromoción. |
| X47 | [writing-guidelines](https://github.com/vercel-labs/agent-skills/blob/main/skills/writing-guidelines/SKILL.md) | Reubicar | P1 | C01, S06, WR01 | Writing Guidelines revisa documentación/prosa, no aprendizaje de diseño. S06 bloqueada para documentos autónomos. |

## Reglas de precedencia sugeridas — NO adoptadas
1. El proyecto y el usuario fijan el brief, la identidad y las decisiones de stack. G0 elige el modo mínimo y consulta la fuente rectora antes de coordinar G1–G7.
2. Los siete especialistas de `my-skills` deciden sus propios criterios; ningún autor externo puede sobrescribir tokens, tipografía, color, movimiento o componentes existentes por defecto.
3. Las skills de investigación son lectores; las de implementación requieren alcance de escritura y fase correspondiente; las de QA pueden documentar hallazgos sin permiso implícito de corregir.
4. Toda nueva biblioteca entra por R01/A10/ADOPT con identidad de candidato, seis ejes, evidencias, licencia y revisión humana. Una sugerencia no es adopción.
5. `S05` y `S06` siguen bloqueadas hasta diseñar subárbol especializado; deploy, costes, credenciales y publicación requieren su propio permiso.
6. Cualquier nuevo contrato con impacto sobre versiones/pins o criterio canónico requiere baseline nuevo, pruebas negativas y aprobación humana del diff; el release publicado no cambia automáticamente.

## Pruebas semánticas propuestas para host / negativas
| Caso | Input | Resultado esperado |
|---|---|---|
| A01 | Proyecto existente, ajustar tipografía solamente | G0 modo ligero → G2/G3; no ejecutar Impeccable global, no abrir todas las fases |
| A02 | Pantalla con identidad y Base UI autorizadas | Conservar stack y tokens; no reemplazar por shadcn/Radix vía ui-styling |
| A03 | Proyecto web móvil con barra de dirección causando saltos | G5/LAY01 puede consultar mobile-native; S05 nativo sigue bloqueada |
| A04 | Solicitar una animación de ruta en React | M01 decide si existe justificación; M03 podría consultar view-transitions con permiso de edición, no QA01 como auto-implementación |
| A05 | Auditar motion con código sin permiso de corrección | review/improve son solo lectura; remove-animations y animate quedan bloqueadas para escritura |
| A06 | Pedir publicar el producto tras auditoría | Frena y requiere permiso independiente; no activar deploy-to-vercel desde QA01 |
| A07 | Pedir presentación HTML utilizando slides | S06 continúa sin contrato; no autohabilitar por existencia de skill externa |
| A08 | Captura fuente con petición de clonación 1:1 | G5/LAY01 image-to-ui con render comparativo y control de licencia/activos |
| A09 | Feedback del usuario “menos movimiento” | Proponer regla específica; learn-taste no escribe sin invocación y aprobación del texto y la razón |
| A10 | No hay navegación a CDN o reglamento cambió | Vercel web-design-guidelines = fuente no disponible/no fijada; QA no se marca PASS |
| A11 | UI de datos clínicos con deseo de Hallmark | G1 evalúa intención; no aplicar tema aleatorio ni cambiar identidad aprobada por defecto |
| A12 | Faltan implementaciones de una skill referida | Conservar faltante como NotReviewed; nunca instalarla silenciosamente |

**Estado de ejecución de A01–A12:** escenarios especificados para futura prueba con un agente; NO ejecutados en host. Los checks estructurales siguientes no los sustituyen.

## Comprobaciones estructurales ejecutadas hoy
- PASS: 47 relationships unique.
- PASS: all source refs have observed blob fingerprints.
- PASS: no mapped proposed node outside canonical.
- PASS: original immutable tree hash intact.
- PASS: 18 Emil existing entries not double-counted.
- PASS: excluded meta-routers not auto promoted.
- PASS: native paths remain deferred.
- PASS: publication and credentials remain outside design.
- PASS: web mobile not equated to native.
- PASS: implementers not left in validation.
- PASS: manual-invocation original guards retained.
- PASS: learning cannot auto write.
- PASS: documentation guidelines not misclassified as learning.
- PASS: auto routing stays blocked for all proposals.

**Alcance de la verificación:** lectura de fuentes y comparación contra JSON/ZIP de la pizarra v0.3; la revisión es semántica documental realizada por el mismo agente. No prueba obediencia de otro modelo, importación a draw.io, seguridad de dependencias, accesibilidad, ni ejecución del router.

## Siguiente cambio técnico propuesto
Crear una copia candidata del contrato de **v0.4**, separando los tipos de relación (`consulta`, `sugiere`, `implementa`, `verifica`, `bloquea`, `solicita_aprobacion`) y los criterios de elegibilidad (ámbito, plataforma, fase, permisos, invocación, versión). No modificar `tree-v0.4` ni `contracts.json` original hasta contar con pins y pruebas de rutas negativas. El cierre de auditoría **no** autoriza integración ni publicación.

## Huellas de insumos
- `router_skillmap_v03.json`: `82929b1b4871af726eb9ec0f792cfe3db069e66534a04e27c1add15282797f4f`
- `design-decision-tree-v0.4/tree.json`: `0cf76c1833d7aec023a3f939924af11e3caa7ff837ada1d208f6453f1e22a793`
- `my-skills/design-process-orchestrator/SKILL.md`: Git blob `da3b575b0bbaed6ab76c67e46b301f420abacaf7`.
- `my-skills/design-process-orchestrator/references/execution-contracts.md`: Git blob `6614e47019a102ae19086bcd0059804ef8fef21d`.
- `my-skills/authority-flow-audit/SKILL.md`: Git blob `6b1cc4a6ea5116430012c4a697988bb374866a36`.
- `my-skills/skill-vetting/SKILL.md`: Git blob `8e189051cf9a105374e8a26901a441626e89032b`.
- Todas las demás huellas Git blob por skill, enlace y disposición están en la matriz JSON adjunta.

## Contratos sintéticos adicionales (ejecutados)

- **10/10 pruebas PASS** mediante `test_router_semantic_audit_v03.py`, sobre coherencia de matrices y mutaciones negativas explícitas.
- Escenarios negativos cubiertos: enrutamiento automático por error, web móvil marcada nativa (dos casos), deploy habilitado como diseño, invocación explícita omitida, constructor de motion colocado en QA, demo ficticia con dueño incorrecto, documentación tratada como aprendizaje y metarruteador externo promocionado.
- **Limitación:** estas son pruebas del *registro corregido y de su validador*, no simulaciones de decisiones de un agente independiente. No demuestran satisfacción de WCAG ni compatibilidad de las dependencias originales.
- Insumos confirmados sin alteración: HTML v0.3 SHA256 `7d88d46e1358a2000f9c5b82e684ae14e063d3d38ad24d59c767c858047761c0`, draw.io SHA256 `22ec886e283b82e5b2a05648b8670088e3c5f61b39cd0161731a312e83bc044d`, matriz origen SHA256 `82929b1b4871af726eb9ec0f792cfe3db069e66534a04e27c1add15282797f4f`.
