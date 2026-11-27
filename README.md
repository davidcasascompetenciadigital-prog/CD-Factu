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
0.0.5 (integración de las versiones 0.0.3/0.0.4 del autor con las novedades 0.0.2)


---

## Novedades de la versión 0.0.5

- **Del autor (v0.0.3):** *Facturas emitidas* añade columna **Núm.FRA.**, botón **Ver factura** con visor y botón
  **Imprimir**; ajuste de columnas y doble clic para ver la factura.
- **Del autor (v0.0.4):** *Productos* pasa a dos columnas con búsqueda por nombre o referencia; *Emitir factura*
  incorpora búsqueda inline de clientes (nombre, CIF, email y teléfono); el visor de factura muestra emisor y cliente
  en dos columnas.
- **De esta rama (0.0.2):** servicios con descripción por factura, gastos y balance trimestral con hoja del modelo 303,
  y Verifactu con QR oficial, envío SOAP y vista previa. Todo ello convive con las mejoras anteriores.

> El visor del autor imprime ahora el PDF respetando la leyenda del QR oficial de Verifactu cuando la factura está registrada.

---

## Novedades de la versión 0.0.2

- **Logo:** la pantalla de carga es más grande y ya no se queda por encima de la ventana ni de los avisos; la
  pregunta de "datos de ejemplo" aparece cuando el logo ya se ha cerrado. El menú principal muestra el logo grande.
- **Servicios:** nueva sección con título y descripción larga (p. ej. "Informe pericial"). En *Emitir factura* hay un
  botón **Añadir servicio**; la descripción se puede ajustar solo para esa factura y sale en el PDF.
- **Gastos y Balance trimestral:** apunta las facturas recibidas y consulta por trimestre ingresos, gastos, cobros,
  pagos pendientes y el resultado del IVA. Genera la **hoja de trabajo del modelo 303** (PDF/CSV) para copiar a la Sede.
  El IVA se calcula por fecha de emisión (no por cobro). La presentación del 303 se hace en la Sede electrónica de la AEAT.
- **Verifactu:** huella SHA-256 encadenada oficial, XML de alta/anulación, QR de cotejo y envío SOAP con certificado
  (.p12/.pfx o PEM) al **entorno de pruebas** o al **entorno real** de la AEAT. Hay una vista previa que no guarda ni envía.
  Antes de enviar hay que rellenar `PRODUCTOR_NIF` en `app/config.py`.

> El envío real tiene efectos fiscales. Prueba siempre antes en el entorno de pruebas. Este software se ofrece sin garantía
> y no sustituye la declaración responsable del productor ni el asesoramiento de un profesional.
