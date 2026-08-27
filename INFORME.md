# Demostración controlada de copia no autorizada desde almacenamiento externo

## 1. Objetivo

Demostrar, dentro de un entorno completamente aislado y con datos sintéticos,
que un proceso con permiso de lectura puede copiar archivos de un medio de
almacenamiento externo. Comparar el resultado con distintos controles de acceso.

## 2. Alcance y consideraciones éticas

La práctica no utiliza malware real. El programa no descubre dispositivos, no
accede a archivos personales, no transmite información y no intenta ocultarse.
Todas las rutas están fijadas dentro del laboratorio y todos los datos son
ficticios. Esto permite estudiar el riesgo sin afectar a personas o sistemas.

## 3. Hipótesis

- H1: sin controles de lectura, el proceso copiará los archivos objetivo.
- H2: marcar un medio como solo lectura no evitará la copia, porque la operación
  de origen sigue siendo una lectura.
- H3: bloquear la lectura para el proceso impedirá la copia.

## 4. Metodología

1. Crear un directorio que representa el disco externo.
2. Generar archivos `.txt`, `.csv` y `.json` con información ficticia, además de
   un archivo no objetivo.
3. Ejecutar los escenarios `sin-controles`, `solo-lectura` y
   `bloqueo-lectura`.
4. Contar los archivos y bytes copiados.
5. Registrar cada acción, su resultado y el hash SHA-256 del archivo copiado.
6. Comparar los resultados.

## 5. Variables

- Variable independiente: política simulada de acceso.
- Variables dependientes: cantidad de archivos copiados y bytes copiados.
- Variables controladas: archivos de entrada, extensiones objetivo y ubicación
  del laboratorio.

## 6. Resultados

Ejecutar `python3 simulador.py comparar` y completar:

| Escenario | Detectados | Copiados | Bytes | Observación |
|---|---:|---:|---:|---|
| Sin controles | 7 | 7 | 8.807 | Todos los formatos objetivo fueron copiados |
| Solo lectura | 7 | 7 | 8.807 | La protección de escritura no evitó la lectura |
| Bloqueo de lectura | 7 | 0 | 0 | La política simulada impidió todas las copias |

Adjuntar como evidencia el resumen de consola y fragmentos anonimizados de
`laboratorio/auditoria.jsonl`.

Como validación opcional autorizada sobre un medio físico, puede ejecutarse
`probar-usb`. El programa crea y lee exclusivamente su propia carpeta marcada;
deben documentarse el modelo del dispositivo, el hash SHA-256 y la cantidad de
bytes copiados, evitando incluir el número de serie completo en el informe.

### 6.1 Validación realizada con USB físico

- Fecha: 27 de agosto de 2026.
- Dispositivo: Kingston DataTraveler 3.0, 14,4 GB.
- Sistema de archivos: exFAT, etiqueta `PROYECTOS`.
- Archivos controlados: TXT, DOCX, XLSX, PPTX y PDF.
- Cantidad copiada: 5 archivos, 8.578 bytes en total.
- Identificación independiente: Microsoft Word 2007+, Microsoft Excel 2007+,
  Microsoft PowerPoint 2007+ y PDF 1.4, además del texto UTF-8.
- Resultado: las cinco copias se completaron y el SHA-256 de cada destino
  coincidió con su correspondiente origen.

## 7. Análisis esperado

Los dos primeros escenarios deberían producir el mismo número de copias. Esto
muestra que un control contra escritura protege la integridad del dispositivo,
pero no la confidencialidad de sus datos. El bloqueo de lectura debería producir
cero copias y eventos de auditoría con resultado de acceso bloqueado.

## 8. Medidas defensivas recomendadas

- Aplicar mínimo privilegio y controles de acceso por proceso o usuario.
- Restringir medios extraíbles mediante políticas de endpoint.
- Cifrar información sensible y gestionar correctamente sus claves.
- Usar controles DLP para detectar copias no autorizadas.
- Monitorizar accesos masivos o inusuales a archivos.
- Capacitar a los usuarios y mantener una política de dispositivos autorizados.

## 9. Limitaciones

El bloqueo es una política simulada en el propio programa, no una evaluación de
un producto EDR/DLP ni del sistema operativo. El laboratorio demuestra el
principio de seguridad, pero no reproduce técnicas de persistencia, evasión o
exfiltración de malware real.

## 10. Conclusión

Completar indicando si las tres hipótesis fueron confirmadas y relacionando los
resultados con el principio de mínimo privilegio y la confidencialidad de la
información.
