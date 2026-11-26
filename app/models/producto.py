# app/models/producto.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class Producto:
    id: Optional[int] = None
    referencia: str = ""
    codigo_barras: str = ""
    nombre: str = ""
    importe_base: float = 0.0
    tipo_iva_id: Optional[int] = None
    porcentaje_iva: float = 21.0
    activo: bool = True
