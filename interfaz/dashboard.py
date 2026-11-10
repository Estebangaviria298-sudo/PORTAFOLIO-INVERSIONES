
import streamlit as st
import pandas as pd
import plotly.express as px

from datetime import date, timedelta

from servicios.gestor_operaciones import GestorOperaciones
from servicios.gestor_renta_fija import GestorRentaFija
from servicios.gestor_dividendos import GestorDividendos
from servicios.resumen_portafolio import ResumenPortafolio
from servicios.proyeccion import ProyeccionPortafolio
from servicios.base_datos import BaseDatos


# --------------------------------------------------
# FUNCIONES GENERALES
# --------------------------------------------------

def formato_dinero(valor, moneda):
    valor = float(valor or 0)

    if moneda == "COP":
        return f"${valor:,.0f} COP"

    return f"${valor:,.2f} USD"


def mostrar_tabla(datos):
    if datos:
        st.dataframe(
            pd.DataFrame(datos),
            width="stretch",
            hide_index=True
        )


# --------------------------------------------------
# APLICACION PRINCIPAL
# --------------------------------------------------

def mostrar_dashboard():

    st.set_page_config(
        page_title="Portafolio de inversión",
        page_icon="📈",
        layout="wide"
    )

    st.title("📈 Seguimiento de portafolio de inversión")
    st.caption(
        "Sistema de administración, análisis y seguimiento "
        "de inversiones financieras."
    )

    # SERVICIOS

    gestor_acciones = GestorOperaciones()
    gestor_renta_fija = GestorRentaFija()
    gestor_dividendos = GestorDividendos()
    resumen_servicio = ResumenPortafolio()
    proyeccion_servicio = ProyeccionPortafolio()
    base_datos = BaseDatos()

    # CARGAR INFORMACION

    try:
        resumen = resumen_servicio.obtener_resumen()

    except Exception as error:
        st.error(f"No se pudo cargar el portafolio: {error}")
        return

    monedas = resumen["monedas"]
    rentabilidad = resumen["rentabilidad"]
    acciones = resumen["acciones"]
    inversiones = resumen["inversiones_fijas"]

    # --------------------------------------------------
    # 1. RESUMEN GENERAL
    # --------------------------------------------------

    st.header("Resumen general")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Acciones en USD",
        formato_dinero(monedas["USD"]["valor_acciones"], "USD")
    )

    col2.metric(
        "Renta fija en USD",
        formato_dinero(monedas["USD"]["valor_renta_fija"], "USD")
    )

    col3.metric(
        "Acciones en COP",
        formato_dinero(monedas["COP"]["valor_acciones"], "COP")
    )

    col4.metric(
        "Renta fija en COP",
        formato_dinero(monedas["COP"]["valor_renta_fija"], "COP")
    )

    st.info(
        "Los dólares y los pesos colombianos se calculan por separado "
        "para evitar mezclar monedas diferentes."
    )

    col1, col2 = st.columns(2)

    col1.metric(
        "Valor total en dólares",
        formato_dinero(monedas["USD"]["valor_total"], "USD")
    )

    col2.metric(
        "Valor total en pesos",
        formato_dinero(monedas["COP"]["valor_total"], "COP")
    )

    st.divider()

    # --------------------------------------------------
    # 2. MERCADO DE ACCIONES: KO Y NKE
    # --------------------------------------------------

    st.header("📈 Mercado de acciones")

    st.write(
        "Cotizaciones de mercado de Coca-Cola y Nike "
        "consultadas mediante Yahoo Finance."
    )

    if acciones:

        tabla_mercado = []

        for accion in acciones:
            tabla_mercado.append({
                "Empresa": accion["nombre"],
                "Símbolo": accion["ticker"],
                "Precio actual (USD)": accion["precio_actual"],
                "Cantidad que posees": accion["cantidad"],
                "Valor de tu inversión (USD)": accion["valor_actual"],
                "Dividendo anual por acción (USD)": (
                    accion["dividendo_anual_por_accion"]
                ),
                "Dividendos anuales estimados (USD)": (
                    accion["dividendos_estimados"]
                )
            })

        st.dataframe(
            pd.DataFrame(tabla_mercado),
            width="stretch",
            hide_index=True
        )

        # GRAFICO DE COTIZACIONES

        datos_precios = pd.DataFrame([
            {
                "Empresa": accion["nombre"],
                "Símbolo": accion["ticker"],
                "Precio": accion["precio_actual"]
            }
            for accion in acciones
        ])

        figura_precios = px.bar(
            datos_precios,
            x="Empresa",
            y="Precio",
            color="Símbolo",
            text_auto=".2f",
            title="Precio actual de Coca-Cola y Nike",
            labels={"Precio": "Precio por acción (USD)"}
        )

        figura_precios.update_layout(
            template="plotly_white",
            xaxis_title="Empresa",
            yaxis_title="Precio (USD)"
        )

        st.plotly_chart(
            figura_precios,
            width="stretch"
        )

    else:
        st.warning(
            "No se pudieron consultar las cotizaciones de las acciones."
        )

    st.divider()

    # --------------------------------------------------
    # 3. COMPRAS Y VENTAS DE ACCIONES
    # --------------------------------------------------

    st.header("Registro de compras y ventas")

    with st.form("form_acciones"):

        tipo_operacion = st.selectbox(
            "Tipo de operación",
            ["COMPRA", "VENTA"]
        )

        ticker = st.selectbox(
            "Empresa",
            ["KO - Coca-Cola", "NKE - Nike"]
        )

        ticker = ticker.split(" - ")[0]

        cantidad = st.number_input(
            "Cantidad de acciones",
            min_value=0.01,
            value=1.0,
            step=1.0
        )

        precio = st.number_input(
            "Precio de ejecución por acción (USD)",
            min_value=0.01,
            value=1.0
        )

        comision = st.number_input(
            "Comisión (USD)",
            min_value=0.0,
            value=0.0
        )

        enviar = st.form_submit_button(
            "Registrar operación"
        )

        if enviar:

            try:

                if tipo_operacion == "COMPRA":

                    mensaje = gestor_acciones.registrar_compra(
                        ticker,
                        cantidad,
                        precio,
                        comision
                    )

                else:

                    mensaje = gestor_acciones.registrar_venta(
                        ticker,
                        cantidad,
                        precio,
                        comision
                    )

                st.success(mensaje)
                st.rerun()

            except Exception as error:
                st.error(str(error))

    st.divider()

    # --------------------------------------------------
    # 4. GRAFICO DEL VALOR DE LAS INVERSIONES
    # --------------------------------------------------

    st.header("📊 Valor de las inversiones")

    datos_inversiones = []

    for accion in acciones:

        if accion["valor_actual"] > 0:

            datos_inversiones.append({
                "Inversión": accion["ticker"],
                "Tipo": "Acciones",
                "Valor": accion["valor_actual"],
                "Moneda": accion["moneda"]
            })

    for inversion in inversiones:

        valor = float(inversion.get("valor_estimado", 0))

        if valor > 0:

            datos_inversiones.append({
                "Inversión": inversion["nombre"],
                "Tipo": inversion["tipo"],
                "Valor": valor,
                "Moneda": inversion["moneda"]
            })

    if datos_inversiones:

        datos_grafico = pd.DataFrame(datos_inversiones)

        col1, col2 = st.columns(2)

        for columna, moneda in [(col1, "USD"), (col2, "COP")]:

            with columna:

                st.subheader(f"Inversiones en {moneda}")

                datos_moneda = datos_grafico[
                    datos_grafico["Moneda"] == moneda
                ]

                if not datos_moneda.empty:

                    figura = px.bar(
                        datos_moneda,
                        x="Inversión",
                        y="Valor",
                        color="Tipo",
                        text_auto=".2s",
                        title=f"Valor de inversiones en {moneda}"
                    )

                    figura.update_layout(
                        template="plotly_white",
                        xaxis_title="Inversión",
                        yaxis_title=f"Valor ({moneda})"
                    )

                    st.plotly_chart(
                        figura,
                        width="stretch"
                    )

                else:
                    st.info(
                        f"No hay inversiones registradas en {moneda}."
                    )

    else:
        st.info(
            "Cuando registres compras o inversiones, "
            "aparecerán aquí sus valores."
        )

    st.divider()

    # --------------------------------------------------
    # 5. DISTRIBUCION DEL PORTAFOLIO
    # --------------------------------------------------

    st.header("Distribución del portafolio")

    col1, col2 = st.columns(2)

    for columna, moneda in [(col1, "USD"), (col2, "COP")]:

        acciones_valor = monedas[moneda]["valor_acciones"]
        renta_valor = monedas[moneda]["valor_renta_fija"]

        with columna:

            st.subheader(f"Distribución en {moneda}")

            if acciones_valor + renta_valor > 0:

                datos_pastel = pd.DataFrame({
                    "Tipo de inversión": [
                        "Renta variable",
                        "Renta fija"
                    ],
                    "Valor": [
                        acciones_valor,
                        renta_valor
                    ]
                })

                figura = px.pie(
                    datos_pastel,
                    names="Tipo de inversión",
                    values="Valor",
                    hole=0.45,
                    title=f"Composición en {moneda}"
                )

                figura.update_layout(
                    template="plotly_white"
                )

                st.plotly_chart(
                    figura,
                    width="stretch"
                )

            else:
                st.info(
                    f"No hay inversiones registradas en {moneda}."
                )

    st.divider()

    # --------------------------------------------------
    # 6. RENTABILIDAD
    # --------------------------------------------------

    st.header("Rentabilidad del portafolio")

    col1, col2 = st.columns(2)

    for columna, moneda in [(col1, "USD"), (col2, "COP")]:

        datos = rentabilidad[moneda]

        with columna:

            st.subheader(f"Resultados en {moneda}")

            st.metric(
                "Total invertido",
                formato_dinero(datos["total_invertido"], moneda)
            )

            st.metric(
                "Ganancia o pérdida",
                formato_dinero(datos["ganancia_total"], moneda)
            )

            st.metric(
                "Rentabilidad acumulada",
                f"{datos['rentabilidad_acumulada']:.2f}%"
            )

            anual = datos.get("rentabilidad_efectiva_anual")

            if anual is None:
                texto_anual = "No disponible"
            else:
                texto_anual = f"{anual:.2f}%"

            st.metric(
                "Rentabilidad efectiva anual",
                texto_anual
            )

    # GRAFICO DE RENTABILIDAD

    st.subheader("Comparación de rentabilidad")

    for moneda in ["USD", "COP"]:

        datos = rentabilidad[moneda]

        valores = [
            {
                "Indicador": "Rentabilidad acumulada",
                "Porcentaje": datos["rentabilidad_acumulada"]
            }
        ]

        anual = datos.get("rentabilidad_efectiva_anual")

        if anual is not None:

            valores.append({
                "Indicador": "Rentabilidad efectiva anual",
                "Porcentaje": anual
            })

        figura = px.bar(
            pd.DataFrame(valores),
            x="Indicador",
            y="Porcentaje",
            text_auto=".2f",
            title=f"Rentabilidad en {moneda}"
        )

        figura.update_layout(
            template="plotly_white",
            showlegend=False,
            yaxis_title="Rentabilidad (%)"
        )

        st.plotly_chart(
            figura,
            width="stretch"
        )

    st.divider()

    # --------------------------------------------------
    # 7. RENTA FIJA: CDT, BONOS Y TES
    # --------------------------------------------------

    st.header("🏦 Inversiones de renta fija")

    if inversiones:
        mostrar_tabla(inversiones)
    else:
        st.info("Todavía no tienes inversiones de renta fija.")

    with st.expander("Registrar CDT, bono o TES"):

        with st.form("form_renta_fija"):

            tipo = st.selectbox(
                "Tipo de inversión",
                ["CDT", "BONO", "TES"]
            )

            nombre = st.text_input(
                "Nombre de la inversión"
            )

            capital = st.number_input(
                "Capital invertido",
                min_value=1.0,
                value=1000000.0,
                step=100000.0
            )

            tasa = st.number_input(
                "Tasa efectiva anual (%)",
                min_value=0.0,
                value=10.0,
                step=0.5
            )

            moneda = st.selectbox(
                "Moneda de la inversión",
                ["COP", "USD"]
            )

            fecha_inicio = st.date_input(
                "Fecha de inicio",
                value=date.today()
            )

            fecha_vencimiento = st.date_input(
                "Fecha de vencimiento",
                value=date.today() + timedelta(days=365)
            )

            frecuencia = st.selectbox(
                "Frecuencia de pago",
                [
                    "MENSUAL",
                    "TRIMESTRAL",
                    "SEMESTRAL",
                    "ANUAL",
                    "AL_VENCIMIENTO"
                ]
            )

            enviar = st.form_submit_button(
                "Guardar inversión"
            )

            if enviar:

                try:

                    if not nombre.strip():
                        raise ValueError(
                            "Debes ingresar el nombre de la inversión."
                        )

                    if fecha_vencimiento <= fecha_inicio:
                        raise ValueError(
                            "La fecha de vencimiento debe ser posterior "
                            "a la fecha de inicio."
                        )

                    identificador = gestor_renta_fija.registrar_inversion(
                        tipo=tipo,
                        nombre=nombre,
                        capital=capital,
                        tasa_ea=tasa / 100,
                        fecha_inicio=fecha_inicio,
                        fecha_vencimiento=fecha_vencimiento,
                        moneda=moneda,
                        frecuencia_pago=frecuencia
                    )

                    st.success(
                        f"Inversión registrada correctamente. "
                        f"Identificador: {identificador}"
                    )

                    st.rerun()

                except Exception as error:
                    st.error(str(error))

    # --------------------------------------------------
    # 8. PAGOS DE RENTA FIJA
    # --------------------------------------------------

    st.subheader("Registro de pagos de renta fija")

    try:
        inversiones_bd = base_datos.obtener_inversiones_fijas()

    except Exception as error:
        inversiones_bd = []
        st.error(f"No se pudieron consultar las inversiones: {error}")

    if inversiones_bd:

        opciones = {
            inversion["id"]: (
                f"{inversion['nombre']} "
                f"(ID {inversion['id']})"
            )
            for inversion in inversiones_bd
        }

        with st.form("form_pagos"):

            inversion_id = st.selectbox(
                "Selecciona la inversión",
                list(opciones.keys()),
                format_func=lambda x: opciones[x]
            )

            tipo_pago = st.selectbox(
                "Tipo de pago",
                ["INTERES", "PAGO_CAPITAL"]
            )

            monto = st.number_input(
                "Monto recibido",
                min_value=0.01,
                value=10000.0
            )

            fecha_pago = st.date_input(
                "Fecha del pago",
                value=date.today()
            )

            descripcion = st.text_input(
                "Descripción"
            )

            enviar = st.form_submit_button(
                "Registrar pago"
            )

            if enviar:

                try:

                    mensaje = gestor_renta_fija.registrar_pago(
                        inversion_id=inversion_id,
                        tipo=tipo_pago,
                        monto=monto,
                        fecha=fecha_pago,
                        descripcion=descripcion
                    )

                    st.success(mensaje)
                    st.rerun()

                except Exception as error:
                    st.error(str(error))

    else:
        st.info(
            "Registra primero un CDT, bono o TES para agregar pagos."
        )

    st.divider()

    # --------------------------------------------------
    # 9. DIVIDENDOS
    # --------------------------------------------------

    st.header("💰 Dividendos de acciones")

    with st.expander("Registrar dividendo recibido"):

        with st.form("form_dividendos"):

            ticker_dividendo = st.selectbox(
                "Acción",
                ["KO", "NKE"]
            )

            monto_dividendo = st.number_input(
                "Monto recibido (USD)",
                min_value=0.01,
                value=1.0
            )

            fecha_dividendo = st.date_input(
                "Fecha del dividendo",
                value=date.today()
            )

            descripcion_dividendo = st.text_input(
                "Descripción del dividendo"
            )

            enviar = st.form_submit_button(
                "Guardar dividendo"
            )

            if enviar:

                try:

                    mensaje = gestor_dividendos.registrar_dividendo(
                        ticker=ticker_dividendo,
                        monto=monto_dividendo,
                        fecha=fecha_dividendo,
                        descripcion=descripcion_dividendo
                    )

                    st.success(mensaje)
                    st.rerun()

                except Exception as error:
                    st.error(str(error))

    st.subheader("Estimación anual de dividendos")

    try:

        dividendos = gestor_dividendos.obtener_estimacion_anual()

        if dividendos:
            mostrar_tabla(dividendos)
        else:
            st.info(
                "Compra acciones para generar una estimación "
                "de dividendos según las cantidades que poseas."
            )

    except Exception as error:
        st.warning(
            f"No se pudieron consultar los dividendos: {error}"
        )

    st.metric(
        "Dividendos anuales estimados (USD)",
        formato_dinero(
            resumen["dividendos_estimados_anuales_usd"],
            "USD"
        )
    )

    st.divider()

    # --------------------------------------------------
    # 10. PROYECCION A UN AÑO
    # --------------------------------------------------

    st.header("🔮 Proyección de rentabilidad a un año")

    st.write(
        "Estimación basada en el comportamiento histórico de las "
        "acciones, sus dividendos y las tasas de las inversiones "
        "de renta fija registradas."
    )

    if st.button("Calcular proyección anual"):

        try:

            proyeccion = proyeccion_servicio.proyectar()

            for moneda in ["USD", "COP"]:

                datos = proyeccion["totales"][moneda]

                st.subheader(f"Proyección en {moneda}")

                col1, col2, col3 = st.columns(3)

                col1.metric(
                    "Valor actual",
                    formato_dinero(
                        datos["valor_actual"],
                        moneda
                    )
                )

                col2.metric(
                    "Valor proyectado",
                    formato_dinero(
                        datos["valor_proyectado"],
                        moneda
                    )
                )

                col3.metric(
                    "Ganancia estimada",
                    formato_dinero(
                        datos["ganancia_proyectada"],
                        moneda
                    )
                )

                st.metric(
                    "Rentabilidad proyectada",
                    f"{datos['rentabilidad_proyectada']:.2f}%"
                )

            if proyeccion["acciones"]:

                st.subheader("Proyección de acciones")
                mostrar_tabla(proyeccion["acciones"])

            if proyeccion["renta_fija"]:

                st.subheader("Proyección de renta fija")
                mostrar_tabla(proyeccion["renta_fija"])

            for error in proyeccion["errores"]:
                st.warning(error)

            st.info(proyeccion["aclaracion"])

        except Exception as error:
            st.error(
                f"No se pudo calcular la proyección: {error}"
            )

    # --------------------------------------------------
    # 11. ERRORES DE ACTUALIZACION
    # --------------------------------------------------

    if resumen["errores_actualizacion"]:

        st.warning(
            "Algunas cotizaciones no pudieron actualizarse:"
        )

        for error in resumen["errores_actualizacion"]:
            st.write(f"- {error}")

    # --------------------------------------------------
    # PIE DE PAGINA
    # --------------------------------------------------

    st.divider()

    st.caption(
        "Seguimiento de portafolio de inversión | "
        "Datos bursátiles consultados mediante Yahoo Finance. "
        "Las proyecciones son estimaciones y no garantizan rendimientos."
    )


if __name__ == "__main__":
    mostrar_dashboard()
