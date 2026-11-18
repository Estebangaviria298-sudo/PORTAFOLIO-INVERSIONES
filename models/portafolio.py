"""Modelo del portafolio: capital inicial en COP y lista de activos."""
from datetime import date
from typing import List
from models.activo import Activo


class Portafolio:
    OBLIGATORIOS = ("KO", "NKE")

    def __init__(self, capital_cop: float, activos: List[Activo],
                 fecha_inicio: date, fecha_fin: date):
        self.capital_cop = capital_cop
        self.activos = activos
        self.fecha_inicio = fecha_inicio
        self.fecha_fin = fecha_fin

    def tickers(self) -> List[str]:
        return [a.ticker for a in self.activos]

    def peso_total(self) -> float:
        return sum(a.peso for a in self.activos)

    def validar(self) -> List[str]:
        """Devuelve lista de errores (vacía si el portafolio es válido)."""
        errores = []
        if self.capital_cop <= 0:
            errores.append("El capital inicial debe ser mayor que 0.")
        if abs(self.peso_total() - 100) > 0.01:
            errores.append(f"Los pesos suman {self.peso_total():.2f}%, deben sumar 100%.")
        faltan = [t for t in self.OBLIGATORIOS if t not in self.tickers()]
        if faltan:
            errores.append(f"Faltan activos obligatorios: {', '.join(faltan)}.")
        return errores
