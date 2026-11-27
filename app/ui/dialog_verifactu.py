# app/ui/dialog_verifactu.py
# Pantalla "Verifactu / AEAT" de una factura: vista previa, envio al entorno de PRUEBAS y envio REAL.
import os
import tempfile
from pathlib import Path
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QTableWidget,
                               QTableWidgetItem, QHeaderView, QMessageBox)
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

from ..db.database import get_connection
from ..services import verifactu as vf
from ..services.qr_generator import generar_qr_png
from ..services.pdf_generator import generar_pdf_factura
from ..config import FACTURAS_DIR
from ..ui.widgets import big_button, info, error, confirm

ESTADOS = {"pendiente": "Pendiente de envío", "correcto": "Aceptado por la AEAT",
           "aceptado_con_errores": "Aceptado con errores", "incorrecto": "Rechazado"}


def _abrir(path):
    try:
        if hasattr(os, "startfile"):
            os.startfile(str(path))
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
    except Exception:
        pass


class VerifactuDialog(QDialog):
    def __init__(self, main_window, factura_id):
        super().__init__(main_window)
        self.main = main_window
        self.fid = factura_id
        conn = get_connection()
        f = conn.execute("SELECT numero, estado FROM facturas WHERE id=?", (factura_id,)).fetchone()
        self.empresa = conn.execute("SELECT * FROM empresa WHERE id=1").fetchone()
        conn.close()
        self.numero = f["numero"]
        self.anulada = f["estado"] == "anulada"
        self.setWindowTitle(f"Verifactu / AEAT - Factura {self.numero}")
        self.setMinimumSize(900, 680)

        v = QVBoxLayout(self)
        v.setSpacing(8)
        t = QLabel(f"Factura {self.numero}")
        t.setStyleSheet("font-size:20px; font-weight:bold;")
        v.addWidget(t)
        exp = QLabel("«Vista previa» no guarda ni envía nada. «Pruebas» envía al entorno de preproducción de la AEAT "
                     "(sin efectos fiscales). «Enviar a la AEAT» registra la factura de verdad y no se puede deshacer: "
                     "solo se corrige con una anulación o una factura rectificativa.")
        exp.setWordWrap(True)
        exp.setStyleSheet("color:#aaaaaa; font-size:13px;")
        v.addWidget(exp)

        self.lbl_avisos = QLabel("")
        self.lbl_avisos.setWordWrap(True)
        self.lbl_avisos.setStyleSheet("color:#ffb74d; font-size:13px;")
        v.addWidget(self.lbl_avisos)

        row = QHBoxLayout()
        b = big_button("Ver cómo quedaría", "secondary")
        b.setMinimumWidth(200)
        b.clicked.connect(self.vista_previa)
        row.addWidget(b)
        b = big_button("Enviar a PRUEBAS AEAT", "primary")
        b.setMinimumWidth(230)
        b.clicked.connect(lambda: self.enviar("pruebas"))
        row.addWidget(b)
        b = big_button("Enviar a la AEAT (REAL)", "danger")
        b.setMinimumWidth(250)
        b.clicked.connect(lambda: self.enviar("real"))
        row.addWidget(b)
        v.addLayout(row)

        row = QHBoxLayout()
        b = big_button("Reintentar pendientes (pruebas)", "secondary")
        b.setMinimumWidth(300)
        b.clicked.connect(lambda: self.reintentar("pruebas"))
        row.addWidget(b)
        b = big_button("Reintentar pendientes (real)", "secondary")
        b.setMinimumWidth(280)
        b.clicked.connect(lambda: self.reintentar("real"))
        row.addWidget(b)
        b = big_button("Cerrar", "secondary")
        b.setMinimumWidth(120)
        b.clicked.connect(self.accept)
        row.addWidget(b)
        row.addStretch()
        v.addLayout(row)

        v.addWidget(QLabel("Historial de esta factura en Verifactu:"))
        self.tabla = QTableWidget(0, 6)
        self.tabla.setHorizontalHeaderLabels(["Entorno", "Operación", "Estado", "CSV", "Fecha", "Detalle"])
        self.tabla.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.setMaximumHeight(160)
        v.addWidget(self.tabla)

        self.lbl_info = QLabel("")
        self.lbl_info.setWordWrap(True)
        v.addWidget(self.lbl_info)
        self.txt = QTextEdit()
        self.txt.setReadOnly(True)
        self.txt.setStyleSheet("font-family: Consolas, monospace; font-size:12px;")
        self.txt.setPlaceholderText("Aquí aparecerá el XML que se enviaría a la AEAT.")
        v.addWidget(self.txt, 1)
        self.refrescar()

    # --- estado
    def refrescar(self):
        regs = vf.registros_de_factura(self.fid)
        self.tabla.setRowCount(0)
        for i, r in enumerate(regs):
            self.tabla.insertRow(i)
            det = (f"{r['codigo_error'] or ''} {r['descripcion_error'] or ''}").strip()
            vals = ["Real" if r["entorno"] == "real" else "Pruebas",
                    "Alta" if r["tipo"] == "alta" else "Anulación", ESTADOS.get(r["estado"], r["estado"]),
                    r["csv"] or "", (r["enviado_en"] or r["creado_en"] or ""), det]
            for c, val in enumerate(vals):
                self.tabla.setItem(i, c, QTableWidgetItem(val))
        av = vf.avisos_previos(self.fid, "pruebas", para_enviar=True)
        self.lbl_avisos.setText("\n".join("⚠ " + a for a in av))

    # --- vista previa
    def vista_previa(self):
        try:
            reg = vf.vista_previa(self.fid, "pruebas")
        except Exception as e:
            error(self, f"No se pudo generar la vista previa: {e}")
            return
        self.txt.setPlainText(reg["xml_envio"].replace("><", ">\n<"))
        self.lbl_info.setText(f"Huella (SHA-256): {reg['huella']}\nQR de cotejo: {reg['qr_url']}\n"
                              f"Tipo de factura: {reg['tipo_factura']} · Esta vista previa no se ha guardado ni enviado.")
        self._pdf_con_qr(reg["qr_url"], marca="VISTA PREVIA - NO ENVIADA A LA AEAT", sufijo="_verifactu_previa")

    def _pdf_con_qr(self, url_qr, marca=None, sufijo="_verifactu"):
        try:
            d = self.main.tab_facturas._cargar_datos_factura(self.fid)
            carpeta = Path(tempfile.gettempdir()) if marca else (FACTURAS_DIR / d["factura"].fecha_emision[:4])
            carpeta.mkdir(parents=True, exist_ok=True)
            qr = carpeta / f"{d['factura'].numero}{sufijo}.png"
            generar_qr_png(url_qr, qr)
            destino = carpeta / f"{d['factura'].numero}{sufijo}.pdf"
            generar_pdf_factura(d["factura"], d["empresa"], d["cliente"], d["lineas"], d["desglose"], str(qr),
                                str(destino), leyenda_qr=vf.LEYENDA_QR, marca=marca)
            _abrir(destino)
            return destino
        except Exception as e:
            error(self, f"No se pudo generar el PDF con el QR de Verifactu: {e}")
            return None

    # --- envios
    def enviar(self, entorno):
        if self.anulada:
            error(self, "Esta factura está anulada. La anulación se envía automáticamente al anularla.")
            return
        av = [a for a in vf.avisos_previos(self.fid, entorno, para_enviar=True)
              if "Falta" in a]
        if av:
            error(self, "Antes de enviar:\n\n" + "\n".join(av))
            return
        if entorno == "real":
            if not self.empresa["verifactu_enabled"]:
                error(self, "El envío real está desactivado. Actívalo en «Mis datos de empresa» → «Activar Verifactu».")
                return
            if not confirm(self, f"Vas a REGISTRAR la factura {self.numero} en la Agencia Tributaria.\n\n"
                                 "Esto tiene efectos fiscales y no se puede deshacer. ¿Quieres continuar?"):
                return
            if not confirm(self, "Última confirmación: ¿has probado antes en el entorno de pruebas y los datos de la "
                                 "factura son correctos?"):
                return
        else:
            if not confirm(self, f"Se enviará la factura {self.numero} al entorno de PRUEBAS de la AEAT "
                                 "(no tiene efectos fiscales). ¿Continuar?"):
                return
        try:
            try:
                vf.registrar(self.fid, entorno, "alta")
            except vf.VerifactuError as e:
                if "ya tiene un registro" not in str(e):
                    raise
            res = vf.enviar_pendientes(entorno)
        except Exception as e:
            error(self, f"No se pudo completar el envío: {e}")
            self.refrescar()
            return
        (info if res.get("ok") else error)(self, res.get("mensaje", ""))
        self.refrescar()
        regs = [r for r in vf.registros_de_factura(self.fid) if r["entorno"] == entorno and r["tipo"] == "alta"
                and r["estado"] in ("correcto", "aceptado_con_errores", "pendiente")]
        if regs:
            self._pdf_con_qr(regs[-1]["qr_url"])

    def reintentar(self, entorno):
        n = vf.pendientes(entorno)
        if n == 0:
            info(self, "No hay registros pendientes en este entorno.")
            return
        if entorno == "real" and not confirm(self, f"Se enviarán {n} registro(s) pendiente(s) a la AEAT REAL. ¿Continuar?"):
            return
        res = vf.enviar_pendientes(entorno)
        (info if res.get("ok") else error)(self, res.get("mensaje", ""))
        self.refrescar()
