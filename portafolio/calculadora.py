"""CalculadoraRentabilidad: rentabilidad acumulada y rentabilidad efectiva anual (E.A.)."""
from typing import List, Optional, Tuple


class CalculadoraRentabilidad:
    DIAS_ANIO = 365

    @staticmethod
    def rentabilidad_acumulada(base: float, ganancia: float) -> float:
        """ganancia / base (base = capital o total invertido)."""
        return ganancia / base if base > 0 else 0.0

    @classmethod
    def anualizar(cls, rentabilidad: float, dias: int) -> float:
        """E.A. simple: (1 + r)^(365/días) - 1."""
        if dias <= 0 or rentabilidad <= -1:
            return rentabilidad
        return (1 + rentabilidad) ** (cls.DIAS_ANIO / dias) - 1

    @classmethod
    def valor_presente_neto(cls, tasa: float, flujos: List[Tuple]) -> float:
        t0 = flujos[0][0]
        return sum(cf / (1 + tasa) ** ((d - t0).days / cls.DIAS_ANIO) for d, cf in flujos)

    @classmethod
    def tasa_efectiva_anual(cls, flujos: List[Tuple]) -> Optional[float]:
        """TIR con fechas (XIRR). flujos = [(fecha, monto)]: compras y comisiones negativas;
        ventas, dividendos, intereses y el valor final del portafolio positivos.
        Resuelve por bisección; devuelve None si no hay solución."""
        flujos = sorted(flujos, key=lambda x: x[0])
        if len(flujos) < 2 or not any(m < 0 for _, m in flujos) or not any(m > 0 for _, m in flujos):
            return None
        if (flujos[-1][0] - flujos[0][0]).days <= 0:
            return None
        bajo, alto = -0.9999, 1000.0
        f_bajo = cls.valor_presente_neto(bajo, flujos)
        if f_bajo * cls.valor_presente_neto(alto, flujos) > 0:
            return None
        for _ in range(200):
            medio = (bajo + alto) / 2
            f_medio = cls.valor_presente_neto(medio, flujos)
            if abs(f_medio) < 1e-9:
                return medio
            if f_bajo * f_medio < 0:
                alto = medio
            else:
                bajo, f_bajo = medio, f_medio
        return (bajo + alto) / 2
