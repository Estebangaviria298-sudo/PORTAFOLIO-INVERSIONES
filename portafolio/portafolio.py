"""Orquestador: arma el calendario, resuelve operaciones y consolida el portafolio."""
import math
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .calculadora import CalculadoraRentabilidad
from .datos import ProveedorDatos
from .modelos import Activo, Parametros, Resultado, TICKERS_OBLIGATORIOS, NOMINAL_RF
from .motor import COLS_DIV, MotorContable, sin_dividendos

COLS_MOTOR = ["Compra", "Venta", "Costo_Compra_COP", "Ingreso_Venta_COP", "Comision_COP", "Interes_COP"]


class Portafolio:
    def __init__(self, activos: List[Activo], params: Parametros,
                 proveedor: Optional[ProveedorDatos] = None,
                 datos_precargados: Optional[Dict[str, pd.DataFrame]] = None,
                 trm_precargada: Optional[pd.Series] = None,
                 dividendos_externos: Optional[Dict[str, pd.DataFrame]] = None,
                 dividendos_manuales: Optional[Dict[str, pd.DataFrame]] = None,
                 auto_dividendos: bool = True,
                 redimir_al_vencimiento: bool = True):
        self.activos = activos
        self.params = params
        self.proveedor = proveedor or ProveedorDatos()
        self._datos = datos_precargados      # permite usar caché o pruebas sin internet
        self._trm = trm_precargada
        self.dividendos_externos = dividendos_externos or {}    # del Excel: reemplazan a yfinance
        self.dividendos_manuales = dividendos_manuales or {}    # registrados a mano: se suman
        self.auto_dividendos = auto_dividendos
        self.redimir_al_vencimiento = redimir_al_vencimiento
        self._validar()

    # ---------------- validaciones ----------------
    def _validar(self):
        tickers = [a.ticker for a in self.activos]
        for t in TICKERS_OBLIGATORIOS:
            if t not in tickers:
                raise ValueError(f"{t} es obligatorio en el portafolio.")
        if len(set(tickers)) != len(tickers):
            raise ValueError("Hay tickers repetidos.")
        for a in self.activos:
            if a.es_renta_fija and a.tasa_ea < 0:
                raise ValueError(f"{a.ticker}: la tasa E.A. no puede ser negativa.")

    def _validar_pesos(self):
        if abs(sum(a.peso for a in self.activos) - 1.0) > 1e-6:
            raise ValueError("Las ponderaciones deben sumar 100 %.")

    def _comision(self, a: Activo) -> float:
        return self.params.comision_pct if a.comision_pct is None else a.comision_pct

    # ---------------- datos ----------------
    def _cargar(self):
        p = self.params
        rv = [a for a in self.activos if not a.es_renta_fija]
        if self._datos is None:
            self._datos = {a.ticker: self.proveedor.descargar_activo(
                a.ticker, p.fecha_inicio, p.fecha_fin) for a in rv}
        if self._trm is None:
            self._trm = self.proveedor.descargar_trm(p.fecha_inicio, p.fecha_fin)

        # Calendario común = unión de días de negociación de la renta variable
        cal = pd.DatetimeIndex(sorted(set().union(*[self._datos[a.ticker].index for a in rv])))
        cal = cal[(cal >= pd.Timestamp(p.fecha_inicio)) & (cal <= pd.Timestamp(p.fecha_fin))]
        if len(cal) < 2:
            raise ValueError("No hay suficientes días de mercado en el periodo elegido.")
        trm = self._trm.reindex(self._trm.index.union(cal)).ffill().bfill().reindex(cal)
        precios = {a.ticker: self._datos[a.ticker]["Precio_USD"].reindex(cal).ffill().bfill()
                   for a in rv}
        return cal, trm, precios

    def _dividendos(self, ticker: str, cal: pd.DatetimeIndex) -> pd.DataFrame:
        """Dividendos del activo: fecha ex, día de pago y TRM vigente ese día."""
        partes = []
        ext = self.dividendos_externos.get(ticker)
        man = self.dividendos_manuales.get(ticker)
        if ext is not None:
            partes.append(ext[["Fecha_Ex", "Dividendo_USD", "Fecha_Pago"]])
        elif self.auto_dividendos and man is None and ticker in self._datos:   # lo escrito a mano manda
            raw = self._datos[ticker]["Dividendo_USD"]
            raw = raw[raw > 0]                       # yfinance entrega la fecha EX
            if len(raw):
                d = pd.DataFrame({"Fecha_Ex": raw.index, "Dividendo_USD": raw.values})
                d["Fecha_Pago"] = d["Fecha_Ex"] + pd.Timedelta(days=self.params.rezago_pago_dias)
                partes.append(d)
        if man is not None:
            partes.append(man)
        if not partes:
            return sin_dividendos()
        df = pd.concat(partes, ignore_index=True)
        for col in ("TRM_Manual", "Acciones_Derecho"):
            if col not in df:
                df[col] = np.nan
        df = df[(df["Fecha_Pago"] >= cal[0]) & (df["Fecha_Pago"] <= cal[-1])].copy()
        if df.empty:
            return sin_dividendos()
        # TRM vigente el día exacto de pago (si es fin de semana, la última publicada)
        auto = [self._trm.asof(f) for f in df["Fecha_Pago"]]
        df["TRM_Pago"] = df["TRM_Manual"].where(df["TRM_Manual"].notna(), pd.Series(auto, index=df.index))
        df["TRM_Pago"] = df["TRM_Pago"].fillna(self._trm.iloc[0])
        # el dinero entra a caja el primer día hábil >= fecha de pago
        df["Fecha_Acreditacion"] = cal[cal.searchsorted(df["Fecha_Pago"])]
        return df[COLS_DIV + ["Fecha_Pago"]]

    # ---------------- renta fija ----------------
    @staticmethod
    def _precio_renta_fija(a: Activo, cal: pd.DatetimeIndex, f0: pd.Timestamp, base: float) -> pd.Series:
        """Valor causado de 1 título: base × (1+EA)^(días/365), con tope en el vencimiento.
        Si no capitaliza (paga cupones aparte) se mantiene en su valor de compra."""
        if not a.capitaliza:
            return pd.Series(base, index=cal)
        dias = np.asarray((cal - f0).days, dtype=float)
        tope = a.plazo_dias if a.plazo_dias > 0 else None
        dias = np.clip(dias, 0, tope)
        return pd.Series(base * (1 + a.tasa_ea) ** (dias / 365.0), index=cal)

    @staticmethod
    def _redencion(a: Activo, ops: pd.DataFrame, cal, f0) -> Optional[pd.DataFrame]:
        """Venta automática (pago de capital + intereses) al vencimiento."""
        if a.plazo_dias <= 0:
            return None
        pos = cal.searchsorted(f0 + pd.Timedelta(days=a.plazo_dias))
        if pos >= len(cal):
            return None                       # vence después del periodo simulado
        fecha = cal[pos]
        previas = ops[ops["Fecha"] <= fecha]
        unidades = previas["Compra"].sum() - previas["Venta"].sum()
        if unidades <= 1e-9:
            return None
        return pd.DataFrame([{"Fecha": fecha, "Ticker": a.ticker, "Compra": 0.0, "Venta": unidades}])

    # ---------------- operaciones ----------------
    def _compras_iniciales(self, cal, trm, precios) -> pd.DataFrame:
        """Día 1: capital COP -> USD con la TRM del primer día -> compra por peso."""
        filas = []
        for a in self.activos:
            presupuesto_cop = self.params.capital_cop * a.peso
            if a.es_renta_fija:
                precio_cop, fracciones = NOMINAL_RF, True      # títulos divisibles
            else:
                precio_cop, fracciones = precios[a.ticker].iloc[0] * trm.iloc[0], self.params.permitir_fracciones
            # se descuenta la comisión para que el desembolso total no exceda el presupuesto
            n = presupuesto_cop / (precio_cop * (1 + self._comision(a)))
            if not fracciones:
                n = math.floor(n)
            filas.append({"Fecha": cal[0], "Ticker": a.ticker, "Compra": n, "Venta": 0.0})
        return pd.DataFrame(filas)

    @staticmethod
    def _alinear(trans: pd.DataFrame, cal) -> pd.DataFrame:
        """Mueve cada operación al siguiente día hábil disponible del calendario."""
        t = trans.copy()
        t["Fecha"] = pd.to_datetime(t["Fecha"]).dt.normalize()
        pos = cal.searchsorted(t["Fecha"])
        t = t[pos < len(cal)].copy()
        t["Fecha"] = cal[pos[pos < len(cal)]]
        return t

    def _enriquecer(self, t: pd.DataFrame, precios, trm) -> pd.DataFrame:
        """Resuelve precio, TRM y comisión de cada operación.
        Lo que el usuario escribió manda; lo que dejó vacío sale del mercado (yfinance)."""
        t = t.copy().reset_index(drop=True)
        for col in ("Precio", "TRM", "Comision_COP", "Interes_COP"):
            if col not in t:
                t[col] = np.nan
        es_rf = {a.ticker: a.es_renta_fija for a in self.activos}
        pct = {a.ticker: self._comision(a) for a in self.activos}
        costo, ingreso, comision, precio_op, trm_op = [], [], [], [], []
        for _, r in t.iterrows():
            tk, f = r["Ticker"], r["Fecha"]
            precio = r["Precio"] if pd.notna(r["Precio"]) else precios[tk].asof(f)
            cambio = 1.0 if es_rf[tk] else (r["TRM"] if pd.notna(r["TRM"]) else trm.asof(f))
            bruto_c, bruto_v = r["Compra"] * precio * cambio, r["Venta"] * precio * cambio
            precio_op.append(precio)
            trm_op.append(cambio)
            costo.append(bruto_c)
            ingreso.append(bruto_v)
            comision.append(r["Comision_COP"] if pd.notna(r["Comision_COP"])
                            else pct[tk] * (bruto_c + bruto_v))
        t["Costo_Compra_COP"], t["Ingreso_Venta_COP"], t["Comision_COP"] = costo, ingreso, comision
        t["Interes_COP"] = t["Interes_COP"].fillna(0.0)
        t["Precio_Op"], t["TRM_Op"] = precio_op, trm_op      # lo realmente aplicado a cada operación
        return t

    # ---------------- simulación ----------------
    def simular(self, transacciones: Optional[pd.DataFrame] = None) -> Resultado:
        cal, trm, precios = self._cargar()
        if transacciones is None or transacciones.empty:
            self._validar_pesos()
            transacciones = self._compras_iniciales(cal, trm, precios)
        else:
            transacciones = self._alinear(transacciones, cal)
            desconocidos = set(transacciones["Ticker"]) - {a.ticker for a in self.activos}
            if desconocidos:
                raise ValueError(f"Hay operaciones de activos que no están en la tabla: {sorted(desconocidos)}")

        # Renta fija: curva de valor causado (desde su primera compra) y redención al vencimiento
        for a in self.activos:
            if not a.es_renta_fija:
                continue
            ops_a = transacciones[transacciones["Ticker"] == a.ticker]
            compras = ops_a[ops_a["Compra"] > 0].sort_values("Fecha")
            f0 = compras["Fecha"].iloc[0] if len(compras) else cal[0]
            base = NOMINAL_RF
            if len(compras) and "Precio" in compras and pd.notna(compras["Precio"].iloc[0]):
                base = float(compras["Precio"].iloc[0])      # valor unitario escrito por el usuario
            precios[a.ticker] = self._precio_renta_fija(a, cal, f0, base)
            if self.redimir_al_vencimiento:
                red = self._redencion(a, ops_a, cal, f0)
                if red is not None:
                    transacciones = pd.concat([transacciones, red], ignore_index=True)

        transacciones = self._enriquecer(transacciones, precios, trm)

        res = Resultado()
        divs_por_activo = {}
        unos = pd.Series(1.0, index=cal)
        for a in self.activos:
            ops = (transacciones[transacciones["Ticker"] == a.ticker]
                   .groupby("Fecha")[COLS_MOTOR].sum())
            divs = sin_dividendos() if a.es_renta_fija else self._dividendos(a.ticker, cal)
            divs_por_activo[a.ticker] = divs
            motor = MotorContable(self._comision(a))
            res.libros[a.ticker] = motor.libro_activo(
                precios[a.ticker], unos if a.es_renta_fija else trm, ops, divs)

        res.consolidado = self._consolidar(res.libros, trm)
        res.metricas = self._metricas(res)
        res.resumen_activos = self._resumen(res)
        res.detalle_operaciones = self._detalle_operaciones(transacciones, res.libros, divs_por_activo)
        res.formato_excel = self._formato_excel(res.detalle_operaciones)
        ultimo = {t: l["Valor_COP"].iloc[-1] for t, l in res.libros.items()}
        ultimo["Caja"] = res.consolidado["Saldo_Caja_COP"].iloc[-1]
        res.pesos_finales = pd.Series(ultimo)
        dist = {"Renta variable": 0.0, "Renta fija": 0.0, "Caja": ultimo["Caja"]}
        for a in self.activos:
            dist[a.tipo] += ultimo[a.ticker]
        res.distribucion_tipo = pd.Series(dist)
        return res

    def _consolidar(self, libros, trm) -> pd.DataFrame:
        c = pd.DataFrame(index=trm.index)
        c["TRM"] = trm
        c["Valor_Activos_COP"] = sum(l["Valor_COP"] for l in libros.values())
        c["Flujo_Neto_COP"] = sum(l["Flujo_Neto_COP"] for l in libros.values())
        c["Dividendos_COP"] = sum(l["Ingreso_Dividendos_COP"] + l["Interes_COP"] for l in libros.values())
        c["Comisiones_COP"] = sum(l["Comision_COP"] for l in libros.values())
        # Saldo_t = Saldo_{t-1} + flujos netos (compras, ventas, dividendos, comisiones)
        c["Saldo_Caja_COP"] = self.params.capital_cop + c["Flujo_Neto_COP"].cumsum()
        c["Valor_Total_COP"] = c["Valor_Activos_COP"] + c["Saldo_Caja_COP"]
        c["Dividendos_Acum_COP"] = c["Dividendos_COP"].cumsum()
        c["Rentabilidad"] = c["Valor_Total_COP"] / self.params.capital_cop - 1
        return c

    def _metricas(self, res: Resultado) -> Dict[str, float]:
        c, cap = res.consolidado, self.params.capital_cop
        final = c["Valor_Total_COP"].iloc[-1]
        div = c["Dividendos_COP"].sum()
        com = c["Comisiones_COP"].sum()
        ganancia = final - cap
        dias = (c.index[-1] - c.index[0]).days
        rent = CalculadoraRentabilidad.rentabilidad_acumulada(cap, ganancia)
        invertido = sum(l["Costo_Compra_COP"].sum() for l in res.libros.values())
        # E.A. = TIR con fechas (XIRR) de los flujos de inversión + valor final de los activos
        flujos = [(f, v) for f, v in c["Flujo_Neto_COP"].items() if abs(v) > 1e-9]
        if c["Valor_Activos_COP"].iloc[-1] > 0:
            flujos.append((c.index[-1], c["Valor_Activos_COP"].iloc[-1]))
        ea = CalculadoraRentabilidad.tasa_efectiva_anual(flujos)
        if ea is None:
            ea = CalculadoraRentabilidad.anualizar(rent, dias)
        ret_diario = c["Valor_Total_COP"].pct_change().dropna()
        pico = c["Valor_Total_COP"].cummax()
        return {
            "capital_inicial": cap,
            "total_invertido": invertido,
            "valor_final": final,
            "ganancia_total": ganancia,
            "rentabilidad_total": rent,
            "rentabilidad_sobre_invertido": CalculadoraRentabilidad.rentabilidad_acumulada(invertido, ganancia),
            "rentabilidad_ea": ea,
            "dias": dias,
            "ganancia_dividendos": div,
            "rent_dividendos": div / cap,
            "ganancia_precio_y_fx": ganancia - div + com,   # precio, TRM e intereses causados
            "comisiones": com,
            "caja_minima": float(c["Saldo_Caja_COP"].min()),
            "trm_inicial": c["TRM"].iloc[0],
            "trm_final": c["TRM"].iloc[-1],
            "var_trm": c["TRM"].iloc[-1] / c["TRM"].iloc[0] - 1,
            "volatilidad_anual": float(ret_diario.std() * np.sqrt(252)) if len(ret_diario) > 1 else 0.0,
            "max_drawdown": float((c["Valor_Total_COP"] / pico - 1).min()),
        }

    def _resumen(self, res: Resultado) -> pd.DataFrame:
        filas = []
        for a in self.activos:
            l = res.libros[a.ticker]
            invertido = l["Costo_Compra_COP"].sum()
            ventas = l["Ingreso_Venta_COP"].sum()
            ingresos = l["Ingreso_Dividendos_COP"].sum() + l["Interes_COP"].sum()
            com = l["Comision_COP"].sum()
            valor = l["Valor_COP"].iloc[-1]
            gan = valor + ventas + ingresos - invertido - com
            filas.append({"Activo": a.ticker, "Tipo": a.tipo, "Instrumento": a.instrumento,
                          "Invertido COP": invertido, "Valor actual COP": valor,
                          "Ventas/redenciones COP": ventas, "Dividendos/intereses COP": ingresos,
                          "Comisiones COP": com, "Ganancia COP": gan,
                          "Rentabilidad": gan / invertido if invertido > 0 else np.nan})
        return pd.DataFrame(filas)

    COLS_DETALLE = ["Fecha", "Activo", "Operación", "Acciones compradas", "Acciones vendidas",
                    "Acciones (saldo / con derecho)", "Precio por acción", "Moneda", "Valor operación USD",
                    "TRM aplicada", "Valor por acción COP", "Valor operación COP",
                    "Dividendo por acción USD", "Fecha de pago", "Dividendo por acción COP",
                    "Dividendo total COP", "Comisión COP"]

    def _detalle_operaciones(self, t: pd.DataFrame, libros, divs_por_activo) -> pd.DataFrame:
        """Una fila por compra, venta, interés o dividendo, con el precio, la TRM y los
        valores en USD y COP que realmente se usaron (TRM de la fecha de la operación;
        TRM de la fecha de PAGO en los dividendos)."""
        es_rf = {a.ticker: a.es_renta_fija for a in self.activos}
        filas = []
        for _, r in t.iterrows():
            tk, f = r["Ticker"], r["Fecha"]
            rf = es_rf[tk]
            saldo = libros[tk]["Acciones"].loc[f]
            for tipo, cant in (("Compra", r["Compra"]), ("Venta", r["Venta"])):
                if cant > 0:
                    filas.append({
                        "Fecha": f, "Activo": tk, "Operación": tipo,
                        "Acciones compradas": cant if tipo == "Compra" else 0.0,
                        "Acciones vendidas": cant if tipo == "Venta" else 0.0,
                        "Acciones (saldo / con derecho)": saldo,
                        "Precio por acción": r["Precio_Op"], "Moneda": "COP" if rf else "USD",
                        "Valor operación USD": np.nan if rf else cant * r["Precio_Op"],
                        "TRM aplicada": np.nan if rf else r["TRM_Op"],
                        "Valor por acción COP": r["Precio_Op"] * r["TRM_Op"],
                        "Valor operación COP": cant * r["Precio_Op"] * r["TRM_Op"],
                        "Comisión COP": r["Comision_COP"]})
            if r["Interes_COP"] > 0:
                filas.append({"Fecha": f, "Activo": tk, "Operación": "Interés", "Moneda": "COP",
                              "Valor operación COP": r["Interes_COP"]})
        for tk, d in divs_por_activo.items():
            for _, x in d.iterrows():
                acc = x["Acciones_Derecho"]
                if pd.isna(acc):
                    acc = libros[tk]["Acciones"].asof(x["Fecha_Ex"])
                acc = 0.0 if pd.isna(acc) else acc
                if acc <= 0:
                    continue                    # sin acciones con derecho no hay dividendo que mostrar
                filas.append({
                    "Fecha": x["Fecha_Pago"], "Activo": tk, "Operación": "Dividendo",
                    "Acciones (saldo / con derecho)": acc, "Moneda": "USD",
                    "TRM aplicada": x["TRM_Pago"],
                    "Dividendo por acción USD": x["Dividendo_USD"], "Fecha de pago": x["Fecha_Pago"],
                    "Dividendo por acción COP": x["Dividendo_USD"] * x["TRM_Pago"],
                    "Dividendo total COP": x["Dividendo_USD"] * x["TRM_Pago"] * acc})
        det = pd.DataFrame(filas, columns=self.COLS_DETALLE)
        return det.sort_values(["Fecha", "Activo"], kind="stable").reset_index(drop=True)

    def _formato_excel(self, det: pd.DataFrame) -> pd.DataFrame:
        """Las operaciones con las columnas y fórmulas de la hoja de Excel.
        Acciones = acciones antes de la fila (con derecho, en dividendos);
        Saldo = Saldo_anterior - (Valor COP x Compra) + (Valor COP x Venta)
                + (Dividendo cop x Acciones) - Comision."""
        filas = []
        for _, r in det.iterrows():
            op = r["Operación"]
            f = {"Fecha": r["Fecha"], "Activo": r["Activo"], "Operación": op, "Acciones": 0.0,
                 "Valor US": 0.0, "Valor COP": 0.0, "Compra": 0.0, "Venta": 0.0, "TRM": 1.0,
                 "Dividendo": 0.0, "Dividendo cop": 0.0, "Comision": 0.0}
            if op in ("Compra", "Venta"):
                comp, vend = r["Acciones compradas"], r["Acciones vendidas"]
                f.update({"Acciones": r["Acciones (saldo / con derecho)"] - comp + vend,
                          "Valor US": r["Precio por acción"] if r["Moneda"] == "USD" else 0.0,
                          "Valor COP": r["Valor por acción COP"], "Compra": comp, "Venta": vend,
                          "TRM": r["TRM aplicada"] if pd.notna(r["TRM aplicada"]) else 1.0,
                          "Comision": r["Comisión COP"]})
            elif op == "Dividendo":
                f.update({"Acciones": r["Acciones (saldo / con derecho)"], "TRM": r["TRM aplicada"],
                          "Dividendo": r["Dividendo por acción USD"],
                          "Dividendo cop": r["Dividendo por acción COP"]})
            else:                                           # Interés: monto en COP x 1
                f.update({"Acciones": 1.0, "Dividendo cop": r["Valor operación COP"]})
            filas.append(f)
        out = pd.DataFrame(filas, columns=["Fecha", "Activo", "Operación", "Acciones", "Valor US", "Valor COP",
                                           "Compra", "Venta", "TRM", "Dividendo", "Dividendo cop",
                                           "Comision", "Saldo"])
        flujo = (-out["Valor COP"] * out["Compra"] + out["Valor COP"] * out["Venta"]
                 + out["Dividendo cop"] * out["Acciones"] - out["Comision"])
        out["Saldo"] = flujo.cumsum()
        return out
