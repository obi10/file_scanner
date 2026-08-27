# Simulador académico de copia no autorizada

Este proyecto demuestra, de manera contenida y auditable, cómo un proceso puede
copiar archivos desde un supuesto disco externo cuando no existen controles de
lectura adecuados.

## Límites de seguridad

- Solo trabaja dentro de la carpeta `laboratorio/` de este proyecto.
- Los archivos usados son generados por el programa y contienen datos ficticios.
- No detecta ni monta dispositivos USB automáticamente.
- El modo USB requiere una ruta explícita y solo toca su carpeta de laboratorio.
- No accede a carpetas personales; la única ruta externa admitida es la raíz
  explícita de un volumen autorizado para el modo USB.
- No usa red, persistencia, ocultamiento, evasión ni ejecución automática.
- Cada intento queda registrado en formato JSON Lines.

## Requisitos

- Python 3.10 o posterior.

## Uso

Inicializar los archivos falsos:

```bash
python3 simulador.py inicializar
```

Ejecutar una comparación completa:

```bash
python3 simulador.py comparar
```

También se puede ejecutar un escenario individual:

```bash
python3 simulador.py simular --control sin-controles
python3 simulador.py simular --control solo-lectura
python3 simulador.py simular --control bloqueo-lectura
```

### Prueba opcional con un USB real autorizado

Este modo no examina el contenido existente del USB. Crea la carpeta exclusiva
`SIMULACION_ACADEMICA_SEGURA`, escribe archivos ficticios TXT, DOCX, XLSX, PPTX
y PDF, y copia solo esos archivos al laboratorio local. La ruta debe ser la raíz
de un volumen montado. Cada copia se verifica mediante SHA-256.

Linux:

```bash
python3 simulador.py probar-usb --ruta-montaje "/run/media/usuario/ETIQUETA"
```

Windows 10 (PowerShell):

```powershell
py -3 simulador.py probar-usb --ruta-montaje "E:\"
```

Use este modo únicamente sobre un dispositivo propio o expresamente autorizado.

Los archivos copiados aparecerán en `laboratorio/resultados/`, separados por
ejecución. El registro se guarda en `laboratorio/auditoria.jsonl`.

## Resultado esperado

| Escenario | Archivos copiados | Interpretación |
|---|---:|---|
| Sin controles | Todos los archivos objetivo | El proceso puede leer y copiar los datos |
| Solo lectura | Todos los archivos objetivo | Proteger contra escritura no evita la copia |
| Bloqueo de lectura | Ninguno | La denegación de lectura impide la copia |

## Pruebas

```bash
python3 -m unittest discover -s tests -v
```

Las pruebas verifican tanto el comportamiento de los escenarios como el límite
que impide operar fuera del laboratorio. Los formatos objetivo contemplados son
TXT, CSV, JSON, RTF, PDF, DOC/DOCX, XLS/XLSX, PPT/PPTX y ODT/ODS/ODP. La copia
se realiza byte por byte: no abre, convierte ni modifica el formato.

## Nota ética

Este código es una simulación defensiva para un entorno académico. No debe
modificarse para inspeccionar dispositivos reales ni utilizarse con datos de
terceros sin autorización expresa.
