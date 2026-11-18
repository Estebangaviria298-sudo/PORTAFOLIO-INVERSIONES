"""Gráficos Plotly de la aplicación."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


class Graficos:
    @staticmethod
    def dona(dist: pd.DataFrame):
        return px.pie(dist, names="Ticker", values="Inversion_COP", hole=0.5,
                      title="Distribución del portafolio")

    @staticmethod
    def evolucion(evo: pd.DataFrame, capital: float):
        fig = go.Figure()
        fig.add_scatter(x=evo.index, y=evo["Valor_COP"], name="Valor activos (COP)")
        fig.add_scatter(x=evo.index, y=evo["Total_COP"], name="Valor + dividendos (COP)")
        fig.add_hline(y=capital, line_dash="dash", annotation_text="Capital inicial")
        fig.update_layout(title="Evolución histórica en COP", yaxis_title="COP")
        return fig

    @staticmethod
    def saldo_caja(df: pd.DataFrame):
        return px.line(df, x="Fecha", y="Saldo_Caja_COP", markers=True,
                       title="Saldo de caja acumulado (COP)")
