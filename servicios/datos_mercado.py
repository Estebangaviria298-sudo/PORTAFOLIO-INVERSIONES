
import yfinance as yf
import pandas as pd


class DatosMercado:

    def __init__(self):
        self.empresas = {
            "KO": "Coca-Cola",
            "NKE": "Nike"
        }

    def obtener_historial(self, ticker):

        ticker = ticker.upper()

        if ticker not in self.empresas:
            raise ValueError("Solo se permiten las acciones KO y NKE.")

        empresa = yf.Ticker(ticker)
        historial = empresa.history(period="1y", auto_adjust=False)

        if historial.empty:
            raise ValueError(f"No se encontraron datos para {ticker}.")

        return historial

    def obtener_precio_actual(self, ticker):

        historial = self.obtener_historial(ticker)

        precio = historial["Close"].dropna().iloc[-1]

        return float(precio)

    def obtener_dividendos(self, ticker):

        ticker = ticker.upper()

        if ticker not in self.empresas:
            raise ValueError("Solo se permiten las acciones KO y NKE.")

        empresa = yf.Ticker(ticker)
        dividendos = empresa.dividends

        if dividendos.empty:
            return 0.0

        fechas = pd.to_datetime(dividendos.index, utc=True)
        fecha_limite = pd.Timestamp.now(tz="UTC") - pd.DateOffset(years=1)

        dividendos_ultimo_anio = dividendos[fechas >= fecha_limite]

        return float(dividendos_ultimo_anio.sum())

    def obtener_datos_accion(self, ticker):

        ticker = ticker.upper()

        if ticker not in self.empresas:
            raise ValueError("Solo se permiten las acciones KO y NKE.")

        precio = self.obtener_precio_actual(ticker)
        dividendos = self.obtener_dividendos(ticker)

        return {
            "ticker": ticker,
            "nombre": self.empresas[ticker],
            "precio_actual": precio,
            "moneda": "USD",
            "dividendo_anual_por_accion": dividendos
        }
