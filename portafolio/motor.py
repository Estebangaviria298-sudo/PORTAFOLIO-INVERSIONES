"""Motor contable: replica las fórmulas del Excel para UN activo.

Fórmulas del Excel implementadas:
  Acciones_t      = Acciones_{t-1} + Compra_t - Venta_t
  Valor_COP_t     = Valor_USD_t * TRM_t
  Dividendo_COP   = Dividendo_USD * TRM del día de PAGO
  Ingreso_Div_COP = Dividendo_COP * Acciones (las que se tenían en la fecha ex-dividendo)
  Comision_t      = %corretaje * (Compra_t + Venta_t) * Precio_COP_t   (o valor manual)
  Flujo_Neto_t    = -(Precio_COP*Compra) + (Precio_COP*Venta)
                    + (Dividendo_COP*Acciones) - Comision
  Saldo_t         = Saldo_{t-1} + Flujo_Neto_t        (se acumula en Portafolio)

Cada operación puede traer su propio precio y TRM: el Portafolio los convierte en
Costo_Compra_COP / Ingreso_Venta_COP (cantidad × precio × TRM de la operación).
Para renta fija la 'moneda' es COP: TRM = 1 y el precio es el valor causado del título.
"""
import pandas as pd

COLS_DIV = ["Fecha_Ex", "Fecha_Acreditacion", "Dividendo_USD", "TRM_Pago", "Acciones_Derecho"]


def sin_dividendos() -> pd.DataFrame:
    return pd.DataFrame(columns=COLS_DIV)


class MotorContable:
    def __init__(self, comision_pct: float):
        self.comision_pct = comision_pct

    @staticmethod
    def _columna(ops: pd.DataFrame, nombre: str, indice):
        return ops[nombre].reindex(indice).fillna(0.0) if nombre in ops else None

    def libro_activo(self, precio_usd: pd.Series, trm: pd.Series,
                     operaciones: pd.DataFrame, dividendos: pd.DataFrame) -> pd.DataFrame:
        """
        precio_usd  : precio de cierre alineado al calendario común
        trm         : serie TRM alineada al mismo índice (1.0 en renta fija)
        operaciones : índice = fecha; Compra, Venta (unidades) y opcionalmente
                      Costo_Compra_COP, Ingreso_Venta_COP, Comision_COP, Interes_COP
        dividendos  : Fecha_Ex, Fecha_Acreditacion, Dividendo_USD, TRM_Pago, Acciones_Derecho
        """
        df = pd.DataFrame({"Precio_USD": precio_usd})
        df["TRM"] = trm
        df["Compra"] = operaciones["Compra"].reindex(df.index).fillna(0.0)
        df["Venta"] = operaciones["Venta"].reindex(df.index).fillna(0.0)

        # Acciones acumuladas: saldo anterior + compra - venta
        acciones, previo = [], 0.0
        for compra, venta in zip(df["Compra"], df["Venta"]):
            previo = previo + compra - venta
            if previo < -1e-9:
                raise ValueError("Se vendieron más acciones de las que se poseen.")
            acciones.append(previo)
        df["Acciones"] = acciones

        df["Precio_COP"] = df["Precio_USD"] * df["TRM"]
        df["Valor_USD"] = df["Acciones"] * df["Precio_USD"]
        df["Valor_COP"] = df["Valor_USD"] * df["TRM"]          # Valor US × TRM

        # Costos e ingresos de las operaciones (con precio/TRM propios si se escribieron)
        costo = self._columna(operaciones, "Costo_Compra_COP", df.index)
        venta = self._columna(operaciones, "Ingreso_Venta_COP", df.index)
        com = self._columna(operaciones, "Comision_COP", df.index)
        df["Costo_Compra_COP"] = df["Precio_COP"] * df["Compra"] if costo is None else costo
        df["Ingreso_Venta_COP"] = df["Precio_COP"] * df["Venta"] if venta is None else venta
        df["Comision_COP"] = (self.comision_pct * (df["Compra"] + df["Venta"]) * df["Precio_COP"]
                              if com is None else com)
        interes = self._columna(operaciones, "Interes_COP", df.index)
        df["Interes_COP"] = 0.0 if interes is None else interes

        # Dividendos: derecho según acciones en la fecha ex; TRM del día de pago
        df["Dividendo_USD"] = 0.0
        df["Dividendo_COP"] = 0.0
        df["Ingreso_Dividendos_COP"] = 0.0
        for _, d in dividendos.iterrows():
            acc = d["Acciones_Derecho"] if "Acciones_Derecho" in d else float("nan")
            if pd.isna(acc):
                acc = df["Acciones"].asof(d["Fecha_Ex"])
            acc = 0.0 if pd.isna(acc) else acc
            f = d["Fecha_Acreditacion"]
            cop = d["Dividendo_USD"] * d["TRM_Pago"]
            df.loc[f, "Dividendo_USD"] += d["Dividendo_USD"]
            df.loc[f, "Dividendo_COP"] += cop
            df.loc[f, "Ingreso_Dividendos_COP"] += cop * acc

        df["Flujo_Neto_COP"] = (-df["Costo_Compra_COP"] + df["Ingreso_Venta_COP"]
                                + df["Ingreso_Dividendos_COP"] + df["Interes_COP"] - df["Comision_COP"])
        return df
