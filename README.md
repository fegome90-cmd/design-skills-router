# Design Skills Router

Design Skills Router ayuda a elegir qué skills consultar para una tarea de diseño y a explicar por qué se propone cada una.

## Ejemplo de selección

«Quiero auditar cómo se distribuye el contenido de una pantalla y si se entiende qué elemento es el más importante».

Para una auditoría con ese alcance, el router propone **G5**, el especialista en composición, cuadrícula y jerarquía visual. La selección reúne tres tareas en modo de **solo lectura**:

- Revisar la coherencia visual de la pantalla.
- Comprobar la accesibilidad de la interfaz.
- Examinar cómo responde el diseño ante casos extremos, como un título demasiado largo.

El resultado es una propuesta de revisión. La persona a cargo decide qué comprobaciones llevar a cabo.

## Prototipo de escritorio

El [prototipo React](board/desktop-demo/README.md) incluye un espacio de trabajo con navegación, conversaciones de ejemplo y un dashboard interactivo. La guía del prototipo explica cómo ejecutarlo y comprobarlo localmente.

## Cómo colaborar

Este repositorio público reúne las propuestas y revisiones de personas y agentes.

- Para proponer un cambio o informar un problema, abre un [issue](https://github.com/fegome90-cmd/design-skills-router/issues). Describe el caso concreto, el resultado esperado y cómo se podría comprobar.
- Para entregar un cambio, abre un [pull request](https://github.com/fegome90-cmd/design-skills-router/pulls) hacia `main`. Enlaza el issue cuando exista y resume qué cambió, cómo lo probaste y qué queda por verificar.

## Seguridad de las contribuciones

El hook comprueba el contenido preparado en Git antes de cada commit. Busca claves de API, material de clave privada y rutas personales de macOS. También bloquea nombres de archivos sensibles, incluso si el archivo está vacío. Para documentar variables de entorno, usa un `.env.example` con valores vacíos.

### Activar el hook en cada clon

Instala Python 3 y [Gitleaks](https://github.com/gitleaks/gitleaks/releases/tag/v8.30.1). La comprobación de GitHub usa Gitleaks 8.30.1. Desde la raíz del clon:

```sh
git config --local core.hooksPath .githooks
git config --local --get core.hooksPath
```

El segundo comando debe mostrar `.githooks`. Después de preparar los archivos con `git add`, puedes comprobarlos con `./scripts/check-secrets.sh staged`. Si se bloquea el commit, retira del índice el archivo privado o sustituye la credencial por una referencia a una variable de entorno, y vuelve a preparar los cambios.

GitHub Actions ejecuta **Secrets and private paths** al recibir un push o un pull request. Para comprobar localmente los commits alcanzables desde `HEAD`, ejecuta `./scripts/check-secrets.sh history`.

Si ya publicaste una credencial, revócala en el proveedor antes de sanear el historial. Para avisar al mantenedor, usa el [reporte privado de seguridad](https://github.com/fegome90-cmd/design-skills-router/security/advisories/new) e indica el archivo y el commit. Omite el valor de la clave.

En el PR que introduce el escáner, el workflow identifica el commit de base inicial y verifica las huellas SHA-256 de los tres archivos de política antes de ejecutarlos. En los PR posteriores usa la política del commit base de cada PR.
