"""Descarga de datos de mercado con yfinance (precios, dividendos y TRM)."""
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd


class ProveedorDatos:
    """Encapsula todo acceso a internet/yfinance."""

    TICKER_TRM = "COP=X"   # Pesos colombianos por 1 USD
    ARCHIVO_CACHE_TRM = ".trm_cache.json"
    FUENTE_TRM = ("Yahoo Finance (COP=X): referencia de mercado USD/COP, no necesariamente la TRM "
                  "oficial certificada por la Superintendencia Financiera de Colombia")

    @staticmethod
    def _limpiar_indice(df: pd.DataFrame) -> pd.DataFrame:
        """Quita zona horaria y hora para poder cruzar series por fecha."""
        df = df.copy()
        df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
        return df[~df.index.duplicated(keep="last")]

    def descargar_activo(self, ticker: str, inicio: date, fin: date) -> pd.DataFrame:
        """Devuelve DataFrame con Precio_USD (cierre) y Dividendo_USD (por acción)."""
        import yfinance as yf  # import diferido: solo se necesita al descargar
        h = yf.Ticker(ticker).history(
            start=inicio.isoformat(),
            end=(fin + timedelta(days=1)).isoformat(),
            auto_adjust=False,   # precio SIN ajustar por dividendos (se suman aparte)
            actions=True,
        )
        if h.empty:
            raise ValueError(f"No se encontraron datos para '{ticker}'.")
        h = self._limpiar_indice(h)
        out = pd.DataFrame({"Precio_USD": h["Close"]})
        out["Dividendo_USD"] = h["Dividends"] if "Dividends" in h else 0.0
        return out

    def descargar_trm(self, inicio: date, fin: date) -> pd.Series:
        """Serie diaria de TRM (COP por USD). Se baja unos días antes para rellenar."""
        import yfinance as yf
        h = yf.Ticker(self.TICKER_TRM).history(
            start=(inicio - timedelta(days=15)).isoformat(),
            end=(fin + timedelta(days=1)).isoformat(),
        )
        if h.empty:
            raise ValueError("No se pudo descargar la TRM (COP=X).")
        return self._limpiar_indice(h)["Close"].rename("TRM")

    # ------------------------------------------------------------------
    # TRM ACTUAL (solo para mostrar en el dashboard; NO reemplaza el TRM histórico
    # de cada operación, que sigue saliendo de descargar_trm)
    # ------------------------------------------------------------------
    def _consultar_trm_actual(self) -> dict:
        """Última cotización USD/COP disponible en Yahoo Finance."""
        import yfinance as yf  # import diferido, igual que en el resto de la clase
        h = yf.Ticker(self.TICKER_TRM).history(period="10d")
        if h.empty:
            raise ValueError("Yahoo Finance no devolvió datos para COP=X.")
        cierre = self._limpiar_indice(h)["Close"].dropna()
        if cierre.empty:
            raise ValueError("Yahoo Finance no devolvió cotizaciones válidas para COP=X.")
        return {"valor": float(cierre.iloc[-1]), "fecha_dato": cierre.index[-1].date().isoformat()}

    @staticmethod
    def _leer_cache(archivo: Path) -> Optional[dict]:
        try:
            dato = json.loads(archivo.read_text(encoding="utf-8"))
            return dato if {"valor", "fecha_dato", "fecha_consulta"} <= set(dato) else None
        except (OSError, ValueError):
            return None

    @staticmethod
    def _guardar_cache(archivo: Path, dato: dict) -> None:
        try:
            archivo.write_text(json.dumps(dato), encoding="utf-8")
        except OSError:
            pass                                    # sin caché en disco el programa sigue igual

    def trm_actual(self, archivo_cache: Optional[str] = None, hoy: Optional[date] = None) -> dict:
        """TRM actual con caché diaria: se consulta una sola vez por día.

        Devuelve {valor, fecha_dato, fecha_consulta, fuente, desde_cache, desactualizado}.
        Si la consulta falla y hay un dato guardado, lo devuelve marcado como desactualizado;
        si no hay nada guardado, lanza la excepción para que quien llama muestre un aviso.
        """
        archivo = Path(archivo_cache or self.ARCHIVO_CACHE_TRM)
        hoy = hoy or date.today()
        cache = self._leer_cache(archivo)
        if cache and cache["fecha_consulta"] == hoy.isoformat():
            return {**cache, "desde_cache": True, "desactualizado": False}
        try:
            dato = self._consultar_trm_actual()
        except Exception as e:
            if cache:
                return {**cache, "desde_cache": True, "desactualizado": True, "error": str(e)}
            raise
        dato.update(fecha_consulta=hoy.isoformat(), fuente=self.FUENTE_TRM)
        self._guardar_cache(archivo, dato)
        return {**dato, "desde_cache": False, "desactualizado": False}
