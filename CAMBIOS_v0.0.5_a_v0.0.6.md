# Cambios del fork respecto a v0.0.5

- **Base comparada:** rama `servicios-balance-verifactu` @ **v0.0.5** (`5e3b629`)
- **Fork:** `csjdeacon/CD-Factu`, rama `servicios-balance-verifactu` @ **v0.0.6**
- **Pull Request:** [#1](https://github.com/davidcasascompetenciadigital-prog/CD-Factu/pull/1)
- **Fecha:** 2026-11-27

## Resumen

Se añade un **balance anual** con dos bloques: resumen anual de IVA para el modelo 390 y previsión orientativa de IRPF
según lo facturado, los gastos y las retenciones. Para que esa previsión sea posible, ahora se registran las retenciones
tanto en las facturas emitidas como en las recibidas.

## Novedades detalladas

### 1. Balance anual (nueva pestaña del menú principal)

- Selector de año y de **tipo efectivo de IRPF** (20 % por defecto, ajustable de 0 % a 60 %).
- **IVA anual:** bases y cuotas por tipo (4 %, 10 %, 21 % y otros), total de cuotas devengadas, bases y cuotas deducibles
  de operaciones interiores corrientes, resultado del régimen general y volumen de operaciones (casilla 99).
- **Desglose trimestral:** cuota devengada, deducible y resultado de cada uno de los cuatro trimestres.
- **Previsión de IRPF:** facturación sin IVA − (gastos + IVA no deducible) = rendimiento neto estimado; se aplica el
  tipo efectivo y se restan las retenciones sufridas. Las retenciones practicadas a proveedores se muestran aparte
  con la advertencia de que pertenecen al modelo 111 y no reducen la cuota propia.
- Exportación a **PDF** y **CSV** con aviso de que es una hoja de trabajo orientativa, no una declaración presentada.

### 2. Retención de IRPF en facturas emitidas

- Nuevo selector "5. Retención IRPF" en *Emitir factura* con 0/7/15/19/20/21 %.
- El resumen muestra la retención en euros y el importe a cobrar del cliente; la confirmación de emisión lo muestra antes de guardar.
- La retención se calcula sobre la **base imponible** y se guarda en `facturas.retencion_irpf`.
- `pendiente` pasa a ser el importe neto a cobrar. Los cobros "total" y "parcial" usan ese importe neto.
- El PDF de la factura muestra "Retención IRPF (x %)" y "Total a cobrar del cliente". El visor de *Facturas emitidas*
  hereda el mismo comportamiento al reimprimir.

### 3. Retención de IRPF en gastos

- Selector "Retención IRPF al proveedor" con 0/1/2/7/15/19/20/21 %.
- El formulario muestra el importe a pagar al proveedor (total menos retención).
- Se guarda en `gastos.retencion_irpf` y se añade una columna **Ret. IRPF** a la tabla de gastos.

### 4. Base de datos y datos de ejemplo

- `schema.sql` y `database.py`: columnas `retencion_irpf` en `facturas` y `gastos`, con migración automática
  para las bases de datos ya existentes (no hace falta borrar datos).
- Los datos de ejemplo incluyen una factura con retención del 15 % y un gasto de gestoría con retención del 15 %,
  para que la previsión anual tenga contenido desde la primera ejecución.

### 5. Interfaz y documentación

- Registro de la pestaña en `MENU_ITEMS`, `pages`, `ir_a` y recarga tras emitir facturas o guardar gastos.
- Texto de ayuda de la nueva pantalla en `app/utils/messages.py`.
- Etiquetas de versión de la ventana y "Acerca de" pasan a leer `APP_VERSION` (estaban fijas en 0.0.2).
- `APP_VERSION = "0.0.6"` y README actualizado.

## Aviso fiscal

La previsión de IRPF es una estimación con un tipo efectivo simplificado. La cuota real depende de la escala de la
Comunidad Autónoma, la situación personal, reducciones y regímenes especiales. Las casillas del 390 son orientativas,
deben cotejarse con los cuatro modelos 303 y comprobarse en el formulario oficial de la AEAT. Quien tribute por el
SII no presenta el modelo 390. El software se ofrece sin garantía y no sustituye el asesoramiento profesional.
