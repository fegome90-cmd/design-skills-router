# Árbol de decisiones de diseño · v0.4

**Entrega:** visor corregido y probado; diseño del router todavía incompleto. No es un plugin instalado ni un runtime de autorización.

Abrir `index.html`. No necesita CDN, servidor, fuentes descargadas ni conexión para presentar el árbol. Los enlaces a fuentes sí requieren conexión. La apertura directa de archivos no pudo verificarse en el navegador de este entorno: `file://` está bloqueado por política. Se probó el mismo contenido HTML mediante `set_content`, sin cambiar esa política.

## Qué se corrigió

Identidad y cobertura ahora son ramas hermanas obligatorias. Los contextos de proyecto existente utilizan las mismas definiciones. El medio se revisa aunque ya exista stack. Hay preguntas explícitas de dirección de arte y microtipografía; lista/arrastre y tipos de movimiento no son falsas alternativas excluyentes. Cada candidato tiene una evaluación propia de identidad, compatibilidad, licencia, seguridad, accesibilidad y coste. `better-interface` tiene una pregunta de revisión conjunta. Se conservan las 82 skills con una disposición propuesta visible.

Los enlaces de los nodos exploran realmente las respuestas; la ficha es una acción separada. Funcionan enlaces por ID, navegación al padre y teclado. Se limitó la indentación acumulativa, y la raíz permanece visible dentro del área del diagrama.

## Fuentes editables

- `tree.json`: árbol canónico y plantilla de evaluación de candidatos. No editar la copia incrustada en HTML.
- `rules.json`: criterios, secciones de las fuentes, categorías y adaptaciones locales.
- `skill-inventory.json`: 82 entradas, asignación o disposición explícita y límites de revisión.
- `criterion-map.json`: correspondencia de criterios con definiciones de nodos.
- `model.py`: expande definiciones compartidas en instancias de un solo padre. No ejecuta decisiones.
- `viewer.js`, `styles.css`, `build.py`: visor y generador.
- `AUDIT.md`: hallazgos cerrados, parciales, nuevos y límites.
- `evidence/`, `tests/`: evidencias y pruebas reproducibles.

La expansión usa definiciones compartidas; no se mantienen manualmente miles de copias. Una instancia conserva `definition_id`, contexto y, cuando corresponde, `candidate_key`. El esquema expandido puede ser muy largo; usar la exploración por rama para revisar.

## Confirmación humana

Todos los nodos y disposiciones están **PENDING**. Confirmar una pregunta y sus skills no equivale a aprobar un resultado de proyecto. El visor no persiste aprobaciones ni impide que un agente use herramientas fuera de él. Las justificaciones requeridas son resúmenes de decisiones y evidencias, no razonamiento privado del modelo.

## Reproducir

Requisitos de la ejecución observada: Python 3; pytest 9.0.2; BeautifulSoup 4.14.3; Playwright 1.57.0; Chromium 144.0.7559.96. Node se usó únicamente para comprobar sintaxis de JavaScript. No se instaló ninguna biblioteca de UI.

```sh
python build.py
pytest -q
python tests/check_regressions.py .
python tests/check_browser.py
node --check viewer.js
```

`tests/check_browser.py` usa `CHROMIUM_PATH` si está definido; busca `chromium` en PATH y, si no existe, intenta el navegador instalado por Playwright. No instala navegadores ni modifica políticas de seguridad.

Las 12 comprobaciones de regresión se solapan con las 25 pruebas del modelo: no deben sumarse como si fueran casos independientes. Las comprobaciones del visor prueban comportamientos y dimensiones concretas, no certificación global de accesibilidad.
