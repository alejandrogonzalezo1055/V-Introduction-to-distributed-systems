from typing import TypedDict
from datetime import datetime

# constantes
peticiones = {
    'CO':'CONSULTA',
    'R':'RESERVA',
    'M':'MODIFICACION',
    'CA':'CANCELACION',
    'N':'NOTIFICACION'
}

estados_rta = {
    'E':'EXITO',
    'R':'RECHAZO',
    'ER':'ERROR',
    'A':'ACK'
}

motivos_rechazo = {
    'S_C': 'SIN_CUPO',
    'N_E': 'NO_EXISTE',
    'D_I': 'DATO_INVALIDO',
    'P_I':'PETICION_INVALIDA'
}

meses = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre']

# peticiones
class Peticion(TypedDict):
    id: int
    tipo: str
    id_cliente: int
    # el cliente debe enviar su ip en el msj de cancelacion?
    datos: dict

class Respuesta(TypedDict):
    id: int
    estado: str
    motivo: str
    datos: dict

# funciones
def crear_req(id, tipo, id_cliente, datos):
    peticion = None
    if tipo in peticiones and id_cliente > 0 and id > 0:
        peticion: Peticion = {
            'id':id,
            'tipo':peticiones[tipo],
            'id_cliente':id_cliente,
            'datos':datos
        }
    return peticion

def crear_rta(id, estado, motivo, datos):
    respuesta = None
    if estado in estados_rta and id > 0 and motivo in motivos_rechazo:
        respuesta: Respuesta = {
            'id':id,
            'estado':estados_rta[estado],
            'motivo':motivos_rechazo[motivo],
            'datos':datos
        }
    return respuesta

