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

Cubre el contenido propio del repositorio: `board/`, `offline/`, `scripts/`, `.github/` y la documentación.

Queda fuera de alcance:

- `vendor/`: las fuentes fijadas de terceros se reportan al proyecto de origen;
- las dependencias embebidas con su propia licencia, como Shoelace y Lit (BSD-3-Clause) y las fuentes tipográficas (OFL-1.1).

## Expectativas

Acuse de recibo en un plazo de cinco días hábiles. No hay compromiso de plazo de corrección. Si lo pedís, se acredita el informe cuando se publique la corrección.
