# Seguimiento de Portafolio de Inversión

## Descripción

Sistema desarrollado en Python para registrar, administrar y analizar un portafolio de inversiones financieras. Permite realizar seguimiento a acciones, CDT, bonos y TES mediante un dashboard interactivo.

El proyecto utiliza Yahoo Finance para consultar información del mercado bursátil y SQLite para almacenar las operaciones e inversiones registradas.

## Objetivo

Desarrollar una aplicación que permita administrar inversiones financieras, consultar su evolución, calcular su rentabilidad y generar proyecciones estimadas a un año.

## Funcionalidades

- Registro de compras y ventas de acciones.
- Seguimiento de acciones de Coca-Cola (KO) y Nike (NKE).
- Consulta de precios bursátiles mediante Yahoo Finance.
- Estimación de dividendos anuales según la cantidad de acciones.
- Registro de inversiones de renta fija: CDT, bonos y TES.
- Registro de pagos de intereses y abonos a capital.
- Cálculo de rentabilidad acumulada y rentabilidad efectiva anual.
- Separación de los resultados en dólares (USD) y pesos colombianos (COP).
- Gráficos de barras y distribución del portafolio.
- Proyección estimada del valor de las inversiones a un año.

## Tecnologías utilizadas

- Python 3.13
- Streamlit
- SQLite
- Pandas
- Plotly
- yfinance

## Organización del proyecto

```text
PORTAFOLIO-INVERSIONES/
│
├── main.py
├── requirements.txt
├── README.md
│
├── modelos/
│   ├── accion.py
│   ├── renta_fija.py
│   ├── operacion.py
│   └── portafolio.py
│
├── servicios/
│   ├── datos_mercado.py
│   ├── calculos.py
│   ├── base_datos.py
│   ├── gestor_operaciones.py
│   ├── gestor_renta_fija.py
│   ├── gestor_dividendos.py
│   ├── resumen_portafolio.py
│   └── proyeccion.py
│
├── interfaz/
│   └── dashboard.py
│
├── database/
├── docs/
└── tests/
```

## Instalación

1. Clonar el repositorio:

```bash
git clone https://github.com/Estebangaviria298-sudo/PORTAFOLIO-INVERSIONES.git
```

2. Entrar a la carpeta:

```bash
cd PORTAFOLIO-INVERSIONES
```

3. Crear el entorno virtual:

```bash
python -m venv .venv
```

4. Activar el entorno virtual en Git Bash:

```bash
source .venv/Scripts/activate
```

5. Instalar las dependencias:

```bash
python -m pip install -r requirements.txt
```

## Ejecución

Para iniciar la aplicación:

```bash
python -m streamlit run main.py
```

La aplicación abrirá el dashboard en el navegador.

## Base de datos

El sistema utiliza SQLite para almacenar las operaciones de compra y venta, las inversiones de renta fija, los dividendos y los pagos registrados.

La base de datos se crea automáticamente cuando se ejecuta el sistema.

## Cálculos financieros

El sistema calcula la rentabilidad teniendo en cuenta los movimientos de dinero registrados, los costos de las operaciones, los ingresos y el valor actual de las inversiones.

La rentabilidad efectiva anual se calcula mediante los flujos de caja y sus fechas.

Las inversiones en USD y COP se presentan por separado para evitar sumar monedas diferentes.

## Proyección

La aplicación permite estimar el comportamiento del portafolio durante un año, teniendo en cuenta el comportamiento histórico de las acciones, los dividendos estimados y las tasas de las inversiones de renta fija.

Las proyecciones son estimaciones y no representan una garantía de rentabilidad futura.

## Autores

Esteban Andres Gaviria Osorio

## Repositorio

[PORTAFOLIO-INVERSIONES en GitHub](https://github.com/Estebangaviria298-sudo/PORTAFOLIO-INVERSIONES)

## Diagrama UML

![Diagrama UML del proyecto](docs/diagrama_uml.png)