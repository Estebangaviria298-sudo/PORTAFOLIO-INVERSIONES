from datetime import date

from servicios.base_datos import BaseDatos
from servicios.datos_mercado import DatosMercado
from servicios.gestor_operaciones import GestorOperaciones


class GestorDividendos:

    def __init__(self):
        self.base_datos = BaseDatos()
        self.datos_mercado = DatosMercado()
        self.gestor_operaciones = GestorOperaciones()

    def obtener_estimacion_anual(self):

        posiciones = self.gestor_operaciones.obtener_posiciones_acciones()
        resultado = []

        for ticker, posicion in posiciones.items():

            datos = self.datos_mercado.obtener_datos_accion(ticker)

            cantidad = posicion["cantidad"]
            dividendo_por_accion = datos["dividendo_anual_por_accion"]

            resultado.append({
                "ticker": ticker,
                "nombre": datos["nombre"],
                "cantidad": cantidad,
                "dividendo_por_accion": dividendo_por_accion,
                "dividendos_estimados": cantidad * dividendo_por_accion,
                "moneda": "USD"
            })

        return resultado

    def registrar_dividendo(
        self, ticker, monto, fecha=None, descripcion=""
    ):

        ticker = ticker.upper()
        monto = float(monto)

        if ticker not in ["KO", "NKE"]:
            raise ValueError("Solo se permiten KO y NKE.")

        if monto <= 0:
            raise ValueError("El dividendo debe ser mayor que cero.")

        if fecha is None:
            fecha = date.today()

        if isinstance(fecha, str):
            fecha = date.fromisoformat(fecha[:10])

        if fecha > date.today():
            raise ValueError("No se pueden registrar dividendos futuros.")

        self.base_datos.registrar_ingreso(
            fecha=fecha,
            tipo_activo="ACCION",
            activo=ticker,
            tipo_ingreso="DIVIDENDO",
            monto=monto,
            descripcion=descripcion,
            moneda="USD"
        )

        return "Dividendo registrado correctamente."