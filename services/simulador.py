"""Simulación del portafolio a 1 año con conversión COP -> USD -> COP."""
import pandas as pd
from models.portafolio import Portafolio
from services.datos_mercado import ServicioMercado


class SimuladorPortafolio:
    def __init__(self, portafolio: Portafolio, mercado: ServicioMercado):
        self.p = portafolio
        self.mercado = mercado
        self.evolucion = pd.DataFrame()
        self.dividendos = pd.DataFrame()
        self.distribucion = pd.DataFrame()
        self.metricas = {}

    def ejecutar(self) -> None:
        p = self.p
        datos = {a.ticker: self.mercado.historico(a.ticker, p.fecha_inicio, p.fecha_fin)
                 for a in p.activos}
        indice = None  # días con precio para todos los activos
        for d in datos.values():
            indice = d.index if indice is None else indice.intersection(d.index)
        trm = self.mercado.trm(p.fecha_inicio, p.fecha_fin, indice)

        capital_usd = p.capital_cop / trm.iloc[0]          # TRM del primer día
        valor_usd = pd.DataFrame(index=indice)
        filas_div, dist = [], []

        for a in p.activos:
            precio = datos[a.ticker]["Close"].reindex(indice)
            acciones = capital_usd * a.fraccion() / precio.iloc[0]
            valor_usd[a.ticker] = acciones * precio
            divs = datos[a.ticker]["Dividends"]
            for f, d in divs[divs > 0].items():
                previas = trm[:f]  # TRM vigente ese día (o la última anterior)
                trm_f = previas.iloc[-1] if len(previas) else trm.iloc[0]
                usd = acciones * d
                filas_div.append({"Fecha": f, "Ticker": a.ticker,
                                  "Dividendo_USD_por_accion": d, "Acciones": acciones,
                                  "Dividendo_USD": usd, "TRM": trm_f,
                                  "Dividendo_COP": usd * trm_f})
            dist.append({"Ticker": a.ticker, "Inversion_COP": p.capital_cop * a.fraccion()})

        self.dividendos = pd.DataFrame(filas_div)
        self.distribucion = pd.DataFrame(dist)
        total_cop = valor_usd.sum(axis=1) * trm
        div_acum = pd.Series(0.0, index=indice)
        if not self.dividendos.empty:
            por_dia = self.dividendos.groupby("Fecha")["Dividendo_COP"].sum()
            div_acum = por_dia.reindex(indice).fillna(0).cumsum()
        self.evolucion = pd.DataFrame({"TRM": trm, "Valor_USD": valor_usd.sum(axis=1),
                                       "Valor_COP": total_cop,
                                       "Dividendos_COP_Acum": div_acum,
                                       "Total_COP": total_cop + div_acum})
        final = self.evolucion.iloc[-1]
        ganancia = final["Total_COP"] - p.capital_cop
        self.metricas = {
            "capital_inicial": p.capital_cop, "valor_final": final["Valor_COP"],
            "dividendos": final["Dividendos_COP_Acum"], "ganancia_total": ganancia,
            "rendimiento_pct": ganancia / p.capital_cop * 100,
            "trm_inicial": trm.iloc[0], "trm_final": trm.iloc[-1],
        }
