"""Modelo de un activo financiero (acción o ETF) dentro del portafolio."""
from dataclasses import dataclass


@dataclass
class Activo:
    ticker: str          # Ej: "KO"
    peso: float          # Porcentaje asignado (0-100)
    obligatorio: bool = False

    def fraccion(self) -> float:
        """Peso como fracción (0-1)."""
        return self.peso / 100.0
