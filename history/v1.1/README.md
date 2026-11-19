# Archivo histórico de la pizarra v1.1

Abrir [la pizarra original](design-router-pizarra-seleccion-minima-v1.1.html) o [la copia anotada](design-router-pizarra-v1.1-auditada.html). El [informe de auditoría](INFORME_AUDITORIA_v11.md) describe el estado observado el 17 de noviembre de 2026. Las capturas documentan [la inclusión indebida de G7 en una auditoría de layout](evidencia_A01_auditoria_G5_G7.png) y [la ausencia de especialista en una auditoría tipográfica](evidencia_A02_auditoria_G2_sin_owner.png).

Los hallazgos, incluidos la exportación de N/A sin validación, la pérdida del dominio elegido y la pérdida de foco, corresponden a la pizarra **v1.1**. La simulación de selección vigente es v1.2 y está incorporada en la pizarra v1.3. El baseline normativo del plugin es el **árbol v0.4** del plugin 0.3.1. La auditoría de la pizarra registra observaciones de interfaz y simulación, con la cobertura de host indicada en el informe.

Se conservaron [las pruebas de humo originales](test_min_route_v11_smoke.py) y [las pruebas de regresión negativas](test_regresion_negativa_v11.py) con sus resultados históricos. Las tres pruebas de humo pasaron. Las cinco pruebas negativas fallaron en v1.1 y así reprodujeron los defectos. La prueba de humo mantiene sus rutas originales del entorno, incluida una referencia al HTML v1.0. Para usarla en otro equipo se deben adaptar las rutas en una copia del script.

Se verificaron los 15 archivos del [manifiesto de auditoría](audit_files_manifest.json), y el script de humo, el modelo y el registro original de QA contra el manifiesto del release v1.1. Los dos HTML también coincidieron byte a byte con sus copias históricas independientes.
