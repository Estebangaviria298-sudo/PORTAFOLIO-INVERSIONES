"""Pruebas sin internet (datos sintéticos).  Ejecutar:  python -m unittest discover -s tests"""
import sys, tempfile, unittest
from datetime import date
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from portafolio import Activo, Parametros, Portafolio
from portafolio.calculadora import CalculadoraRentabilidad
from portafolio.datos import ProveedorDatos
from portafolio.operacion import LibroOperaciones, Operacion

IDX = pd.bdate_range("2025-01-02", "2026-01-02")


def mercado():
    plano = pd.DataFrame({"Precio_USD": 100.0, "Dividendo_USD": 0.0}, index=IDX)
    datos = {"KO": plano.copy(), "NKE": plano.copy()}
    trm = pd.Series(4000.0, index=IDX, name="TRM")
    return datos, trm


def correr(libro, auto=False, capital=50_000_000, redimir=False):
    datos, trm = mercado()
    p = Parametros(capital, date(2025, 1, 2), date(2026, 1, 2), comision_pct=0.002)
    return Portafolio(libro.activos(), p, datos_precargados=datos, trm_precargada=trm,
                      dividendos_manuales=libro.dividendos_manuales(), auto_dividendos=auto,
                      redimir_al_vencimiento=redimir).simular(libro.transacciones())


class Pruebas(unittest.TestCase):
    def test_precio_y_trm_manuales(self):
        libro = LibroOperaciones([Operacion(date(2025, 2, 3), "Compra", "NKE", "Acción", 10, 127.0, 4548.5)])
        r = correr(libro)
        l = r.libros["NKE"]
        costo = 10 * 127.0 * 4548.5
        self.assertAlmostEqual(l["Costo_Compra_COP"].sum(), costo, 4)
        self.assertAlmostEqual(l["Comision_COP"].sum(), costo * 0.002, 4)
        self.assertAlmostEqual(r.consolidado["Saldo_Caja_COP"].iloc[-1], 50_000_000 - costo * 1.002, 2)

    def test_dividendo_manual_con_trm_de_pago(self):
        libro = LibroOperaciones([
            Operacion(date(2025, 2, 3), "Compra", "KO", "Acción", 10),
            Operacion(date(2025, 3, 3), "Dividendo", "KO", "Acción", 10, 0.5, 4100.0)])
        r = correr(libro)
        self.assertAlmostEqual(r.libros["KO"]["Ingreso_Dividendos_COP"].sum(), 10 * 0.5 * 4100.0, 4)

    def test_cdt_causacion_y_redencion(self):
        compra = Operacion(date(2025, 2, 3), "Compra", "CDT-1", "CDT", 1, 5_000_000, 0, 0, 0.12,
                           date(2025, 8, 3))
        r = correr(LibroOperaciones([compra]), redimir=True)
        recibido = r.libros["CDT-1"]["Ingreso_Venta_COP"].sum()
        self.assertAlmostEqual(recibido, 5_000_000 * 1.12 ** (181 / 365), 2)

    def test_no_se_puede_vender_mas_de_lo_que_se_tiene(self):
        libro = LibroOperaciones([Operacion(date(2025, 2, 3), "Compra", "KO", "Acción", 5)])
        with self.assertRaises(ValueError):
            libro.agregar(Operacion(date(2025, 3, 3), "Venta", "KO", "Acción", 6))

    def test_tir_con_fechas(self):
        ea = CalculadoraRentabilidad.tasa_efectiva_anual([(date(2025, 1, 1), -100), (date(2026, 1, 1), 110)])
        self.assertAlmostEqual(ea, 0.10, 6)


class PruebasTRMyDetalle(unittest.TestCase):
    """TRM actual (caché diaria, errores) y detalle de operaciones frente a las capturas del Excel."""

    # ---------- TRM actual ----------
    class _Proveedor(ProveedorDatos):
        def __init__(self, resultado):
            self.resultado, self.llamadas = resultado, 0

        def _consultar_trm_actual(self):
            self.llamadas += 1
            if isinstance(self.resultado, Exception):
                raise self.resultado
            return dict(self.resultado)

    def test_trm_actual_una_sola_consulta_por_dia(self):
        with tempfile.TemporaryDirectory() as tmp:
            arch = str(Path(tmp) / "trm.json")
            prov = self._Proveedor({"valor": 3900.5, "fecha_dato": "2026-11-16"})
            a = prov.trm_actual(arch, hoy=date(2026, 11, 17))
            b = prov.trm_actual(arch, hoy=date(2026, 11, 17))
            self.assertEqual(prov.llamadas, 1)
            self.assertFalse(a["desde_cache"]); self.assertTrue(b["desde_cache"])
            self.assertEqual(b["fecha_dato"], "2026-11-16")
            prov.trm_actual(arch, hoy=date(2026, 11, 18))          # día nuevo -> vuelve a consultar
            self.assertEqual(prov.llamadas, 2)

    def test_trm_actual_sin_conexion(self):
        with tempfile.TemporaryDirectory() as tmp:
            arch = str(Path(tmp) / "trm.json")
            fallo = self._Proveedor(ConnectionError("sin red"))
            with self.assertRaises(ConnectionError):               # sin dato guardado: avisa quien llama
                fallo.trm_actual(arch, hoy=date(2026, 11, 17))
            self._Proveedor({"valor": 3900.5, "fecha_dato": "2026-11-16"}).trm_actual(arch, hoy=date(2026, 11, 16))
            r = fallo.trm_actual(arch, hoy=date(2026, 11, 17))     # con dato guardado: lo devuelve marcado
            self.assertTrue(r["desactualizado"]); self.assertEqual(r["valor"], 3900.5)

    def test_dashboard_no_se_cae_si_falla_la_trm_actual(self):
        for modulo in ("streamlit", "plotly", "plotly.express", "plotly.graph_objects"):
            try:
                __import__(modulo)
            except ImportError:
                sys.modules[modulo] = mock.MagicMock()            # solo para poder importar sin esas librerías
        from portafolio import dashboard
        with mock.patch.object(dashboard, "st") as st, \
             mock.patch.object(dashboard, "ProveedorDatos") as prov:
            prov.return_value.trm_actual.side_effect = ConnectionError("sin red")
            dashboard.Dashboard()._trm_actual_sidebar()           # no debe lanzar
            self.assertTrue(st.sidebar.warning.called)

    # ---------- dividendos con TRM de la fecha de pago ----------
    def test_dividendo_usa_trm_del_dia_de_pago(self):
        datos, _ = mercado()
        trm = pd.Series(np.linspace(4000, 4400, len(IDX)), index=IDX, name="TRM")
        ex, pago = pd.Timestamp("2025-03-03"), pd.Timestamp("2025-04-07")
        divs = {"KO": pd.DataFrame([{"Fecha_Ex": ex, "Dividendo_USD": 0.5, "Fecha_Pago": pago}])}
        libro = LibroOperaciones([Operacion(date(2025, 2, 3), "Compra", "KO", "Acción", 10)])
        p = Parametros(50_000_000, date(2025, 1, 2), date(2026, 1, 2))
        r = Portafolio(libro.activos(), p, datos_precargados=datos, trm_precargada=trm,
                       dividendos_externos=divs).simular(libro.transacciones())
        self.assertAlmostEqual(r.libros["KO"]["Ingreso_Dividendos_COP"].sum(), 10 * 0.5 * trm.asof(pago), 4)

    # ---------- capturas del Excel ----------
    def test_detalle_coincide_con_capturas(self):
        idx = pd.bdate_range("2023-01-30", "2023-12-29")
        plano = pd.DataFrame({"Precio_USD": 100.0, "Dividendo_USD": 0.0}, index=idx)
        trm = pd.Series(4000.0, index=idx, name="TRM")
        d = date
        libro = LibroOperaciones([
            Operacion(d(2023, 1, 30), "Compra", "NKE", "Acción", 20, 127.0, 4548.5),
            Operacion(d(2023, 2, 14), "Compra", "KO", "Acción", 50, 60.0, 4818.62),
            Operacion(d(2023, 2, 28), "Venta", "KO", "Acción", 50, 59.5, 4808.14),
            Operacion(d(2023, 4, 2), "Dividendo", "NKE", "Acción", 20, 0.34, 4646.08),
            Operacion(d(2023, 6, 22), "Venta", "NKE", "Acción", 20, 110.0, 3971.38),
            Operacion(d(2023, 7, 4), "Dividendo", "NKE", "Acción", 20, 0.34, 4177.58)])
        p = Parametros(30_000_000, d(2023, 1, 30), d(2023, 12, 29), comision_pct=0.002)
        r = Portafolio(libro.activos(), p, datos_precargados={"KO": plano, "NKE": plano.copy()},
                       trm_precargada=trm, auto_dividendos=False,
                       dividendos_manuales=libro.dividendos_manuales(),
                       redimir_al_vencimiento=False).simular(libro.transacciones())
        det = r.detalle_operaciones
        fila = lambda a, o, n=0: det[(det["Activo"] == a) & (det["Operación"] == o)].iloc[n]
        # (valor COP por acción, comisión) tal como aparecen en la captura, redondeados a pesos
        esperado = {("NKE", "Compra", 0): (577_660, 23_106), ("KO", "Compra", 0): (289_117, 28_912),
                    ("KO", "Venta", 0): (286_084, 28_608), ("NKE", "Venta", 0): (436_852, 17_474)}
        for (a, o, n), (valor, com) in esperado.items():
            f = fila(a, o, n)
            self.assertAlmostEqual(f["Valor por acción COP"], valor, delta=1, msg=(a, o))
            self.assertAlmostEqual(f["Comisión COP"], com, delta=1, msg=(a, o))
        self.assertAlmostEqual(fila("NKE", "Dividendo", 0)["Dividendo por acción COP"], 1579.67, delta=0.01)
        self.assertAlmostEqual(fila("NKE", "Dividendo", 1)["Dividendo por acción COP"], 1420.38, delta=0.01)
        # la venta del 22/06 no quita el derecho al dividendo con pago el 4/07: 20 acciones
        self.assertEqual(fila("NKE", "Dividendo", 1)["Acciones (saldo / con derecho)"], 20)
        self.assertAlmostEqual(fila("NKE", "Dividendo", 1)["Dividendo total COP"], 20 * 0.34 * 4177.58, 4)
        self.assertEqual(str(fila("NKE", "Dividendo", 1)["Fecha de pago"].date()), "2023-07-04")


    def test_operaciones_del_excel_dan_el_mismo_saldo(self):
        """Al registrar a mano las operaciones del Excel (con yfinance trayendo sus propios dividendos)
        el resultado debe ser el del Excel: sin contar dividendos dos veces."""
        idx = pd.bdate_range("2023-01-30", "2023-12-29")
        auto = pd.DataFrame({"Precio_USD": 100.0, "Dividendo_USD": 0.0}, index=idx)
        auto.loc[["2023-03-02", "2023-06-01"], "Dividendo_USD"] = 0.34      # ex-dividendos de yfinance
        trm = pd.Series(4000.0, index=idx, name="TRM")
        d = date
        libro = LibroOperaciones([
            Operacion(d(2023, 1, 30), "Compra", "NKE", "Acción", 20, 127.0, 4548.5),
            Operacion(d(2023, 2, 14), "Compra", "KO", "Acción", 50, 60.0, 4818.62),
            Operacion(d(2023, 2, 28), "Venta", "KO", "Acción", 50, 59.5, 4808.14),
            Operacion(d(2023, 4, 2), "Dividendo", "NKE", "Acción", 0, 0.34, 4646.08, fecha_ex=d(2023, 3, 2)),
            Operacion(d(2023, 6, 22), "Venta", "NKE", "Acción", 20, 110.0, 3971.38),
            Operacion(d(2023, 7, 4), "Dividendo", "NKE", "Acción", 0, 0.34, 4177.58, fecha_ex=d(2023, 6, 1))])
        p = Parametros(30_000_000, d(2023, 1, 30), d(2023, 12, 29), comision_pct=0.002)
        r = Portafolio(libro.activos(), p, datos_precargados={"KO": auto.copy(), "NKE": auto.copy()},
                       trm_precargada=trm, auto_dividendos=True,          # casilla por defecto
                       dividendos_manuales=libro.dividendos_manuales(),
                       redimir_al_vencimiento=False).simular(libro.transacciones())
        esperado = (-127 * 4548.5 * 20 * 1.002 - 60 * 4818.62 * 50 * 1.002 + 0.34 * 4646.08 * 20
                    + 59.5 * 4808.14 * 50 * 0.998 + 0.34 * 4177.58 * 20 + 110 * 3971.38 * 20 * 0.998)
        ex = r.formato_excel
        self.assertAlmostEqual(ex["Saldo"].iloc[-1], esperado, 4)
        self.assertAlmostEqual(r.metricas["ganancia_total"], esperado, 4)      # todo vendido
        self.assertEqual(list(ex[ex["Operación"] == "Dividendo"]["Acciones"]), [20, 20])
        self.assertAlmostEqual(ex["Dividendo cop"].iloc[ex.index[ex["Operación"] == "Dividendo"][0]], 1579.6672, 4)


if __name__ == "__main__":
    unittest.main()
