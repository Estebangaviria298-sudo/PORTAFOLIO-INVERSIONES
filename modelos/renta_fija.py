
from datetime import date


class RentaFija:

    def __init__(self, tipo, nombre, capital, tasa_ea,
                 fecha_inicio, fecha_vencimiento):

        self.tipo = tipo.upper()
        self.nombre = nombre
        self.capital = capital
        self.tasa_ea = tasa_ea
        self.fecha_inicio = fecha_inicio
        self.fecha_vencimiento = fecha_vencimiento

    def calcular_dias_invertidos(self):
        fecha_actual = min(date.today(), self.fecha_vencimiento)

        dias = (fecha_actual - self.fecha_inicio).days

        return max(0, dias)

    def calcular_intereses_estimados(self):
        dias = self.calcular_dias_invertidos()

        tasa_diaria = (1 + self.tasa_ea) ** (1 / 365) - 1

        valor_final = self.capital * ((1 + tasa_diaria) ** dias)

        return valor_final - self.capital

    def calcular_valor_estimado(self):
        return self.capital + self.calcular_intereses_estimados()
