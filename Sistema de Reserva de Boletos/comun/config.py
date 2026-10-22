"""Configuración compartida de las tres capas.

HOST_* son destinos para connect(). Un servidor escucha con bind('tcp://*:puerto').
Se lee comun/.env desde una ruta explícita: cambiar de terminal no cambia el archivo.
Las variables exportadas en la terminal tienen prioridad sobre ese archivo.
"""
import os
from pathlib import Path
import zmq
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name('.env'), override=False)

HOST_CLI = os.getenv("HOST_CAPA_CONSUMIDORES", "127.0.0.1")
HOST_SERV = os.getenv("HOST_CAPA_SERVICIOS", "127.0.0.1")
HOST_PERS = os.getenv("HOST_CAPA_PERSISTENCIA", "127.0.0.1")
GT_PORT_CLI = os.getenv("GT_PUERTO_CLIENTES", "5555")
GT_PORT_RMC = os.getenv("GT_PUERTO_RMC", "5556")
GT_PORT_CANC = os.getenv("GT_PUERTO_CANCELACION", "5557")
SP_PORT = os.getenv("SP_PUERTO", "5558")
DB_URL = os.getenv("DB_URL")
DB_PASSWD = os.getenv("DB_PASSWD")  # Conservada por compatibilidad; la URL ya contiene la clave.

# Reservar hace dos llamadas a persistencia. El cliente debe esperar más tiempo
# que esas llamadas. Un timeout limita espera; no recupera un proceso caído.
TIMEOUT_PERSISTENCIA_MS = int(os.getenv("TIMEOUT_PERSISTENCIA_MS", "3000"))
TIMEOUT_CLIENTE_MS = int(os.getenv("TIMEOUT_CLIENTE_MS", "10000"))


def time_out_sockets(socket, timeout_ms=TIMEOUT_CLIENTE_MS):
    """Limita envío y recepción en clientes REQ; no usar en servidores inactivos."""
    if timeout_ms <= 0:
        raise ValueError("El timeout debe ser positivo")
    socket.setsockopt(zmq.SNDTIMEO, timeout_ms)
    socket.setsockopt(zmq.RCVTIMEO, timeout_ms)
    # Cerrar no debe esperar a entregar mensajes a un proceso desconectado.
    socket.setsockopt(zmq.LINGER, 0)
