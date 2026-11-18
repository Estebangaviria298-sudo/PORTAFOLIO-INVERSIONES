"""Clase Dashboard: interfaz Streamlit que orquesta las demás clases.

Dos vistas:
  1) Registro de operaciones: el usuario escribe cada compra/venta/dividendo con SU precio,
     TRM y comisión (o los deja en 0 para usar el mercado).
  2) Simulación por pesos: reparte el capital por ponderación o usa el Excel.
"""
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from .datos import ProveedorDatos
from .graficos import Graficador
from .importador import ImportadorExcel
from .modelos import Activo, INSTRUMENTOS_RF, INSTRUMENTOS_RV, Parametros, TICKERS_OBLIGATORIOS
from .operacion import LibroOperaciones, Operacion
from .portafolio import Portafolio


@st.cache_data(show_spinner="Descargando datos de yfinance…", ttl=3600)
def cargar_datos(tickers: tuple, inicio: date, fin: date):
    """Descarga (con caché) precios/dividendos de renta variable y la TRM."""
    prov = ProveedorDatos()
    return {t: prov.descargar_activo(t, inicio, fin) for t in tickers}, prov.descargar_trm(inicio, fin)


class Dashboard:
    # ================================================================== punto de entrada
    def ejecutar(self) -> None:
        st.set_page_config(page_title="Portafolio COP/USD", page_icon="📈", layout="wide")
        st.markdown("""<style>
        div[data-testid="stMetric"]{background:rgba(120,130,160,.10);border:1px solid rgba(120,130,160,.25);
        border-radius:14px;padding:14px 18px;} div[data-testid="stMetricValue"]{font-size:1.5rem;}
        </style>""", unsafe_allow_html=True)
        p = self._barra_lateral()
        st.title("📈 Seguimiento de portafolio (inversión en COP)")
        st.caption("Inviertes en pesos, compras en dólares y ves la rentabilidad en pesos con la TRM; "
                   "dividendos con la TRM del día de pago; renta fija causada a su tasa E.A.")
        t1, t2 = st.tabs(["🧾 Registro de operaciones", "🔮 Simulación por pesos / Excel"])
        with t1:
            self._vista_operaciones(p)
        with t2:
            self._vista_simulacion(p)

    # ================================================================== utilidades
    @staticmethod
    def _fig(fig) -> None:
        try:
            st.plotly_chart(fig, width="stretch")
        except TypeError:
            st.plotly_chart(fig, use_container_width=True)

    @staticmethod
    def _df(df, **kw) -> None:
        try:
            st.dataframe(df, width="stretch", **kw)
        except TypeError:
            st.dataframe(df, use_container_width=True, **kw)

    @staticmethod
    def _cop(x: float) -> str:
        return f"${x:,.0f}"

    def _barra_lateral(self) -> dict:
        st.sidebar.header("⚙️ Parámetros")
        st.session_state.setdefault("capital", 10_000_000)
        capital = st.sidebar.number_input("Capital inicial (COP)", 1_000_000, 10_000_000_000,
                                          step=500_000, key="capital")
        comision = st.sidebar.number_input("Comisión de corretaje (%)", 0.0, 5.0, 0.2, step=0.05) / 100
        fracciones = st.sidebar.checkbox("Permitir acciones fraccionadas (simulación)", True)
        rezago = st.sidebar.number_input("Días entre ex-dividendo y pago", 0, 90, 30,
                                         help="Solo para dividendos tomados de yfinance.")
        self._trm_actual_sidebar()
        return {"capital": capital, "comision": comision, "fracciones": fracciones, "rezago": int(rezago)}

    def _trm_actual_sidebar(self) -> None:
        """TRM actual (USD/COP). Solo informativa: los cálculos usan el TRM histórico de cada fecha."""
        st.sidebar.divider()
        st.sidebar.subheader("💱 TRM actual USD/COP")
        try:
            d = ProveedorDatos().trm_actual()     # una consulta por día (caché en .trm_cache.json)
        except Exception:
            st.sidebar.warning("No se pudo consultar la TRM actual (¿sin conexión?). "
                               "El resto del programa sigue funcionando con los datos históricos.")
            return
        st.sidebar.metric("Referencia de mercado", f"${d['valor']:,.2f} COP")
        st.sidebar.caption(f"Último dato disponible: {d['fecha_dato']} · consultado el {d['fecha_consulta']}")
        if d.get("desactualizado"):
            st.sidebar.warning("No se pudo actualizar hoy; se muestra el último dato guardado.")
        st.sidebar.caption(f"Fuente: {d.get('fuente', ProveedorDatos.FUENTE_TRM)}. "
                           "Las operaciones usan el TRM histórico de su fecha, no este valor.")

    # ================================================================== vista 1: operaciones
    def _vista_operaciones(self, p: dict) -> None:
        st.session_state.setdefault("libro", LibroOperaciones())
        libro: LibroOperaciones = st.session_state["libro"]

        st.subheader("Registrar operación")
        self._formulario(libro)

        c2, c3 = st.columns(2)
        if c2.button("🗑️ Vaciar operaciones"):
            libro.limpiar()
            st.session_state.pop("res_ops", None)
        c3.download_button("⬇️ Exportar operaciones (CSV)", libro.a_dataframe().to_csv(index=False).encode(),
                           "operaciones.csv", "text/csv")
        with st.expander("⬆️ Importar operaciones desde CSV"):
            archivo = st.file_uploader("CSV exportado por esta aplicación", type="csv", key="csv_ops")
            if archivo is not None and st.button("Importar CSV"):
                try:
                    libro.reemplazar(LibroOperaciones.desde_dataframe(pd.read_csv(archivo)))
                    st.session_state.pop("res_ops", None)
                    st.success("Operaciones importadas.")
                except Exception as e:
                    st.error(f"No se pudo importar: {e}")

        if not libro.operaciones:
            st.info("Aún no hay operaciones. Registra una arriba.")
            return
        tickers = {o.ticker for o in libro.operaciones}
        faltan = [t for t in TICKERS_OBLIGATORIOS if t not in tickers]
        if faltan:
            st.warning(f"El portafolio debe incluir {' y '.join(faltan)} (obligatorio).")

        st.divider()
        st.subheader("Operaciones registradas")
        df = libro.a_dataframe()
        df.insert(0, "#", range(len(df)))
        self._df(df, hide_index=True)
        a, b = st.columns([1, 3])
        idx = a.selectbox("Eliminar operación #", list(range(len(df))))
        if b.button("Eliminar operación seleccionada"):
            try:
                libro.eliminar(idx)
                st.session_state.pop("res_ops", None)
                st.rerun()
            except ValueError as e:
                st.error(f"No se puede eliminar: {e}")

        st.checkbox("Calcular además los dividendos automáticamente con yfinance", True, key="auto_div",
                    help="Los activos con dividendos registrados por ti no usan yfinance, así no se cuentan dos veces.")
        if st.button("📊 Calcular portafolio", type="primary"):
            self._calcular_operaciones(libro, p)
        res = st.session_state.get("res_ops")
        if res is not None:
            self._resultados(res, p["capital"], "ops")

    def _formulario(self, libro: LibroOperaciones) -> None:
        c1, c2, c3, c4 = st.columns(4)
        instrumento = c1.selectbox("Instrumento", Operacion.INSTRUMENTOS)
        tipo = c2.selectbox("Operación", Operacion.TIPOS)
        fecha = c3.date_input("Fecha", value=date.today(), min_value=date(2000, 1, 1), max_value=date.today(),
                              help="En dividendos es la fecha de PAGO.")
        ident = c4.text_input("Ticker / Nombre", placeholder="KO · NKE · CDT Banco X")
        rf = instrumento in INSTRUMENTOS_RF

        cantidad, precio, trm, comision = 1.0, 0.0, 0.0, 0.0
        tasa, venc, capitaliza, fecha_ex = None, None, True, None
        c5, c6, c7, c8 = st.columns(4)
        if tipo == "Interés":
            precio = c5.number_input("Monto recibido (COP)", 0.0, step=10_000.0)
        elif tipo == "Dividendo":
            cantidad = c5.number_input("Acciones con derecho (0 = las que tenías en la fecha ex, o de pago)", 0.0,
                                       value=0.0, step=1.0)
            precio = c6.number_input("Dividendo por acción (USD)", 0.0, step=0.01, format="%.4f")
            trm = c7.number_input("TRM del día de pago (0 = de mercado)", 0.0, step=1.0)
            if c8.checkbox("Indicar fecha ex-dividendo", help="Define las acciones con derecho al dividendo."):
                fecha_ex = c8.date_input("Fecha ex-dividendo", value=fecha, min_value=date(2000, 1, 1), max_value=fecha)
        else:
            cantidad = c5.number_input("Cantidad", 0.0, value=1.0, step=1.0)
            precio = c6.number_input(
                "Valor unitario (COP)" if rf else "Precio por acción (USD)", 0.0,
                step=100_000.0 if rf else 0.01, format="%.2f",
                help="0 = " + ("valor causado a esa fecha." if rf else "precio de cierre de mercado de esa fecha."))
            if not rf:
                trm = c7.number_input("TRM (COP por USD, 0 = de mercado)", 0.0, step=1.0)
            comision = c8.number_input("Comisión (COP, 0 = % global)", 0.0, step=1_000.0)
        if rf and tipo == "Compra":
            d1, d2, d3 = st.columns(3)
            tasa = d1.number_input("Tasa efectiva anual (% E.A.)", 0.0, 100.0, 10.0, step=0.1) / 100
            venc = d2.date_input("Vencimiento", value=date.today() + timedelta(days=365),
                                 min_value=date(2000, 1, 1), max_value=date(2100, 1, 1))
            capitaliza = d3.checkbox("Capitaliza intereses (CDT/TES)", True,
                                     help="Si paga cupones aparte, desmárcalo y registra 'Interés'.")

        if st.button("➕ Registrar operación", type="primary"):
            ident = ident.strip()
            ticker = ident if rf else ident.upper()
            try:
                libro.agregar(Operacion(fecha, tipo, ticker, instrumento, cantidad, precio, trm,
                                        comision, tasa, venc, capitaliza, fecha_ex))
                st.session_state.pop("res_ops", None)
                st.success(f"{tipo} de {ticker} registrada.")
            except ValueError as e:
                st.error(str(e))

    def _calcular_operaciones(self, libro: LibroOperaciones, p: dict) -> None:
        try:
            activos = libro.activos()
            inicio = libro.fecha_inicio()
            fin = min(date.today(), max(inicio + timedelta(days=365), libro.fecha_fin()))
            rv = tuple(a.ticker for a in activos if not a.es_renta_fija)
            datos, trm = cargar_datos(rv, inicio, fin)
            params = Parametros(p["capital"], inicio, fin, p["comision"], p["fracciones"], p["rezago"])
            st.session_state["res_ops"] = Portafolio(
                activos, params, datos_precargados=datos, trm_precargada=trm,
                dividendos_manuales=libro.dividendos_manuales(),
                auto_dividendos=st.session_state.get("auto_div", True),
                redimir_al_vencimiento=False).simular(libro.transacciones())
        except Exception as e:
            st.error(f"No se pudo calcular: {e}")

    # ================================================================== vista 2: simulación
    def _vista_simulacion(self, p: dict) -> None:
        archivo = st.file_uploader("Excel de seguimiento (opcional)", type=["xlsx"], key="xlsx_sim",
                                   help="Usa las compras/ventas y la tabla de dividendos del Excel.")
        tx, divs_excel = None, {}
        if archivo is not None:
            try:
                tx, divs_excel = ImportadorExcel().leer(archivo)
                st.success(f"{len(tx)} operaciones leídas del Excel.")
            except Exception as e:
                st.error(f"No se pudo leer el Excel: {e}")
        inicio_def = tx["Fecha"].min().date() if tx is not None else date.today() - timedelta(days=365)
        inicio = st.date_input("Primer día de la simulación", inicio_def, key=f"ini_{inicio_def}")
        fin = min(inicio + timedelta(days=365), date.today())
        st.caption(f"Fin de la simulación (1 año): {fin}")

        base = pd.DataFrame([
            {"Ticker": "KO", "Instrumento": "Acción", "Peso %": 30.0, "Tasa E.A. %": 0.0, "Plazo (días)": 0},
            {"Ticker": "NKE", "Instrumento": "Acción", "Peso %": 30.0, "Tasa E.A. %": 0.0, "Plazo (días)": 0},
            {"Ticker": "SPY", "Instrumento": "ETF", "Peso %": 20.0, "Tasa E.A. %": 0.0, "Plazo (días)": 0},
            {"Ticker": "CDT-1", "Instrumento": "CDT", "Peso %": 20.0, "Tasa E.A. %": 11.0, "Plazo (días)": 360}])
        st.markdown("**Activos y ponderación** (KO y NKE obligatorios)")
        try:
            tabla = st.data_editor(
                base, num_rows="dynamic", hide_index=True, width="stretch", key="tabla_activos",
                column_config=self._config_tabla())
        except TypeError:
            tabla = st.data_editor(base, num_rows="dynamic", hide_index=True, use_container_width=True,
                                   key="tabla_activos", column_config=self._config_tabla())
        suma = float(tabla["Peso %"].fillna(0).sum())
        if tx is not None:
            st.info("Con Excel cargado, las operaciones salen del archivo y los pesos no se usan.")
        else:
            st.metric("Suma de pesos", f"{suma:.2f} %")

        if st.button("🚀 Simular", type="primary", key="btn_sim"):
            try:
                activos = self._activos_desde_tabla(tabla)
                rv = tuple(a.ticker for a in activos if not a.es_renta_fija)
                datos, trm = cargar_datos(rv, inicio, fin)
                params = Parametros(p["capital"], inicio, fin, p["comision"], p["fracciones"], p["rezago"])
                st.session_state["res_sim"] = Portafolio(
                    activos, params, datos_precargados=datos, trm_precargada=trm,
                    dividendos_externos=divs_excel).simular(tx)
            except Exception as e:
                st.error(f"No se pudo simular: {e}")
        res = st.session_state.get("res_sim")
        if res is not None:
            self._resultados(res, p["capital"], "sim")

    @staticmethod
    def _config_tabla() -> dict:
        return {
            "Instrumento": st.column_config.SelectboxColumn(options=list(INSTRUMENTOS_RV + INSTRUMENTOS_RF)),
            "Peso %": st.column_config.NumberColumn(min_value=0.0, max_value=100.0, step=1.0),
            "Tasa E.A. %": st.column_config.NumberColumn(min_value=0.0, max_value=100.0, step=0.1),
            "Plazo (días)": st.column_config.NumberColumn(min_value=0, step=30)}

    @staticmethod
    def _activos_desde_tabla(tabla: pd.DataFrame):
        activos = []
        for _, r in tabla.iterrows():
            t = "" if pd.isna(r["Ticker"]) else str(r["Ticker"]).strip().upper()
            if not t:
                continue
            instr = r["Instrumento"] if not pd.isna(r["Instrumento"]) else "Acción"
            rf = instr in INSTRUMENTOS_RF
            activos.append(Activo(
                t, float(r["Peso %"] or 0) / 100, t in TICKERS_OBLIGATORIOS, instr,
                float(r["Tasa E.A. %"] or 0) / 100 if rf else 0.0,
                int(r["Plazo (días)"] or 0) if rf else 0, 0.0 if rf else None))
        return activos

    # ================================================================== resultados (comunes)
    def _resultados(self, res, capital: float, clave: str) -> None:
        m = res.metricas
        if m["caja_minima"] < -1:
            st.warning(f"El capital no alcanza: la caja llegó a {self._cop(m['caja_minima'])} COP. "
                       f"Súbelo al menos a {self._cop(capital - m['caja_minima'])}.")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Capital inicial", self._cop(m["capital_inicial"]))
        c2.metric("Total invertido", self._cop(m["total_invertido"]))
        c3.metric("Valor actual del portafolio", self._cop(m["valor_final"]))
        c4.metric("Rendimiento total estimado", self._cop(m["ganancia_total"]), f"{m['rentabilidad_total']:.2%}")
        c5, c6, c7, c8 = st.columns(4)
        c5.metric("Rentabilidad efectiva anual (E.A.)", f"{m['rentabilidad_ea']:.2%}",
                  help="TIR con fechas (XIRR) de todos los flujos. En periodos cortos puede ser muy alta o baja.")
        c6.metric("Ganancia por dividendos/intereses", self._cop(m["ganancia_dividendos"]),
                  f"{m['rent_dividendos']:.2%}")
        c7.metric("Comisiones pagadas", self._cop(m["comisiones"]))
        c8.metric("TRM inicial → final", f"{m['trm_inicial']:,.0f} → {m['trm_final']:,.0f}", f"{m['var_trm']:.2%}")
        st.caption(f"Rentabilidad acumulada sobre capital {m['rentabilidad_total']:.2%} · sobre lo invertido "
                   f"{m['rentabilidad_sobre_invertido']:.2%} · {m['dias']} días · volatilidad anual "
                   f"{m['volatilidad_anual']:.1%} · máxima caída {m['max_drawdown']:.1%}")

        t1, t2, t3, t4, t5, t6 = st.tabs(["Dashboard", "Resumen por activo", "Dividendos", "Libro contable",
                                          "Por activo", "Detalle de operaciones"])
        with t1:
            a, b = st.columns(2)
            with a:
                self._fig(Graficador.dona_pesos(res))
            with b:
                self._fig(Graficador.dona_tipo(res))
            self._fig(Graficador.comparativa_activos(res))
            self._fig(Graficador.evolucion_total(res, capital))
            self._fig(Graficador.composicion(res))
        with t2:
            r = res.resumen_activos
            fmt = {c: "{:,.0f}" for c in r.columns if c.endswith("COP")}
            fmt["Rentabilidad"] = "{:.2%}"
            self._df(r.style.format(fmt, na_rep="N/D"), hide_index=True)
        with t3:
            self._fig(Graficador.dividendos(res))
        with t4:
            self._df(res.consolidado.style.format("{:,.2f}"))
            st.download_button("⬇️ Descargar libro (CSV)", res.consolidado.to_csv().encode(),
                               "libro_portafolio.csv", key=f"dl_{clave}")
        with t5:
            t = st.selectbox("Activo", list(res.libros), key=f"sel_{clave}")
            self._df(res.libros[t].style.format("{:,.2f}"))
        with t6:
            det = res.detalle_operaciones
            fmt = {c: "{:,.2f}" for c in det.columns
                   if c not in ("Fecha", "Activo", "Operación", "Moneda", "Fecha de pago")}
            fmt.update({"Fecha": "{:%Y-%m-%d}", "Fecha de pago": "{:%Y-%m-%d}"})
            ex = res.formato_excel
            st.markdown("**Formato Excel** (mismas columnas y fórmulas de tu hoja)")
            fx = {c: "{:,.2f}" for c in ex.columns if c not in ("Fecha", "Activo", "Operación")}
            fx["Fecha"] = "{:%Y-%m-%d}"
            self._df(ex.style.format(fx, na_rep="—"), hide_index=True)
            st.caption(f"Saldo final (flujo neto de caja): {self._cop(ex['Saldo'].iloc[-1])} COP. Con todas las "
                       "posiciones cerradas coincide con el rendimiento total.")
            st.markdown("**Detalle completo**")
            st.caption("TRM aplicada = la de la fecha de cada operación; en dividendos, la de la fecha de pago.")
            self._df(det.style.format(fmt, na_rep="—"), hide_index=True)
            st.download_button("⬇️ Descargar detalle (CSV)", det.to_csv(index=False).encode(),
                               "detalle_operaciones.csv", key=f"dd_{clave}")
