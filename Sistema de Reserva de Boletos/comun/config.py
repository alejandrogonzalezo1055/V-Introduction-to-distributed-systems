import os

from dotenv import load_dotenv

load_dotenv()

HOST_CONS = os.getenv("HOST_CAPA_CONSUMIDORES")
HOST_SERV = os.getenv("HOST_CAPA_SERVICIOS")
HOST_PERS = os.getenv("HOST_CAPA_PERSISTENCIA")

GT_PORT_CONS = os.getenv("GT_PUERTO_CLIENTES")
GT_PORT_RMC = os.getenv("GT_PUERTO_RMC")
GT_PORT_CANC = os.getenv("GT_PUERTO_CANCELACION")

SP_PORT = os.getenv("SP_PUERTO")
DB_URL = os.getenv("DB_URL")
DB_PASSWD = os.getenv("DB_PASSWD")

def armar_direccion(consultante, peticion=''):
    direccion = None
    match consultante:
        case "cliente":
            if peticion == '':
                direccion = 'tcp://' + HOST_SERV + ':' + GT_PORT_CONS

    return direccion