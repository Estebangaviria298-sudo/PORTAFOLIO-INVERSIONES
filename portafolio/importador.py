"""Lee el Excel de seguimiento (hoja por activo) y devuelve operaciones y dividendos.

Estructura esperada (igual al archivo de ejemplo):
  - Título del activo en la fila sobre los encabezados (p. ej. "Nike").
  - Encabezados con 'Fecha', 'Compra', 'Venta' (cantidades de acciones).
  - A la derecha, tabla 'Fecha ex-dividendo | Dividendo | Tipo | Fecha de pago'.
"""
from datetime import datetime
from typing import Dict, Tuple

import openpyxl
import pandas as pd


class ImportadorExcel:
    NOMBRES = {"nike": "NKE", "coca-cola": "KO", "coca cola": "KO", "cocacola": "KO"}

    @staticmethod
    def _fecha(v):
        """Convierte celdas con fechas (datetime o texto dd/mm/aaaa o dd.mm.aaaa)."""
        if v is None or v == "":
            return pd.NaT
        if isinstance(v, (datetime, pd.Timestamp)):
            return pd.Timestamp(v).normalize()
        s = str(v).strip().replace(".", "/").replace("-", "/")
        for fmt in ("%d/%m/%Y", "%Y/%m/%d", "%d/%m/%y"):
            try:
                return pd.Timestamp(datetime.strptime(s, fmt))
            except ValueError:
                continue
        return pd.NaT

    @staticmethod
    def _numero(v) -> float:
        """Convierte números con coma decimal ('0,41') y porcentajes."""
        if v is None or v == "":
            return 0.0
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).strip().replace("%", "").replace(" ", "")
        if "," in s:
            s = s.replace(".", "").replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return 0.0

    def leer(self, archivo) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame]]:
        """Devuelve (transacciones, dividendos_por_ticker)."""
        wb = openpyxl.load_workbook(archivo, data_only=False)
        ops, divs = [], {}
        for ws in wb:
            filas = list(ws.iter_rows(min_row=1, max_row=min(ws.max_row, 400)))
            # 1) fila de encabezados: contiene 'Fecha' y 'Compra'
            h = None
            for i, fila in enumerate(filas[:20]):
                nombres = [str(c.value).strip().lower() if c.value is not None else "" for c in fila]
                if "fecha" in nombres and "compra" in nombres:
                    h = i
                    cab = {}
                    for j, n in enumerate(nombres):
                        cab.setdefault(n, j)          # primera aparición de cada nombre
                    break
            if h is None:
                continue
            # 2) ticker a partir del título (fila superior)
            titulo = next((c.value for c in filas[h - 1] if c.value), ws.title) if h > 0 else ws.title
            ticker = self.NOMBRES.get(str(titulo).strip().lower(), str(titulo).strip().upper())
            # 3) operaciones
            for fila in filas[h + 1:]:
                f = self._fecha(fila[cab["fecha"]].value)
                c = self._numero(fila[cab["compra"]].value)
                v = self._numero(fila[cab["venta"]].value) if "venta" in cab else 0.0
                if pd.notna(f) and (c > 0 or v > 0):
                    ops.append({"Fecha": f, "Ticker": ticker, "Compra": c, "Venta": v})
            # 4) tabla de dividendos: sus encabezados pueden estar en otra fila que los de las operaciones
            for i, fila in enumerate(filas[:20]):
                nombres = [str(c.value).strip().lower() if c.value is not None else "" for c in fila]
                col_ex = next((j for j, n in enumerate(nombres) if n.startswith("fecha ex")), None)
                if col_ex is None:
                    continue
                col_pago = next((j for j, n in enumerate(nombres) if n == "fecha de pago"), col_ex + 3)
                filas_div = []
                for f2 in filas[i + 1:]:
                    ex = self._fecha(f2[col_ex].value)
                    pago = self._fecha(f2[col_pago].value)
                    d = self._numero(f2[col_ex + 1].value)
                    if pd.notna(ex) and pd.notna(pago) and d > 0:
                        filas_div.append({"Fecha_Ex": ex, "Dividendo_USD": d, "Fecha_Pago": pago})
                if filas_div:
                    divs[ticker] = pd.DataFrame(filas_div).sort_values("Fecha_Ex").reset_index(drop=True)
                break
        if not ops:
            raise ValueError("No se encontraron operaciones de compra/venta en el Excel.")
        return pd.DataFrame(ops).sort_values("Fecha").reset_index(drop=True), divs
