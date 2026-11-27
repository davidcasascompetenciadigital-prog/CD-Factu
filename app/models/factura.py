# app/models/factura.py
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class LineaFactura:
    concepto: str = ""
    cantidad: float = 1.0
    importe_base: float = 0.0       # unitario sin IVA
    porcentaje_iva: float = 21.0
    producto_id: Optional[int] = None
    tipo_iva_id: Optional[int] = None
    # calculados
    base_linea: float = 0.0
    iva_linea: float = 0.0
    total_linea: float = 0.0

    def recalcular(self):
        self.base_linea = round(self.cantidad * self.importe_base, 2)
        self.iva_linea = round(self.base_linea * self.porcentaje_iva / 100.0, 2)
        self.total_linea = round(self.base_linea + self.iva_linea, 2)

@dataclass
class Factura:
    id: Optional[int] = None
    numero: str = ""
    fecha_emision: str = ""
    cliente_id: Optional[int] = None
    contacto_fact_id: Optional[int] = None
    lineas: list = field(default_factory=list)
    base_imponible: float = 0.0
    total_iva: float = 0.0
    total_factura: float = 0.0
    retencion_irpf: float = 0.0      # importe retenido por el cliente (€)
    retencion_pct: float = 0.0       # porcentaje de retención aplicado (%)
    desglose_iva: dict = field(default_factory=dict)  # {pct: (base, cuota)}
    estado: str = "emitida"
    estado_cobro: str = "no_cobrada"
    pendiente: float = 0.0
    pdf_path: Optional[str] = None
    hash_registro: str = ""
    hash_anterior: Optional[str] = None
    factura_original_id: Optional[int] = None
    motivo_rectificacion: Optional[str] = None

    def recalcular_totales(self):
        self.base_imponible = round(sum(l.base_linea for l in self.lineas), 2)
        self.total_iva = round(sum(l.iva_linea for l in self.lineas), 2)
        self.total_factura = round(self.base_imponible + self.total_iva, 2)
        self.pendiente = round(self.total_factura - self.retencion_irpf, 2)
        # desglose por tipo de IVA
        d = {}
        for l in self.lineas:
            pct = l.porcentaje_iva
            if pct not in d:
                d[pct] = [0.0, 0.0]
            d[pct][0] = round(d[pct][0] + l.base_linea, 2)
            d[pct][1] = round(d[pct][1] + l.iva_linea, 2)
        self.desglose_iva = {k: (v[0], v[1]) for k, v in d.items()}

    def aplicar_retencion(self, pct: float):
        """Retención de IRPF sobre la base imponible (la practica el cliente al pagar)."""
        self.retencion_pct = round(float(pct or 0), 2)
        self.retencion_irpf = round(self.base_imponible * self.retencion_pct / 100.0, 2)
        self.pendiente = round(self.total_factura - self.retencion_irpf, 2)
