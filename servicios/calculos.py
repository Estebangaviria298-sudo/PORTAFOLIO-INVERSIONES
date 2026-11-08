
from datetime import date, datetime
import math


class Calculos:

    @staticmethod
    def convertir_fecha(fecha):

        if isinstance(fecha, datetime):
            return fecha.date()

        if isinstance(fecha, date):
            return fecha

        return datetime.strptime(str(fecha)[:10], "%Y-%m-%d").date()

    @staticmethod
    def construir_flujos(operaciones, ingresos):

        flujos = []

        for operacion in operaciones:

            fecha = Calculos.convertir_fecha(operacion["fecha"])

            cantidad = float(operacion["cantidad"])
            precio = float(operacion["precio_unitario"])
            comision = float(operacion["comision"])

            total = cantidad * precio

            if operacion["tipo"].upper() == "COMPRA":
                monto = -(total + comision)

            elif operacion["tipo"].upper() == "VENTA":
                monto = total - comision

            else:
                continue

            flujos.append({
                "fecha": fecha,
                "monto": monto
            })

        for ingreso in ingresos:

            fecha = Calculos.convertir_fecha(ingreso["fecha"])
            monto = float(ingreso["monto"])

            flujos.append({
                "fecha": fecha,
                "monto": monto
            })

        return flujos

    @staticmethod
    def calcular_rentabilidad_acumulada(flujos, valor_actual):

        inversion_total = sum(
            abs(flujo["monto"])
            for flujo in flujos
            if flujo["monto"] < 0
        )

        ingresos_recibidos = sum(
            flujo["monto"]
            for flujo in flujos
            if flujo["monto"] > 0
        )

        resultado = ingresos_recibidos + valor_actual - inversion_total

        if inversion_total == 0:
            return 0.0

        return (resultado / inversion_total) * 100

    @staticmethod
    def calcular_xirr(flujos, valor_actual=0, fecha_valoracion=None):

        if not flujos:
            return None

        if fecha_valoracion is None:
            fecha_valoracion = date.today()

        fecha_valoracion = Calculos.convertir_fecha(fecha_valoracion)

        movimientos = []

        for flujo in flujos:

            movimientos.append((
                Calculos.convertir_fecha(flujo["fecha"]),
                float(flujo["monto"])
            ))

        if valor_actual > 0:
            movimientos.append((
                fecha_valoracion,
                float(valor_actual)
            ))

        movimientos.sort(key=lambda x: x[0])

        if not any(monto < 0 for _, monto in movimientos):
            return None

        if not any(monto > 0 for _, monto in movimientos):
            return None

        fecha_inicial = movimientos[0][0]

        def calcular_van(tasa):

            resultado = 0.0

            for fecha, monto in movimientos:

                dias = (fecha - fecha_inicial).days
                exponente = dias / 365.0

                try:
                    resultado += monto / ((1 + tasa) ** exponente)
                except (OverflowError, ZeroDivisionError):
                    return float("inf")

            return resultado

        limite_inferior = -0.9999
        limite_superior = 1.0

        van_inferior = calcular_van(limite_inferior)
        van_superior = calcular_van(limite_superior)

        while (
            van_inferior * van_superior > 0
            and limite_superior < 100000
        ):
            limite_superior = (limite_superior * 2) + 1
            van_superior = calcular_van(limite_superior)

        if van_inferior * van_superior > 0:
            return None

        for _ in range(200):

            tasa_media = (
                limite_inferior + limite_superior
            ) / 2

            van_medio = calcular_van(tasa_media)

            if abs(van_medio) < 0.000001:
                return tasa_media * 100

            if van_inferior * van_medio <= 0:

                limite_superior = tasa_media

            else:

                limite_inferior = tasa_media
                van_inferior = van_medio

        return (
            (limite_inferior + limite_superior) / 2
        ) * 100

    @staticmethod
    def calcular_resumen(flujos, valor_actual):

        rentabilidad = Calculos.calcular_rentabilidad_acumulada(
            flujos,
            valor_actual
        )

        rentabilidad_ea = Calculos.calcular_xirr(
            flujos,
            valor_actual
        )

        inversion_total = sum(
            abs(flujo["monto"])
            for flujo in flujos
            if flujo["monto"] < 0
        )

        ingresos = sum(
            flujo["monto"]
            for flujo in flujos
            if flujo["monto"] > 0
        )

        ganancia = ingresos + valor_actual - inversion_total

        return {
            "total_invertido": inversion_total,
            "ingresos_recibidos": ingresos,
            "valor_actual": valor_actual,
            "ganancia_total": ganancia,
            "rentabilidad_acumulada": rentabilidad,
            "rentabilidad_efectiva_anual": rentabilidad_ea
        }
