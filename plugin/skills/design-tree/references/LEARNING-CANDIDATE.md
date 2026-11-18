# Candidato de aprendizaje · plantilla de mantenimiento

Un problema repetible puede producir conocimiento útil, pero **no aplica** por
sí solo un cambio. Crear cada instancia **fuera del plugin**, junto con el
experimento y sus trazas. La plantilla no otorga autoridad, no instala una
skill y no genera aprobaciones de usuario.

```yaml
id: LC-YYYY-NNN
status: PROPOSED
source_release: "pluginrel_... / v..."
owning_file: "tests/test_release.py"
reproduction:
  command: "python3 -B -m unittest ..."
  expected: "resultado del comportamiento deseado"
  observed: "error exacto que se produjo"
before_evidence:
  - "ruta externa, log y SHA-256"
after_evidence:
  - "ruta externa, log y SHA-256 tras la corrección en copia"
minimal_diff: "ruta a parche externo o referencia a diff"
scope: "archivo y requisito exactos"
safety: "sin credenciales, expedientes reales ni cambios remotos"
licence: "procedencia y permiso de reutilización"
review_gate: "requiere aprobación humana del diff exacto"
```

## Procedimiento sin automatización

1. Reproducir en una copia y guardar evidencia del fallo, versión y archivo dueño.
2. Proponer **un** cambio mínimo y observar el test rojo y luego verde.
3. Registrar `PROPOSED`, sin editar `SKILL.md`, contratos, visor ni catálogo instalado.
4. Revisar el alcance, las licencias, el efecto en gates y la reversibilidad.
5. Sólo tras la **aprobación** explícita, aplicar por el flujo ordinario de
   mantenimiento y prueba de release, conservando trazas y el release previo.
6. La aprobación de un candidato no es autoridad de publicación; promover
   requiere gate adicional. Rechazado o desactualizado sigue como historia.

Ningún script de esta plantilla ejecuta cambios. No crear una nueva base de
datos, servidor, cola ni sistema de aprendizaje automático.
