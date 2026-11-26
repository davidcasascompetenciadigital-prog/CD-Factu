# app/models/cliente.py
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Contacto:
    id: Optional[int] = None
    nombre: str = ""
    telefono: str = ""
    email: str = ""
    tipo: str = "Facturación"  # Facturación / Administrativo / Comercial

@dataclass
class Cliente:
    id: Optional[int] = None
    nombre: str = ""
    apellidos: str = ""
    empresa: Optional[str] = None
    dni_cif: str = ""
    direccion: str = ""
    cp: str = ""
    ciudad: str = ""
    comunidad_autonoma: str = ""
    pais: str = "España"
    contactos: list = field(default_factory=list)

    def nombre_mostrar(self) -> str:
        if self.empresa:
            return f"Empresa: {self.empresa}"
        return f"{self.nombre} {self.apellidos}".strip()
