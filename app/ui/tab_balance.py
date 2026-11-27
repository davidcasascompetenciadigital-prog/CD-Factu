# app/ui/tab_balance.py
from datetime import date
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QTextBrowser,
                               QFileDialog)
from ..db.database import get_connection
from ..ui.widgets import big_button, title_label, help_popup, info, error
from ..utils.messages import ayuda
from ..services import balance as svc


def eur(x: float) -> str:
    s = f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s} €"


class TabBalance(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.datos = None
        v = QVBoxLayout(self)
        v.setSpacing(8)
        v.addWidget(title_label("Balance trimestral"))

        row = QHBoxLayout()
        row.addWidget(QLabel("Año:"))
        self.cmb_anio = QComboBox()
        hoy = date.today()
        for a in range(hoy.year + 1, hoy.year - 6, -1):
            self.cmb_anio.addItem(str(a), a)
        self.cmb_anio.setCurrentIndex(self.cmb_anio.findData(hoy.year))
        row.addWidget(self.cmb_anio)
        row.addWidget(QLabel("Trimestre:"))
        self.cmb_trim = QComboBox()
        for t in range(1, 5):
            self.cmb_trim.addItem(f"{t}T", t)
        self.cmb_trim.setCurrentIndex((hoy.month - 1) // 3)
        row.addWidget(self.cmb_trim)
        self.cmb_anio.currentIndexChanged.connect(self.refrescar)
        self.cmb_trim.currentIndexChanged.connect(self.refrescar)
        b = big_button("Exportar hoja 303 (PDF)", "primary")
        b.setMinimumWidth(240)
        b.clicked.connect(self.exportar_pdf)
        row.addWidget(b)
        b = big_button("Exportar CSV", "secondary")
        b.clicked.connect(self.exportar_csv)
        row.addWidget(b)
        b = big_button("?", "secondary")
        b.setFixedWidth(60)
        b.clicked.connect(lambda: help_popup(self, ayuda("balance")))
        row.addWidget(b)
        row.addStretch()
        v.addLayout(row)

        self.vista = QTextBrowser()
        self.vista.setOpenExternalLinks(True)
        v.addWidget(self.vista, 1)
        self.refrescar()

    def _empresa(self):
        conn = get_connection()
        r = conn.execute("SELECT nombre, nif FROM empresa WHERE id=1").fetchone()
        conn.close()
        return dict(r) if r else {}

    def refrescar(self, *_):
        b = svc.calcular(self.cmb_anio.currentData(), self.cmb_trim.currentData())
        self.datos = b
        i, g, c = b["ingresos"], b["gastos"], b["cobros"]
        res = b["resultado_iva"]
        if res > 0:
            txt_res, col = f"A INGRESAR: {eur(res)}", "#ef9a9a"
        elif res < 0:
            txt_res, col = f"A COMPENSAR / DEVOLVER: {eur(-res)}", "#a5d6a7"
        else:
            txt_res, col = "Resultado: 0,00 €", "#f5f5f5"

        def filas_iva(d):
            if not d:
                return "<tr><td colspan='3'><i>Sin movimientos</i></td></tr>"
            return "".join(f"<tr><td>IVA {p:g}%</td><td align='right'>{eur(bs)}</td><td align='right'>{eur(cu)}</td></tr>"
                           for p, (bs, cu) in d.items())

        formas = "".join(f"<tr><td>{f}</td><td align='right'>{eur(t)}</td></tr>" for f, t in c["por_forma"]) \
            or "<tr><td colspan='2'><i>Sin cobros en el trimestre</i></td></tr>"
        aviso_anul = f" ({i['anuladas']} anulada/s no incluida/s)" if i["anuladas"] else ""
        html = f"""
        <style>td,th{{padding:4px 10px;}} h3{{color:#66bb6a;margin-top:14px;}} th{{text-align:left;color:#aaa;}}</style>
        <h2>{b['trimestre']}T {b['anio']} <small style='color:#aaa'>({b['inicio']} a {b['fin']})</small></h2>
        <p style='font-size:20px;font-weight:bold;color:{col};'>Modelo 303 · {txt_res}</p>
        <p style='color:#aaa'>Plazo de presentación: {b['plazo']}.</p>

        <h3>Ingresos · {i['n']} factura(s){aviso_anul}</h3>
        <table><tr><th>Concepto</th><th>Base</th><th>IVA repercutido</th></tr>{filas_iva(b['devengado'])}
        <tr><td><b>Total</b></td><td align='right'><b>{eur(i['base'])}</b></td><td align='right'><b>{eur(b['cuota_devengada'])}</b></td></tr></table>
        <p>Total facturado (con IVA): <b>{eur(i['total'])}</b></p>

        <h3>Cobros</h3>
        <table>{formas}<tr><td><b>Cobrado en el trimestre</b></td><td align='right'><b>{eur(c['total'])}</b></td></tr></table>
        <p>Pendiente de cobro de las facturas del trimestre: <b>{eur(i['pendiente_cobro'])}</b></p>

        <h3>Gastos · {g['n']} factura(s) recibida(s)</h3>
        <table><tr><th>Concepto</th><th>Base</th><th>IVA soportado deducible</th></tr>{filas_iva(b['soportado'])}
        <tr><td><b>Total</b></td><td align='right'><b>{eur(g['base'])}</b></td><td align='right'><b>{eur(b['cuota_deducible'])}</b></td></tr></table>
        <p>Total gastos (con IVA): <b>{eur(g['total'])}</b> · Pagado: {eur(g['pagado'])} · Pendiente de pago: <b>{eur(g['por_pagar'])}</b></p>

        <h3>Resultado</h3>
        <table>
        <tr><td>IVA repercutido (ventas)</td><td align='right'>{eur(b['cuota_devengada'])}</td></tr>
        <tr><td>− IVA soportado deducible (gastos)</td><td align='right'>{eur(b['cuota_deducible'])}</td></tr>
        <tr><td><b>Resultado IVA (modelo 303)</b></td><td align='right'><b>{eur(res)}</b></td></tr>
        <tr><td>Beneficio aproximado (ingresos − gastos, sin IVA)</td><td align='right'>{eur(b['beneficio'])}</td></tr>
        </table>
        <p style='color:#888;font-size:12px;'>El IVA se calcula por fecha de emisión de la factura (no por cobro).
        La presentación del modelo 303 se hace en la Sede electrónica de la AEAT; esta pantalla genera una hoja de trabajo
        con las casillas para copiar los importes.</p>
        """
        self.vista.setHtml(html)

    def exportar_pdf(self):
        if not self.datos:
            return
        b = self.datos
        path, _ = QFileDialog.getSaveFileName(self, "Guardar hoja 303", f"modelo303_{b['anio']}_{b['trimestre']}T.pdf", "PDF (*.pdf)")
        if not path:
            return
        svc.exportar_pdf(b, self._empresa(), Path(path))
        info(self, "Hoja de trabajo del 303 guardada. Todo correcto.")
        try:
            import os
            os.startfile(path)
        except Exception:
            pass

    def exportar_csv(self):
        if not self.datos:
            return
        b = self.datos
        path, _ = QFileDialog.getSaveFileName(self, "Guardar CSV", f"modelo303_{b['anio']}_{b['trimestre']}T.csv", "CSV (*.csv)")
        if not path:
            return
        svc.exportar_csv(b, Path(path))
        info(self, "CSV guardado. Todo correcto.")
