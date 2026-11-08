
from datetime import date

from modelos.renta_fija import RentaFija
from servicios.base_datos import BaseDatos


class GestorRentaFija:

    def __init__(self):
        self.base_datos = BaseDatos()

    def registrar_inversion(
        self,
        tipo,
        nombre,
        capital,
        tasa_ea,
        fecha_inicio,
        fecha_vencimiento,
        moneda="COP",
        frecuencia_pago="AL_VENCIMIENTO"
    ):

        inversion = RentaFija(
            tipo,
            nombre,
            capital,
            tasa_ea,
            fecha_inicio,
            fecha_vencimiento,
            moneda,
            frecuencia_pago
        )

        identificador = self.base_datos.registrar_inversion_fija(
            inversion
        )

        return identificador

    def registrar_pago(
        self,
        inversion_id,
        tipo,
        monto,
        fecha=None,
        descripcion=""
    ):

        tipo = tipo.upper()

        if tipo not in ["INTERES", "PAGO_CAPITAL"]:
            raise ValueError(
                "El pago debe ser INTERES o PAGO_CAPITAL."
            )

        monto = float(monto)

        if monto <= 0:
            raise ValueError("El monto debe ser mayor que cero.")

        inversion = self.base_datos.obtener_inversion_fija(
            inversion_id
        )

        if inversion is None:
            raise ValueError("La inversión no existe.")

        if fecha is None:
            fecha = date.today()

        fecha = RentaFija.convertir_fecha(fecha)

        fecha_inicio = RentaFija.convertir_fecha(
            inversion["fecha_inicio"]
        )

        fecha_vencimiento = RentaFija.convertir_fecha(
            inversion["fecha_vencimiento"]
        )

        if fecha < fecha_inicio or fecha > fecha_vencimiento:
            raise ValueError(
                "La fecha del pago debe estar dentro del plazo "
                "de la inversión."
            )

        if fecha > date.today():
            raise ValueError("No se pueden registrar pagos futuros.")

        saldo = float(inversion["saldo_pendiente"])

        if tipo == "PAGO_CAPITAL" and monto > saldo:
            raise ValueError(
                "El pago de capital supera el saldo pendiente."
            )

        if tipo == "INTERES":
            intereses = self.calcular_intereses_pendientes(inversion)

            if monto > intereses:
                raise ValueError(
                    "El pago supera los intereses pendientes."
                )

        self.base_datos.registrar_pago_renta_fija(
            inversion_id,
            fecha,
            tipo,
            monto,
            descripcion,
            inversion["moneda"]
        )

        return "Pago registrado correctamente."

    def calcular_intereses_pendientes(self, inversion):

        fecha_inicio = RentaFija.convertir_fecha(
            inversion["fecha_inicio"]
        )

        fecha_fin = min(
            date.today(),
            RentaFija.convertir_fecha(
                inversion["fecha_vencimiento"]
            )
        )

        if fecha_fin <= fecha_inicio:
            return 0.0

        tasa_ea = float(inversion["tasa_ea"])

        tasa_diaria = (1 + tasa_ea) ** (1 / 365) - 1

        saldo = float(inversion["capital"])
        intereses = 0.0
        fecha_anterior = fecha_inicio

        pagos = self.base_datos.obtener_pagos_renta_fija(
            inversion["id"]
        )

        for pago in pagos:

            fecha_pago = RentaFija.convertir_fecha(
                pago["fecha"]
            )

            if fecha_pago > fecha_fin:
                break

            dias = (fecha_pago - fecha_anterior).days

            if dias > 0:
                intereses += (
                    saldo * ((1 + tasa_diaria) ** dias - 1)
                )

            if pago["tipo"] == "INTERES":
                intereses = max(
                    0.0,
                    intereses - float(pago["monto"])
                )

            elif pago["tipo"] == "PAGO_CAPITAL":
                saldo -= float(pago["monto"])

            fecha_anterior = fecha_pago

        dias_finales = (fecha_fin - fecha_anterior).days

        if dias_finales > 0:
            intereses += (
                saldo * ((1 + tasa_diaria) ** dias_finales - 1)
            )

        return max(0.0, intereses)

    def obtener_resumen_inversion(self, inversion_id):

        inversion = self.base_datos.obtener_inversion_fija(
            inversion_id
        )

        if inversion is None:
            raise ValueError("La inversión no existe.")

        capital_pendiente = float(
            inversion["saldo_pendiente"]
        )

        intereses_pendientes = (
            self.calcular_intereses_pendientes(inversion)
        )

        return {
            "id": inversion["id"],
            "tipo": inversion["tipo"],
            "nombre": inversion["nombre"],
            "capital_inicial": float(inversion["capital"]),
            "capital_pendiente": capital_pendiente,
            "intereses_pendientes": intereses_pendientes,
            "valor_estimado": (
                capital_pendiente + intereses_pendientes
            ),
            "tasa_ea": float(inversion["tasa_ea"]),
            "moneda": inversion["moneda"],
            "fecha_inicio": inversion["fecha_inicio"],
            "fecha_vencimiento": inversion["fecha_vencimiento"],
            "frecuencia_pago": inversion["frecuencia_pago"]
        }

    def obtener_resumen_general(self):

        inversiones = self.base_datos.obtener_inversiones_fijas()

        resultado = []

        for inversion in inversiones:
            resumen = self.obtener_resumen_inversion(
                inversion["id"]
            )
            resultado.append(resumen)

        return resultado

    def calcular_valor_total(self):

        inversiones = self.obtener_resumen_general()

        totales = {}

        for inversion in inversiones:

            moneda = inversion["moneda"]

            if moneda not in totales:
                totales[moneda] = 0.0

            totales[moneda] += inversion["valor_estimado"]

        return totales
