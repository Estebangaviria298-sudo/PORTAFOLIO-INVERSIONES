
class Operacion:

    def __init__(self, fecha, tipo, tipo_activo, activo,
                 cantidad, precio_unitario, comision=0):

        self.fecha = fecha
        self.tipo = tipo.upper()
        self.tipo_activo = tipo_activo.upper()
        self.activo = activo
        self.cantidad = cantidad
        self.precio_unitario = precio_unitario
        self.comision = comision

    def calcular_total_bruto(self):
        return self.cantidad * self.precio_unitario

    def calcular_total_neto(self):

        total = self.calcular_total_bruto()

        if self.tipo == "COMPRA":
            return total + self.comision

        elif self.tipo == "VENTA":
            return total - self.comision

        else:
            return total - self.comision
