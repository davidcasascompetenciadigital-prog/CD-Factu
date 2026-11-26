# app/models/empresa.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class Empresa:
    nombre: str = ""
    nif: str = ""
    direccion: str = ""
    cp: str = ""
    ciudad: str = ""
    comunidad_autonoma: str = ""
    pais: str = "España"
    logo_path: Optional[str] = None
    tipos_iva: list = None  # list of dict {id, porcentaje, descripcion, activo}
    def __post_init__(self):
        if self.tipos_iva is None:
            self.tipos_iva = []
