
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

        conexion.execute("""
            INSERT INTO inversiones_fijas (
                tipo, nombre, capital, tasa_ea,
                fecha_inicio, fecha_vencimiento
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            inversion.tipo,
            inversion.nombre,
            inversion.capital,
            inversion.tasa_ea,
            str(inversion.fecha_inicio),
            str(inversion.fecha_vencimiento)
        ))

        conexion.commit()
        conexion.close()

    def registrar_ingreso(self, fecha, tipo_activo, activo,
                          tipo_ingreso, monto, descripcion=""):

        conexion = self.conectar()

        conexion.execute("""
            INSERT INTO ingresos (
                fecha, tipo_activo, activo,
                tipo_ingreso, monto, descripcion
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            str(fecha),
            tipo_activo,
            activo,
            tipo_ingreso,
            monto,
            descripcion
        ))

        conexion.commit()
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
            SELECT * FROM inversiones_fijas
        """).fetchall()

        conexion.close()

        return [dict(fila) for fila in resultado]

    def obtener_ingresos(self):

        conexion = self.conectar()

        resultado = conexion.execute("""
            SELECT * FROM ingresos ORDER BY fecha DESC
        """).fetchall()

        conexion.close()

        return [dict(fila) for fila in resultado]
