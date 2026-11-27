# app/services/verifactu.py
# Registros de facturacion VERI*FACTU (Orden HAC/1177/2024) y remision a la AEAT.
#
# - Huella SHA-256 encadenada (alta y anulacion).
# - XML de RegistroAlta / RegistroAnulacion segun el diseno de la AEAT (SuministroLR / SuministroInformacion).
# - URL del QR de cotejo.
# - Envio SOAP 1.1 con certificado cliente (TLS mutuo) al entorno de PRUEBAS o REAL.
#
# IMPORTANTE: el envio real tiene efectos fiscales. Probar siempre antes en el entorno de pruebas.
import hashlib
import os
import tempfile
import uuid
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from datetime import datetime, date
from urllib.parse import quote
from xml.sax.saxutils import escape

from ..config import (APP_VERSION, SISTEMA_NOMBRE, SISTEMA_ID, PRODUCTOR_NOMBRE, PRODUCTOR_NIF)
from ..db.database import get_connection

NS_SOAP = "http://schemas.xmlsoap.org/soap/envelope/"
_BASE_NS = "https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tike/cont/ws/"
NS_SUM = _BASE_NS + "SuministroLR.xsd"
NS_SUM1 = _BASE_NS + "SuministroInformacion.xsd"

# Endpoints del servicio web (verificar contra el WSDL oficial si la AEAT los cambia).
ENDPOINTS = {
    "pruebas": "https://prewww1.aeat.es/wlpl/TIKE-CONT/ws/SistemaFacturacion/VerifactuSOAP",
    "real": "https://www1.agenciatributaria.gob.es/wlpl/TIKE-CONT/ws/SistemaFacturacion/VerifactuSOAP",
}
QR_BASE = {
    "pruebas": "https://prewww2.aeat.es/wlpl/TIKE-CONT/ValidarQR",
    "real": "https://www2.agenciatributaria.gob.es/wlpl/TIKE-CONT/ValidarQR",
}
LEYENDA_QR = "Factura verificable en la sede electrónica de la AEAT"
MAX_REGISTROS_ENVIO = 1000
ESPERA_POR_DEFECTO = 60  # segundos entre envios (la AEAT lo actualiza en cada respuesta)


# ----------------------------------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------------------------------
def fecha_aeat(iso: str) -> str:
    """YYYY-MM-DD -> dd-mm-yyyy"""
    return date.fromisoformat(iso[:10]).strftime("%d-%m-%Y")


def num(x) -> str:
    return f"{float(x):.2f}"


def ahora_huso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_upper(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest().upper()


def huella_alta(id_emisor, num_serie, fecha_exp, tipo_factura, cuota_total, importe_total,
                huella_anterior, fecha_hora_huso) -> str:
    cadena = (f"IDEmisorFactura={id_emisor.strip()}&NumSerieFactura={num_serie.strip()}"
              f"&FechaExpedicionFactura={fecha_exp.strip()}&TipoFactura={tipo_factura.strip()}"
              f"&CuotaTotal={cuota_total.strip()}&ImporteTotal={importe_total.strip()}"
              f"&Huella={(huella_anterior or '').strip()}&FechaHoraHusoGenRegistro={fecha_hora_huso.strip()}")
    return sha256_upper(cadena)


def huella_anulacion(id_emisor, num_serie, fecha_exp, huella_anterior, fecha_hora_huso) -> str:
    cadena = (f"IDEmisorFacturaAnulada={id_emisor.strip()}&NumSerieFacturaAnulada={num_serie.strip()}"
              f"&FechaExpedicionFacturaAnulada={fecha_exp.strip()}"
              f"&Huella={(huella_anterior or '').strip()}&FechaHoraHusoGenRegistro={fecha_hora_huso.strip()}")
    return sha256_upper(cadena)


def qr_url(entorno: str, nif: str, num_serie: str, fecha_iso: str, importe: float) -> str:
    return (f"{QR_BASE[entorno]}?nif={quote(nif.strip())}&numserie={quote(num_serie.strip(), safe='')}"
            f"&fecha={fecha_aeat(fecha_iso)}&importe={num(importe)}")


def _x(valor) -> str:
    return escape(str(valor if valor is not None else "").strip())


def numero_instalacion(conn) -> str:
    r = conn.execute("SELECT valor FROM ajustes WHERE clave='numero_instalacion'").fetchone()
    if r and r["valor"]:
        return r["valor"]
    nuevo = uuid.uuid4().hex[:20].upper()
    conn.execute("INSERT OR REPLACE INTO ajustes (clave, valor) VALUES ('numero_instalacion', ?)", (nuevo,))
    conn.commit()
    return nuevo


def _bloque_sistema(conn) -> str:
    return (
        "<sum1:SistemaInformatico>"
        f"<sum1:NombreRazon>{_x(PRODUCTOR_NOMBRE)}</sum1:NombreRazon>"
        f"<sum1:NIF>{_x(PRODUCTOR_NIF or 'XXXXXXXXX')}</sum1:NIF>"
        f"<sum1:NombreSistemaInformatico>{_x(SISTEMA_NOMBRE)}</sum1:NombreSistemaInformatico>"
        f"<sum1:IdSistemaInformatico>{_x(SISTEMA_ID)}</sum1:IdSistemaInformatico>"
        f"<sum1:Version>{_x(APP_VERSION)}</sum1:Version>"
        f"<sum1:NumeroInstalacion>{_x(numero_instalacion(conn))}</sum1:NumeroInstalacion>"
        "<sum1:TipoUsoPosibleSoloVerifactu>N</sum1:TipoUsoPosibleSoloVerifactu>"
        "<sum1:TipoUsoPosibleMultiOT>N</sum1:TipoUsoPosibleMultiOT>"
        "<sum1:IndicadorMultiplesOT>N</sum1:IndicadorMultiplesOT>"
        "</sum1:SistemaInformatico>")


def _ultimo_registro(conn, entorno):
    return conn.execute("""SELECT id_emisor, num_serie, fecha_expedicion, huella FROM verifactu_registros
                           WHERE entorno=? ORDER BY id DESC LIMIT 1""", (entorno,)).fetchone()


def _bloque_encadenamiento(ant) -> str:
    if not ant:
        return "<sum1:Encadenamiento><sum1:PrimerRegistro>S</sum1:PrimerRegistro></sum1:Encadenamiento>"
    return ("<sum1:Encadenamiento><sum1:RegistroAnterior>"
            f"<sum1:IDEmisorFactura>{_x(ant['id_emisor'])}</sum1:IDEmisorFactura>"
            f"<sum1:NumSerieFactura>{_x(ant['num_serie'])}</sum1:NumSerieFactura>"
            f"<sum1:FechaExpedicionFactura>{_x(ant['fecha_expedicion'])}</sum1:FechaExpedicionFactura>"
            f"<sum1:Huella>{_x(ant['huella'])}</sum1:Huella>"
            "</sum1:RegistroAnterior></sum1:Encadenamiento>")


# ----------------------------------------------------------------------------------------------
# Construccion de registros
# ----------------------------------------------------------------------------------------------
class VerifactuError(Exception):
    pass


def _datos_factura(conn, factura_id):
    f = conn.execute("SELECT * FROM facturas WHERE id=?", (factura_id,)).fetchone()
    if not f:
        raise VerifactuError("No se encontró la factura.")
    emp = conn.execute("SELECT * FROM empresa WHERE id=1").fetchone()
    cli = conn.execute("SELECT * FROM clientes WHERE id=?", (f["cliente_id"],)).fetchone()
    lineas = conn.execute("SELECT concepto FROM lineas_factura WHERE factura_id=? ORDER BY orden", (factura_id,)).fetchall()
    desglose = conn.execute("""SELECT porcentaje, SUM(base) base, SUM(cuota) cuota FROM desglose_iva_factura
                               WHERE factura_id=? GROUP BY porcentaje ORDER BY porcentaje DESC""", (factura_id,)).fetchall()
    return f, emp, cli, lineas, desglose


def avisos_previos(factura_id, entorno, para_enviar=True):
    """Lista de avisos/bloqueos antes de generar o enviar."""
    conn = get_connection()
    try:
        f, emp, cli, lineas, desglose = _datos_factura(conn, factura_id)
    finally:
        conn.close()
    av = []
    if not (emp["nif"] or "").strip():
        av.append("Falta el NIF de tu empresa (Mis datos de empresa).")
    if not (emp["nombre"] or "").strip():
        av.append("Falta el nombre o razón social de tu empresa.")
    if not (cli["dni_cif"] or "").strip():
        av.append("El cliente no tiene NIF/CIF: la factura se registrará como simplificada (F2).")
    if any(abs(d["porcentaje"]) < 1e-9 for d in desglose):
        av.append("Hay líneas con IVA 0 %: se registran como exentas (E1). Revisa la causa de exención con tu asesor.")
    if para_enviar:
        if not PRODUCTOR_NIF.strip():
            av.append("Falta el NIF del productor del software (PRODUCTOR_NIF en app/config.py).")
        if not (emp["verifactu_cert_path"] or "").strip():
            av.append("Falta el certificado electrónico (Mis datos de empresa → Verifactu).")
    return av


def _construir_alta(conn, factura_id, entorno):
    f, emp, cli, lineas, desglose = _datos_factura(conn, factura_id)
    nif = (emp["nif"] or "").strip().upper()
    nombre_emisor = (emp["nombre"] or "").strip()
    num_serie = f["numero"]
    fecha_exp = fecha_aeat(f["fecha_emision"])
    cuota_total, importe_total = num(f["total_iva"]), num(f["total_factura"])
    nif_cli = (cli["dni_cif"] or "").strip().upper()
    tipo = "F1" if nif_cli else "F2"
    nombre_cli = (cli["empresa"] or f"{cli['nombre']} {cli['apellidos'] or ''}").strip()

    desc = "; ".join(l["concepto"].split("\n", 1)[0] for l in lineas)[:500] or "Prestación de servicios"

    det = ""
    for d in desglose:
        base, cuota, pct = num(d["base"]), num(d["cuota"]), d["porcentaje"]
        pct_txt = f"{pct:g}"
        if abs(pct) < 1e-9:
            cal = "<sum1:OperacionExenta>E1</sum1:OperacionExenta>"
            det += ("<sum1:DetalleDesglose><sum1:ClaveRegimen>01</sum1:ClaveRegimen>" + cal +
                    f"<sum1:BaseImponibleOimporteNoSujeto>{base}</sum1:BaseImponibleOimporteNoSujeto>"
                    "</sum1:DetalleDesglose>")
        else:
            det += ("<sum1:DetalleDesglose><sum1:ClaveRegimen>01</sum1:ClaveRegimen>"
                    "<sum1:CalificacionOperacion>S1</sum1:CalificacionOperacion>"
                    f"<sum1:TipoImpositivo>{pct_txt}</sum1:TipoImpositivo>"
                    f"<sum1:BaseImponibleOimporteNoSujeto>{base}</sum1:BaseImponibleOimporteNoSujeto>"
                    f"<sum1:CuotaRepercutida>{cuota}</sum1:CuotaRepercutida></sum1:DetalleDesglose>")

    dest = ""
    if tipo == "F1":
        dest = ("<sum1:Destinatarios><sum1:IDDestinatario>"
                f"<sum1:NombreRazon>{_x(nombre_cli)}</sum1:NombreRazon><sum1:NIF>{_x(nif_cli)}</sum1:NIF>"
                "</sum1:IDDestinatario></sum1:Destinatarios>")

    rechazo = conn.execute("""SELECT 1 FROM verifactu_registros WHERE factura_id=? AND entorno=? AND tipo='alta'
                              AND estado='incorrecto'""", (factura_id, entorno)).fetchone()
    subsana = ("<sum1:Subsanacion>S</sum1:Subsanacion><sum1:RechazoPrevio>X</sum1:RechazoPrevio>" if rechazo else "")
    ant = _ultimo_registro(conn, entorno)
    huella_ant = ant["huella"] if ant else ""
    ts = ahora_huso()
    huella = huella_alta(nif, num_serie, fecha_exp, tipo, cuota_total, importe_total, huella_ant, ts)

    xml = (
        "<sum1:RegistroAlta><sum1:IDVersion>1.0</sum1:IDVersion>"
        "<sum1:IDFactura>"
        f"<sum1:IDEmisorFactura>{_x(nif)}</sum1:IDEmisorFactura>"
        f"<sum1:NumSerieFactura>{_x(num_serie)}</sum1:NumSerieFactura>"
        f"<sum1:FechaExpedicionFactura>{fecha_exp}</sum1:FechaExpedicionFactura>"
        "</sum1:IDFactura>"
        f"<sum1:NombreRazonEmisor>{_x(nombre_emisor)}</sum1:NombreRazonEmisor>"
        f"{subsana}"
        f"<sum1:TipoFactura>{tipo}</sum1:TipoFactura>"
        f"<sum1:DescripcionOperacion>{_x(desc)}</sum1:DescripcionOperacion>"
        f"{dest}"
        f"<sum1:Desglose>{det}</sum1:Desglose>"
        f"<sum1:CuotaTotal>{cuota_total}</sum1:CuotaTotal>"
        f"<sum1:ImporteTotal>{importe_total}</sum1:ImporteTotal>"
        f"{_bloque_encadenamiento(ant)}"
        f"{_bloque_sistema(conn)}"
        f"<sum1:FechaHoraHusoGenRegistro>{ts}</sum1:FechaHoraHusoGenRegistro>"
        "<sum1:TipoHuella>01</sum1:TipoHuella>"
        f"<sum1:Huella>{huella}</sum1:Huella>"
        "</sum1:RegistroAlta>")
    return {
        "factura_id": factura_id, "entorno": entorno, "tipo": "alta", "id_emisor": nif,
        "num_serie": num_serie, "fecha_expedicion": fecha_exp, "fecha_hora_huso": ts,
        "huella": huella, "huella_anterior": huella_ant, "xml_registro": xml,
        "qr_url": qr_url(entorno, nif, num_serie, f["fecha_emision"], f["total_factura"]),
        "nombre_emisor": nombre_emisor, "tipo_factura": tipo,
    }


def _construir_anulacion(conn, factura_id, entorno):
    f, emp, cli, lineas, desglose = _datos_factura(conn, factura_id)
    nif = (emp["nif"] or "").strip().upper()
    num_serie = f["numero"]
    fecha_exp = fecha_aeat(f["fecha_emision"])
    ant = _ultimo_registro(conn, entorno)
    huella_ant = ant["huella"] if ant else ""
    ts = ahora_huso()
    huella = huella_anulacion(nif, num_serie, fecha_exp, huella_ant, ts)
    xml = (
        "<sum1:RegistroAnulacion><sum1:IDVersion>1.0</sum1:IDVersion>"
        "<sum1:IDFactura>"
        f"<sum1:IDEmisorFacturaAnulada>{_x(nif)}</sum1:IDEmisorFacturaAnulada>"
        f"<sum1:NumSerieFacturaAnulada>{_x(num_serie)}</sum1:NumSerieFacturaAnulada>"
        f"<sum1:FechaExpedicionFacturaAnulada>{fecha_exp}</sum1:FechaExpedicionFacturaAnulada>"
        "</sum1:IDFactura>"
        f"{_bloque_encadenamiento(ant)}"
        f"{_bloque_sistema(conn)}"
        f"<sum1:FechaHoraHusoGenRegistro>{ts}</sum1:FechaHoraHusoGenRegistro>"
        "<sum1:TipoHuella>01</sum1:TipoHuella>"
        f"<sum1:Huella>{huella}</sum1:Huella>"
        "</sum1:RegistroAnulacion>")
    return {
        "factura_id": factura_id, "entorno": entorno, "tipo": "anulacion", "id_emisor": nif,
        "num_serie": num_serie, "fecha_expedicion": fecha_exp, "fecha_hora_huso": ts,
        "huella": huella, "huella_anterior": huella_ant, "xml_registro": xml, "qr_url": None,
        "nombre_emisor": (emp["nombre"] or "").strip(), "tipo_factura": "",
    }


def envoltorio_soap(nif_obligado: str, nombre_obligado: str, registros_xml: list) -> str:
    cuerpo = "".join(f"<sum:RegistroFactura>{r}</sum:RegistroFactura>" for r in registros_xml)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<soapenv:Envelope xmlns:soapenv="{NS_SOAP}" xmlns:sum="{NS_SUM}" xmlns:sum1="{NS_SUM1}">'
        "<soapenv:Header/><soapenv:Body><sum:RegFactuSistemaFacturacion><sum:Cabecera>"
        "<sum1:ObligadoEmision>"
        f"<sum1:NombreRazon>{_x(nombre_obligado)}</sum1:NombreRazon><sum1:NIF>{_x(nif_obligado)}</sum1:NIF>"
        "</sum1:ObligadoEmision></sum:Cabecera>"
        f"{cuerpo}</sum:RegFactuSistemaFacturacion></soapenv:Body></soapenv:Envelope>")


def vista_previa(factura_id: int, entorno: str = "pruebas") -> dict:
    """Genera el registro, el XML y el QR SIN guardar nada ni enviar nada."""
    conn = get_connection()
    try:
        reg = _construir_alta(conn, factura_id, entorno)
        emp = conn.execute("SELECT nif, nombre FROM empresa WHERE id=1").fetchone()
    finally:
        conn.close()
    reg["xml_envio"] = envoltorio_soap(emp["nif"].strip().upper(), emp["nombre"], [reg["xml_registro"]])
    reg["avisos"] = avisos_previos(factura_id, entorno, para_enviar=False)
    return reg


def registrar(factura_id: int, entorno: str, tipo: str = "alta") -> int:
    """Guarda el registro (pendiente de envio) en la cadena del entorno. Devuelve su id."""
    if entorno not in ENDPOINTS:
        raise VerifactuError("Entorno no válido.")
    conn = get_connection()
    try:
        if tipo == "alta":
            ya = conn.execute("""SELECT 1 FROM verifactu_registros WHERE factura_id=? AND entorno=? AND tipo='alta'
                                 AND estado IN ('pendiente','correcto','aceptado_con_errores')""",
                              (factura_id, entorno)).fetchone()
            if ya:
                raise VerifactuError("Esta factura ya tiene un registro de alta en este entorno.")
            reg = _construir_alta(conn, factura_id, entorno)
        else:
            reg = _construir_anulacion(conn, factura_id, entorno)
        cur = conn.execute("""INSERT INTO verifactu_registros (factura_id, entorno, tipo, id_emisor, num_serie,
                              fecha_expedicion, fecha_hora_huso, huella, huella_anterior, xml_registro, qr_url)
                              VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                           (reg["factura_id"], entorno, reg["tipo"], reg["id_emisor"], reg["num_serie"],
                            reg["fecha_expedicion"], reg["fecha_hora_huso"], reg["huella"],
                            reg["huella_anterior"], reg["xml_registro"], reg["qr_url"]))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def registros_de_factura(factura_id: int):
    conn = get_connection()
    rows = conn.execute("""SELECT id, entorno, tipo, estado, csv, codigo_error, descripcion_error, enviado_en,
                                  creado_en, huella, qr_url FROM verifactu_registros
                           WHERE factura_id=? ORDER BY id""", (factura_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def qr_url_registrado(factura_id: int):
    """URL del QR del ultimo registro de alta de la factura (real si existe, si no pruebas)."""
    conn = get_connection()
    r = conn.execute("""SELECT qr_url, entorno FROM verifactu_registros WHERE factura_id=? AND tipo='alta'
                        ORDER BY (entorno='real') DESC, id DESC LIMIT 1""", (factura_id,)).fetchone()
    conn.close()
    return (r["qr_url"], r["entorno"]) if r else (None, None)


# ----------------------------------------------------------------------------------------------
# Certificado y envio
# ----------------------------------------------------------------------------------------------
@contextmanager
def _pem_temporales(cert_path, key_path, password):
    """Devuelve (cert.pem, key.pem) temporales sin contrasena para usarlos como certificado cliente.
    Admite .p12/.pfx (con contrasena) o par PEM (clave opcionalmente cifrada). Se borran al terminar."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.serialization import pkcs12
    pwd = password.encode("utf-8") if password else None
    ext = os.path.splitext(cert_path)[1].lower()
    if ext in (".p12", ".pfx"):
        with open(cert_path, "rb") as f:
            key, cert, extra = pkcs12.load_key_and_certificates(f.read(), pwd)
        if key is None or cert is None:
            raise VerifactuError("El archivo .p12/.pfx no contiene certificado y clave privada.")
        chain = [cert] + list(extra or [])
    else:
        if not key_path:
            raise VerifactuError("Falta la clave privada del certificado.")
        with open(cert_path, "rb") as f:
            cert_bytes = f.read()
        with open(key_path, "rb") as f:
            key = serialization.load_pem_private_key(f.read(), pwd)
        from cryptography import x509
        chain = x509.load_pem_x509_certificates(cert_bytes)
    cert_pem = b"".join(c.public_bytes(serialization.Encoding.PEM) for c in chain)
    key_pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL,
                                serialization.NoEncryption())
    d = tempfile.mkdtemp(prefix="cdfactu_")
    cp, kp = os.path.join(d, "c.pem"), os.path.join(d, "k.pem")
    try:
        for path, data in ((cp, cert_pem), (kp, key_pem)):
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "wb") as f:
                f.write(data)
        yield cp, kp
    finally:
        for p in (cp, kp):
            try:
                os.remove(p)
            except OSError:
                pass
        try:
            os.rmdir(d)
        except OSError:
            pass


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _texto(el, nombre):
    for e in el.iter():
        if _local(e.tag) == nombre:
            return (e.text or "").strip()
    return ""


def interpretar_respuesta(xml_texto: str) -> dict:
    """Extrae CSV, estado global, tiempo de espera y estado por registro de la respuesta SOAP."""
    raiz = ET.fromstring(xml_texto)
    fault = next((e for e in raiz.iter() if _local(e.tag) == "Fault"), None)
    if fault is not None:
        return {"fault": _texto(fault, "faultstring") or "Error SOAP", "lineas": []}
    lineas = []
    for rl in (e for e in raiz.iter() if _local(e.tag) == "RespuestaLinea"):
        idf = next((e for e in rl if _local(e.tag) == "IDFactura"), None)
        lineas.append({
            "num_serie": (_texto(idf, "NumSerieFactura") or _texto(idf, "NumSerieFacturaAnulada")) if idf is not None else "",
            "tipo_operacion": _texto(rl, "TipoOperacion"),
            "estado": next((e.text or "" for e in rl if _local(e.tag) == "EstadoRegistro"), "").strip(),
            "codigo": next((e.text or "" for e in rl if _local(e.tag) == "CodigoErrorRegistro"), "").strip(),
            "descripcion": next((e.text or "" for e in rl if _local(e.tag) == "DescripcionErrorRegistro"), "").strip(),
        })
    espera = _texto(raiz, "TiempoEsperaEnvio")
    return {"fault": None, "csv": _texto(raiz, "CSV"), "estado_envio": _texto(raiz, "EstadoEnvio"),
            "espera": int(espera) if espera.isdigit() else ESPERA_POR_DEFECTO, "lineas": lineas}


def segundos_hasta_poder_enviar(entorno: str) -> int:
    conn = get_connection()
    r = conn.execute("""SELECT enviado_en, tiempo_espera FROM verifactu_envios
                        WHERE entorno=? AND estado_envio IS NOT NULL AND estado_envio!='error'
                        ORDER BY id DESC LIMIT 1""", (entorno,)).fetchone()
    conn.close()
    if not r:
        return 0
    try:
        ultimo = datetime.strptime(r["enviado_en"], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return 0
    espera = r["tiempo_espera"] or ESPERA_POR_DEFECTO
    return max(0, int(espera - (datetime.now() - ultimo).total_seconds()))


def pendientes(entorno: str) -> int:
    conn = get_connection()
    n = conn.execute("SELECT COUNT(*) c FROM verifactu_registros WHERE entorno=? AND estado='pendiente'",
                     (entorno,)).fetchone()["c"]
    conn.close()
    return n


def enviar_pendientes(entorno: str, post=None) -> dict:
    """Envia a la AEAT todos los registros pendientes del entorno (maximo 1000) en un solo mensaje.
    `post` permite inyectar un cliente HTTP (pruebas). Devuelve {'ok', 'mensaje', 'lineas', 'csv'}."""
    if entorno not in ENDPOINTS:
        return {"ok": False, "mensaje": "Entorno no válido."}
    conn = get_connection()
    emp = conn.execute("SELECT * FROM empresa WHERE id=1").fetchone()
    pend = conn.execute("""SELECT * FROM verifactu_registros WHERE entorno=? AND estado='pendiente'
                           ORDER BY id LIMIT ?""", (entorno, MAX_REGISTROS_ENVIO)).fetchall()
    conn.close()
    if not pend:
        return {"ok": True, "mensaje": "No hay registros pendientes de envío.", "lineas": []}
    if not PRODUCTOR_NIF.strip():
        return {"ok": False, "mensaje": "Falta el NIF del productor del software (PRODUCTOR_NIF en app/config.py)."}
    cert, key, pwd = (emp["verifactu_cert_path"] or "").strip(), (emp["verifactu_key_path"] or "").strip(), emp["verifactu_cert_password"] or ""
    if not cert:
        return {"ok": False, "mensaje": "Falta el certificado electrónico en 'Mis datos de empresa'."}
    espera = segundos_hasta_poder_enviar(entorno)
    if espera > 0 and len(pend) < MAX_REGISTROS_ENVIO:
        return {"ok": False, "espera": espera,
                "mensaje": f"La AEAT exige esperar entre envíos. Quedan {espera} s; el registro queda pendiente y puedes reintentar."}

    xml = envoltorio_soap(emp["nif"].strip().upper(), emp["nombre"], [p["xml_registro"] for p in pend])
    headers = {"Content-Type": "text/xml; charset=utf-8", "SOAPAction": ""}
    try:
        if post is None:
            import requests
            def post(url, data, headers, cert_pair):
                return requests.post(url, data=data, headers=headers, cert=cert_pair, timeout=60)
        with _pem_temporales(cert, key, pwd) as pair:
            resp = post(ENDPOINTS[entorno], xml.encode("utf-8"), headers, pair)
        texto = resp.text
    except Exception as e:  # conexion, certificado, TLS...
        _log_envio(entorno, len(pend), "error", None, None, f"{type(e).__name__}: {e}", xml, None)
        return {"ok": False, "mensaje": f"No se pudo enviar (los registros siguen pendientes): {e}"}

    try:
        r = interpretar_respuesta(texto)
    except ET.ParseError:
        _log_envio(entorno, len(pend), "error", None, None, f"Respuesta no válida (HTTP {resp.status_code})", xml, texto)
        return {"ok": False, "mensaje": f"La AEAT devolvió una respuesta no interpretable (HTTP {resp.status_code}). "
                                        "Los registros siguen pendientes."}
    if r["fault"]:
        _log_envio(entorno, len(pend), "error", None, None, r["fault"], xml, texto)
        return {"ok": False, "mensaje": f"La AEAT rechazó el mensaje completo: {r['fault']}"}

    mapa = {"Correcto": "correcto", "AceptadoConErrores": "aceptado_con_errores", "Incorrecto": "incorrecto"}
    conn = get_connection()
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pendientes_por_serie = {}
    for p in pend:
        pendientes_por_serie.setdefault((p["num_serie"], p["tipo"]), []).append(p["id"])
    for ln in r["lineas"]:
        tipo = "anulacion" if ln["tipo_operacion"] == "Anulacion" else "alta"
        ids = pendientes_por_serie.get((ln["num_serie"], tipo)) or pendientes_por_serie.get((ln["num_serie"], "alta"), [])
        if not ids:
            continue
        rid = ids.pop(0)
        conn.execute("""UPDATE verifactu_registros SET estado=?, csv=?, codigo_error=?, descripcion_error=?, enviado_en=?
                        WHERE id=?""", (mapa.get(ln["estado"], "incorrecto"), r["csv"], ln["codigo"] or None,
                                        ln["descripcion"] or None, ahora, rid))
    conn.commit()
    conn.close()
    _log_envio(entorno, len(pend), r["estado_envio"] or "Correcto", r["csv"], r["espera"], "", xml, texto)
    malos = [ln for ln in r["lineas"] if ln["estado"] != "Correcto"]
    msg = f"Estado del envío: {r['estado_envio'] or '-'}. CSV: {r['csv'] or '-'}."
    if malos:
        msg += "\n" + "\n".join(f"· {l['num_serie']}: {l['estado']} {l['codigo']} {l['descripcion']}".strip() for l in malos)
    return {"ok": not malos, "mensaje": msg, "lineas": r["lineas"], "csv": r["csv"]}


def _log_envio(entorno, n, estado, csv, espera, mensaje, xml_env, xml_resp):
    conn = get_connection()
    conn.execute("""INSERT INTO verifactu_envios (entorno, n_registros, estado_envio, csv, tiempo_espera, mensaje,
                    xml_enviado, xml_respuesta) VALUES (?,?,?,?,?,?,?,?)""",
                 (entorno, n, estado, csv, espera, mensaje, xml_env, xml_resp))
    conn.commit()
    conn.close()
