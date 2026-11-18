"""Operacion y LibroOperaciones: registro manual de operaciones (precio, TRM y comisión editables)."""
from dataclasses import dataclass
from datetime import date, datetime
from typing import ClassVar, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .modelos import Activo, INSTRUMENTOS_RF, INSTRUMENTOS_RV, TICKERS_OBLIGATORIOS


@dataclass
class Operacion:
    """Una operación o flujo de caja.

    - Compra/Venta/Pago de capital: cantidad × precio. Precio 0 = usar el cierre de mercado
      (renta variable) o el valor causado a la fecha (renta fija).
    - trm: COP por USD de la operación (0 = TRM de mercado). No aplica a renta fija (COP).
    - comision: valor en COP (0 = usar el % de corretaje global).
    - Dividendo: cantidad = acciones con derecho (0 = las que se tenían), precio = dividendo
      por acción en USD, fecha = fecha de PAGO, trm = TRM de ese día (0 = de mercado).
      Si se indica fecha_ex, las acciones con derecho son las que se tenían en esa fecha.
    - Interés: precio = monto recibido en COP.
    - tasa_ea, vencimiento y capitaliza solo aplican a la compra de renta fija.
    """
    fecha: date
    tipo: str
    ticker: str
    instrumento: str = "Acción"
    cantidad: float = 1.0
    precio: float = 0.0
    trm: float = 0.0
    comision: float = 0.0
    tasa_ea: Optional[float] = None
    vencimiento: Optional[date] = None
    capitaliza: bool = True
    fecha_ex: Optional[date] = None      # solo dividendos: define las acciones con derecho

    TIPOS: ClassVar[Tuple[str, ...]] = ("Compra", "Venta", "Dividendo", "Interés", "Pago de capital")
    SALIDAS: ClassVar[Tuple[str, ...]] = ("Venta", "Pago de capital")
    INSTRUMENTOS: ClassVar[Tuple[str, ...]] = INSTRUMENTOS_RV + INSTRUMENTOS_RF
    COLUMNAS: ClassVar[Tuple[str, ...]] = (
        "fecha", "tipo", "ticker", "instrumento", "cantidad", "precio", "trm",
        "comision", "tasa_ea", "vencimiento", "capitaliza", "fecha_ex")

    @property
    def es_renta_fija(self) -> bool:
        return self.instrumento in INSTRUMENTOS_RF

    def a_dict(self) -> Dict:
        return {"fecha": self.fecha.isoformat(), "tipo": self.tipo, "ticker": self.ticker,
                "instrumento": self.instrumento, "cantidad": self.cantidad, "precio": self.precio,
                "trm": self.trm, "comision": self.comision, "tasa_ea": self.tasa_ea,
                "vencimiento": self.vencimiento.isoformat() if self.vencimiento else None,
                "capitaliza": self.capitaliza,
                "fecha_ex": self.fecha_ex.isoformat() if self.fecha_ex else None}

    @classmethod
    def desde_dict(cls, d: Dict) -> "Operacion":
        def num(k, defecto=0.0):
            v = d.get(k)
            return defecto if v is None or pd.isna(v) else float(v)
        venc = d.get("vencimiento")
        tasa = d.get("tasa_ea")
        fex = d.get("fecha_ex")
        return cls(
            fecha=date.fromisoformat(str(d["fecha"])[:10]), tipo=str(d["tipo"]), ticker=str(d["ticker"]),
            instrumento=str(d["instrumento"]), cantidad=num("cantidad", 1.0), precio=num("precio"),
            trm=num("trm"), comision=num("comision"),
            tasa_ea=None if tasa is None or pd.isna(tasa) else float(tasa),
            vencimiento=None if venc is None or pd.isna(venc) else date.fromisoformat(str(venc)[:10]),
            capitaliza=str(d.get("capitaliza", True)).strip().lower() in ("true", "1", "1.0"),
            fecha_ex=None if fex is None or pd.isna(fex) else date.fromisoformat(str(fex)[:10]))


class LibroOperaciones:
    """Lista validada de operaciones; la convierte en la entrada del Portafolio."""
    TOL = 1e-9

    def __init__(self, operaciones: Optional[List[Operacion]] = None):
        self.operaciones: List[Operacion] = []
        for op in sorted(operaciones or [], key=lambda o: o.fecha):
            self.agregar(op)

    # ---------------- registro ----------------
    def agregar(self, op: Operacion) -> None:
        self._validar_operacion(op)
        self._validar_saldos(self.operaciones + [op])
        self.operaciones.append(op)

    def eliminar(self, indice: int) -> None:
        restantes = [o for i, o in enumerate(self.operaciones) if i != indice]
        self._validar_saldos(restantes)
        self.operaciones = restantes

    def limpiar(self) -> None:
        self.operaciones = []

    def reemplazar(self, otro: "LibroOperaciones") -> None:
        self.operaciones = list(otro.operaciones)

    def fecha_inicio(self) -> Optional[date]:
        return min((o.fecha for o in self.operaciones), default=None)

    def fecha_fin(self) -> Optional[date]:
        return max((o.fecha for o in self.operaciones), default=None)

    def a_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame([o.a_dict() for o in self.operaciones], columns=list(Operacion.COLUMNAS))

    def a_dataframe_excel(self) -> pd.DataFrame:
        """Devuelve la tabla con las columnas y cálculos exactos de la hoja de Excel."""
        filas = []
        saldo_acc: Dict[str, float] = {}
        for i, o in enumerate(self.operaciones):
            acc_prev = saldo_acc.get(o.ticker, 0.0)
            compra = o.cantidad if o.tipo == "Compra" else 0.0
            venta = o.cantidad if o.tipo in Operacion.SALIDAS else 0.0

            if o.tipo == "Compra":
                saldo_acc[o.ticker] = acc_prev + compra
            elif o.tipo in Operacion.SALIDAS:
                saldo_acc[o.ticker] = acc_prev - venta

            valor_us = (o.cantidad * o.precio) if o.tipo in ("Compra", "Venta") and not o.es_renta_fija else 0.0
            valor_cop = valor_us * (o.trm if o.trm > 0 else 1.0)
            div_usd = o.precio if o.tipo == "Dividendo" else 0.0
            acc_div = o.cantidad if (o.tipo == "Dividendo" and o.cantidad > 0) else acc_prev
            div_cop = div_usd * (o.trm if o.trm > 0 else 1.0) * acc_div
            pago = (o.cantidad * o.precio) if o.tipo in ("Interés", "Pago de capital") else 0.0

            filas.append({
                "#": i,
                "Ticker": o.ticker,
                "Fecha": o.fecha.isoformat(),
                "Acciones": acc_prev if o.tipo != "Dividendo" else acc_div,
                "Valor US": round(valor_us, 2),
                "Valor COP": round(valor_cop, 0),
                "Compra": compra,
                "Venta": venta,
                "TRM": o.trm,
                "Dividendo": div_usd,
                "Dividendo cop": round(div_cop, 2),
                "Pago": round(pago, 0),
                "Comision": round(o.comision, 0),
            })
        return pd.DataFrame(filas)

    @classmethod
    def desde_dataframe(cls, df: pd.DataFrame) -> "LibroOperaciones":
        cols_lower = {c.strip().lower(): c for c in df.columns}
        # Soporta tanto el formato exportado de la app como el formato exacto de tu Excel
        if "valor us" in cols_lower or "dividendo cop" in cols_lower:
            ops = []

            def limpiar_num(val) -> float:
                if val is None or pd.isna(val) or str(val).strip() == "":
                    return 0.0
                s = str(val).replace("$", "").replace(" ", "").strip()
                if "," in s and "." in s:
                    s = s.replace(".", "").replace(",", ".")
                elif "," in s:
                    s = s.replace(",", ".")
                try:
                    return float(s)
                except ValueError:
                    return 0.0

            def limpiar_fecha(val) -> date:
                s = str(val).strip().replace(".", "/").replace("-", "/")
                for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y/%m/%d"):
                    try:
                        return datetime.strptime(s, fmt).date()
                    except ValueError:
                        continue
                return date.fromisoformat(str(val)[:10])

            for _, row in df.iterrows():
                tk_raw = str(row.get(cols_lower.get("ticker", "Ticker"), "")).strip().upper()
                if not tk_raw or tk_raw == "NAN":
                    tk_raw = "NKE"  # En el Excel original las filas de dividendos sin ticker pertenecen a Nike
                if tk_raw == "NK":
                    tk_raw = "NKE"

                f = limpiar_fecha(row[cols_lower["fecha"]])
                compra = limpiar_num(row.get(cols_lower.get("compra", "Compra"), 0))
                venta = limpiar_num(row.get(cols_lower.get("venta", "Venta"), 0))
                acciones = limpiar_num(row.get(cols_lower.get("acciones", "Acciones"), 0))
                valor_us = limpiar_num(row.get(cols_lower.get("valor us", "Valor US"), 0))
                trm = limpiar_num(row.get(cols_lower.get("trm", "TRM"), 0))
                div_usd = limpiar_num(row.get(cols_lower.get("dividendo", "Dividendo"), 0))
                comision = limpiar_num(row.get(cols_lower.get("comision", "Comision"), 0))

                if compra > 0:
                    precio_u = (valor_us / compra) if valor_us > 0 else 0.0
                    ops.append(Operacion(f, "Compra", tk_raw, "Acción", compra, precio_u, trm, comision))
                if venta > 0:
                    precio_u = (valor_us / venta) if valor_us > 0 else 0.0
                    ops.append(Operacion(f, "Venta", tk_raw, "Acción", venta, precio_u, trm, comision))
                if div_usd > 0:
                    ops.append(Operacion(f, "Dividendo", tk_raw, "Acción", acciones, div_usd, trm, 0.0))

            return cls(ops)

        return cls([Operacion.desde_dict(f) for f in df.to_dict("records")])

    # ---------------- validaciones ----------------
    def _validar_operacion(self, op: Operacion) -> None:
        if op.tipo not in Operacion.TIPOS:
            raise ValueError(f"Tipo de operación inválido: {op.tipo}")
        if not op.ticker.strip():
            raise ValueError("Escribe el ticker o el nombre del instrumento.")
        if op.precio < 0 or op.trm < 0 or op.comision < 0:
            raise ValueError("Precio, TRM y comisión no pueden ser negativos.")
        if op.tipo == "Dividendo":
            if op.es_renta_fija or op.precio <= 0:
                raise ValueError("El dividendo es de una acción/ETF y requiere el valor por acción (USD).")
            if op.cantidad < 0:
                raise ValueError("Las acciones con derecho no pueden ser negativas.")
            if op.fecha_ex is not None and op.fecha_ex > op.fecha:
                raise ValueError("La fecha ex-dividendo no puede ser posterior a la fecha de pago.")
        elif op.cantidad <= 0:
            raise ValueError("La cantidad debe ser mayor que 0.")
        if op.tipo == "Interés" and op.precio <= 0:
            raise ValueError("Escribe el monto de intereses recibido (COP).")
        if op.tipo == "Compra" and op.es_renta_fija:
            if op.precio <= 0:
                raise ValueError("En renta fija escribe el valor unitario de compra (COP).")
            if op.tasa_ea is None or op.vencimiento is None or op.vencimiento <= op.fecha:
                raise ValueError("Renta fija: indica tasa E.A. y un vencimiento posterior a la compra.")
            if any(o.ticker == op.ticker and o.tipo == "Compra" for o in self.operaciones):
                raise ValueError(f"'{op.ticker}' ya tiene una compra: registra cada CDT/bono/TES con un nombre distinto.")
        previos = {o.instrumento for o in self.operaciones if o.ticker == op.ticker}
        if previos and op.instrumento not in previos:
            raise ValueError(f"'{op.ticker}' ya existe como {sorted(previos)[0]}.")

    def _validar_saldos(self, operaciones: List[Operacion]) -> None:
        """No se puede vender más de lo que se tiene (orden cronológico, compras primero)."""
        saldo: Dict[str, float] = {}
        for o in sorted(operaciones, key=lambda x: (x.fecha, 0 if x.tipo == "Compra" else 1)):
            if o.tipo == "Compra":
                saldo[o.ticker] = saldo.get(o.ticker, 0.0) + o.cantidad
            elif o.tipo in Operacion.SALIDAS:
                saldo[o.ticker] = saldo.get(o.ticker, 0.0) - o.cantidad
                if saldo[o.ticker] < -self.TOL:
                    raise ValueError(f"No puedes {o.tipo.lower()} {o.cantidad:g} {o.ticker} el {o.fecha}: "
                                     f"solo tenías {saldo[o.ticker] + o.cantidad:g}.")

    # ---------------- conversión a entradas del Portafolio ----------------
    def activos(self) -> List[Activo]:
        """Activos implícitos en las operaciones (+ KO y NKE obligatorios, aunque sin posición)."""
        out: Dict[str, Activo] = {}
        for o in sorted(self.operaciones, key=lambda x: x.fecha):
            if o.ticker in out:
                continue
            if o.es_renta_fija:
                compra = next((c for c in self.operaciones if c.ticker == o.ticker and c.tipo == "Compra"), None)
                out[o.ticker] = Activo(
                    o.ticker, 0.0, instrumento=o.instrumento, comision_pct=0.0,
                    tasa_ea=(compra.tasa_ea or 0.0) if compra else 0.0,
                    plazo_dias=(compra.vencimiento - compra.fecha).days if compra else 0,
                    capitaliza=compra.capitaliza if compra else True)
            else:
                out[o.ticker] = Activo(o.ticker, 0.0, t_obl(o.ticker), o.instrumento)
        for t in TICKERS_OBLIGATORIOS:
            out.setdefault(t, Activo(t, 0.0, True, "Acción"))
        return list(out.values())

    def transacciones(self) -> pd.DataFrame:
        """Compras, ventas e intereses (los dividendos van aparte). 0 se traduce a 'automático' (NaN)."""
        filas = []
        for o in self.operaciones:
            if o.tipo == "Dividendo":
                continue
            interes = o.tipo == "Interés"
            filas.append({
                "Fecha": pd.Timestamp(o.fecha), "Ticker": o.ticker,
                "Compra": o.cantidad if o.tipo == "Compra" else 0.0,
                "Venta": o.cantidad if o.tipo in Operacion.SALIDAS else 0.0,
                "Precio": np.nan if interes or o.precio == 0 else o.precio,
                "TRM": np.nan if o.trm == 0 or o.es_renta_fija else o.trm,
                "Comision_COP": np.nan if o.comision == 0 else o.comision,
                "Interes_COP": o.precio * o.cantidad if interes else 0.0})
        return pd.DataFrame(filas, columns=["Fecha", "Ticker", "Compra", "Venta", "Precio",
                                            "TRM", "Comision_COP", "Interes_COP"])

    def dividendos_manuales(self) -> Dict[str, pd.DataFrame]:
        por_ticker: Dict[str, list] = {}
        for o in self.operaciones:
            if o.tipo == "Dividendo":
                por_ticker.setdefault(o.ticker, []).append({
                    "Fecha_Ex": pd.Timestamp(o.fecha_ex or o.fecha), "Fecha_Pago": pd.Timestamp(o.fecha),
                    "Dividendo_USD": o.precio,
                    "TRM_Manual": np.nan if o.trm == 0 else o.trm,
                    "Acciones_Derecho": np.nan if o.cantidad == 0 else o.cantidad})
        return {t: pd.DataFrame(f) for t, f in por_ticker.items()}


def t_obl(ticker: str) -> bool:
    return ticker in TICKERS_OBLIGATORIOS