"""Pruebas locales del contrato y de la cadena completa, sobre PostgreSQL temporal.

Ejecutar: python -m unittest discover -s tests -v
La BD usa un puerto libre y memoria del contenedor. No toca compose ni la base
srb del usuario. Los servidores probados son los mismos main.py del proyecto.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from datetime import date
import io
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import uuid

from comun import mensajes as msjs

RAIZ = Path(__file__).resolve().parents[1]


class PruebasContrato(unittest.TestCase):
    def test_uuid_y_serializacion(self):
        peticion = msjs.crear_req('CO', 1, {'mes': 'noviembre'})
        self.assertEqual(msjs.decodificar(msjs.codificar(peticion)), peticion)
        msjs.validar_peticion(peticion)
        respuesta = msjs.crear_rta('E', None, {}, peticion['uuid'])
        self.assertEqual(respuesta['uuid'], peticion['uuid'])
        self.assertEqual(respuesta['estado'], 'EXITO')
        with self.assertRaises(ValueError):
            msjs.crear_req('CO', True, {})
        with self.assertRaises(ValueError):
            msjs.validar_peticion([])

    def test_importar_consumidores_no_inicia_carga(self):
        resultado = subprocess.run(
            [sys.executable, '-c', 'import capa_consumidores.main; import capa_consumidores.carga_clientes'],
            cwd=RAIZ, capture_output=True, text=True, timeout=5,
        )
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        self.assertEqual(resultado.stdout, '')


class PruebasTresCapas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('docker'):
            raise unittest.SkipTest('La integración necesita Docker para PostgreSQL temporal')
        disponible = subprocess.run(['docker', 'info'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if disponible.returncode:
            raise unittest.SkipTest('El servicio Docker no está disponible')
        import psycopg
        cls.temporal = tempfile.TemporaryDirectory(prefix='srb-pruebas-')
        cls.directorio = Path(cls.temporal.name)
        cls.procesos = {}
        cls.logs = {}
        cls.contenedor = 'srb-tres-capas-prueba-' + uuid.uuid4().hex[:10]
        cls.creado = False
        cls.entorno_anterior = dict(os.environ)
        cls.addClassCleanup(cls.limpiar)
        clave = secrets.token_hex(16)
        subprocess.run(
            ['docker', 'run', '--rm', '-d', '--name', cls.contenedor,
             '-p', '127.0.0.1::5432', '--tmpfs', '/var/lib/postgresql/data',
             '-e', 'POSTGRES_USER=srb', '-e', 'POSTGRES_DB=srb_pruebas', '-e', 'POSTGRES_PASSWORD', 'postgres:16'],
            env={**os.environ, 'POSTGRES_PASSWORD': clave}, check=True, capture_output=True,
        )
        cls.creado = True
        puerto_bd = subprocess.check_output(['docker', 'port', cls.contenedor, '5432/tcp'], text=True).strip().rsplit(':', 1)[1]
        limite = time.monotonic() + 30
        while True:
            try:
                with psycopg.connect(host='127.0.0.1', port=puerto_bd, user='srb',
                                     password=clave, dbname='srb_pruebas', connect_timeout=1):
                    break
            except psycopg.OperationalError:
                if time.monotonic() > limite:
                    raise RuntimeError('No arrancó PostgreSQL de pruebas')
                time.sleep(.1)
        # Reservar puertos libres y liberarlos justo antes de arrancar los servidores.
        reservados = []
        for _ in range(3):
            canal = socket.socket()
            canal.bind(('127.0.0.1', 0))
            reservados.append(canal)
        cli, rmc, persistencia = [str(c.getsockname()[1]) for c in reservados]
        for canal in reservados:
            canal.close()
        cls.entorno = {
            **os.environ, 'PYTHONUNBUFFERED': '1',
            'HOST_CAPA_CONSUMIDORES': '127.0.0.1',
            'HOST_CAPA_SERVICIOS': '127.0.0.1', 'HOST_CAPA_PERSISTENCIA': '127.0.0.1',
            'GT_PUERTO_CLIENTES': cli, 'GT_PUERTO_RMC': rmc, 'SP_PUERTO': persistencia,
            'DB_URL': f'postgresql+psycopg://srb:{clave}@127.0.0.1:{puerto_bd}/srb_pruebas',
            'TIMEOUT_PERSISTENCIA_MS': '300', 'TIMEOUT_CLIENTE_MS': '2000',
        }
        # Configurar antes de importar módulos que crean el engine/leen comun.config.
        os.environ.update(cls.entorno)
        from capa_persistencia.conexion_bd import engine
        from capa_persistencia.cargar_datos import generar, cargar
        cls.engine = engine
        cls.archivo_datos = cls.directorio / 'eventos.json'
        with redirect_stdout(io.StringIO()):
            generar(str(cls.archivo_datos))
            cargar(str(cls.archivo_datos))
        cls.arrancar('persistencia', ['-m', 'capa_persistencia.main'])
        cls.arrancar('gt', ['-m', 'capa_servicios.main', 'gt'])
        cls.arrancar('rmc', ['-m', 'capa_servicios.main', 'rmc'])
        cls.esperar_cadena()

    @classmethod
    def arrancar(cls, nombre, argumentos):
        if nombre not in cls.logs:
            cls.logs[nombre] = open(cls.directorio / f'{nombre}.log', 'w+')
        cls.procesos[nombre] = subprocess.Popen([sys.executable, *argumentos], cwd=RAIZ,
                                               env=cls.entorno, stdout=cls.logs[nombre], stderr=subprocess.STDOUT)

    @classmethod
    def esperar_cadena(cls):
        from capa_consumidores.cliente import Cliente
        limite = time.monotonic() + 12
        while time.monotonic() < limite:
            for nombre, proceso in cls.procesos.items():
                if proceso.poll() is not None:
                    cls.logs[nombre].flush()
                    raise RuntimeError(f"Se detuvo {nombre}: " + (cls.directorio / f'{nombre}.log').read_text())
            cliente = Cliente(1)
            cliente.conectar_con_gt()
            try:
                respuesta = cliente.consultar_evento('noviembre', 2026)
                if respuesta['estado'] == 'EXITO':
                    return
            finally:
                cliente.cerrar_socket()
                cliente.terminar_contexto()
            time.sleep(.1)
        raise RuntimeError('La cadena cliente-GT-RMC-persistencia no respondió')

    @classmethod
    def limpiar(cls):
        for proceso in cls.procesos.values():
            if proceso.poll() is None:
                proceso.terminate()
        for proceso in cls.procesos.values():
            try:
                proceso.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proceso.kill()
                proceso.wait()
        for archivo in cls.logs.values():
            archivo.close()
        if hasattr(cls, 'engine'):
            cls.engine.dispose()
        if cls.creado:
            subprocess.run(['docker', 'stop', '--time', '2', cls.contenedor],
                           check=True, capture_output=True)
        os.environ.clear()
        os.environ.update(cls.entorno_anterior)
        cls.temporal.cleanup()

    def setUp(self):
        from sqlalchemy import text
        from capa_persistencia.cargar_datos import cargar
        # Borrar solo en el contenedor temporal creado por esta clase.
        with self.engine.begin() as conexion:
            conexion.execute(text('TRUNCATE reserva, ocurrencia, evento RESTART IDENTITY CASCADE'))
        with redirect_stdout(io.StringIO()):
            cargar(str(self.archivo_datos))

    def cliente(self, identificador=1):
        from capa_consumidores.cliente import Cliente
        cliente = Cliente(identificador)
        cliente.conectar_con_gt()
        self.addCleanup(cliente.terminar_contexto)
        self.addCleanup(cliente.cerrar_socket)
        return cliente

    def estado(self):
        from sqlalchemy import text
        with self.engine.connect() as conexion:
            return {tabla: conexion.execute(text(f'SELECT * FROM {tabla} ORDER BY id')).mappings().all()
                    for tabla in ('evento', 'ocurrencia', 'reserva')}

    def test_datos_iniciales_y_consultas(self):
        datos = self.estado()
        self.assertEqual(len(datos['evento']), 50)
        self.assertEqual(len(datos['ocurrencia']), 70)
        self.assertEqual(datos['reserva'], [])
        self.assertTrue(all(o['capacidad'] == 100 and o['puestos_ocupados'] == 0 for o in datos['ocurrencia']))
        cliente = self.cliente()
        respuesta = cliente.consultar_evento('noviembre', 2026)
        self.assertEqual(respuesta['estado'], 'EXITO')
        self.assertEqual(len(respuesta['datos']['eventos']), 70)
        self.assertEqual(cliente.consultar_evento('noviembre', 2027)['datos']['eventos'], [])
        self.assertEqual(cliente.consultar_evento('enero', 2026)['datos']['eventos'], [])

    def test_reserva_y_rechazo_sin_cambiar_la_base(self):
        cliente = self.cliente()
        reserva = cliente.reservar_evento(date(2026, 11, 1), 'E1', 3)
        self.assertEqual(reserva['estado'], 'EXITO', reserva)
        self.assertIsInstance(reserva['datos']['id_reserva'], int)
        antes = self.estado()
        rechazo = cliente.reservar_evento(date(2026, 11, 1), 'E1', 98)
        self.assertEqual(rechazo['motivo'], 'SIN_CUPO')
        self.assertEqual(antes, self.estado())
        self.assertEqual(self.estado()['reserva'][0]['numero_puestos'], 3)
        self.assertEqual(next(o for o in self.estado()['ocurrencia'] if o['evento_id'] == 'E1')['puestos_ocupados'], 3)

    def test_fecha_y_cantidades_invalidas(self):
        cliente = self.cliente()
        antes = self.estado()
        for cantidad in (0, -1, 1.5, True, '2', 2147483648):
            respuesta = cliente.reservar_evento(date(2026, 11, 1), 'E1', cantidad)
            self.assertEqual(respuesta['motivo'], 'DATO_INVALIDO')
        self.assertEqual(cliente.reservar_evento(date(2026, 11, 7), 'E1', 1)['motivo'], 'NO_EXISTE')
        self.assertEqual(antes, self.estado())

    def test_varios_clientes_sin_sobreventa(self):
        # Hay 100 asientos: cada uno de 20 clientes pide 10. Deben aceptarse diez.
        def reservar(indice):
            from capa_consumidores.cliente import Cliente
            cliente = Cliente(indice + 1)
            cliente.conectar_con_gt()
            try:
                return cliente.reservar_evento(date(2026, 11, 1), 'E1', 10)
            finally:
                cliente.cerrar_socket()
                cliente.terminar_contexto()
        with ThreadPoolExecutor(max_workers=20) as grupo:
            respuestas = list(grupo.map(reservar, range(20)))
        self.assertEqual(sum(r['estado'] == 'EXITO' for r in respuestas), 10)
        self.assertEqual(sum(r['motivo'] == 'SIN_CUPO' for r in respuestas), 10)
        self.assertEqual(len({r['uuid'] for r in respuestas}), 20)
        self.assertEqual(sum(r['numero_puestos'] for r in self.estado()['reserva']), 100)

    def test_json_malformado_no_detiene_rmc(self):
        import zmq
        direccion = f"tcp://127.0.0.1:{self.entorno['GT_PUERTO_CLIENTES']}"
        with zmq.Context() as contexto, contexto.socket(zmq.REQ) as canal:
            canal.setsockopt(zmq.LINGER, 0)
            canal.setsockopt(zmq.RCVTIMEO, 2000)
            canal.connect(direccion)
            for mensaje in (b'{invalido', b'[1, 2]', b'\xff'):
                canal.send(mensaje)
                self.assertEqual(canal.recv_json()['estado'], 'ERROR')
        self.assertEqual(self.cliente().consultar_evento('noviembre', 2026)['estado'], 'EXITO')

    def test_error_insert_revierte_ocupacion(self):
        from sqlalchemy import text
        antes = self.estado()
        with self.engine.begin() as conexion:
            conexion.execute(text('ALTER TABLE reserva ADD CONSTRAINT fallo_prueba CHECK (numero_puestos < 3)'))
        try:
            respuesta = self.cliente().reservar_evento(date(2026, 11, 1), 'E1', 3)
            self.assertEqual(respuesta['motivo'], 'ERROR_BD')
            self.assertEqual(antes, self.estado())
        finally:
            with self.engine.begin() as conexion:
                conexion.execute(text('ALTER TABLE reserva DROP CONSTRAINT fallo_prueba'))

    def test_cargar_no_borra_una_base_existente(self):
        from capa_persistencia.cargar_datos import cargar
        self.cliente().reservar_evento(date(2026, 11, 1), 'E1', 2)
        antes = self.estado()
        with self.assertRaises(ValueError):
            cargar(str(self.archivo_datos))
        self.assertEqual(antes, self.estado())

    def test_comandos_de_caso_carga_y_estado(self):
        caso = subprocess.run([sys.executable, '-m', 'capa_consumidores.main', 'caso'],
                              cwd=RAIZ, env=self.entorno, capture_output=True, text=True, timeout=10)
        self.assertEqual(caso.returncode, 0, caso.stdout + caso.stderr)
        self.assertEqual(len(self.estado()['reserva']), 1)
        carga = subprocess.run([sys.executable, '-m', 'capa_consumidores.main', 'carga',
                                '--rpm', '120', '--minutos', '0.05', '--porcentaje-consulta', '50'],
                               cwd=RAIZ, env=self.entorno, capture_output=True, text=True, timeout=10)
        self.assertEqual(carga.returncode, 0, carga.stdout + carga.stderr)
        self.assertIn("'enviadas': 6", carga.stdout)
        self.assertIn("'errores': 0", carga.stdout)
        foto = subprocess.run([sys.executable, '-m', 'capa_persistencia.main', '--estado'],
                              cwd=RAIZ, env=self.entorno, capture_output=True, text=True, timeout=10)
        self.assertEqual(foto.returncode, 0, foto.stderr)
        self.assertIn('70 ocurrencias', foto.stdout)

    def test_z_persistencia_ausente_responde_timeout_y_permite_seguir(self):
        self.procesos['persistencia'].terminate()
        self.procesos['persistencia'].wait(timeout=5)
        try:
            inicio = time.monotonic()
            respuesta = self.cliente().consultar_evento('noviembre', 2026)
            self.assertEqual(respuesta['motivo'], 'TIEMPO_AGOTADO')
            self.assertLess(time.monotonic() - inicio, 3)
        finally:
            self.arrancar('persistencia', ['-m', 'capa_persistencia.main'])
            self.esperar_cadena()
        self.assertEqual(self.cliente().consultar_evento('noviembre', 2026)['estado'], 'EXITO')


if __name__ == '__main__':
    unittest.main()
