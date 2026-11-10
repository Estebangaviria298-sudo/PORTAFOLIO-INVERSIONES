
class Portafolio:

    MONEDAS = ["USD", "COP"]

    def __init__(self, nombre):
        self.nombre = nombre
        self.acciones = []
        self.inversiones_fijas = []
        self.operaciones = []

    def agregar_accion(self, accion):
        self.acciones.append(accion)

    def agregar_inversion_fija(self, inversion):
        self.inversiones_fijas.append(inversion)

    def agregar_operacion(self, operacion):
        self.operaciones.append(operacion)

    def calcular_valor_acciones(self, moneda="USD"):
        moneda = moneda.upper()

        if moneda not in self.MONEDAS:
            raise ValueError("La moneda debe ser USD o COP.")

        if moneda != "USD":
            return 0.0

        total = 0.0

        for accion in self.acciones:
            total += float(accion.calcular_valor_actual())

        return total

    def calcular_valor_renta_fija(self, moneda=None):

        if moneda is not None:
            moneda = moneda.upper()

            if moneda not in self.MONEDAS:
                raise ValueError("La moneda debe ser USD o COP.")

            total = 0.0

            for inversion in self.inversiones_fijas:

                moneda_inversion = getattr(
                    inversion, "moneda", "COP"
                ).upper()

                if moneda_inversion == moneda:
                    total += float(
                        inversion.calcular_valor_estimado()
                    )

            return total

        totales = {
            "USD": 0.0,
            "COP": 0.0
        }

        for inversion in self.inversiones_fijas:

            moneda_inversion = getattr(
                inversion, "moneda", "COP"
            ).upper()

            if moneda_inversion not in self.MONEDAS:
                raise ValueError(
                    f"Moneda no permitida: {moneda_inversion}"
                )

            totales[moneda_inversion] += float(
                inversion.calcular_valor_estimado()
            )

        return totales

    def calcular_valor_total(self, moneda=None):

        if moneda is not None:
            moneda = moneda.upper()

            if moneda not in self.MONEDAS:
                raise ValueError("La moneda debe ser USD o COP.")

            return (
                self.calcular_valor_acciones(moneda)
                + self.calcular_valor_renta_fija(moneda)
            )

        return {
            "USD": self.calcular_valor_total("USD"),
            "COP": self.calcular_valor_total("COP")
        }

    def calcular_distribucion(self, moneda=None):

        if moneda is not None:
            moneda = moneda.upper()

            if moneda not in self.MONEDAS:
                raise ValueError("La moneda debe ser USD o COP.")

            valor_acciones = self.calcular_valor_acciones(moneda)
            valor_fija = self.calcular_valor_renta_fija(moneda)

            total = valor_acciones + valor_fija

            if total == 0:
                return {
                    "renta_variable": 0.0,
                    "renta_fija": 0.0
                }

            return {
                "renta_variable": (
                    valor_acciones / total
                ) * 100,

                "renta_fija": (
                    valor_fija / total
                ) * 100
            }

        return {
            "USD": self.calcular_distribucion("USD"),
            "COP": self.calcular_distribucion("COP")
        }
