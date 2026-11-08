from datetime import date

from servicios.resumen_portafolio import ResumenPortafolio
from servicios.datos_mercado import DatosMercado


class ProyeccionPortafolio:

    def __init__(self):
        self.resumen = ResumenPortafolio()
        self.datos_mercado = DatosMercado()

    def proyectar(self):

        resumen = self.resumen.obtener_resumen()

        resultado = {
            "USD": {
                "valor_actual": 0.0,
                "valor_proyectado": 0.0,
                "ganancia_proyectada": 0.0,
                "rentabilidad_proyectada": 0.0
            },
            "COP": {
                "valor_actual": 0.0,
                "valor_proyectado": 0.0,
                "ganancia_proyectada": 0.0,
                "rentabilidad_proyectada": 0.0
            }
        }

        detalle_acciones = []
        detalle_renta_fija = []
        errores = []

        # Proyección de las acciones.

        for accion in resumen["acciones"]:

            ticker = accion["ticker"]
            moneda = accion["moneda"]

            try:
                historial = self.datos_mercado.obtener_historial(ticker)
                precios = historial["Close"].dropna()

                if len(precios) < 2:
                    raise ValueError("No hay suficientes precios históricos.")

                precio_inicial = float(precios.iloc[0])
                precio_final = float(precios.iloc[-1])

                rendimiento_historico = (
                    (precio_final / precio_inicial) - 1
                )

                valor_actual = float(accion["valor_actual"])

                valor_acciones_proyectado = (
                    valor_actual * (1 + rendimiento_historico)
                )

                dividendos = float(
                    accion["dividendos_estimados"]
                )

                valor_proyectado = (
                    valor_acciones_proyectado + dividendos
                )

                resultado[moneda]["valor_actual"] += valor_actual
                resultado[moneda]["valor_proyectado"] += valor_proyectado

                detalle_acciones.append({
                    "ticker": ticker,
                    "rendimiento_historico": rendimiento_historico * 100,
                    "valor_actual": valor_actual,
                    "valor_acciones_proyectado": valor_acciones_proyectado,
                    "dividendos_estimados": dividendos,
                    "valor_proyectado": valor_proyectado,
                    "moneda": moneda
                })

            except Exception as error:
                errores.append(
                    f"No se pudo proyectar {ticker}: {error}"
                )

        # Proyección de las inversiones de renta fija.

        for inversion in resumen["inversiones_fijas"]:

            moneda = inversion["moneda"]

            capital = float(inversion["capital_pendiente"])
            tasa_ea = float(inversion["tasa_ea"])
            valor_actual = float(inversion["valor_estimado"])

            vencimiento = date.fromisoformat(
                inversion["fecha_vencimiento"]
            )

            dias_restantes = max(
                0,
                (vencimiento - date.today()).days
            )

            dias_proyeccion = min(365, dias_restantes)

            intereses_futuros = capital * (
                (1 + tasa_ea) ** (dias_proyeccion / 365) - 1
            )

            valor_proyectado = valor_actual + intereses_futuros

            resultado[moneda]["valor_actual"] += valor_actual
            resultado[moneda]["valor_proyectado"] += valor_proyectado

            detalle_renta_fija.append({
                "nombre": inversion["nombre"],
                "tipo": inversion["tipo"],
                "capital_pendiente": capital,
                "intereses_futuros": intereses_futuros,
                "valor_actual": valor_actual,
                "valor_proyectado": valor_proyectado,
                "dias_proyeccion": dias_proyeccion,
                "moneda": moneda
            })

        # Calcular ganancias y rentabilidad por moneda.

        for moneda in resultado:

            valor_actual = resultado[moneda]["valor_actual"]
            valor_proyectado = resultado[moneda]["valor_proyectado"]

            ganancia = valor_proyectado - valor_actual

            if valor_actual > 0:
                rentabilidad = (ganancia / valor_actual) * 100
            else:
                rentabilidad = 0.0

            resultado[moneda]["ganancia_proyectada"] = ganancia
            resultado[moneda]["rentabilidad_proyectada"] = rentabilidad

        return {
            "periodo": "Hasta un año",
            "acciones": detalle_acciones,
            "renta_fija": detalle_renta_fija,
            "totales": resultado,
            "errores": errores,
            "aclaracion": (
                "La proyección es estimada y utiliza el rendimiento "
                "histórico de precios, los dividendos recientes y las "
                "tasas de renta fija registradas. No garantiza ganancias."
            )
        }