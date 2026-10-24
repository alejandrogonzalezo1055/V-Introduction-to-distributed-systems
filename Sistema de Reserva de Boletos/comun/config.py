import os
import zmq
from dotenv import load_dotenv

load_dotenv()

HOST_CLI = os.getenv("HOST_CAPA_CONSUMIDORES")
HOST_SERV = os.getenv("HOST_CAPA_SERVICIOS")
HOST_PERS = os.getenv("HOST_CAPA_PERSISTENCIA")

GT_PORT_CLI = os.getenv("GT_PUERTO_CLIENTES")
GT_PORT_RMC = os.getenv("GT_PUERTO_RMC")
GT_PORT_CANC = os.getenv("GT_PUERTO_CANCELACION")

PS_PORT = os.getenv("PUERTO_SP")
DB_URL = os.getenv("DB_URL")
DB_PASSWD = os.getenv("DB_PASSWD")

def time_out_sockets(socket):
    socket.setsockopt(zmq.RCVTIMEO, 3000)  # milisegundos, desde config
    socket.setsockopt(zmq.LINGER, 0)