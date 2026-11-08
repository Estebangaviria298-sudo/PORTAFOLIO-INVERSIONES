from datetime import date, datetime


class RentaFija:

    TIPOS_PERMITIDOS = ["CDT", "BONO", "TES"]

    FRECUENCIAS_PERMITIDAS = [
        "MENSUAL",
        "TRIMESTRAL",
        "SEMESTRAL",
        "ANUAL",
        "AL_VENCIMIENTO"
    ]

    def __init__(
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

        self.tipo = tipo.upper()
        self.nombre = nombre
        self.capital = float(capital)
        self.tasa_ea = float(tasa_ea)

        self.fecha_inicio = self.convertir_fecha(fecha_inicio)
        self.fecha_vencimiento = self.convertir_fecha(
            fecha_vencimiento
        )

        self.moneda = moneda.upper()
        self.frecuencia_pago = frecuencia_pago.upper()

        if self.tipo not in self.TIPOS_PERMITIDOS:
            raise ValueError("El tipo debe ser CDT, BONO o TES.")

        if self.capital <= 0:
            raise ValueError("El capital debe ser mayor que cero.")

        if self.tasa_ea < 0:
            raise ValueError("La tasa no puede ser negativa.")

        if self.fecha_vencimiento <= self.fecha_inicio:
            raise ValueError(
                "El vencimiento debe ser posterior al inicio."
            )

        if self.moneda not in ["COP", "USD"]:
            raise ValueError("La moneda debe ser COP o USD.")

        if self.frecuencia_pago not in self.FRECUENCIAS_PERMITIDAS:
            raise ValueError("La frecuencia de pago no es válida.")

    @staticmethod
    def convertir_fecha(fecha):

        if isinstance(fecha, datetime):
            return fecha.date()

        if isinstance(fecha, date):
            return fecha

        return datetime.strptime(str(fecha)[:10], "%Y-%m-%d").date()

    def calcular_intereses(self, capital=None, dias=None):

        if capital is None:
            capital = self.capital

        if dias is None:
            dias = (
                self.fecha_vencimiento - self.fecha_inicio
            ).days

        tasa_diaria = (1 + self.tasa_ea) ** (1 / 365) - 1

        valor_final = capital * ((1 + tasa_diaria) ** dias)

        return valor_final - capital

    def calcular_valor_estimado(self):

        fecha_actual = min(date.today(), self.fecha_vencimiento)

        dias = max(
            0,
            (fecha_actual - self.fecha_inicio).days
        )

        return self.capital + self.calcular_intereses(
            self.capital,
            dias
        )