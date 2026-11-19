# Política de seguridad

## Versiones soportadas

Solo se mantiene la rama `main`. No hay versiones publicadas ni etiquetas: un informe se aplica al commit que esté en `main` en ese momento.

## Cómo reportar

No abras un issue público. Usá el [reporte privado de seguridad](https://github.com/fegome90-cmd/design-skills-router/security/advisories/new) e indicá:

- el archivo y el commit afectados;
- qué permite hacer el problema y en qué condiciones;
- cómo reproducirlo, si es posible.

Omití el valor de cualquier credencial. Si ya publicaste una, revocala en el proveedor antes de avisar.

## Alcance

Cubre las vulnerabilidades del código propio y de las integraciones mantenidas en este repositorio, incluidos `plugin/`, `telemetry/`, `board/`, `offline/`, `tools/`, `scripts/`, `.github/` y la documentación. La enumeración no limita el alcance a esas rutas.

Los problemas exclusivos del código de terceros (`vendor/`, si se incorpora, dependencias como Shoelace y Lit, o fuentes tipográficas) corresponden también a sus proyectos de origen. Si el problema afecta a cómo se incorpora, configura o utiliza una dependencia en este repositorio, se acepta su reporte privado aquí.

## Expectativas

Acuse de recibo en un plazo de cinco días hábiles. No hay compromiso de plazo de corrección. Si lo pedís, se acredita el informe cuando se publique la corrección.
