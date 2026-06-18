#!/usr/bin/env python3
# =====================================================================
# test_webhook_provisioner.py — Proyecto TeleSecure, Fase 3
#
# Tests unitarios (unittest) de la CAPA DE FORMATEO del webhook:
# valida que los datos se normalicen, saneen y estructuren
# correctamente ANTES de tocar la base de datos de FreePBX.
#
# Ejecutar:  python3 -m unittest test_webhook_provisioner -v
# =====================================================================

import unittest

from webhook_provisioner import (
    CONTEXTO_POR_DEFECTO,
    EXTENSION_MAX,
    EXTENSION_MIN,
    construir_payload_extension,
    filas_pjsip_para_sip_table,
    generar_secret_sip,
    sanear_nombre,
    validar_extension,
    validar_oid,
)

OID_VALIDO = "3f2504e0-4f89-11d3-9a0c-0305e82c3301"


class TestValidarExtension(unittest.TestCase):
    """La extensión debe ser numérica y estar dentro del rango."""

    def test_extension_valida_como_string(self):
        self.assertEqual(validar_extension("1001"), "1001")

    def test_extension_valida_como_entero(self):
        self.assertEqual(validar_extension(1500), "1500")

    def test_extension_con_espacios_se_normaliza(self):
        self.assertEqual(validar_extension("  1001  "), "1001")

    def test_rechaza_letras(self):
        with self.assertRaises(ValueError):
            validar_extension("10a1")

    def test_rechaza_inyeccion_sql(self):
        with self.assertRaises(ValueError):
            validar_extension("1001; DROP TABLE devices;--")

    def test_rechaza_fuera_de_rango_inferior(self):
        with self.assertRaises(ValueError):
            validar_extension(str(EXTENSION_MIN - 1))

    def test_rechaza_fuera_de_rango_superior(self):
        with self.assertRaises(ValueError):
            validar_extension(str(EXTENSION_MAX + 1))


class TestSanearNombre(unittest.TestCase):
    """El nombre debe quedar seguro para los archivos generados por FreePBX."""

    def test_nombre_normal_no_cambia(self):
        self.assertEqual(sanear_nombre("Saul Janampa"), "Saul Janampa")

    def test_elimina_caracteres_peligrosos_para_asterisk(self):
        # ; inicia comentario en .conf, [] abren secciones, comillas rompen valores
        self.assertEqual(
            sanear_nombre('Sa;ul "J[ana]mpa\''),
            "Saul Janampa",
        )

    def test_colapsa_espacios_multiples(self):
        self.assertEqual(sanear_nombre("Saul    Janampa"), "Saul Janampa")

    def test_trunca_a_50_caracteres(self):
        self.assertEqual(len(sanear_nombre("X" * 120)), 50)

    def test_rechaza_nombre_vacio(self):
        with self.assertRaises(ValueError):
            sanear_nombre("   ")

    def test_conserva_tildes_y_enie(self):
        self.assertEqual(sanear_nombre("José Ñahui"), "José Ñahui")


class TestValidarOid(unittest.TestCase):
    """El OID de midPoint debe ser un UUID bien formado."""

    def test_oid_valido(self):
        self.assertEqual(validar_oid(OID_VALIDO), OID_VALIDO)

    def test_oid_se_normaliza_a_minusculas(self):
        self.assertEqual(validar_oid(OID_VALIDO.upper()), OID_VALIDO)

    def test_rechaza_oid_truncado(self):
        with self.assertRaises(ValueError):
            validar_oid(OID_VALIDO[:-1])

    def test_rechaza_oid_vacio(self):
        with self.assertRaises(ValueError):
            validar_oid("")


class TestGenerarSecretSip(unittest.TestCase):
    """El secret SIP debe cumplir la política de contraseñas (A.5.17)."""

    def test_longitud_por_defecto(self):
        self.assertEqual(len(generar_secret_sip()), 24)

    def test_contiene_mayuscula_minuscula_y_digito(self):
        s = generar_secret_sip()
        self.assertTrue(any(c.islower() for c in s))
        self.assertTrue(any(c.isupper() for c in s))
        self.assertTrue(any(c.isdigit() for c in s))

    def test_solo_caracteres_seguros_para_asterisk(self):
        s = generar_secret_sip()
        self.assertTrue(s.isalnum(), "El secret no debe llevar símbolos "
                                     "conflictivos con los .conf de Asterisk")

    def test_no_se_repite(self):
        self.assertNotEqual(generar_secret_sip(), generar_secret_sip())

    def test_rechaza_longitud_debil(self):
        with self.assertRaises(ValueError):
            generar_secret_sip(8)


class TestConstruirPayloadExtension(unittest.TestCase):
    """La frontera de calidad: todo lo que va a la BD pasa por aquí."""

    def _payload(self, **overrides):
        base = dict(
            oid=OID_VALIDO,
            nombre="  María   Quispe; ",
            correo="  MQuispe@Hospital.PE ",
            extension=" 1002 ",
            secret="Abc123Abc123Abc123Abc123",
        )
        base.update(overrides)
        return construir_payload_extension(**base)

    def test_payload_completo_y_normalizado(self):
        p = self._payload()
        self.assertEqual(p["midpoint_oid"], OID_VALIDO)
        self.assertEqual(p["nombre"], "María Quispe")
        self.assertEqual(p["correo"], "mquispe@hospital.pe")
        self.assertEqual(p["extension"], "1002")
        self.assertEqual(p["contexto"], CONTEXTO_POR_DEFECTO)

    def test_correo_ausente_queda_none(self):
        self.assertIsNone(self._payload(correo=None)["correo"])

    def test_propaga_error_de_extension_invalida(self):
        with self.assertRaises(ValueError):
            self._payload(extension="abc")

    def test_propaga_error_de_oid_invalido(self):
        with self.assertRaises(ValueError):
            self._payload(oid="no-es-un-oid")


class TestFilasPjsipParaSipTable(unittest.TestCase):
    """Las filas keyword/data deben tener la forma exacta que FreePBX espera."""

    def setUp(self):
        self.filas = filas_pjsip_para_sip_table("1003", "SecretoXYZ123")

    def test_todas_las_filas_apuntan_a_la_extension(self):
        self.assertTrue(all(f[0] == "1003" for f in self.filas))

    def test_estructura_de_cuatro_columnas(self):
        # (id, keyword, data, flags) -> formato de executemany
        self.assertTrue(all(len(f) == 4 for f in self.filas))

    def test_incluye_el_secret(self):
        kv = {f[1]: f[2] for f in self.filas}
        self.assertEqual(kv["secret"], "SecretoXYZ123")

    def test_contexto_correcto(self):
        kv = {f[1]: f[2] for f in self.filas}
        self.assertEqual(kv["context"], CONTEXTO_POR_DEFECTO)

    def test_flags_son_indices_consecutivos(self):
        self.assertEqual([f[3] for f in self.filas],
                         list(range(len(self.filas))))

    def test_keywords_sin_duplicados(self):
        keywords = [f[1] for f in self.filas]
        self.assertEqual(len(keywords), len(set(keywords)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
