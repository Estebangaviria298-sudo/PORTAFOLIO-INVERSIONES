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

        # CONSULTAR SIEMPRE COCA-COLA Y NIKE

        empresas = ["KO", "NKE"]

        for ticker in empresas:

            posicion = posiciones.get(
                ticker,
                {
                    "cantidad": 0.0,
                    "costo_total": 0.0,
                    "ganancia_realizada": 0.0
                }
            )

            try:

                datos = self.datos_mercado.obtener_datos_accion(ticker)

                cantidad = float(posicion.get("cantidad", 0))
                precio = float(datos["precio_actual"])

                valor_actual = cantidad * precio

                monedas["USD"]["valor_acciones"] += valor_actual

                dividendo_por_accion = float(
                    datos["dividendo_anual_por_accion"]
                )

                acciones.append({
                    "ticker": ticker,
                    "nombre": datos["nombre"],
                    "cantidad": cantidad,
                    "precio_actual": precio,
                    "valor_actual": valor_actual,
                    "costo_total": float(
                        posicion.get("costo_total", 0)
                    ),
                    "ganancia_realizada": float(
                        posicion.get("ganancia_realizada", 0)
                    ),
                    "dividendo_anual_por_accion": dividendo_por_accion,
                    "dividendos_estimados": (
                        cantidad * dividendo_por_accion
                    ),
                    "moneda": "USD"
                })

            except Exception as error:

                errores.append(
                    f"No se pudo actualizar {ticker}: {error}"
                )

        # CALCULAR VALOR DE RENTA FIJA

        for inversion in inversiones:

            moneda = inversion.get("moneda", "COP")

            if moneda in monedas:

                monedas[moneda]["valor_renta_fija"] += float(
                    inversion.get("valor_estimado", 0)
                )

        # CALCULAR TOTALES POR MONEDA

        for moneda in monedas:

            monedas[moneda]["valor_total"] = (
                monedas[moneda]["valor_acciones"]
                + monedas[moneda]["valor_renta_fija"]
            )

        # CONSTRUIR FLUJOS DE DINERO

        flujos = {
            "USD": [],
            "COP": []
        }

        for operacion in operaciones:

            moneda = operacion.get("moneda", "USD")

            if moneda not in flujos:
                continue

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

        # AGREGAR DIVIDENDOS, INTERESES Y OTROS INGRESOS

        for ingreso in ingresos:

            moneda = ingreso.get("moneda", "COP")

            if moneda not in flujos:
                continue

            flujos[moneda].append({
                "fecha": self.convertir_fecha(ingreso["fecha"]),
                "monto": float(ingreso["monto"])
            })

        # AGREGAR CAPITAL DE RENTA FIJA INVERTIDO

        for inversion in inversiones_fijas:

            moneda = inversion.get("moneda", "COP")

            if moneda not in flujos:
                continue

            flujos[moneda].append({
                "fecha": self.convertir_fecha(
                    inversion["fecha_inicio"]
                ),
                "monto": -float(inversion["capital"])
            })

        # CALCULAR RENTABILIDAD POR MONEDA

        rentabilidad = {}

        for moneda in ["USD", "COP"]:

            rentabilidad[moneda] = Calculos.calcular_resumen(
                flujos[moneda],
                monedas[moneda]["valor_total"]
            )

        # CALCULAR DIVIDENDOS ANUALES ESTIMADOS

        dividendos_anuales = sum(
            accion["dividendos_estimados"]
            for accion in acciones
        )

        return {
            "acciones": acciones,
            "inversiones_fijas": inversiones,
            "monedas": monedas,
            "rentabilidad": rentabilidad,
            "dividendos_estimados_anuales_usd": dividendos_anuales,
            "errores_actualizacion": errores
        }