
class Accion:

    def __init__(self, ticker, nombre, cantidad=0,
                 precio_promedio=0, precio_actual=0,
                 dividendo_anual_por_accion=0):

        self.ticker = ticker
        self.nombre = nombre
        self.cantidad = cantidad
        self.precio_promedio = precio_promedio
        self.precio_actual = precio_actual
        self.dividendo_anual_por_accion = dividendo_anual_por_accion

    def calcular_valor_invertido(self):
        return self.cantidad * self.precio_promedio

    def calcular_valor_actual(self):
        return self.cantidad * self.precio_actual

    def calcular_ganancia(self):
        return self.calcular_valor_actual() - self.calcular_valor_invertido()

    def calcular_dividendos_anuales(self):
        return self.cantidad * self.dividendo_anual_por_accion

    def actualizar_precio(self, nuevo_precio):
        self.precio_actual = nuevo_precio
