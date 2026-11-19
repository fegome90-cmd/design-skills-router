# Mapa funcional · Design Skills Router v1.0

**Dictamen:** el árbol v0.4 ya organiza ámbitos tipografía, color, layout, tokens, motion y revisión. El plugin 0.3.1 propone las fuentes en esos nodos; no ejecuta skills automáticamente.

El piloto por paquetes de cuatro skills no debe sustituir el enrutamiento por necesidad. Las 47 propuestas se modelan como fuentes de **funciones atómicas**; una skill puede aportar más de una, y varias skills pueden aportar una misma función.

## Ejemplo tipografía

G0 (ligero) → G2 (T01,T02,T06) y G3 (TY01,TY02,TY03) → Jakub better-typography ya inventariada, si aplica → consulta UI UX Pro Max / impecable typeset solo cuando aporta evidencia o implementación autorizada. No ejecutar todas las 82 fuentes.

## Directorio de funciones

| Función | Autoridad posible | Nodos | Skills candidatas |
|---|---|---|---|
| Metaenrutadores externos | Fuera | GOV00 | ask-emil, design, uizze-ui |
| Investigar referencias de interfaces | G1, G5, G6 | ART01, L01, R01 | anti-ui-slop, ui-design, ui-radar, ui-ux-pro-max |
| Dirección de arte y concepto | G1 | D07, ART01, ART05 | banner-design, design-taste-frontend, frontend-design, hallmark, impeccable, ui-ux-pro-max |
| Identidad y voz de marca | G1 | D01, ART01 | brand |
| Elección y emparejamiento tipográfico | G2 | T01, T02, T06 | ui-design, ui-ux-pro-max |
| Escala y microtipografía | G3 | TY01, TY02, TY03 | apple-design, impeccable, make-interfaces-feel-better, ui-ux-pro-max |
| Paleta, roles y contraste | G4 | K01, K02 | impeccable, ui-design, ui-ux-pro-max |
| Grillas, jerarquía y densidad | G5 | L01, LAY01 | design-taste-frontend, impeccable, ui-design, ui-ux-pro-max |
| Ergonomía web en teléfonos | G5, G7 | LAY01, MOV04 | apple-design, mobile-native |
| Tokens y sistema de diseño | G6 | V01 | design-system, impeccable, ui-ux-pro-max |
| API de componentes y detalles | G6 | V01, RC01, R01 | ask-sonner, composition-patterns, emil-design-eng, make-interfaces-feel-better, react-best-practices, ui-design, ui-styling, ui-ux-pro-max |
| Selección/adopción de bibliotecas | G6 | R01, A10 | pick-ui-library |
| Prototipos de alternativas | G1, G5 | ART05 | prototype |
| Implementación fiel a captura | G5 | LAY01, ART05 | image-to-ui |
| Decidir si debe haber movimiento | G7 | M01 | animation-vocabulary, apple-design, find-animation-opportunities |
| Construir, reducir o coordinar movimiento | G7 | M03, MOV01, MOV02 | animate, choreograph, emil-design-eng, gestures, impeccable, react-view-transitions, remove-animations |
| Auditar movimiento e interrupciones | G7 | MOV04, QA01 | animation-performance, emil-design-eng, improve-animations, make-interfaces-feel-better, review-animations |
| Auditoría de interfaz y coherencia | G1, G3, G4, G5, G6, G7 | QA01 | anti-ui-slop, impeccable, web-design-guidelines |
| Accesibilidad de interfaz | G3, G5, G6, G7 | AC01, TY03 | web-design-guidelines |
| Rendimiento de UI y animaciones | G6, G7 | MOV04, QA01 | animation-performance, react-best-practices |
| Pruebas adversariales de UI | G5, G6 | LAY01, QA01 | break-ui |
| Textos de interfaz | G5 | C01, WR01 | impeccable, writing-guidelines |
| Revisión de documentación | G0 | C01, WR01 | writing-guidelines |
| Demos ficticias y escenas de producto | G1 | ART02 | stageshow |
| Capturar correcciones aprobadas | G0, G1, G2, G3, G4, G5, G6, G7 | GOV00, QA01 | learn-taste |
| Despliegue, credenciales y costes | Fuera | ENV02 | deploy-to-vercel, vercel-cli-with-tokens, vercel-optimize |
| Desarrollo nativo | Fuera | S05 | animate-expo, react-native-skills, write-swift |
| Documentos, slides e impresión | Fuera | S06 | banner-design, slides |

## Matriz individual (47 fuentes, 83 vínculos funcionales)

| ID | Skill | Funciones / efecto propuesto | Resolución anterior |
|---|---|---|---|
| X01 | uizze-ui | meta (excluir) | EXCLUDE |
| X02 | impeccable | art-direction (consultar), type-micro (implementar), color-system (implementar), layout (implementar), tokens (consultar), ux-writing (consultar), motion-build (implementar), visual-qa (auditar) | SPLIT |
| X03 | ask-emil | meta (excluir) | EXCLUDE |
| X04 | design | meta (excluir) | EXCLUDE |
| X05 | ui-radar | ui-research (consultar) | REFINE |
| X06 | ui-ux-pro-max | ui-research (consultar), art-direction (consultar), type-choice (consultar), type-micro (consultar), color-system (consultar), layout (consultar), tokens (consultar), components (consultar) | SPLIT |
| X07 | deploy-to-vercel | infra (externo) | DEFER |
| X08 | vercel-cli-with-tokens | infra (externo) | DEFER |
| X09 | react-native-skills | native (externo) | DEFER |
| X10 | animate-expo | native (externo) | DEFER |
| X11 | write-swift | native (externo) | DEFER |
| X12 | slides | slides (externo) | DEFER |
| X13 | frontend-design | art-direction (consultar) | KEEP |
| X14 | design-taste-frontend | art-direction (prototipar), layout (implementar) | KEEP |
| X15 | hallmark | art-direction (prototipar) | KEEP |
| X16 | ui-design | ui-research (consultar), type-choice (consultar), color-system (consultar), layout (implementar), components (implementar) | SPLIT |
| X17 | image-to-ui | image-fidelity (implementar) | KEEP |
| X18 | brand | brand-identity (consultar) | KEEP |
| X19 | banner-design | art-direction (prototipar), slides (externo) | SPLIT |
| X20 | prototype | variants (prototipar) | KEEP |
| X21 | mobile-native | web-mobile (implementar) | REFINE |
| X22 | composition-patterns | components (consultar) | KEEP |
| X23 | design-system | tokens (consultar) | KEEP |
| X24 | ui-styling | components (implementar) | REFINE |
| X25 | pick-ui-library | component-lib (consultar) | KEEP |
| X26 | ask-sonner | components (consultar), components (implementar) | KEEP |
| X27 | stageshow | faux-demo (prototipar) | MOVE |
| X28 | anti-ui-slop | visual-qa (auditar), ui-research (consultar) | REFINE |
| X29 | make-interfaces-feel-better | type-micro (auditar), components (auditar), components (implementar), motion-review (auditar) | SPLIT |
| X30 | web-design-guidelines | visual-qa (auditar), accessibility (auditar) | REFINE |
| X31 | react-best-practices | performance (auditar), performance (implementar), components (consultar) | KEEP |
| X32 | react-view-transitions | motion-build (implementar) | MOVE |
| X33 | vercel-optimize | infra (externo) | DEFER |
| X34 | find-animation-opportunities | motion-assess (analizar) | MOVE |
| X35 | remove-animations | motion-build (implementar) | MOVE |
| X36 | animate | motion-build (implementar) | MOVE |
| X37 | review-animations | motion-review (auditar) | KEEP |
| X38 | improve-animations | motion-review (auditar) | KEEP |
| X39 | animation-performance | performance (auditar), motion-review (auditar) | KEEP |
| X40 | animation-vocabulary | motion-assess (consultar) | MOVE |
| X41 | choreograph | motion-build (implementar) | MOVE |
| X42 | gestures | motion-build (implementar) | MOVE |
| X43 | apple-design | web-mobile (consultar), motion-assess (consultar), type-micro (consultar) | REFINE |
| X44 | emil-design-eng | components (consultar), components (implementar), motion-build (implementar), motion-review (auditar) | KEEP |
| X45 | break-ui | stress-test (analizar), stress-test (prototipar) | REFINE |
| X46 | learn-taste | learning (aprender) | REFINE |
| X47 | writing-guidelines | docs-review (auditar), ux-writing (auditar) | MOVE |

## Hallazgos a corregir

1. Separar cobertura de dominio de invocación y permisos: D10 es cobertura; no implica ejecutar los especialistas en todas las tareas.
2. Resolver relaciones muchos-a-muchos función/nodo/skill, no una etapa por skill.
3. No sumar wrappers externos (X01,X03,X04) como routers; son referencias catalogadas, excluidas.
4. Multi-playbooks X02,X06,X16,X29: seleccionar comando/consulta específica, no adoptar workflow entero.
5. Tratar S05/S06/infra como fuera de ruta y sin permiso.
6. Para aprobación futura: commits/pins, licencias de recursos auxiliares, vetting, contratos del host y tests negativos.

## Límites

Esta matriz es un nuevo análisis de la auditoría anterior y las fuentes identificadas, no una reevaluación en runtime de cada script o dependencia. Los efectos son capacidades potenciales, no permisos de ejecución. No hay cambios al plugin 0.3.1.
