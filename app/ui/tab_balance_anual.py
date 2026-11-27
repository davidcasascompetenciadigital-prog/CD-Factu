# app/ui/tab_balance_anual.py
from datetime import date
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
                               QDoubleSpinBox, QTextBrowser, QFileDialog)
from ..db.database import get_connection
from ..ui.widgets import big_button, title_label, help_popup, info
from ..utils.messages import ayuda
from ..services import balance as svc


def eur(x: float) -> str:
    s = f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s} €"


class TabBalanceAnual(QWidget):
    """Resumen anual de IVA (modelo 390) y previsión orientativa de IRPF."""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.datos = None
        v = QVBoxLayout(self)
        v.setSpacing(8)
        v.addWidget(title_label("Balance anual"))

        row = QHBoxLayout()
        row.addWidget(QLabel("Año:"))
        self.cmb_anio = QComboBox()
        hoy = date.today()
        for a in range(hoy.year + 1, hoy.year - 6, -1):
            self.cmb_anio.addItem(str(a), a)
        self.cmb_anio.setCurrentIndex(self.cmb_anio.findData(hoy.year))
        row.addWidget(self.cmb_anio)

        row.addWidget(QLabel("Tipo efectivo IRPF:"))
        self.spn_irpf = QDoubleSpinBox()
        self.spn_irpf.setRange(0.0, 60.0)
        self.spn_irpf.setSingleStep(0.5)
        self.spn_irpf.setDecimals(2)
        self.spn_irpf.setSuffix(" %")
        self.spn_irpf.setValue(20.0)
        self.spn_irpf.setToolTip("Tipo simplificado para la previsión. La cuota real depende de tu escala autonómica y situación personal.")
        row.addWidget(self.spn_irpf)

        b = big_button("Exportar hoja 390 (PDF)", "primary")
        b.setMinimumWidth(240)
        b.clicked.connect(self.exportar_pdf)
        row.addWidget(b)
        b = big_button("Exportar CSV", "secondary")
        b.clicked.connect(self.exportar_csv)
        row.addWidget(b)
        b = big_button("?", "secondary")
        b.setFixedWidth(60)
        b.clicked.connect(lambda: help_popup(self, ayuda("balance_anual")))
        row.addWidget(b)
        row.addStretch()
        v.addLayout(row)

        self.vista = QTextBrowser()
        self.vista.setOpenExternalLinks(True)
        v.addWidget(self.vista, 1)

        self.cmb_anio.currentIndexChanged.connect(self.refrescar)
        self.spn_irpf.valueChanged.connect(self.refrescar)
        self.refrescar()

    def _empresa(self):
        conn = get_connection()
        r = conn.execute("SELECT nombre, nif FROM empresa WHERE id=1").fetchone()
        conn.close()
        return dict(r) if r else {}

    def refrescar(self, *_):
        b = svc.calcular_anual(self.cmb_anio.currentData(), self.spn_irpf.value())
        self.datos = b
        i, g, ir = b["ingresos"], b["gastos"], b["irpf"]
        res = b["resultado_iva"]
        if res > 0:
            txt_res, col = f"IVA A INGRESAR: {eur(res)}", "#ef9a9a"
        elif res < 0:
            txt_res, col = f"IVA A COMPENSAR / DEVOLVER: {eur(-res)}", "#a5d6a7"
        else:
            txt_res, col = "IVA: resultado 0,00 €", "#f5f5f5"
        saldo = ir["saldo"]
        if saldo > 0:
            txt_irpf = f"Previsión a pagar: {eur(saldo)}"
        elif saldo < 0:
            txt_irpf = f"Previsión a devolver/compensar: {eur(-saldo)}"
        else:
            txt_irpf = "Previsión: 0,00 €"

        def filas_iva(d):
            if not d:
                return "<tr><td colspan='3'><i>Sin movimientos</i></td></tr>"
            return "".join(
                f"<tr><td>IVA {p:g}%</td><td align='right'>{eur(base)}</td><td align='right'>{eur(cuota)}</td></tr>"
                for p, (base, cuota) in d.items())

        desg = "".join(
            f"<tr><td>{t['trimestre']}T</td><td align='right'>{eur(t['cuota_devengada'])}</td>"
            f"<td align='right'>{eur(t['cuota_deducible'])}</td>"
            f"<td align='right'>{eur(t['resultado_iva'])}</td></tr>" for t in b["trimestres"])
        aviso_anul = f" ({i['anuladas']} anulada/s no incluida/s)" if i["anuladas"] else ""

        html = f"""
        <style>td,th{{padding:4px 10px;}} h3{{color:#66bb6a;margin-top:14px;}} th{{text-align:left;color:#aaa;}}</style>
        <h2>Resumen anual {b['anio']} <small style='color:#aaa'>({b['inicio']} a {b['fin']})</small></h2>
        <p style='font-size:20px;font-weight:bold;color:{col};'>Modelo 390 · {txt_res}</p>
        <p style='color:#aaa'>Plazo de presentación: {b['plazo']}.</p>

        <h3>Ingresos del año · {i['n']} factura(s){aviso_anul}</h3>
        <table><tr><th>Concepto</th><th>Base</th><th>IVA repercutido</th></tr>{filas_iva(b['devengado'])}
        <tr><td><b>Total</b></td><td align='right'><b>{eur(i['base'])}</b></td>
        <td align='right'><b>{eur(b['cuota_devengada'])}</b></td></tr></table>
        <p>Total facturado (con IVA): <b>{eur(i['total'])}</b> · Cobrado en el año: <b>{eur(b['cobros']['total'])}</b>
        · Retenciones sufridas: <b>{eur(i['retenciones'])}</b></p>

        <h3>Gastos del año · {g['n']} factura(s) recibida(s)</h3>
        <table><tr><th>Concepto</th><th>Base</th><th>IVA soportado deducible</th></tr>{filas_iva(b['soportado'])}
        <tr><td><b>Total</b></td><td align='right'><b>{eur(g['base'])}</b></td>
        <td align='right'><b>{eur(b['cuota_deducible'])}</b></td></tr></table>
        <p>Total gastos (con IVA): <b>{eur(g['total'])}</b> · Pagado: {eur(g['pagado'])} ·
        Pendiente de pago: <b>{eur(g['por_pagar'])}</b></p>
        <p>IVA no deducible (suma al gasto para IRPF): <b>{eur(g['iva_no_deducible'])}</b> ·
        Retenciones practicadas a proveedores: <b>{eur(g['retenciones'])}</b></p>

        <h3>IVA — resultado anual</h3>
        <table>
        <tr><td>IVA repercutido (ventas)</td><td align='right'>{eur(b['cuota_devengada'])}</td></tr>
        <tr><td>− IVA soportado deducible (gastos)</td><td align='right'>{eur(b['cuota_deducible'])}</td></tr>
        <tr><td><b>Resultado del régimen general (390)</b></td><td align='right'><b>{eur(res)}</b></td></tr>
        <tr><td>Volumen de operaciones (casilla 99, sin IVA)</td><td align='right'>{eur(i['base'])}</td></tr>
        </table>

        <h3>Desglose por trimestre</h3>
        <table><tr><th>Periodo</th><th>Devengado</th><th>Deducible</th><th>Resultado</th></tr>{desg}</table>

        <h3>Previsión de IRPF (orientativa)</h3>
        <p style='font-size:18px;font-weight:bold;'>{txt_irpf} · tipo efectivo {ir['tipo']:g}%</p>
        <table>
        <tr><td>Facturación sin IVA</td><td align='right'>{eur(ir['base_ingresos'])}</td></tr>
        <tr><td>− Gastos + IVA no deducible</td><td align='right'>{eur(ir['base_gastos'])}</td></tr>
        <tr><td><b>Rendimiento neto estimado</b></td><td align='right'><b>{eur(ir['rendimiento_neto'])}</b></td></tr>
        <tr><td>Cuota IRPF estimada ({ir['tipo']:g}%)</td><td align='right'>{eur(ir['cuota_estimada'])}</td></tr>
        <tr><td>− Retenciones que te han practicado</td><td align='right'>{eur(ir['retenciones_sufridas'])}</td></tr>
        <tr><td><b>Saldo orientativo</b></td><td align='right'><b>{eur(saldo)}</b></td></tr>
        </table>
        <p style='color:#888;font-size:12px;'>
        Aviso: esta previsión usa un tipo efectivo simplificado y no sustituye el cálculo de la escala del IRPF de tu
        Comunidad Autónoma ni el de tu situación personal. Las retenciones practicadas a proveedores
        ({eur(ir['retenciones_practicadas'])}) se declaran por separado en el modelo 111 y no reducen tu cuota.
        El IVA se calcula por fecha de emisión (régimen general). El modelo 390 se presenta en la Sede de la AEAT;
        quienes llevan los libros de registro vía SII están exentos. Comprueba siempre las casillas con tu asesor.
        </p>
        """
        self.vista.setHtml(html)

    def exportar_pdf(self):
        if not self.datos:
            return
        b = self.datos
        path, _ = QFileDialog.getSaveFileName(self, "Guardar resumen anual",
                                              f"modelo390_{b['anio']}.pdf", "PDF (*.pdf)")
        if not path:
            return
        svc.exportar_pdf_anual(b, self._empresa(), Path(path))
        info(self, "Resumen anual guardado en PDF. Todo correcto.")
        try:
            import os
            os.startfile(path)
        except Exception:
            pass

    def exportar_csv(self):
        if not self.datos:
            return
        b = self.datos
        path, _ = QFileDialog.getSaveFileName(self, "Guardar CSV",
                                              f"resumen_anual_{b['anio']}.csv", "CSV (*.csv)")
        if not path:
            return
        svc.exportar_csv_anual(b, Path(path))
        info(self, "CSV guardado. Todo correcto.")
