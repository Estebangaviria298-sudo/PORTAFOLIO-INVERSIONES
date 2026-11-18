"""Gráficos Plotly del dashboard."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .modelos import Resultado


class Graficador:
    @staticmethod
    def dona_pesos(res: Resultado) -> go.Figure:
        s = res.pesos_finales[res.pesos_finales > 0]
        fig = px.pie(values=s.values, names=s.index, hole=0.55,
                     title="Distribución del portafolio (valor final en COP)")
        fig.update_traces(textinfo="label+percent")
        return fig

    @staticmethod
    def dona_tipo(res: Resultado) -> go.Figure:
        s = res.distribucion_tipo[res.distribucion_tipo > 0]
        fig = px.pie(values=s.values, names=s.index, hole=0.55,
                     title="Renta fija vs renta variable vs caja")
        fig.update_traces(textinfo="label+percent")
        return fig

    @staticmethod
    def evolucion_total(res: Resultado, capital: float) -> go.Figure:
        c = res.consolidado
        fig = go.Figure()
        fig.add_scatter(x=c.index, y=c["Valor_Total_COP"], name="Valor total (activos + caja)")
        fig.add_scatter(x=c.index, y=c["Valor_Activos_COP"], name="Solo activos", line=dict(dash="dot"))
        fig.add_hline(y=capital, line_dash="dash", annotation_text="Capital inicial")
        fig.update_layout(title="Evolución del portafolio en COP", yaxis_title="COP",
                          hovermode="x unified")
        return fig

    @staticmethod
    def comparativa_activos(res: Resultado) -> go.Figure:
        """Rentabilidad acumulada por activo EN COP (precio × TRM), base 0 %."""
        fig = go.Figure()
        for t, l in res.libros.items():
            serie = l["Precio_COP"] / l["Precio_COP"].iloc[0] - 1
            fig.add_scatter(x=l.index, y=serie, name=t)
        fig.add_scatter(x=res.consolidado.index, y=res.consolidado["Rentabilidad"],
                        name="PORTAFOLIO", line=dict(width=4, color="black"))
        fig.update_layout(title="Comparativa de rentabilidad acumulada (COP)",
                          yaxis_tickformat=".0%", hovermode="x unified")
        return fig

    @staticmethod
    def composicion(res: Resultado) -> go.Figure:
        d = pd.DataFrame({t: l["Valor_COP"] for t, l in res.libros.items()})
        d["Caja"] = res.consolidado["Saldo_Caja_COP"]
        fig = px.area(d, title="Composición del portafolio en el tiempo (COP)")
        fig.update_layout(yaxis_title="COP", legend_title="")
        return fig

    @staticmethod
    def dividendos(res: Resultado) -> go.Figure:
        filas = []
        for t, l in res.libros.items():
            ingreso = l["Ingreso_Dividendos_COP"] + l["Interes_COP"]
            for f, v in ingreso[ingreso > 0].items():
                filas.append({"Fecha": f, "Ticker": t, "Dividendos e intereses COP": v})
        if not filas:
            return go.Figure().update_layout(title="Sin dividendos ni intereses en el periodo")
        return px.bar(pd.DataFrame(filas), x="Fecha", y="Dividendos e intereses COP", color="Ticker",
                      title="Dividendos (TRM del día de pago) e intereses recibidos")
