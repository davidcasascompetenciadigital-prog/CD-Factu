# app/utils/validators.py
def requerido(valor: str) -> bool:
    return bool(valor and str(valor).strip())

def es_numero_positivo(v) -> bool:
    try:
        return float(v) >= 0
    except (ValueError, TypeError):
        return False

# --- Verificación DNI / NIF / CIF ---

_LETRAS_DNI = "TRWAGMYFPDXBNJZSQVHLCKE"

def calcular_letra_dni(numero: str) -> str:
    try:
        n = int(numero)
    except ValueError:
        return ""
    return _LETRAS_DNI[n % 23]

def validar_dni(texto: str) -> bool:
    texto = (texto or "").strip().upper().replace(" ", "").replace("-", "")
    if len(texto) != 9:
        return False
    if not texto[:8].isdigit():
        return False
    return texto[8] == calcular_letra_dni(texto[:8])

def normalizar_dni(texto: str) -> str:
    """Si se introducen 8 dígitos, añade la letra calculada."""
    t = (texto or "").strip().upper().replace(" ", "").replace("-", "")
    if len(t) == 8 and t.isdigit():
        return t + calcular_letra_dni(t)
    return t

def validar_cif(texto: str) -> bool:
    texto = (texto or "").strip().upper().replace(" ", "").replace("-", "")
    if len(texto) != 9:
        return False
    if not texto[1:8].isdigit():
        return False
    tipo = texto[0]
    if tipo not in "ABCDEFGHJNPQRSUVW":
        return False
    # Cálculo del dígito de control
    suma = 0
    for i, ch in enumerate(texto[1:8]):
        d = int(ch)
        if i % 2 == 0:  # posiciones 1,3,5,7 (0-indexed pares) -> x2
            d *= 2
            if d > 9:
                d -= 9
        suma += d
    control = (10 - (suma % 10)) % 10
    ultimo = texto[8]
    # Si el tipo es P,Q,S,N,W -> letra; resto -> dígito (o letra según caso)
    if tipo in "PQRSNW":
        letras = "JABCDEFGHI"
        return ultimo == letras[control]
    return ultimo == str(control) or ultimo == "JABCDEFGHI"[control]

def normalizar_cif(texto: str) -> str:
    t = (texto or "").strip().upper().replace(" ", "").replace("-", "")
    if len(t) == 8 and t[0].isalpha() and t[1:].isdigit():
        # calcular control
        suma = 0
        for i, ch in enumerate(t[1:]):
            d = int(ch)
            if i % 2 == 0:
                d *= 2
                if d > 9:
                    d -= 9
            suma += d
        control = (10 - (suma % 10)) % 10
        tipo = t[0]
        if tipo in "PQRSNW":
            ctrl = "JABCDEFGHI"[control]
        else:
            ctrl = str(control)
        return t + ctrl
    return t

def validar_nif_cif(texto: str) -> bool:
    t = (texto or "").strip().upper().replace(" ", "").replace("-", "")
    if not t:
        return True  # vacío se valida por requerido aparte
    if len(t) == 9 and t[:8].isdigit():
        return validar_dni(t)
    if len(t) == 9 and t[0].isalpha():
        return validar_cif(t)
    return False
