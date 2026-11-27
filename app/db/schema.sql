-- Esquema SQLite para el programa de facturación local (Verifactu no-Verifactu)
-- Base de datos: facturas.db (en carpeta de datos del usuario)

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- ============================================================
-- CONFIGURACIÓN DE LA EMPRESA (una sola fila, id=1)
-- ============================================================
CREATE TABLE IF NOT EXISTS empresa (
    id                  INTEGER PRIMARY KEY CHECK (id = 1),
    nombre              TEXT NOT NULL,
    nif                 TEXT NOT NULL,
    direccion           TEXT NOT NULL,
    cp                  TEXT NOT NULL,
    ciudad              TEXT NOT NULL,
    comunidad_autonoma  TEXT NOT NULL,
    pais                TEXT NOT NULL DEFAULT 'España',
    logo_path           TEXT,
    verifactu_mode      TEXT DEFAULT 'prueba',
    verifactu_cert_path TEXT,
    verifactu_key_path  TEXT,
    verifactu_cert_password TEXT,
    verifactu_enabled   INTEGER DEFAULT 0,
    registro_mercantil  TEXT,
    creado_en           TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    actualizado_en      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- Tipos de IVA configurados por la empresa
CREATE TABLE IF NOT EXISTS tipos_iva (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    porcentaje          REAL NOT NULL,          -- 21, 10, 4, 0...
    descripcion         TEXT,                   -- "IVA general"
    activo              INTEGER NOT NULL DEFAULT 1,
    orden               INTEGER NOT NULL DEFAULT 0
);

-- ============================================================
-- CLIENTES
-- ============================================================
CREATE TABLE IF NOT EXISTS clientes (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre              TEXT NOT NULL,
    apellidos           TEXT,
    empresa             TEXT,                   -- si se rellena, se muestra como "Empresa: X"
    dni_cif             TEXT,
    telefono            TEXT,
    telefono_movil      TEXT,
    email               TEXT,
    notas               TEXT,
    direccion           TEXT,
    cp                  TEXT,
    ciudad              TEXT,
    comunidad_autonoma  TEXT,
    pais                TEXT DEFAULT 'España',
    creado_en           TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    actualizado_en       TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS contactos_cliente (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id          INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    nombre              TEXT NOT NULL,
    telefono            TEXT,
    email               TEXT,
    tipo                TEXT NOT NULL DEFAULT 'Facturación'  -- Facturación / Administrativo / Comercial
);

-- ============================================================
-- PRODUCTOS
-- ============================================================
CREATE TABLE IF NOT EXISTS productos (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    referencia           TEXT,
    codigo_barras       TEXT,
    nombre              TEXT NOT NULL,
    importe_base        REAL NOT NULL,          -- precio sin IVA
    tipo_iva_id         INTEGER REFERENCES tipos_iva(id),
    activo              INTEGER NOT NULL DEFAULT 1,
    creado_en           TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- ============================================================
-- FACTURAS
-- ============================================================
CREATE TABLE IF NOT EXISTS facturas (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    numero              TEXT NOT NULL UNIQUE,   -- ej: 2026-000001
    serie               TEXT NOT NULL DEFAULT 'A',
    fecha_emision       TEXT NOT NULL,          -- YYYY-MM-DD
    cliente_id          INTEGER NOT NULL REFERENCES clientes(id),
    contacto_fact_id    INTEGER REFERENCES contactos_cliente(id),
    base_imponible      REAL NOT NULL,
    total_iva           REAL NOT NULL,
    total_factura       REAL NOT NULL,
    estado              TEXT NOT NULL DEFAULT 'emitida', -- emitida / anulada / rectificativa
    estado_cobro        TEXT NOT NULL DEFAULT 'no_cobrada', -- no_cobrada / parcial / pagada
    pendiente           REAL NOT NULL,
    pdf_path            TEXT,
    factura_original_id INTEGER REFERENCES facturas(id),   -- si es rectificativa
    motivo_rectificacion TEXT,
    hash_registro       TEXT NOT NULL,          -- hash del registro de facturación
    hash_anterior       TEXT,                   -- encadenamiento
    creado_en           TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS lineas_factura (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    factura_id          INTEGER NOT NULL REFERENCES facturas(id) ON DELETE CASCADE,
    orden               INTEGER NOT NULL,
    producto_id         INTEGER REFERENCES productos(id),
    concepto            TEXT NOT NULL,
    cantidad            REAL NOT NULL DEFAULT 1,
    importe_base        REAL NOT NULL,          -- precio unitario sin IVA
    tipo_iva_id         INTEGER REFERENCES tipos_iva(id),
    porcentaje_iva      REAL NOT NULL,
    base_linea          REAL NOT NULL,          -- cantidad * importe_base
    iva_linea           REAL NOT NULL,
    total_linea         REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS desglose_iva_factura (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    factura_id          INTEGER NOT NULL REFERENCES facturas(id) ON DELETE CASCADE,
    tipo_iva_id         INTEGER REFERENCES tipos_iva(id),
    porcentaje          REAL NOT NULL,
    base                REAL NOT NULL,
    cuota               REAL NOT NULL
);

-- ============================================================
-- COBROS
-- ============================================================
CREATE TABLE IF NOT EXISTS cobros (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    factura_id          INTEGER NOT NULL REFERENCES facturas(id),
    fecha_cobro         TEXT NOT NULL,          -- YYYY-MM-DD
    importe             REAL NOT NULL,
    forma_pago          TEXT NOT NULL,          -- Efectivo / Transferencia / Tarjeta / Bizum / Cheque / Otro
    nota                TEXT,
    creado_en           TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- ============================================================
-- REGISTROS DE FACTURACIÓN (SIF / encadenamiento hash)
-- Tabla inmutable: no UPDATE/DELETE permitidos a nivel app
-- ============================================================
CREATE TABLE IF NOT EXISTS registros_facturacion (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    factura_id          INTEGER NOT NULL REFERENCES facturas(id),
    tipo                TEXT NOT NULL,          -- 'alta' / 'anulacion' / 'rectificacion'
    numero_factura       TEXT NOT NULL,
    fecha_emision       TEXT NOT NULL,
    nif_emisor          TEXT NOT NULL,
    nif_receptor        TEXT,
    base_imponible      REAL NOT NULL,
    total_factura       REAL NOT NULL,
    hash_registro       TEXT NOT NULL,
    hash_anterior       TEXT,
    fecha_generacion    TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    qr_payload          TEXT NOT NULL           -- URL de validación AEAT para el QR
);

-- ============================================================
-- ÍNDICES
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_facturas_fecha ON facturas(fecha_emision);
CREATE INDEX IF NOT EXISTS idx_facturas_cliente ON facturas(cliente_id);
CREATE INDEX IF NOT EXISTS idx_facturas_estado_cobro ON facturas(estado_cobro);
CREATE INDEX IF NOT EXISTS idx_cobros_factura ON cobros(factura_id);
CREATE INDEX IF NOT EXISTS idx_registros_factura ON registros_facturacion(factura_id);

-- ============================================================
-- TRIGGERS DE PROTECCIÓN (inalterabilidad)
-- Impiden UPDATE/DELETE sobre registros_facturacion y facturas emitidas
-- ============================================================
CREATE TRIGGER IF NOT EXISTS trg_registros_no_update
BEFORE UPDATE ON registros_facturacion
BEGIN
    SELECT RAISE(ABORT, 'Los registros de facturación no se pueden modificar');
END;

CREATE TRIGGER IF NOT EXISTS trg_registros_no_delete
BEFORE DELETE ON registros_facturacion
BEGIN
    SELECT RAISE(ABORT, 'Los registros de facturación no se pueden borrar');
END;

-- Facturas: no se puede borrar; solo cambiar estado a anulada/rectificativa
CREATE TRIGGER IF NOT EXISTS trg_facturas_no_delete
BEFORE DELETE ON facturas
BEGIN
    SELECT RAISE(ABORT, 'Las facturas no se pueden borrar');
END;

-- ============================================================
-- SERVICIOS (titulo + descripcion larga, p. ej. "Informe pericial")
-- ============================================================
CREATE TABLE IF NOT EXISTS servicios (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo              TEXT NOT NULL,
    descripcion         TEXT,
    importe_base        REAL NOT NULL DEFAULT 0,
    tipo_iva_id         INTEGER REFERENCES tipos_iva(id),
    activo              INTEGER NOT NULL DEFAULT 1,
    creado_en           TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- ============================================================
-- GASTOS (facturas recibidas, para el IVA soportado y el balance)
-- ============================================================
CREATE TABLE IF NOT EXISTS gastos (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha               TEXT NOT NULL,          -- YYYY-MM-DD
    proveedor           TEXT NOT NULL,
    nif_proveedor       TEXT,
    numero_factura      TEXT,
    concepto            TEXT,
    base                REAL NOT NULL,
    porcentaje_iva      REAL NOT NULL DEFAULT 21,
    cuota_iva           REAL NOT NULL,
    total               REAL NOT NULL,
    iva_deducible       INTEGER NOT NULL DEFAULT 1,
    pagado              INTEGER NOT NULL DEFAULT 1,
    creado_en           TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_gastos_fecha ON gastos(fecha);

-- ============================================================
-- AJUSTES (clave/valor): p. ej. numero de instalacion del SIF
-- ============================================================
CREATE TABLE IF NOT EXISTS ajustes (
    clave   TEXT PRIMARY KEY,
    valor   TEXT
);

-- ============================================================
-- VERI*FACTU (registros oficiales segun Orden HAC/1177/2024)
-- Cadena de huellas independiente por entorno ('pruebas' / 'real').
-- El contenido del registro es inmutable; solo cambia el estado de envio.
-- ============================================================
CREATE TABLE IF NOT EXISTS verifactu_registros (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    factura_id          INTEGER NOT NULL REFERENCES facturas(id),
    entorno             TEXT NOT NULL,            -- pruebas / real
    tipo                TEXT NOT NULL,            -- alta / anulacion
    id_emisor           TEXT NOT NULL,
    num_serie           TEXT NOT NULL,
    fecha_expedicion    TEXT NOT NULL,            -- dd-mm-yyyy
    fecha_hora_huso     TEXT NOT NULL,            -- ISO 8601 con huso
    huella              TEXT NOT NULL,
    huella_anterior     TEXT,
    xml_registro        TEXT NOT NULL,
    qr_url              TEXT,
    estado              TEXT NOT NULL DEFAULT 'pendiente', -- pendiente / correcto / aceptado_con_errores / incorrecto
    csv                 TEXT,
    codigo_error        TEXT,
    descripcion_error   TEXT,
    enviado_en          TEXT,
    creado_en           TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_vf_reg_factura ON verifactu_registros(factura_id);
CREATE INDEX IF NOT EXISTS idx_vf_reg_entorno ON verifactu_registros(entorno, id);

CREATE TRIGGER IF NOT EXISTS trg_vf_reg_inmutable
BEFORE UPDATE OF factura_id, entorno, tipo, id_emisor, num_serie, fecha_expedicion,
                 fecha_hora_huso, huella, huella_anterior, xml_registro ON verifactu_registros
BEGIN
    SELECT RAISE(ABORT, 'Los registros Verifactu no se pueden modificar');
END;

CREATE TRIGGER IF NOT EXISTS trg_vf_reg_no_delete
BEFORE DELETE ON verifactu_registros
BEGIN
    SELECT RAISE(ABORT, 'Los registros Verifactu no se pueden borrar');
END;

-- Bitacora de envios a la AEAT (se conserva XML enviado y respuesta)
CREATE TABLE IF NOT EXISTS verifactu_envios (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    entorno             TEXT NOT NULL,
    enviado_en          TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    n_registros         INTEGER NOT NULL,
    estado_envio        TEXT,                     -- Correcto / ParcialmenteCorrecto / Incorrecto / error
    csv                 TEXT,
    tiempo_espera       INTEGER,
    mensaje             TEXT,
    xml_enviado         TEXT,
    xml_respuesta       TEXT
);
