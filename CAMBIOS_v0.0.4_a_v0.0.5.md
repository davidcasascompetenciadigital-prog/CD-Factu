# Cambios del fork respecto a v0.0.4

- **Base comparada:** `davidcasascompetenciadigital-prog/CD-Factu` @ **v0.0.4** (`e56ffa2`)
- **Fork:** `csjdeacon/CD-Factu`, rama `servicios-balance-verifactu` @ **v0.0.5** (`9c4f8c4`)
- **Pull Request:** [#1](https://github.com/davidcasascompetenciadigital-prog/CD-Factu/pull/1)
- **Fecha:** 2026-11-27
- **Resultado:** 24 archivos cambiados, +1974 / -516 líneas.

## Resumen de novedades añadidas por el fork

1. **Servicios.** Nueva sección donde se dan de alta servicios con título, descripción larga, importe base e IVA. En *Emitir factura* existe el botón **Añadir servicio**; la descripción se puede editar solo para esa factura y viaja al PDF.

2. **Gastos y balance trimestral.** Registro de facturas recibidas y consulta por trimestre de ingresos, gastos, cobros, pagos pendientes y resultado del IVA. Genera la **hoja de trabajo del modelo 303** en PDF/CSV para copiar a la Sede electrónica. El IVA se calcula por fecha de emisión, no por fecha de cobro.

3. **Verifactu completo.** Huella SHA-256 encadenada, XML de alta/anulación, QR oficial de cotejo y envío SOAP con certificado (`.p12/.pfx` o PEM) al entorno de **pruebas** o al entorno **real** de la AEAT. Incluye vista previa que no guarda ni envía, y generación del registro de anulación cuando se anula una factura ya registrada.

4. **Integración con v0.0.4 del autor.** Se conservan íntegramente las mejoras que el autor publicó en v0.0.3/v0.0.4: columna **Núm.FRA.** y visor de factura en *Facturas emitidas*, productos a dos columnas con búsqueda, y búsqueda inline de clientes en *Emitir factura*. El conflicto de `tab_emitir.py` se resolvió manteniendo la búsqueda inline junto al botón de selección, y el visor del autor imprime ahora respetando la leyenda del QR oficial cuando la factura está registrada.

## Commits incluidos desde v0.0.4

| Commit | Descripción |
| --- | --- |
| `37c21de` | v0.0.2: servicios, gastos/balance trimestral y Verifactu |
| `9c4f8c4` | v0.0.5: integrar v0.0.3/v0.0.4 del autor con servicios, balance y Verifactu |

## Archivos nuevos

| Archivo | Líneas |
| --- | ---: |
| `app/services/balance.py` | +162 |
| `app/services/verifactu.py` | +526 |
| `app/ui/dialog_verifactu.py` | +206 |
| `app/ui/tab_balance.py` | +144 |
| `app/ui/tab_gastos.py` | +216 |
| `app/ui/tab_servicios.py` | +161 |

## Archivos modificados

| Archivo | Cambio |
| --- | --- |
| `.gitignore` | +5 / -1 |
| `README.md` | +138 / -44 (documentación de v0.0.5) |
| `app/config.py` | +25 / -3 (versión 0.0.5, constantes Verifactu) |
| `app/db/database.py` | +2 (migraciones) |
| `app/db/schema.sql` | +96 (servicios, gastos, registros Verifactu) |
| `app/models/factura.py` | +1 |
| `app/services/backup.py` | +23 / -16 |
| `app/services/pdf_generator.py` | +76 / -34 (descripción de servicios, leyenda QR) |
| `app/services/qr_generator.py` | +2 / -1 |
| `app/services/sample_data.py` | +19 |
| `app/ui/main_window.py` | +139 / -95 (pestañas nuevas, logo) |
| `app/ui/tab_emitir.py` | +261 / -155 (servicios + Verifactu + búsqueda inline del autor) |
| `app/ui/tab_empresa.py` | +192 / -86 (configuración Verifactu) |
| `app/ui/tab_facturas.py` | +52 / -16 (botón Verifactu + QR oficial + visor del autor) |
| `app/ui/widgets.py` | +2 / -1 |
| `app/utils/messages.py` | +3 |
| `main.py` | +37 / -24 (splash y arranque) |
| `requirements.txt` | +2 |

## Ejecutable portable

`dist/CD-Factu-0.0.5.exe` — compilado con PyInstaller (`--onefile --windowed`), sin necesidad de instalar Python. Para que el módulo de certificados funcione en Python 3.15 se usa `cryptography 44.0.3` (cumple `>=42` de `requirements.txt`).

## Aviso

Antes de enviar a la AEAT real hay que rellenar `PRODUCTOR_NIF` en `app/config.py`. El envío real tiene efectos fiscales; prueba siempre primero en el entorno de pruebas. El software se ofrece sin garantía y no sustituye el asesoramiento profesional ni la declaración responsable del productor.
