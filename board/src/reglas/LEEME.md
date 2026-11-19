# Reglas y medidas

Capa que se activa y se desactiva sobre la pizarra para medir componentes. Se abre con el botón del ícono de regla en la cabecera (nombre accesible "Reglas"), visible también en celular, o con la tecla R.

- **Reglas:** en píxeles CSS arriba y a la izquierda; en milímetros y centímetros abajo y a la derecha.
- **Guías:** se crean arrastrando desde una regla en píxeles y se borran devolviéndolas a la regla.
- **Medidor:** al pasar el puntero sobre un componente muestra su ancho y su alto en píxeles y en milímetros.

Los milímetros son milímetros CSS: 1 cm = 37,7952 px de referencia (96 px por pulgada). No equivalen a milímetros físicos de la pantalla, que dependen de la densidad del monitor.

## Dependencia embebida

| Paquete | Versión | Licencia | Archivo | SHA-256 del archivo |
|---|---|---|---|---|
| [@scena/guides](https://github.com/daybrush/guides) | 0.29.2 | MIT (Copyright (c) 2019 Daybrush) | `guides.min.js` (es `dist/guides.min.js` sin modificar) | `c40eef9b3f214fad3c78f2e9aefb04f57680026bc40571f2e2368dda5d48aac5` |

La integridad del tarball coincide con la que publica el registro de npm: `sha512-gnXiB/Ji3ix/mGCgJiWz4k6U9OjEwcpdKUvmh3pYLXuL2x6DouCPAJ/PwnrYgaSMURhSyNkzp4WJdHqbAdYDXw==`. El archivo conserva la cabecera de licencia del autor. Va embebido en el HTML para que la variante offline funcione sin red.
