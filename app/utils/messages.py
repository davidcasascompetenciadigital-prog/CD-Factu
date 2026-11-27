# app/utils/messages.py
# Mensajes en lenguaje natural, sin tecnicismos.

MSG_FACTURA_GUARDADA = "Factura guardada. Todo correcto."
MSG_CLIENTE_GUARDADO = "Cliente guardado. Todo correcto."
MSG_PRODUCTO_GUARDADO = "Producto guardado. Todo correcto."
MSG_COBRO_REGISTRADO = "Cobro registrado. Todo correcto."
MSG_FALTA_NOMBRE_CLIENTE = "Falta el nombre del cliente. Escribe aquí: "
MSG_FALTA_NIF_EMPRESA = "Falta el NIF de tu empresa. Escribe aquí: "
MSG_CONFIRMAR_EMITIR = "Vas a emitir una factura a {cliente} por {total} €. ¿Es correcto?"
MSG_QUITAR_LINEA = "¿Seguro que quieres quitar esta línea?"
MSG_ANULAR = "¿Seguro que quieres anular esta factura? Se generará una factura rectificativa."
MSG_BACKUP = "Copia de seguridad guardada en {ruta}"

def ayuda(tab: str) -> str:
    textos = {
        "empresa": "Aquí pones los datos de tu empresa. Se rellena una sola vez, con ayuda de tu asesor si hace falta.",
        "clientes": "Aquí eliges a quién le facturas. Si no aparece, créalo con el botón GUARDAR CLIENTE.",
        "productos": "Aquí guardas los productos o servicios que vendes. El IVA más habitual es el 21%.",
        "emitir": "Elige un cliente, añade líneas y pulsa EMITIR FACTURA. No se puede editar después.",
        "cobros": "Aquí registras los pagos que recibes de tus facturas.",
        "facturas": "Aquí ves todas las facturas emitidas y su estado de pago.",
        "servicios": "Aquí guardas tus servicios con un título y una descripción larga. Al facturar podrás añadirlos con un clic.",
        "gastos": "Aquí apuntas las facturas que recibes de tus proveedores. Sirven para calcular el IVA soportado.",
        "balance": "Resumen del trimestre: ingresos, gastos, cobros y el IVA a ingresar o compensar (modelo 303).",
        "balance_anual": "Resumen del año: IVA anual (modelo 390) y previsión orientativa de IRPF según lo facturado, "
                         "los gastos y las retenciones. Puedes cambiar el tipo efectivo de IRPF.",
    }
    return textos.get(tab, "Pulsa ? en cualquier pantalla para ver ayuda.")
