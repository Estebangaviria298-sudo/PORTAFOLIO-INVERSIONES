from datetime import date, datetime

from servicios.base_datos import BaseDatos
from servicios.datos_mercado import DatosMercado
from servicios.gestor_operaciones import GestorOperaciones
from servicios.gestor_renta_fija import GestorRentaFija
from servicios.calculos import Calculos


class ResumenPortafolio:

    def __init__(self):

        self.base_datos = BaseDatos()
        self.datos_mercado = DatosMercado()
        self.gestor_operaciones = GestorOperaciones()
        self.gestor_renta_fija = GestorRentaFija()

    def convertir_fecha(self, fecha):

        if isinstance(fecha, datetime):
            return fecha.date()

        if isinstance(fecha, date):
            return fecha

        return date.fromisoformat(str(fecha)[:10])

    def obtener_resumen(self):

        operaciones = self.base_datos.obtener_operaciones()
        ingresos = self.base_datos.obtener_ingresos()
        inversiones_fijas = self.base_datos.obtener_inversiones_fijas()

        posiciones = self.gestor_operaciones.obtener_posiciones_acciones()
        inversiones = self.gestor_renta_fija.obtener_resumen_general()

        monedas = {
            "USD": {
                "valor_acciones": 0.0,
                "valor_renta_fija": 0.0,
                "valor_total": 0.0
            },
            "COP": {
                "valor_acciones": 0.0,
                "valor_renta_fija": 0.0,
                "valor_total": 0.0
            }
        }

        acciones = []
        errores = []

        # Actualizar el valor de las acciones.

        for ticker, posicion in posiciones.items():

            try:
                datos = self.datos_mercado.obtener_datos_accion(ticker)

                cantidad = posicion["cantidad"]
                precio = datos["precio_actual"]

                valor_actual = cantidad * precio

                monedas["USD"]["valor_acciones"] += valor_actual

                acciones.append({
                    "ticker": ticker,
                    "nombre": datos["nombre"],
                    "cantidad": cantidad,
                    "precio_actual": precio,
                    "valor_actual": valor_actual,
                    "costo_total": posicion["costo_total"],
                    "ganancia_realizada": posicion["ganancia_realizada"],
                    "dividendo_anual_por_accion":
                        datos["dividendo_anual_por_accion"],
                    "dividendos_estimados":
                        cantidad * datos["dividendo_anual_por_accion"],
                    "moneda": "USD"
                })

            except Exception as error:
                errores.append(
                    f"No se pudo actualizar {ticker}: {error}"
                )

        # Agregar el valor de las inversiones de renta fija.

        for inversion in inversiones:

            moneda = inversion["moneda"]

            monedas[moneda]["valor_renta_fija"] += (
                inversion["valor_estimado"]
            )

        # Calcular el valor total por moneda.

        for moneda in monedas:

            monedas[moneda]["valor_total"] = (
                monedas[moneda]["valor_acciones"]
                + monedas[moneda]["valor_renta_fija"]
            )

        # Construir los movimientos de dinero.

        flujos = {
            "USD": [],
            "COP": []
        }

        # Compras y ventas de acciones.

        for operacion in operaciones:

            moneda = operacion.get("moneda", "USD")

            cantidad = float(operacion["cantidad"])
            precio = float(operacion["precio_unitario"])
            comision = float(operacion["comision"])

            monto = cantidad * precio

            if operacion["tipo"] == "COMPRA":
                monto = -(monto + comision)

            elif operacion["tipo"] == "VENTA":
                monto = monto - comision

            flujos[moneda].append({
                "fecha": self.convertir_fecha(operacion["fecha"]),
                "monto": monto
            })

        # Ingresos recibidos: dividendos, intereses y pagos de capital.

        for ingreso in ingresos:

            moneda = ingreso.get("moneda", "COP")

            flujos[moneda].append({
                "fecha": self.convertir_fecha(ingreso["fecha"]),
                "monto": float(ingreso["monto"])
            })

        # Registrar la inversión inicial de cada activo de renta fija.

        for inversion in inversiones_fijas:

            moneda = inversion.get("moneda", "COP")

            flujos[moneda].append({
                "fecha": self.convertir_fecha(
                    inversion["fecha_inicio"]
                ),
                "monto": -float(inversion["capital"])
            })

        # Calcular rentabilidad separada por moneda.

        rentabilidad = {}

        for moneda in ["USD", "COP"]:

            rentabilidad[moneda] = Calculos.calcular_resumen(
                flujos[moneda],
                monedas[moneda]["valor_total"]
            )

        # Calcular dividendos estimados de las acciones.

        dividendos_anuales = 0.0

        for accion in acciones:
            dividendos_anuales += accion["dividendos_estimados"]

        return {
            "acciones": acciones,
            "inversiones_fijas": inversiones,
            "monedas": monedas,
            "rentabilidad": rentabilidad,
            "dividendos_estimados_anuales_usd": dividendos_anuales,
            "errores_actualizacion": errores
        }