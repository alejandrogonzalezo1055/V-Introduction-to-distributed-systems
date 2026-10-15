from typing import TypedDict
import uuid
import json

# constantes
peticiones = {
    'CO':'CONSULTA',
    'CO_D':'CONSULTA_DISPONIBILIDAD',
    'R':'RESERVA',
    'A_R':'AGREGAR_RESERVA',
    'M':'MODIFICACION',
    'CA':'CANCELACION',
    'N':'NOTIFICACION'
}

estados_rta = {
    'E':'EXITO',
    'F':'FALLO',
    'ER':'ERROR',
    'A':'ACK'
}

motivos_rechazo = {
    'S_C': 'SIN_CUPO',
    'N_E': 'NO_EXISTE',
    'D_I': 'DATO_INVALIDO',
    'P_I':'PETICION_INVALIDA',
    'N_I': 'NO_IMPLEMENTADO'
}

meses = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre']

# peticiones
class Peticion(TypedDict):
    uuid: str
    tipo: str
    id_cliente: int
    # el cliente debe enviar su ip en el msj de cancelacion?
    datos: dict

class Respuesta(TypedDict):
    uuid: str
    estado: str
    motivo: str
    datos: dict

# funciones
def crear_req(tipo, id_cliente, datos, uuID=''):
    peticion = None
    if tipo in peticiones and id_cliente > 0 and uuID == '':
        peticion: Peticion = {
            'uuid':str(uuid.uuid4()),
            'tipo':peticiones[tipo],
            'id_cliente':id_cliente,
            'datos':datos
        }
    else:
        peticion: Peticion = {
            'uuid': uuID,
            'tipo': peticiones[tipo],
            'id_cliente': id_cliente,
            'datos': datos
        }
    return peticion

def crear_rta(estado, motivo, datos):
    respuesta = None
    if estado in estados_rta and motivo in motivos_rechazo:
        respuesta: Respuesta = {
            'uuid':str(uuid.uuid4()),
            'estado':estados_rta[estado],
            'motivo':motivos_rechazo[motivo],
            'datos':datos
        }
    return respuesta

def codificar(peticion):
    return json.dumps(peticion)

def decodificar(peticion):
    return json.loads(peticion)