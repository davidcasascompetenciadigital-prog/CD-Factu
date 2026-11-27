# CD Factu

**CD Factu** es un programa de facturación sencilla para autónomos y micropymes, con integración de **Verifactu** (modalidad local: registros inalterables encadenados por hash, código QR de validación AEAT y exportación para el asesor).

## Características principales
- Interfaz ultra-sencilla, con botones grandes y tema oscuro.
- Gestión de empresa, clientes, productos y facturas.
- Emisión de facturas en PDF con QR Verifactu.
- Control de cobros y estado de pago.
- Anulación/rectificación de facturas (sin borrar).
- Copia de seguridad automática.
- Funciona sin conexión a internet (datos locales).

## Requisitos
- Windows 10 o superior.
- No requiere instalación de Python (ejecutable incluido en la Release).

## Uso
1. Descarga `CD Factu.exe` desde la Release.
2. Ejecútalo (se crea la base de datos automáticamente).
3. Rellena “Mis datos de empresa” (con ayuda de tu asesor si es necesario).
4. ¡Empieza a facturar!

## Datos de ejemplo
En la primera ejecución se ofrece cargar datos de ejemplo para probar el flujo.

## Verifactu
- Modalidad local: no requiere certificado por parte del usuario final.
- Configuración opcional de certificado (prueba/real) en “Mis datos de empresa”.
- Exportación de registros para el asesor (“Exportar para mi asesor”).

## Garantía y licencia
Este software se proporciona **“tal cual” (AS IS)**, **SIN GARANTÍA** de ningún tipo, ni expresa ni implícita. El usuario asume toda la responsabilidad de su uso.

Licencia: **Creative Commons Compartir Igual Mención (CC BY-SA)**. Software GRATUITO.

## Autor
David Casas M.
- YouTube: @Competencia_Digital
- Twitch: davidcasasm
- GitHub: davidcasascompetenciadigital-prog

## Versión
0.0.1 (inicial)

## Ejecución en Linux

### Desde código fuente
```bash
pip install -r requirements.txt
python3 main.py
```

### Compilar ejecutable (Linux)
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "CD-Factu" \
  --add-data "assets:assets" --add-data "app/db/schema.sql:app/db" main.py
./dist/CD-Factu
```

Los datos se guardan en `~/.local/share/CD Factu/` y las copias de seguridad en `~/Desktop/Backup_Facturas` (o en `$HOME` si no existe el Escritorio).
