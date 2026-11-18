"""Modelos de datos (clases simples) usados por toda la aplicación."""
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, Optional

import pandas as pd

# Activos que SIEMPRE deben estar en el portafolio (requisito del proyecto)
TICKERS_OBLIGATORIOS = ("KO", "NKE")

INSTRUMENTOS_RV = ("Acción", "ETF")          # renta variable (precio de mercado en USD)
INSTRUMENTOS_RF = ("CDT", "Bono", "TES")     # renta fija (tasa E.A. en COP)
NOMINAL_RF = 1_000_000.0                     # valor nominal de 1 "título" de renta fija (COP)


@dataclass
class Activo:
    """Un activo del portafolio con su ponderación (0.0 a 1.0)."""
    ticker: str                         # símbolo (renta variable) o nombre (p. ej. CDT-1)
    peso: float
    obligatorio: bool = False
    instrumento: str = "Acción"         # Acción, ETF, CDT, Bono o TES
    tasa_ea: float = 0.0                # tasa efectiva anual (0.11 = 11 %), solo renta fija
    plazo_dias: int = 0                 # días al vencimiento, solo renta fija
    comision_pct: Optional[float] = None  # None = usa la comisión global
    capitaliza: bool = True             # renta fija: True = el valor crece a la tasa E.A.

    @property
    def es_renta_fija(self) -> bool:
        return self.instrumento in INSTRUMENTOS_RF

    @property
    def tipo(self) -> str:
        return "Renta fija" if self.es_renta_fija else "Renta variable"


@dataclass
class Parametros:
    """Parámetros de la simulación definidos por el usuario."""
    capital_cop: float                 # Capital inicial en pesos colombianos
    fecha_inicio: date                 # Primer día de la simulación
    fecha_fin: date                    # Último día (≈ 1 año después)
    comision_pct: float = 0.002        # Corretaje: 0.2 % (el del Excel)
    permitir_fracciones: bool = True
    rezago_pago_dias: int = 30         # días entre ex-dividendo y pago (si no hay Excel)


@dataclass
class Resultado:
    """Salida de la simulación."""
    libros: Dict[str, pd.DataFrame] = field(default_factory=dict)  # por activo
    consolidado: pd.DataFrame = None                               # portafolio
    metricas: Dict[str, float] = field(default_factory=dict)
    pesos_finales: pd.Series = None                                # por activo + caja
    distribucion_tipo: pd.Series = None                            # renta fija / variable / caja
    resumen_activos: pd.DataFrame = None                           # tabla por activo
    detalle_operaciones: pd.DataFrame = None                       # operaciones y dividendos con TRM
    formato_excel: pd.DataFrame = None                             # mismas columnas que la hoja de Excel
