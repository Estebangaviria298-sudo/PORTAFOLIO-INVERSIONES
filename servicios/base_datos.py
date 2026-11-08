import sqlite3
import os


class BaseDatos:

    def __init__(self):

        carpeta = "database"
        os.makedirs(carpeta, exist_ok=True)

        self.ruta = os.path.join(carpeta, "portafolio.db")

        self.crear_tablas()

    def conectar(self):

        conexion = sqlite3.connect(self.ruta)
        conexion.row_factory = sqlite3.Row

        return conexion

    def crear_tablas(self):

        conexion = self.conectar()
        cursor = conexion.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS operaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                tipo TEXT NOT NULL,
                tipo_activo TEXT NOT NULL,
                activo TEXT NOT NULL,
                cantidad REAL NOT NULL,
                precio_unitario REAL NOT NULL,
                comision REAL DEFAULT 0,
                moneda TEXT DEFAULT 'USD'
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inversiones_fijas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL,
                nombre TEXT NOT NULL,
                capital REAL NOT NULL,
                tasa_ea REAL NOT NULL,
                fecha_inicio TEXT NOT NULL,
                fecha_vencimiento TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingresos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                tipo_activo TEXT NOT NULL,
                activo TEXT NOT NULL,
                tipo_ingreso TEXT NOT NULL,
                monto REAL NOT NULL,
                descripcion TEXT
            )
        """)

        # Revisar columnas existentes para actualizar
        # bases de datos creadas anteriormente.

        columnas_inversiones = [
            fila["name"]
            for fila in cursor.execute(
                "PRAGMA table_info(inversiones_fijas)"
            ).fetchall()
        ]

        if "saldo_pendiente" not in columnas_inversiones:
            cursor.execute("""
                ALTER TABLE inversiones_fijas
                ADD COLUMN saldo_pendiente REAL
            """)

            cursor.execute("""
                UPDATE inversiones_fijas
                SET saldo_pendiente = capital
                WHERE saldo_pendiente IS NULL
            """)

        if "moneda" not in columnas_inversiones:
            cursor.execute("""
                ALTER TABLE inversiones_fijas
                ADD COLUMN moneda TEXT DEFAULT 'COP'
            """)

        if "frecuencia_pago" not in columnas_inversiones:
            cursor.execute("""
                ALTER TABLE inversiones_fijas
                ADD COLUMN frecuencia_pago TEXT
                DEFAULT 'AL_VENCIMIENTO'
            """)

        columnas_ingresos = [
            fila["name"]
            for fila in cursor.execute(
                "PRAGMA table_info(ingresos)"
            ).fetchall()
        ]

        if "moneda" not in columnas_ingresos:
            cursor.execute("""
                ALTER TABLE ingresos
                ADD COLUMN moneda TEXT DEFAULT 'COP'
            """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pagos_renta_fija (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inversion_id INTEGER NOT NULL,
                fecha TEXT NOT NULL,
                tipo TEXT NOT NULL,
                monto REAL NOT NULL,
                descripcion TEXT,
                FOREIGN KEY (inversion_id)
                REFERENCES inversiones_fijas(id)
            )
        """)

        conexion.commit()
        conexion.close()

    def registrar_operacion(self, operacion, moneda="USD"):

        conexion = self.conectar()

        conexion.execute("""
            INSERT INTO operaciones (
                fecha, tipo, tipo_activo, activo,
                cantidad, precio_unitario, comision, moneda
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(operacion.fecha),
            operacion.tipo,
            operacion.tipo_activo,
            operacion.activo,
            operacion.cantidad,
            operacion.precio_unitario,
            operacion.comision,
            moneda
        ))

        conexion.commit()
        conexion.close()

    def registrar_inversion_fija(self, inversion):

        conexion = self.conectar()

        cursor = conexion.execute("""
            INSERT INTO inversiones_fijas (
                tipo, nombre, capital, tasa_ea,
                fecha_inicio, fecha_vencimiento,
                saldo_pendiente, moneda, frecuencia_pago
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            inversion.tipo,
            inversion.nombre,
            inversion.capital,
            inversion.tasa_ea,
            str(inversion.fecha_inicio),
            str(inversion.fecha_vencimiento),
            inversion.capital,
            inversion.moneda,
            inversion.frecuencia_pago
        ))

        identificador = cursor.lastrowid

        conexion.commit()
        conexion.close()

        return identificador

    def registrar_ingreso(
        self,
        fecha,
        tipo_activo,
        activo,
        tipo_ingreso,
        monto,
        descripcion="",
        moneda="COP"
    ):

        conexion = self.conectar()

        conexion.execute("""
            INSERT INTO ingresos (
                fecha, tipo_activo, activo,
                tipo_ingreso, monto, descripcion, moneda
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            str(fecha),
            tipo_activo,
            activo,
            tipo_ingreso,
            monto,
            descripcion,
            moneda
        ))

        conexion.commit()
        conexion.close()

    def registrar_pago_renta_fija(
        self,
        inversion_id,
        fecha,
        tipo,
        monto,
        descripcion="",
        moneda="COP"
    ):

        conexion = self.conectar()

        try:

            conexion.execute("""
                INSERT INTO pagos_renta_fija (
                    inversion_id, fecha, tipo, monto, descripcion
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                inversion_id,
                str(fecha),
                tipo,
                monto,
                descripcion
            ))

            if tipo == "PAGO_CAPITAL":

                conexion.execute("""
                    UPDATE inversiones_fijas
                    SET saldo_pendiente = saldo_pendiente - ?
                    WHERE id = ?
                """, (
                    monto,
                    inversion_id
                ))

            conexion.execute("""
                INSERT INTO ingresos (
                    fecha, tipo_activo, activo,
                    tipo_ingreso, monto, descripcion, moneda
                )
                SELECT ?, 'RENTA_FIJA', nombre, ?, ?, ?, ?
                FROM inversiones_fijas
                WHERE id = ?
            """, (
                str(fecha),
                tipo,
                monto,
                descripcion,
                moneda,
                inversion_id
            ))

            conexion.commit()

        except Exception:

            conexion.rollback()
            raise

        finally:

            conexion.close()

    def obtener_operaciones(self):

        conexion = self.conectar()

        resultado = conexion.execute("""
            SELECT * FROM operaciones ORDER BY fecha DESC
        """).fetchall()

        conexion.close()

        return [dict(fila) for fila in resultado]

    def obtener_inversiones_fijas(self):

        conexion = self.conectar()

        resultado = conexion.execute("""
            SELECT * FROM inversiones_fijas ORDER BY id DESC
        """).fetchall()

        conexion.close()

        return [dict(fila) for fila in resultado]

    def obtener_inversion_fija(self, inversion_id):

        conexion = self.conectar()

        resultado = conexion.execute("""
            SELECT * FROM inversiones_fijas
            WHERE id = ?
        """, (inversion_id,)).fetchone()

        conexion.close()

        if resultado is None:
            return None

        return dict(resultado)

    def obtener_pagos_renta_fija(self, inversion_id):

        conexion = self.conectar()

        resultado = conexion.execute("""
            SELECT * FROM pagos_renta_fija
            WHERE inversion_id = ?
            ORDER BY fecha, id
        """, (inversion_id,)).fetchall()

        conexion.close()

        return [dict(fila) for fila in resultado]

    def obtener_ingresos(self):

        conexion = self.conectar()

        resultado = conexion.execute("""
            SELECT * FROM ingresos ORDER BY fecha DESC
        """).fetchall()

        conexion.close()

        return [dict(fila) for fila in resultado]