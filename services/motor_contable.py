"""Motor contable: replica las fórmulas del Excel de transacciones."""
import pandas as pd


class MotorContable:
    COLUMNAS = ["Fecha", "Valor_USD", "Compra", "Venta", "TRM", "Dividendo_USD"]

    def __init__(self, tasa_corretaje: float, saldo_inicial: float = 0.0):
        self.tasa = tasa_corretaje          # Ej: 0.005 = 0.5 %
        self.saldo_inicial = saldo_inicial

    def calcular(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        for c in ["Valor_USD", "Compra", "Venta", "TRM", "Dividendo_USD"]:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
        df["Valor_COP"] = df["Valor_USD"] * df["TRM"]
        df["Dividendo_COP"] = df["Dividendo_USD"] * df["TRM"]
        df["Comision"] = self.tasa * df["Valor_COP"] * (df["Compra"] + df["Venta"])
        acciones, saldos = [], []
        acc_ant, saldo_ant = 0.0, self.saldo_inicial
        for _, r in df.iterrows():
            acc = acc_ant + r["Compra"] - r["Venta"]               # Acciones acumuladas
            saldo = (saldo_ant - r["Valor_COP"] * r["Compra"]
                     + r["Valor_COP"] * r["Venta"]
                     + r["Dividendo_COP"] * acc - r["Comision"])    # Saldo de caja
            acciones.append(acc); saldos.append(saldo)
            acc_ant, saldo_ant = acc, saldo
        df["Acciones_Acum"] = acciones
        df["Saldo_Caja_COP"] = saldos
        return df
