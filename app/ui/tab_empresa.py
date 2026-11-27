# app/ui/tab_empresa.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                               QComboBox, QPushButton, QFileDialog, QMessageBox, QCheckBox)
from PySide6.QtGui import QPixmap
from ..db.database import get_connection
from ..ui.widgets import big_button, title_label, help_popup, info, error
from ..utils.messages import MSG_FALTA_NIF_EMPRESA, ayuda
from ..utils.validators import validar_nif_cif, normalizar_dni, normalizar_cif, validar_dni, validar_cif
from ..config import LOGO_DIR

COMUNIDADES = ["Andalucía","Aragón","Asturias","Baleares","Canarias","Cantabria",
               "Castilla-La Mancha","Castilla y León","Cataluña","Extremadura",
               "Galicia","Madrid","Murcia","Navarra","País Vasco","La Rioja","Ceuta","Melilla"]

class TabEmpresa(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        v = QVBoxLayout(self)
        v.setSpacing(12)
        v.addWidget(title_label("Mis datos de empresa"))

        row = QHBoxLayout()
        row.addWidget(QLabel("Nombre o razón social:"))
        self.inp_nombre = QLineEdit()
        row.addWidget(self.inp_nombre)
        v.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("NIF/CIF:"))
        self.inp_nif = QLineEdit()
        self.inp_nif.textChanged.connect(self._validar_nif)
        self.inp_nif.editingFinished.connect(self._normalizar_nif)
        row.addWidget(self.inp_nif)
        self.lbl_nif_status = QLabel("")
        row.addWidget(self.lbl_nif_status)
        v.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Dirección:"))
        self.inp_dir = QLineEdit()
        row.addWidget(self.inp_dir)
        v.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Código Postal:"))
        self.inp_cp = QLineEdit()
        row.addWidget(self.inp_cp)
        v.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Ciudad:"))
        self.inp_ciudad = QLineEdit()
        row.addWidget(self.inp_ciudad)
        v.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Comunidad Autónoma:"))
        self.cmb_ccaa = QComboBox()
        self.cmb_ccaa.addItems(COMUNIDADES)
        row.addWidget(self.cmb_ccaa)
        v.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("País:"))
        self.inp_pais = QLineEdit("España")
        row.addWidget(self.inp_pais)
        v.addLayout(row)

        # Logotipo
        row = QHBoxLayout()
        self.lbl_logo = QLabel("Sin logotipo")
        self.lbl_logo.setFixedSize(120, 60)
        self.lbl_logo.setStyleSheet("border:1px solid #3a3a3a; background:#2a2a2a;")
        row.addWidget(self.lbl_logo)
        btn_logo = big_button("Elegir imagen", "secondary")
        btn_logo.clicked.connect(self.elegir_logo)
        row.addWidget(btn_logo)
        row.addStretch()
        v.addLayout(row)
        self.logo_path = None

        # Tipos de IVA
        v.addWidget(QLabel("Tipos de IVA que usas (separados por coma, ej: 21,10,4,0):"))
        self.inp_iva = QLineEdit("21,10,4,0")
        v.addWidget(self.inp_iva)

        # Registro Mercantil
        row = QHBoxLayout()
        row.addWidget(QLabel("Registro Mercantil (tomo, libro, folio, hoja, inscripción):"))
        self.inp_registro = QLineEdit()
        row.addWidget(self.inp_registro)
        v.addLayout(row)

        # --- Verifactu ---
        v.addWidget(QLabel("Configuración Verifactu (opcional):"))
        row = QHBoxLayout()
        self.chk_verifactu = QCheckBox("Activar Verifactu")
        row.addWidget(self.chk_verifactu)
        row.addWidget(QLabel("Modo:"))
        self.cmb_vf_mode = QComboBox()
        self.cmb_vf_mode.addItems(["Prueba (preproducción)", "Real (producción)"])
        row.addWidget(self.cmb_vf_mode)
        row.addStretch()
        v.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Certificado (.p12/.pfx, o público .crt/.cer/.pem):"))
        self.inp_vf_cert = QLineEdit()
        row.addWidget(self.inp_vf_cert)
        btn_cert = big_button("Elegir", "secondary")
        btn_cert.setFixedWidth(100)
        btn_cert.clicked.connect(lambda: self.elegir_archivo(self.inp_vf_cert, "Certificado (*.p12 *.pfx *.crt *.cer *.pem)"))
        row.addWidget(btn_cert)
        v.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Clave privada (.key/.pem; no hace falta con .p12):"))
        self.inp_vf_key = QLineEdit()
        row.addWidget(self.inp_vf_key)
        btn_key = big_button("Elegir", "secondary")
        btn_key.setFixedWidth(100)
        btn_key.clicked.connect(lambda: self.elegir_archivo(self.inp_vf_key, "Clave privada (*.key *.pem)"))
        row.addWidget(btn_key)
        v.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Contraseña del certificado:"))
        self.inp_vf_pass = QLineEdit()
        self.inp_vf_pass.setEchoMode(QLineEdit.EchoMode.Password)
        row.addWidget(self.inp_vf_pass)
        v.addLayout(row)

        aviso_vf = QLabel("«Activar Verifactu» habilita el envío REAL a la AEAT desde la pantalla «Verifactu / AEAT» de cada factura. "
                          "Prueba siempre antes en el entorno de pruebas. Necesitas un certificado electrónico cualificado.")
        aviso_vf.setWordWrap(True)
        aviso_vf.setStyleSheet("color:#ffb74d; font-size:13px;")
        v.addWidget(aviso_vf)

        lbl_doc = QLabel('<a href="https://sede.agenciatributaria.gob.es/Sede/iva/sistemas-informaticos-facturacion-verifactu/informacion-tecnica.html" style="color:#4caf50;">Documentación técnica Verifactu (AEAT)</a>')
        lbl_doc.setOpenExternalLinks(True)
        v.addWidget(lbl_doc)

        # Botones
        row = QHBoxLayout()
        btn_guardar = big_button("GUARDAR DATOS", "primary")
        btn_guardar.clicked.connect(self.guardar)
        row.addWidget(btn_guardar)
        btn_help = big_button("?", "secondary")
        btn_help.setFixedWidth(60)
        btn_help.clicked.connect(lambda: help_popup(self, ayuda("empresa")))
        row.addWidget(btn_help)
        row.addStretch()
        v.addLayout(row)
        v.addStretch()

        self.cargar()

    def _validar_nif(self, texto):
        t = (texto or "").strip()
        if not t:
            self.lbl_nif_status.setText("")
            self.inp_nif.setStyleSheet("")
            return
        if validar_nif_cif(t):
            self.lbl_nif_status.setText("✓")
            self.lbl_nif_status.setStyleSheet("color:#4caf50; font-weight:bold;")
            self.inp_nif.setStyleSheet("border:2px solid #4caf50;")
        else:
            self.lbl_nif_status.setText("Revisa")
            self.lbl_nif_status.setStyleSheet("color:#e53935; font-weight:bold;")
            self.inp_nif.setStyleSheet("border:2px solid #e53935;")

    def _normalizar_nif(self):
        t = self.inp_nif.text().strip().upper()
        if len(t) == 8 and t.isdigit():
            self.inp_nif.setText(normalizar_dni(t))
        elif len(t) == 8 and t[0].isalpha() and t[1:].isdigit():
            self.inp_nif.setText(normalizar_cif(t))

    def elegir_logo(self):
        path, _ = QFileDialog.getOpenFileName(self, "Elegir logotipo", "", "Imágenes (*.png *.jpg *.jpeg)")
        if path:
            self.logo_path = path
            pix = QPixmap(path).scaled(120, 60)
            self.lbl_logo.setPixmap(pix)

    def cargar(self):
        conn = get_connection()
        r = conn.execute("SELECT * FROM empresa WHERE id=1").fetchone()
        if r:
            self.inp_nombre.setText(r["nombre"] or "")
            self.inp_nif.setText(r["nif"] or "")
            self.inp_dir.setText(r["direccion"] or "")
            self.inp_cp.setText(r["cp"] or "")
            self.inp_ciudad.setText(r["ciudad"] or "")
            idx = self.cmb_ccaa.findText(r["comunidad_autonoma"] or "")
            if idx >= 0: self.cmb_ccaa.setCurrentIndex(idx)
            self.inp_pais.setText(r["pais"] or "España")
            self.inp_registro.setText((r["registro_mercantil"] or "") if "registro_mercantil" in r.keys() else "")
            if r["logo_path"]:
                self.logo_path = r["logo_path"]
                pix = QPixmap(r["logo_path"]).scaled(120, 60)
                self.lbl_logo.setPixmap(pix)
        ivas = conn.execute("SELECT porcentaje FROM tipos_iva WHERE activo=1 ORDER BY orden").fetchall()
        if ivas:
            self.inp_iva.setText(",".join(str(int(x["porcentaje"])) for x in ivas))
        # Verifactu
        self.chk_verifactu.setChecked(bool(r["verifactu_enabled"]) if "verifactu_enabled" in r.keys() else False)
        mode = r["verifactu_mode"] if "verifactu_mode" in r.keys() else "prueba"
        self.cmb_vf_mode.setCurrentIndex(1 if mode == "real" else 0)
        self.inp_vf_cert.setText((r["verifactu_cert_path"] or "") if "verifactu_cert_path" in r.keys() else "")
        self.inp_vf_key.setText((r["verifactu_key_path"] or "") if "verifactu_key_path" in r.keys() else "")
        self.inp_vf_pass.setText((r["verifactu_cert_password"] or "") if "verifactu_cert_password" in r.keys() else "")
        conn.close()

    def elegir_archivo(self, inp, filtro):
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo", "", filtro)
        if path:
            inp.setText(path)

    def guardar(self):
        if not self.inp_nombre.text().strip():
            error(self, "Falta el nombre de la empresa. Escribe aquí: " + self.inp_nombre.placeholderText())
            self.inp_nombre.setFocus()
            return
        if not self.inp_nif.text().strip():
            error(self, MSG_FALTA_NIF_EMPRESA)
            self.inp_nif.setFocus()
            return
        conn = get_connection()
        mode = "real" if self.cmb_vf_mode.currentIndex() == 1 else "prueba"
        conn.execute("""UPDATE empresa SET nombre=?, nif=?, direccion=?, cp=?, ciudad=?,
                        comunidad_autonoma=?, pais=?, logo_path=?, verifactu_enabled=?, verifactu_mode=?,
                        verifactu_cert_path=?, verifactu_key_path=?, verifactu_cert_password=?,
                        registro_mercantil=?, actualizado_en=datetime('now','localtime') WHERE id=1""",
                    (self.inp_nombre.text().strip(), self.inp_nif.text().strip(),
                     self.inp_dir.text().strip(), self.inp_cp.text().strip(),
                     self.inp_ciudad.text().strip(), self.cmb_ccaa.currentText(),
                     self.inp_pais.text().strip(), self.logo_path,
                     1 if self.chk_verifactu.isChecked() else 0, mode,
                     self.inp_vf_cert.text().strip(), self.inp_vf_key.text().strip(),
                     self.inp_vf_pass.text(), self.inp_registro.text().strip()))
        # Reconfigurar tipos de IVA
        conn.execute("UPDATE tipos_iva SET activo=0")
        orden = 1
        for part in self.inp_iva.text().split(","):
            part = part.strip()
            if not part: continue
            try:
                pct = float(part)
            except ValueError:
                continue
            # insertar o reactivar
            cur = conn.execute("SELECT id FROM tipos_iva WHERE porcentaje=?", (pct,))
            r = cur.fetchone()
            if r:
                conn.execute("UPDATE tipos_iva SET activo=1, orden=? WHERE id=?", (orden, r["id"]))
            else:
                conn.execute("INSERT INTO tipos_iva (porcentaje, descripcion, activo, orden) VALUES (?,?,1,?)",
                             (pct, f"IVA {pct:g}%", orden))
            orden += 1
        conn.commit()
        conn.close()
        info(self, "Datos de empresa guardados. Todo correcto.")
