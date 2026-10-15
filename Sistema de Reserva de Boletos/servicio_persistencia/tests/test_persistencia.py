"""Pruebas con PostgreSQL real; cada prueba usa y elimina su propio esquema."""

from concurrent.futures import ThreadPoolExecutor
import os
import socket
import subprocess
import sys
import time
import unittest
import uuid

from psycopg import sql
from psycopg.conninfo import make_conninfo
import zmq

from persistencia.base_datos import conectar, crear_esquema, cargar_datos
from persistencia.cliente import enviar_peticion, consultar, reservar, modificar, cancelar
from persistencia.operaciones import procesar

URL = os.environ.get("SRB_TEST_DATABASE_URL")


@unittest.skipUnless(URL, "Defina SRB_TEST_DATABASE_URL o ejecute probar_con_docker.py")
class PruebasPersistencia(unittest.TestCase):
    def setUp(self):
        self.esquema = "prueba_" + uuid.uuid4().hex
        self.admin = conectar(URL)
        self.admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.esquema)))
        self.url = make_conninfo(URL, options=f"-c search_path={self.esquema}")
        self.conexion = conectar(self.url)
        crear_esquema(self.conexion)
        cargar_datos(self.conexion, eventos=3, dobles=1, capacidad=10)

    def tearDown(self):
        self.conexion.close()
        self.admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.esquema)))
        self.admin.close()

    def peticion(self, operacion, **datos):
        return procesar(self.conexion, {"id": str(uuid.uuid4()), "operacion": operacion, **datos})

    def crear_reserva(self, cantidad=3, evento="E1", ocurrencia=1, cliente=1):
        respuesta = self.peticion("reserva", id_cliente=cliente, id_evento=evento,
                                  ocurrencia=ocurrencia, cantidad_asientos=cantidad)
        self.assertTrue(respuesta["ok"], respuesta)
        return respuesta["datos"]["reserva"]["id_reserva"]

    def estado(self):
        return {tabla: self.conexion.execute(f"SELECT * FROM {tabla} ORDER BY 1, 2").fetchall()
                for tabla in ("ocurrencias", "reservas")}

    def test_consultas_eventos_disponibilidad_y_reserva(self):
        datos = self.peticion("consulta", mes="2026-10")["datos"]
        self.assertEqual(len(datos["ocurrencias"]), 4)
        self.assertEqual(self.peticion("consulta", mes="2026-11")["datos"]["ocurrencias"], [])
        self.assertEqual(self.peticion("consulta", mes="octubre")["codigo"], "MES_INVALIDO")
        id_reserva = self.crear_reserva()
        reserva = self.peticion("consulta", tipo="reserva", id_cliente=1, id_reserva=id_reserva)
        self.assertEqual(reserva["datos"]["reserva"]["cantidad_asientos"], 3)
        self.assertEqual(reserva["datos"]["reserva"]["fecha"], "2026-10-01")
        disponibilidad = self.peticion("consulta", tipo="disponibilidad", id_evento="E1", ocurrencia=1)
        self.assertEqual(disponibilidad["datos"]["ocurrencia"]["libres"], 7)

    def test_validaciones_y_falta_cupo_no_cambian_datos(self):
        self.crear_reserva(9)
        antes = self.estado()
        for cantidad in (0, -1, True, 1.5, "2", None, 2147483648):
            respuesta = self.peticion("reserva", id_cliente=1, id_evento="E1", ocurrencia=1,
                                      cantidad_asientos=cantidad)
            self.assertEqual(respuesta["codigo"], "DATOS_INVALIDOS")
        self.assertEqual(self.peticion("reserva", id_cliente=1, id_evento="E1", ocurrencia=1,
                                      cantidad_asientos=2)["codigo"], "SIN_CUPO")
        self.assertEqual(self.peticion("reserva", id_cliente=1, id_evento="E99", ocurrencia=1,
                                      cantidad_asientos=1)["codigo"], "OCURRENCIA_NO_ENCONTRADA")
        self.assertEqual(antes, self.estado())

    def test_modificar_cantidad_y_fecha(self):
        reserva = self.crear_reserva()
        for cantidad in (5, 2):
            cambio = self.peticion("modificacion", id_cliente=1, id_reserva=reserva, cantidad_asientos=cantidad)
            self.assertTrue(cambio["ok"], cambio)
            self.assertEqual(cambio["datos"]["libres"], 10 - cantidad)
        cambio = self.peticion("modificacion", id_cliente=1, id_reserva=reserva, ocurrencia=2)
        self.assertTrue(cambio["ok"], cambio)
        self.assertEqual(cambio["datos"]["reserva"]["cantidad_asientos"], 2)
        self.assertEqual(cambio["datos"]["reserva"]["fecha"], "2026-10-02")
        filas = self.conexion.execute("SELECT ocupados FROM ocurrencias WHERE id_evento='E1' ORDER BY numero").fetchall()
        self.assertEqual([f["ocupados"] for f in filas], [0, 2])

    def test_modificacion_rechazada_conserva_reserva(self):
        reserva = self.crear_reserva(3)
        self.crear_reserva(9, ocurrencia=2)
        antes = self.estado()
        for cambio, codigo in (({"cantidad_asientos": 11}, "SIN_CUPO"),
                               ({"ocurrencia": 2}, "SIN_CUPO"),
                               ({"ocurrencia": 99}, "OCURRENCIA_NO_ENCONTRADA"),
                               ({"ocurrencia": 2, "cantidad_asientos": 2}, "CAMBIO_INVALIDO"),
                               ({"id_evento": "E2", "ocurrencia": 1}, "CAMBIO_INVALIDO")):
            respuesta = self.peticion("modificacion", id_cliente=1, id_reserva=reserva, **cambio)
            self.assertEqual(respuesta["codigo"], codigo)
            self.assertEqual(antes, self.estado())

    def test_fecha_rechaza_otro_mes_y_anio(self):
        reserva = self.crear_reserva()
        for numero, fecha in ((3, "2026-11-01"), (4, "2027-10-01")):
            self.conexion.execute("INSERT INTO ocurrencias VALUES ('E1', %s, %s, 10, 0)", (numero, fecha))
            antes = self.estado()
            cambio = self.peticion("modificacion", id_cliente=1, id_reserva=reserva, ocurrencia=numero)
            self.assertEqual(cambio["codigo"], "CAMBIO_INVALIDO")
            self.assertEqual(antes, self.estado())

    def test_evento_con_una_ocurrencia_permite_cantidad(self):
        reserva = self.crear_reserva(evento="E2")
        self.assertTrue(self.peticion("modificacion", id_cliente=1, id_reserva=reserva,
                                     cantidad_asientos=7)["ok"])
        self.assertFalse(self.peticion("modificacion", id_cliente=1, id_reserva=reserva, ocurrencia=2)["ok"])

    def test_propiedad_reserva_y_cancelacion_una_sola_vez(self):
        reserva = self.crear_reserva()
        antes = self.estado()
        for operacion, datos in (("consulta", {"tipo": "reserva"}),
                                 ("modificacion", {"cantidad_asientos": 5}), ("cancelacion", {})):
            respuesta = self.peticion(operacion, id_cliente=2, id_reserva=reserva, **datos)
            self.assertEqual(respuesta["codigo"], "RESERVA_NO_ENCONTRADA")
            self.assertEqual(antes, self.estado())
        cancelacion = self.peticion("cancelacion", id_cliente=1, id_reserva=reserva)
        self.assertTrue(cancelacion["ok"])
        self.assertEqual(cancelacion["datos"]["asientos_liberados"], 3)
        self.assertEqual(cancelacion["datos"]["libres"], 10)
        despues = self.estado()
        self.assertEqual(despues["reservas"], [])
        self.assertEqual(self.peticion("cancelacion", id_cliente=1, id_reserva=reserva)["codigo"],
                         "RESERVA_NO_ENCONTRADA")
        self.assertEqual(despues, self.estado())

    def test_rollback_si_falla_escritura_despues_de_ocupar(self):
        # Fuerza un error real de BD después de UPDATE ocupados, durante INSERT reserva.
        self.conexion.execute("ALTER TABLE reservas ADD CONSTRAINT fallo_prueba CHECK (cantidad_asientos < 3)")
        antes = self.estado()
        respuesta = self.peticion("reserva", id_cliente=1, id_evento="E1", ocurrencia=1, cantidad_asientos=3)
        self.assertEqual(respuesta["codigo"], "ERROR_BD")
        self.assertEqual(antes, self.estado())
        self.crear_reserva(2)  # La conexión debe seguir sirviendo después del rollback.

    def test_concurrencia_con_conexiones_reales_no_sobrevende(self):
        def reservar_uno(indice):
            with conectar(self.url) as conexion:
                return procesar(conexion, {"id": f"concurrente-{indice}", "operacion": "reserva",
                                          "id_cliente": indice + 1, "id_evento": "E1",
                                          "ocurrencia": 1, "cantidad_asientos": 1})
        with ThreadPoolExecutor(max_workers=20) as grupo:
            respuestas = list(grupo.map(reservar_uno, range(20)))
        self.assertEqual(sum(r["ok"] for r in respuestas), 10)
        self.assertEqual(sum(r["codigo"] == "SIN_CUPO" for r in respuestas), 10)
        self.assertEqual(sum(f["cantidad_asientos"] for f in self.estado()["reservas"]), 10)

    def test_dos_cancelaciones_simultaneas_liberan_una_vez(self):
        reserva = self.crear_reserva()
        def cancelar_una(indice):
            with conectar(self.url) as conexion:
                return procesar(conexion, {"id": str(indice), "operacion": "cancelacion",
                                          "id_cliente": 1, "id_reserva": reserva})
        with ThreadPoolExecutor(max_workers=2) as grupo:
            respuestas = list(grupo.map(cancelar_una, range(2)))
        self.assertEqual(sum(r["ok"] for r in respuestas), 1)
        self.assertTrue(all(f["ocupados"] == 0 for f in self.estado()["ocurrencias"]))

    def test_confirmacion_visible_desde_otra_conexion(self):
        reserva = self.crear_reserva()
        with conectar(self.url) as otra:
            self.assertEqual(otra.execute("SELECT cantidad_asientos FROM reservas WHERE id_reserva=%s",
                                         (reserva,)).fetchone()["cantidad_asientos"], 3)

    def test_zmq_cuatro_operaciones_y_respuestas_al_emisor_correcto(self):
        with socket.socket() as temporal:
            temporal.bind(("127.0.0.1", 0))
            direccion = f"tcp://127.0.0.1:{temporal.getsockname()[1]}"
        entorno = {**os.environ, "SRB_DATABASE_URL": self.url}
        proceso = subprocess.Popen([sys.executable, "-m", "persistencia.servidor", "--bind", direccion],
                                   env=entorno, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            limite = time.monotonic() + 10
            while True:
                respuesta = enviar_peticion({"operacion": "consulta", "mes": "2026-10"}, direccion, 500)
                if respuesta["ok"]:
                    break
                if proceso.poll() is not None or time.monotonic() >= limite:
                    self.fail("No arrancó el servidor de persistencia")
            datos = reservar({"id_cliente": 1, "id_evento": "E1", "ocurrencia": 1,
                              "cantidad_asientos": 3}, direccion)
            self.assertTrue(datos["ok"], datos)
            referencia = {"id_cliente": 1, "id_reserva": datos["datos"]["reserva"]["id_reserva"]}
            self.assertTrue(consultar({**referencia, "tipo": "reserva"}, direccion)["ok"])
            self.assertTrue(modificar({**referencia, "ocurrencia": 2}, direccion)["ok"])
            self.assertTrue(cancelar(referencia, direccion)["ok"])
            # JSON roto y no-objeto deben obtener error y dejar el servidor funcionando.
            with zmq.Context() as contexto, contexto.socket(zmq.REQ) as canal:
                canal.setsockopt(zmq.LINGER, 0)
                canal.setsockopt(zmq.RCVTIMEO, 2000)
                canal.connect(direccion)
                for mensaje in (b'{invalido', b'[1, 2]'):
                    canal.send(mensaje)
                    self.assertEqual(canal.recv_json()["codigo"], "MENSAJE_INVALIDO")
            def consultar_uno(indice):
                mensaje = {"id": f"consulta-{indice}", "operacion": "consulta", "mes": "2026-10"}
                return enviar_peticion(mensaje, direccion)
            with ThreadPoolExecutor(max_workers=10) as grupo:
                respuestas = list(grupo.map(consultar_uno, range(10)))
            for indice, respuesta in enumerate(respuestas):
                self.assertTrue(respuesta["ok"])
                self.assertEqual(respuesta["id"], f"consulta-{indice}")
            # Ejecutar también el ejemplo que se entrega al grupo.
            demo = subprocess.run([sys.executable, "demo_servicios.py", "--direccion", direccion],
                                  capture_output=True, text=True, timeout=30)
            self.assertEqual(demo.returncode, 0, demo.stdout + demo.stderr)
        finally:
            proceso.terminate()
            proceso.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
