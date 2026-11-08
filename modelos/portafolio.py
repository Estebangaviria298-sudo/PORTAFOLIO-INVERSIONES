
class Portafolio:

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

    def calcular_valor_acciones(self):
        total = 0

        for accion in self.acciones:
            total += accion.calcular_valor_actual()

        return total

    def calcular_valor_renta_fija(self):
        total = 0

        for inversion in self.inversiones_fijas:
            total += inversion.calcular_valor_estimado()

        return total

    def calcular_valor_total(self):
        return (
            self.calcular_valor_acciones()
            + self.calcular_valor_renta_fija()
        )

    def calcular_distribucion(self):

        total = self.calcular_valor_total()

        if total == 0:
            return {
                "renta_variable": 0,
                "renta_fija": 0
            }

        porcentaje_variable = (
            self.calcular_valor_acciones() / total
        ) * 100

        porcentaje_fija = (
            self.calcular_valor_renta_fija() / total
        ) * 100

        return {
            "renta_variable": porcentaje_variable,
            "renta_fija": porcentaje_fija
        }
