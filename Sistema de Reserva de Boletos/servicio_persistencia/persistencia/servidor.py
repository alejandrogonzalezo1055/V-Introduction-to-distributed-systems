"""Servidor ROUTER: recibe peticiones REQ de RMC y cancelaciones en el puerto 5557."""

import argparse
import json
import logging

import psycopg
import zmq

from persistencia.base_datos import conectar
from persistencia.operaciones import procesar
from persistencia.protocolo import respuesta_error


def servir(direccion):
    contexto = zmq.Context()
    socket = contexto.socket(zmq.ROUTER)
    socket.setsockopt(zmq.LINGER, 0)
    socket.setsockopt(zmq.ROUTER_MANDATORY, 1)
    socket.setsockopt(zmq.SNDTIMEO, 1000)
    # Limita el tamaño de las peticiones de este protocolo pequeño.
    socket.setsockopt(zmq.MAXMSGSIZE, 65536)
    conexion = None
    try:
        conexion = conectar()
        # Fallar al arrancar si falta inicializar el esquema.
        conexion.execute("SELECT 1 FROM reservas LIMIT 1")
        socket.bind(direccion)
        logging.info("Persistencia escuchando en %s", direccion)
        while True:
            partes = socket.recv_multipart()
            identidad = partes[0]
            # REQ envía: identidad (agregada por ROUTER), separador vacío, JSON.
            if len(partes) != 3 or partes[1] != b"":
                logging.warning("Mensaje con envoltura incompatible; se requiere REQ/ROUTER")
                continue
            try:
                peticion = json.loads(partes[2])
                respuesta = procesar(conexion, peticion)
            except (ValueError, UnicodeError):
                respuesta = respuesta_error("MENSAJE_INVALIDO", "Se esperaba JSON válido.")
            except Exception:
                logging.exception("Error inesperado procesando una petición")
                respuesta = respuesta_error("ERROR_INTERNO", "No se pudo procesar la petición.")
            logging.info("id=%s operacion=%s ok=%s codigo=%s", respuesta["id"],
                         respuesta["operacion"], respuesta["ok"], respuesta["codigo"])
            try:
                socket.send_multipart([identidad, b"", json.dumps(respuesta, ensure_ascii=False).encode()])
            except zmq.ZMQError:
                # El emisor pudo desconectarse tras vencer su timeout.
                logging.warning("No se pudo entregar la respuesta id=%s", respuesta["id"])
    except KeyboardInterrupt:
        logging.info("Persistencia detenida")
    finally:
        if conexion:
            conexion.close()
        socket.close()
        contexto.term()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bind", default="tcp://127.0.0.1:5557")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [persistencia] %(message)s")
    try:
        servir(args.bind)
    except psycopg.Error:
        parser.exit(1, "No se pudo conectar o falta el esquema de PostgreSQL. Ejecute base_datos iniciar.\n")


if __name__ == "__main__":
    main()
