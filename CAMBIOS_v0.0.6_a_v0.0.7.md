# Cambios de la versión 0.0.7 (integración)

- **Base del fork:** rama `servicios-balance-verifactu` @ **v0.0.6** (`30f1aa3`)
- **Base comparada:** autor @ `c51ff53` (v0.0.5), `2ee4112` (v0.0.6) y `92b29c7` (README Windows)
- **Fork:** `csjdeacon/CD-Factu`, rama `servicios-balance-verifactu` @ **v0.0.7**
- **Pull Request:** [#1](https://github.com/davidcasascompetenciadigital-prog/CD-Factu/pull/1)
- **Fecha:** 2026-11-27

## Resumen

El autor publicó su propia **v0.0.6** (`2ee4112`) mientras que el fork ya tenía una **v0.0.6** distinta (`30f1aa3`).
Para evitar colisionar con el tag del autor, la integración se publica como **v0.0.7**. El objetivo es que convivan,
en un único ejecutable, todas las mejoras del autor y todas las del fork.

## Novedades incorporadas del autor

1. **QR Verifactu según normativa:** la URL de validación usa los cuatro parámetros obligatorios (`nif`, `numserie`,
   `fecha` en formato `DD-MM-AAAA` e `importe`), sin incluir el hash, y distingue el endpoint de facturas verificables.
   El código QR se genera con versión 1, borde 4 y corrección de errores M.
2. **Copias de seguridad:** backup automático al cerrar, funciones `listar_backups()` y `restaurar_backup()`, y botones
   **Backup** y **Restaurar** en la cabecera.
3. **Actualizaciones:** verificación de la última release de GitHub al arrancar y auto-descarga/instalación respetando
   los datos locales (`app/updater.py`, `app/version.py`). La versión de control es `VERSION = "0.0.7"`.
4. **Interfaz:** nuevo submenú en *Mis datos de empresa* con tres páginas (datos, **notas internas** y Verifactu),
   ficha de cliente en *Emitir factura*, botón **Listado de clientes**, y tabla de líneas con **Cantidad**, **Precio**
   y **Dto.%** editables, con **Total descuento** en el PDF y en el visor.
5. **Documentación:** sección Windows del README y capturas de pantalla.

## Funcionalidad del fork que se conserva

- **Servicios** con título y descripción larga por factura; el concepto con salto de línea se respeta en el PDF.
- **Gastos** (facturas recibidas) y **balance trimestral** con hoja de trabajo del modelo 303 en PDF/CSV.
- **Balance anual** con resumen del modelo 390 y previsión de IRPF en PDF/CSV.
- **Retenciones IRPF** al emitir facturas y al registrar gastos, con su impacto en cobros, PDF y visor.
- **Verifactu local:** encadenamiento SHA-256, envío SOAP con certificado y vista previa; botón **Verifactu / AEAT**
  en *Facturas emitidas*.
- Búsqueda inline de clientes y compatibilidad con el selector de clientes del autor.
- Formulario Verifactu con soporte para `.p12/.pfx` además de certificado público y clave privada.

## Resolución de conflictos

- `qr_generator.py`: se toman los parámetros normativos del autor (`version=1`, `border=4`) manteniendo `box_size=6`.
- `pdf_generator.py`: columnas del autor (`Cant.`, `Precio`, `Dto.%`, `IVA %`, `Total`) con el bloque de retención IRPF
  y el formato de concepto con descripción multilínea del fork.
- `main_window.py`: se conservan las páginas del fork y se añaden `Slot`, `Path`, updater, backup, botones y
  `verificar_actualizacion()` del autor. La etiqueta de versión sigue usando `APP_VERSION`.
- `tab_empresa.py`: se integran las tres páginas del autor con los campos Verifactu y las notas del fork.
- `tab_emitir.py`: combinación de búsqueda inline, selector del autor, servicios, retención IRPF, Verifactu y
  columnas editables de cantidad/descuento.
- `tab_facturas.py`: se conserva el botón **Verifactu / AEAT** junto al **Exportar para mi asesor** del autor.
- `README.md`: documentación del autor y changelog del fork, con la versión actualizada a 0.0.7.

## Validación realizada

- `git diff --check`, `python -m compileall` de `app/` y `main.py`.
- Apertura headless (`QT_QPA_PLATFORM=offscreen`) de `MainWindow` y comprobación de las diez pestañas y los widgets clave.
- Cálculo de línea con descuento y retención (base 180,00 €, IVA 37,80 €, total 217,80 €, retención 27,00 €,
  a cobrar 190,80 €).
- Generación de QR, PDF de factura y exportaciones PDF/CSV de los balances trimestral y anual.
- Ejecutable Windows generado con PyInstaller y `cryptography==44.0.3`.

## Aviso fiscal

La previsión de IRPF es una estimación con un tipo efectivo simplificado. La cuota real depende de la escala de la
Comunidad Autónoma, la situación personal, reducciones y regímenes especiales. El envío real a la AEAT tiene efectos
fiscales: prueba siempre en el entorno de pruebas. El software se ofrece sin garantía y no sustituye el asesoramiento
profesional.
