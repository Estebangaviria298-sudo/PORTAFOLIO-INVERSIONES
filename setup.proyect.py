"""setup_proyecto.py — reconstruye el proyecto de portafolio en la carpeta actual.

Uso (en la raíz del proyecto, p. ej. desde la terminal de VS Code):
    python setup_proyecto.py          # pide confirmación antes de borrar
    python setup_proyecto.py --yes    # sin preguntar

Qué hace:
  1. Elimina el código antiguo: carpetas portafolio/ y tests/, todas las carpetas __pycache__
     y los .py sueltos de la raíz (excepto este script).
  2. Crea o sobrescribe app.py, requirements.txt, README.md y el paquete portafolio/.
     (.gitignore solo se crea si no existe.)

Nunca toca: .git, .venv/venv, .vscode, ni archivos de datos (.xlsx, .csv, etc.).
"""
import shutil
import sys
from pathlib import Path

RAIZ = Path.cwd()
ESTE = Path(__file__).resolve()
PROTEGIDOS = {".git", ".venv", "venv", ".vscode", "node_modules"}

FILES = {
    'requirements.txt': r'''streamlit>=1.40
yfinance>=0.2.50
pandas>=2.0
numpy>=1.26
plotly>=5.20
openpyxl>=3.1
''',
    '.gitignore': r'''__pycache__/
*.pyc
.venv/
.streamlit/secrets.toml

.trm_cache.json
''',
    'README.md': r'''# Seguimiento de portafolio COP/USD (renta variable + renta fija)

App en Streamlit para registrar y simular un portafolio: inviertes en COP, compras acciones/ETF en USD
(KO y NKE obligatorias), también CDT/bonos/TES en COP, y todo se mide en COP con la TRM.
Calcula rentabilidad acumulada y **efectiva anual (E.A.)**, total invertido, valor actual y la
distribución renta fija / renta variable / caja.

## Instalación
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
python -m unittest discover -s tests                 # pruebas sin internet
```

## Cómo se usa
**Registro de operaciones** (pestaña 1): eliges instrumento, tipo de operación, fecha y ticker, y escribes
**tu** precio, TRM y comisión. Si dejas el precio o la TRM en 0 se usa el de mercado (yfinance); si dejas la
comisión en 0 se usa el % global de la barra lateral. Tipos: Compra, Venta, Dividendo (fecha de pago,
valor por acción en USD y TRM de ese día), Interés (monto en COP) y Pago de capital. Para CDT/Bono/TES
escribes valor unitario, tasa E.A. y vencimiento (cada título con un nombre distinto).
Puedes eliminar operaciones, exportar/importar CSV y cargar un ejemplo.

**Simulación por pesos / Excel** (pestaña 2): reparte el capital por ponderación o usa las operaciones y la
tabla de dividendos (fecha ex y de pago) de tu Excel.

## Estructura
| Archivo | Clase | Responsabilidad |
|---|---|---|
| `app.py` | – | Archivo principal: carga el Dashboard |
| `portafolio/dashboard.py` | `Dashboard` | Interfaz Streamlit |
| `portafolio/modelos.py` | `Activo`, `Parametros`, `Resultado` | Datos del dominio |
| `portafolio/operacion.py` | `Operacion`, `LibroOperaciones` | Registro y validación de operaciones |
| `portafolio/datos.py` | `ProveedorDatos` | yfinance: precios, dividendos (fecha ex), TRM histórica y TRM actual `COP=X` (caché diaria) |
| `portafolio/importador.py` | `ImportadorExcel` | Lee operaciones y dividendos del Excel |
| `portafolio/motor.py` | `MotorContable` | Fórmulas del Excel para un activo |
| `portafolio/calculadora.py` | `CalculadoraRentabilidad` | Rentabilidad acumulada y E.A. (XIRR) |
| `portafolio/portafolio.py` | `Portafolio` | Orquesta, renta fija, consolida, métricas |
| `portafolio/graficos.py` | `Graficador` | Gráficos Plotly |
| `tests/test_calculos.py` | – | Pruebas unitarias |

## Diagrama UML
```mermaid
classDiagram
    class Activo { +str ticker; +float peso; +bool obligatorio; +str instrumento; +float tasa_ea; +int plazo_dias; +float comision_pct; +bool capitaliza; +es_renta_fija() bool; +tipo() str }
    class Parametros { +float capital_cop; +date fecha_inicio; +date fecha_fin; +float comision_pct; +bool permitir_fracciones; +int rezago_pago_dias }
    class Resultado { +dict libros; +DataFrame consolidado; +dict metricas; +Series pesos_finales; +Series distribucion_tipo; +DataFrame resumen_activos; +DataFrame detalle_operaciones; +DataFrame formato_excel }
    class Operacion { +date fecha; +str tipo; +str ticker; +str instrumento; +float cantidad; +float precio; +float trm; +float comision; +float tasa_ea; +date vencimiento; +bool capitaliza; +date fecha_ex }
    class LibroOperaciones { +agregar(op); +eliminar(i); +activos() list; +transacciones() DataFrame; +dividendos_manuales() dict }
    class ProveedorDatos { +descargar_activo(ticker, inicio, fin) DataFrame; +descargar_trm(inicio, fin) Series; +trm_actual() dict }
    class ImportadorExcel { +leer(archivo) tuple }
    class MotorContable { +float comision_pct; +libro_activo(precio_usd, trm, operaciones, dividendos) DataFrame }
    class CalculadoraRentabilidad { +rentabilidad_acumulada(base, ganancia) float; +anualizar(rent, dias) float; +tasa_efectiva_anual(flujos) float }
    class Portafolio { +simular(transacciones) Resultado }
    class Graficador { +dona_pesos(); +dona_tipo(); +evolucion_total(); +comparativa_activos(); +composicion(); +dividendos() }
    class Dashboard { +ejecutar() }
    LibroOperaciones o-- Operacion
    Portafolio o-- Activo
    Portafolio --> Parametros
    Portafolio --> ProveedorDatos
    Portafolio ..> MotorContable : crea uno por activo
    Portafolio ..> CalculadoraRentabilidad : usa
    Portafolio ..> Resultado : crea
    Graficador ..> Resultado : usa
    Dashboard --> LibroOperaciones
    Dashboard --> Portafolio
    Dashboard --> ImportadorExcel
    Dashboard --> Graficador
    LibroOperaciones ..> Activo : genera
```

## Fórmulas (idénticas al Excel)
- Acciones = Acciones_anterior + Compra − Venta
- Valor COP = Valor USD × TRM del día
- Dividendo COP = Dividendo USD × TRM del día de **pago**, sobre las acciones que se tenían en la fecha ex (o las indicadas a mano)
- Comisión = % de corretaje (0,2 %) × Precio COP × (Compra + Venta), o el valor escrito
- Saldo caja = Saldo_anterior − (Precio COP × Compra) + (Precio COP × Venta) + (Dividendo COP × Acciones) − Comisión
- Renta fija: valor = valor de compra × (1 + E.A.)^(días/365), sin crecer después del vencimiento
- Rentabilidad acumulada = Valor final / Capital − 1 · E.A. = TIR con fechas (XIRR) de los flujos

## Git (rúbrica: varias ramas y varios commits)
```bash
git init && git add . && git commit -m "Estructura inicial del proyecto"
git checkout -b feature/motor-contable   # commits: motor, pruebas
git checkout -b feature/renta-fija main  # commits: renta fija, E.A.
git checkout -b feature/dashboard main   # commits: operaciones manuales, gráficos
git checkout main && git merge feature/motor-contable feature/renta-fija feature/dashboard
```
''',
    'app.py': r'''"""Archivo principal.  Ejecutar con:  streamlit run app.py"""
from portafolio.dashboard import Dashboard

Dashboard().ejecutar()
''',
    'portafolio/__init__.py': r'''"""Paquete de simulación y seguimiento de portafolio de inversión (COP/USD)."""
from .modelos import Activo, Parametros, Resultado
from .datos import ProveedorDatos
from .motor import MotorContable
from .operacion import LibroOperaciones, Operacion
from .portafolio import Portafolio

__all__ = ["Activo", "Parametros", "Resultado", "ProveedorDatos", "MotorContable",
           "LibroOperaciones", "Operacion", "Portafolio"]
''',
    'portafolio/modelos.py': r'''"""Modelos de datos (clases simples) usados por toda la aplicación."""
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, Optional

import pandas as pd

# Activos que SIEMPRE deben estar en el portafolio (requisito del proyecto)
TICKERS_OBLIGATORIOS = ("KO", "NKE")

INSTRUMENTOS_RV = ("Acción", "ETF")          # renta variable (precio de mercado en USD)
INSTRUMENTOS_RF = ("CDT", "Bono", "TES")     # renta fija (tasa E.A. en COP)
NOMINAL_RF = 1_000_000.0                     # valor nominal de 1 "título" de renta fija (COP)


@dataclass
class Activo:
    """Un activo del portafolio con su ponderación (0.0 a 1.0)."""
    ticker: str                         # símbolo (renta variable) o nombre (p. ej. CDT-1)
    peso: float
    obligatorio: bool = False
    instrumento: str = "Acción"         # Acción, ETF, CDT, Bono o TES
    tasa_ea: float = 0.0                # tasa efectiva anual (0.11 = 11 %), solo renta fija
    plazo_dias: int = 0                 # días al vencimiento, solo renta fija
    comision_pct: Optional[float] = None  # None = usa la comisión global
    capitaliza: bool = True             # renta fija: True = el valor crece a la tasa E.A.

    @property
    def es_renta_fija(self) -> bool:
        return self.instrumento in INSTRUMENTOS_RF

    @property
    def tipo(self) -> str:
        return "Renta fija" if self.es_renta_fija else "Renta variable"


@dataclass
class Parametros:
    """Parámetros de la simulación definidos por el usuario."""
    capital_cop: float                 # Capital inicial en pesos colombianos
    fecha_inicio: date                 # Primer día de la simulación
    fecha_fin: date                    # Último día (≈ 1 año después)
    comision_pct: float = 0.002        # Corretaje: 0.2 % (el del Excel)
    permitir_fracciones: bool = True
    rezago_pago_dias: int = 30         # días entre ex-dividendo y pago (si no hay Excel)


@dataclass
class Resultado:
    """Salida de la simulación."""
    libros: Dict[str, pd.DataFrame] = field(default_factory=dict)  # por activo
    consolidado: pd.DataFrame = None                               # portafolio
    metricas: Dict[str, float] = field(default_factory=dict)
    pesos_finales: pd.Series = None                                # por activo + caja
    distribucion_tipo: pd.Series = None                            # renta fija / variable / caja
    resumen_activos: pd.DataFrame = None                           # tabla por activo
    detalle_operaciones: pd.DataFrame = None                       # operaciones y dividendos con TRM
    formato_excel: pd.DataFrame = None                             # mismas columnas que la hoja de Excel
''',
    'portafolio/datos.py': r'''"""Descarga de datos de mercado con yfinance (precios, dividendos y TRM)."""
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd


class ProveedorDatos:
    """Encapsula todo acceso a internet/yfinance."""

    TICKER_TRM = "COP=X"   # Pesos colombianos por 1 USD
    ARCHIVO_CACHE_TRM = ".trm_cache.json"
    FUENTE_TRM = ("Yahoo Finance (COP=X): referencia de mercado USD/COP, no necesariamente la TRM "
                  "oficial certificada por la Superintendencia Financiera de Colombia")

    @staticmethod
    def _limpiar_indice(df: pd.DataFrame) -> pd.DataFrame:
        """Quita zona horaria y hora para poder cruzar series por fecha."""
        df = df.copy()
        df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
        return df[~df.index.duplicated(keep="last")]

    def descargar_activo(self, ticker: str, inicio: date, fin: date) -> pd.DataFrame:
        """Devuelve DataFrame con Precio_USD (cierre) y Dividendo_USD (por acción)."""
        import yfinance as yf  # import diferido: solo se necesita al descargar
        h = yf.Ticker(ticker).history(
            start=inicio.isoformat(),
            end=(fin + timedelta(days=1)).isoformat(),
            auto_adjust=False,   # precio SIN ajustar por dividendos (se suman aparte)
            actions=True,
        )
        if h.empty:
            raise ValueError(f"No se encontraron datos para '{ticker}'.")
        h = self._limpiar_indice(h)
        out = pd.DataFrame({"Precio_USD": h["Close"]})
        out["Dividendo_USD"] = h["Dividends"] if "Dividends" in h else 0.0
        return out

    def descargar_trm(self, inicio: date, fin: date) -> pd.Series:
        """Serie diaria de TRM (COP por USD). Se baja unos días antes para rellenar."""
        import yfinance as yf
        h = yf.Ticker(self.TICKER_TRM).history(
            start=(inicio - timedelta(days=15)).isoformat(),
            end=(fin + timedelta(days=1)).isoformat(),
        )
        if h.empty:
            raise ValueError("No se pudo descargar la TRM (COP=X).")
        return self._limpiar_indice(h)["Close"].rename("TRM")

    # ------------------------------------------------------------------
    # TRM ACTUAL (solo para mostrar en el dashboard; NO reemplaza el TRM histórico
    # de cada operación, que sigue saliendo de descargar_trm)
    # ------------------------------------------------------------------
    def _consultar_trm_actual(self) -> dict:
        """Última cotización USD/COP disponible en Yahoo Finance."""
        import yfinance as yf  # import diferido, igual que en el resto de la clase
        h = yf.Ticker(self.TICKER_TRM).history(period="10d")
        if h.empty:
            raise ValueError("Yahoo Finance no devolvió datos para COP=X.")
        cierre = self._limpiar_indice(h)["Close"].dropna()
        if cierre.empty:
            raise ValueError("Yahoo Finance no devolvió cotizaciones válidas para COP=X.")
        return {"valor": float(cierre.iloc[-1]), "fecha_dato": cierre.index[-1].date().isoformat()}

    @staticmethod
    def _leer_cache(archivo: Path) -> Optional[dict]:
        try:
            dato = json.loads(archivo.read_text(encoding="utf-8"))
            return dato if {"valor", "fecha_dato", "fecha_consulta"} <= set(dato) else None
        except (OSError, ValueError):
            return None

    @staticmethod
    def _guardar_cache(archivo: Path, dato: dict) -> None:
        try:
            archivo.write_text(json.dumps(dato), encoding="utf-8")
        except OSError:
            pass                                    # sin caché en disco el programa sigue igual

    def trm_actual(self, archivo_cache: Optional[str] = None, hoy: Optional[date] = None) -> dict:
        """TRM actual con caché diaria: se consulta una sola vez por día.

        Devuelve {valor, fecha_dato, fecha_consulta, fuente, desde_cache, desactualizado}.
        Si la consulta falla y hay un dato guardado, lo devuelve marcado como desactualizado;
        si no hay nada guardado, lanza la excepción para que quien llama muestre un aviso.
        """
        archivo = Path(archivo_cache or self.ARCHIVO_CACHE_TRM)
        hoy = hoy or date.today()
        cache = self._leer_cache(archivo)
        if cache and cache["fecha_consulta"] == hoy.isoformat():
            return {**cache, "desde_cache": True, "desactualizado": False}
        try:
            dato = self._consultar_trm_actual()
        except Exception as e:
            if cache:
                return {**cache, "desde_cache": True, "desactualizado": True, "error": str(e)}
            raise
        dato.update(fecha_consulta=hoy.isoformat(), fuente=self.FUENTE_TRM)
        self._guardar_cache(archivo, dato)
        return {**dato, "desde_cache": False, "desactualizado": False}
''',
    'portafolio/importador.py': r'''"""Lee el Excel de seguimiento (hoja por activo) y devuelve operaciones y dividendos.

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
''',
    'portafolio/operacion.py': r'''"""Operacion y LibroOperaciones: registro manual de operaciones (precio, TRM y comisión editables)."""
from dataclasses import dataclass
from datetime import date
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

    @classmethod
    def desde_dataframe(cls, df: pd.DataFrame) -> "LibroOperaciones":
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
''',
    'portafolio/motor.py': r'''"""Motor contable: replica las fórmulas del Excel para UN activo.

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
''',
    'portafolio/calculadora.py': r'''"""CalculadoraRentabilidad: rentabilidad acumulada y rentabilidad efectiva anual (E.A.)."""
from typing import List, Optional, Tuple


class CalculadoraRentabilidad:
    DIAS_ANIO = 365

    @staticmethod
    def rentabilidad_acumulada(base: float, ganancia: float) -> float:
        """ganancia / base (base = capital o total invertido)."""
        return ganancia / base if base > 0 else 0.0

    @classmethod
    def anualizar(cls, rentabilidad: float, dias: int) -> float:
        """E.A. simple: (1 + r)^(365/días) - 1."""
        if dias <= 0 or rentabilidad <= -1:
            return rentabilidad
        return (1 + rentabilidad) ** (cls.DIAS_ANIO / dias) - 1

    @classmethod
    def valor_presente_neto(cls, tasa: float, flujos: List[Tuple]) -> float:
        t0 = flujos[0][0]
        return sum(cf / (1 + tasa) ** ((d - t0).days / cls.DIAS_ANIO) for d, cf in flujos)

    @classmethod
    def tasa_efectiva_anual(cls, flujos: List[Tuple]) -> Optional[float]:
        """TIR con fechas (XIRR). flujos = [(fecha, monto)]: compras y comisiones negativas;
        ventas, dividendos, intereses y el valor final del portafolio positivos.
        Resuelve por bisección; devuelve None si no hay solución."""
        flujos = sorted(flujos, key=lambda x: x[0])
        if len(flujos) < 2 or not any(m < 0 for _, m in flujos) or not any(m > 0 for _, m in flujos):
            return None
        if (flujos[-1][0] - flujos[0][0]).days <= 0:
            return None
        bajo, alto = -0.9999, 1000.0
        f_bajo = cls.valor_presente_neto(bajo, flujos)
        if f_bajo * cls.valor_presente_neto(alto, flujos) > 0:
            return None
        for _ in range(200):
            medio = (bajo + alto) / 2
            f_medio = cls.valor_presente_neto(medio, flujos)
            if abs(f_medio) < 1e-9:
                return medio
            if f_bajo * f_medio < 0:
                alto = medio
            else:
                bajo, f_bajo = medio, f_medio
        return (bajo + alto) / 2
''',
    'portafolio/portafolio.py': r'''"""Orquestador: arma el calendario, resuelve operaciones y consolida el portafolio."""
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
''',
    'portafolio/graficos.py': r'''"""Gráficos Plotly del dashboard."""
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
''',
    'portafolio/dashboard.py': r'''"""Clase Dashboard: interfaz Streamlit que orquesta las demás clases.

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
''',
    'tests/test_calculos.py': r'''"""Pruebas sin internet (datos sintéticos).  Ejecutar:  python -m unittest discover -s tests"""
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
''',
}


def a_borrar():
    """Lista lo que se eliminará (código antiguo), sin tocar carpetas protegidas."""
    out = []
    for carpeta in ("portafolio", "tests"):
        if (RAIZ / carpeta).is_dir():
            out.append(RAIZ / carpeta)
    for p in RAIZ.rglob("__pycache__"):
        if not (set(p.relative_to(RAIZ).parts) & PROTEGIDOS) and p.is_dir():
            out.append(p)
    for p in RAIZ.glob("*.py"):                      # solo la raíz, no subcarpetas
        if p.resolve() != ESTE:
            out.append(p)
    # sin duplicados (un __pycache__ dentro de portafolio/ ya se borra con su carpeta)
    unicos = []
    for p in sorted(out, key=lambda x: len(x.parts)):
        if not any(u in p.parents for u in unicos):
            unicos.append(p)
    return unicos


def main():
    if (RAIZ / ".git").exists():
        print("✔ Se detectó .git (no se tocará).")
    borrar = a_borrar()
    print("Se eliminarán:" if borrar else "No hay código antiguo que eliminar.")
    for p in borrar:
        print("  -", p.relative_to(RAIZ))
    print("Se crearán/sobrescribirán:")
    for ruta in FILES:
        print("  +", ruta)

    if "--yes" not in sys.argv and input("\n¿Continuar? [s/N] ").strip().lower() not in ("s", "si", "sí", "y", "yes"):
        print("Cancelado. No se modificó nada.")
        return

    for p in borrar:
        shutil.rmtree(p) if p.is_dir() else p.unlink()

    for ruta, contenido in FILES.items():
        destino = RAIZ / ruta
        if ruta == ".gitignore" and destino.exists():
            continue                                  # no pisar el .gitignore del usuario
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(contenido, encoding="utf-8")

    print("\n✅ Listo. Siguientes pasos:")
    print("   pip install -r requirements.txt")
    print("   streamlit run app.py")


if __name__ == "__main__":
    main()