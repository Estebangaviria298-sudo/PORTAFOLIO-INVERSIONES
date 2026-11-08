
import os
import tempfile

from servicios.base_datos import BaseDatos
from servicios.gestor_renta_fija import GestorRentaFija


def probar_renta_fija():

    with tempfile.TemporaryDirectory() as carpeta:

        db = BaseDatos.__new__(BaseDatos)
        db.ruta = os.path.join(carpeta, "prueba.db")
        db.crear_tablas()

        gestor = GestorRentaFija.__new__(GestorRentaFija)
        gestor.base_datos = db

        identificador = gestor.registrar_inversion(
            tipo="CDT",
            nombre="CDT de prueba",
            capital=1000000,
            tasa_ea=0.12,
            fecha_inicio="2026-01-01",
            fecha_vencimiento="2027-01-01",
            moneda="COP",
            frecuencia_pago="SEMESTRAL"
        )

        print("Inversión registrada:", identificador)

        resumen_inicial = gestor.obtener_resumen_inversion(
            identificador
        )

        assert resumen_inicial["capital_pendiente"] == 1000000

        gestor.registrar_pago(
            identificador,
            "INTERES",
            20000,
            fecha="2026-06-01",
            descripcion="Primer pago de intereses"
        )

        gestor.registrar_pago(
            identificador,
            "PAGO_CAPITAL",
            100000,
            fecha="2026-06-01",
            descripcion="Abono parcial de capital"
        )

        resumen = gestor.obtener_resumen_inversion(
            identificador
        )

        print("\nRESUMEN DE LA INVERSIÓN")
        print(resumen)

        assert resumen["capital_inicial"] == 1000000
        assert resumen["capital_pendiente"] == 900000
        assert resumen["intereses_pendientes"] >= 0
        assert resumen["valor_estimado"] >= 900000

        print("\nTODAS LAS PRUEBAS FUERON SUPERADAS.")


if __name__ == "__main__":
    probar_renta_fija()
