
from datetime import date, datetime


class Calculos:

    @staticmethod
    def convertir_fecha(fecha):
        if isinstance(fecha, datetime):
            return fecha.date()
        if isinstance(fecha, date):
            return fecha
        return datetime.strptime(str(fecha)[:10], "%Y-%m-%d").date()

    @staticmethod
    def calcular_rentabilidad_acumulada(flujos, valor_actual):
        movimientos = sum(float(f["monto"]) for f in flujos)
        inversion_neta = -sum(
            float(f["monto"]) for f in flujos if float(f["monto"]) < 0
        )

        ganancia = movimientos + float(valor_actual)

        if inversion_neta <= 0:
            return 0.0

        return (ganancia / inversion_neta) * 100

    @staticmethod
    def calcular_xirr(flujos, valor_actual=0, fecha_valoracion=None):
        if fecha_valoracion is None:
            fecha_valoracion = date.today()

        movimientos = [
            (Calculos.convertir_fecha(f["fecha"]), float(f["monto"]))
            for f in flujos
        ]

        if valor_actual > 0:
            movimientos.append(
                (Calculos.convertir_fecha(fecha_valoracion), float(valor_actual))
            )

        if not movimientos:
            return None

        movimientos.sort(key=lambda x: x[0])

        if not any(m < 0 for _, m in movimientos):
            return None

        if not any(m > 0 for _, m in movimientos):
            return None

        fecha_inicial = movimientos[0][0]

        def van(tasa):
            return sum(
                monto / ((1 + tasa) ** ((fecha - fecha_inicial).days / 365))
                for fecha, monto in movimientos
            )

        inferior = -0.9999
        superior = 1.0

        for _ in range(100):
            medio = (inferior + superior) / 2

            if van(medio) > 0:
                inferior = medio
            else:
                superior = medio

        return ((inferior + superior) / 2) * 100

    @staticmethod
    def calcular_resumen(flujos, valor_actual):
        inversion = sum(
            abs(float(f["monto"]))
            for f in flujos if float(f["monto"]) < 0
        )

        ingresos = sum(
            float(f["monto"])
            for f in flujos if float(f["monto"]) > 0
        )

        ganancia = ingresos + float(valor_actual) - inversion

        return {
            "total_invertido": inversion,
            "ingresos_recibidos": ingresos,
            "valor_actual": float(valor_actual),
            "ganancia_total": ganancia,
            "rentabilidad_acumulada": (
                ganancia / inversion * 100 if inversion > 0 else 0.0
            ),
            "rentabilidad_efectiva_anual": Calculos.calcular_xirr(
                flujos, valor_actual
            )
        }
