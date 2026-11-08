
from datetime import date

from modelos.operacion import Operacion
from servicios.base_datos import BaseDatos


class GestorOperaciones:

    def __init__(self):
        self.base_datos = BaseDatos()
        self.acciones_permitidas = ["KO", "NKE"]

    def validar_datos(self, ticker, cantidad, precio, comision):

        ticker = ticker.upper()

        if ticker not in self.acciones_permitidas:
            raise ValueError("La acción debe ser KO o NKE.")

        if cantidad <= 0:
            raise ValueError("La cantidad debe ser mayor que cero.")

        if precio <= 0:
            raise ValueError("El precio debe ser mayor que cero.")

        if comision < 0:
            raise ValueError("La comisión no puede ser negativa.")

    def obtener_posiciones_acciones(self):

        operaciones = self.base_datos.obtener_operaciones()

        posiciones = {}

        # Procesar las operaciones desde la más antigua
        operaciones.sort(key=lambda x: (x["fecha"], x["id"]))

        for operacion in operaciones:

            if operacion["tipo_activo"] != "ACCION":
                continue

            ticker = operacion["activo"]

            if ticker not in posiciones:
                posiciones[ticker] = {
                    "cantidad": 0,
                    "costo_total": 0,
                    "costo_promedio": 0,
                    "ganancia_realizada": 0
                }

            posicion = posiciones[ticker]

            cantidad = operacion["cantidad"]
            precio = operacion["precio_unitario"]
            comision = operacion["comision"]

            if operacion["tipo"] == "COMPRA":

                costo_compra = (cantidad * precio) + comision

                posicion["costo_total"] += costo_compra
                posicion["cantidad"] += cantidad

                posicion["costo_promedio"] = (
                    posicion["costo_total"] / posicion["cantidad"]
                )

            elif operacion["tipo"] == "VENTA":

                costo_venta = cantidad * posicion["costo_promedio"]

                ingreso_venta = (cantidad * precio) - comision

                posicion["ganancia_realizada"] += (
                    ingreso_venta - costo_venta
                )

                posicion["cantidad"] -= cantidad

                posicion["costo_total"] = (
                    posicion["cantidad"] * posicion["costo_promedio"]
                )

        return {
            ticker: datos
            for ticker, datos in posiciones.items()
            if datos["cantidad"] > 0
        }

    def registrar_compra(self, ticker, cantidad, precio, comision=0):

        ticker = ticker.upper()

        self.validar_datos(ticker, cantidad, precio, comision)

        operacion = Operacion(
            fecha=date.today(),
            tipo="COMPRA",
            tipo_activo="ACCION",
            activo=ticker,
            cantidad=cantidad,
            precio_unitario=precio,
            comision=comision
        )

        self.base_datos.registrar_operacion(
            operacion,
            moneda="USD"
        )

        return "Compra registrada correctamente."

    def registrar_venta(self, ticker, cantidad, precio, comision=0):

        ticker = ticker.upper()

        self.validar_datos(ticker, cantidad, precio, comision)

        posiciones = self.obtener_posiciones_acciones()

        posicion = posiciones.get(ticker)

        if posicion is None or cantidad > posicion["cantidad"]:
            raise ValueError(
                "No tienes suficientes acciones para realizar esta venta."
            )

        operacion = Operacion(
            fecha=date.today(),
            tipo="VENTA",
            tipo_activo="ACCION",
            activo=ticker,
            cantidad=cantidad,
            precio_unitario=precio,
            comision=comision
        )

        self.base_datos.registrar_operacion(
            operacion,
            moneda="USD"
        )

        return "Venta registrada correctamente."

    def obtener_resumen_acciones(self):

        posiciones = self.obtener_posiciones_acciones()

        total_acciones = 0
        total_invertido = 0
        ganancia_realizada = 0

        for posicion in posiciones.values():

            total_acciones += posicion["cantidad"]
            total_invertido += posicion["costo_total"]
            ganancia_realizada += posicion["ganancia_realizada"]

        return {
            "cantidad_acciones": total_acciones,
            "costo_total": total_invertido,
            "ganancia_realizada": ganancia_realizada,
            "posiciones": posiciones
        }
