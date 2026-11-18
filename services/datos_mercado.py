"""Servicio de acceso a Yahoo Finance (precios, dividendos y TRM)."""
import pandas as pd
import yfinance as yf


class ServicioMercado:
    TICKER_TRM = "COP=X"

    @staticmethod
    def _limpiar(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
        return df

    def historico(self, ticker: str, inicio, fin) -> pd.DataFrame:
        """Columnas: Close (sin ajustar), Dividends."""
        df = yf.Ticker(ticker).history(start=inicio, end=fin, auto_adjust=False)
        if df.empty:
            raise ValueError(f"Sin datos para {ticker}.")
        return self._limpiar(df)[["Close", "Dividends"]]

    def trm(self, inicio, fin, indice: pd.DatetimeIndex) -> pd.Series:
        """Serie TRM (COP por USD) alineada al índice dado (ffill/bfill)."""
        df = self._limpiar(yf.Ticker(self.TICKER_TRM).history(start=inicio, end=fin))
        if df.empty:
            raise ValueError("Sin datos de TRM (COP=X).")
        serie = df["Close"].reindex(df.index.union(indice)).ffill().bfill()
        return serie.reindex(indice).rename("TRM")
