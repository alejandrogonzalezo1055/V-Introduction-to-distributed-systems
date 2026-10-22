"""Contrato JSON compartido por consumidores, negocio y persistencia.

Dentro de Python trabajamos con dict. codificar lo convierte en texto JSON para
la red; decodificar hace el camino inverso UNA vez al recibir. TypedDict ayuda
al editor, pero no valida datos durante la ejecución.
"""
from typing import TypedDict
import uuid
import json

# Clave corta usada en Python -> valor que viaja en el JSON.
peticiones = {
    'CO': 'CONSULTA', 'CO_D': 'CONSULTA_DISPONIBILIDAD', 'R': 'RESERVA',
    'A_R': 'AGREGAR_RESERVA', 'M': 'MODIFICACION', 'CA': 'CANCELACION',
    'N': 'NOTIFICACION',
}
estados_rta = {'E': 'EXITO', 'F': 'FALLO', 'ER': 'ERROR', 'A': 'ACK'}
motivos_rechazo = {
    'S_C': 'SIN_CUPO', 'N_E': 'NO_EXISTE', 'D_I': 'DATO_INVALIDO',
    'P_I': 'PETICION_INVALIDA', 'N_I': 'NO_IMPLEMENTADO',
    'T_A': 'TIEMPO_AGOTADO', 'E_BD': 'ERROR_BD',
}
meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
         'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']


class Peticion(TypedDict):
    uuid: str
    tipo: str
    id_cliente: int
    datos: dict


class Respuesta(TypedDict):
    uuid: str
    estado: str
    motivo: str | None
    datos: dict


def crear_req(tipo, id_cliente, datos, uuID=''):
    """Genera un UUID nuevo o conserva el del cliente cuando RMC reenvía."""
    if tipo not in peticiones:
        raise ValueError('Tipo de petición desconocido')
    if type(id_cliente) is not int or id_cliente <= 0:
        raise ValueError('id_cliente debe ser un entero positivo')
    if not isinstance(datos, dict):
        raise ValueError('datos debe ser un diccionario')
    return {'uuid': uuID or str(uuid.uuid4()), 'tipo': peticiones[tipo],
            'id_cliente': id_cliente, 'datos': datos}


def crear_rta(estado, motivo, datos, uuID=''):
    """Responde con el UUID recibido, sin generar otro. Un éxito admite motivo=None."""
    if estado not in estados_rta or (motivo is not None and motivo not in motivos_rechazo):
        raise ValueError('Estado o motivo de respuesta desconocido')
    return {'uuid': uuID, 'estado': estados_rta[estado],
            'motivo': motivos_rechazo[motivo] if motivo is not None else None, 'datos': datos}


def validar_peticion(peticion):
    """Valida la envoltura común; los métodos de negocio validan además sus datos."""
    if not isinstance(peticion, dict):
        raise ValueError('La petición debe ser un objeto JSON')
    if not isinstance(peticion.get('uuid'), str) or not peticion['uuid'].strip():
        raise ValueError('Falta uuid de la petición')
    if peticion.get('tipo') not in peticiones.values():
        raise ValueError('Tipo de petición desconocido')
    if type(peticion.get('id_cliente')) is not int or peticion['id_cliente'] <= 0:
        raise ValueError('id_cliente debe ser un entero positivo')
    if not isinstance(peticion.get('datos'), dict):
        raise ValueError('datos debe ser un objeto JSON')


def codificar(peticion):
    """dict -> texto JSON. Las fechas ya deben ser cadenas antes de este paso."""
    return json.dumps(peticion, ensure_ascii=False)


def decodificar(peticion):
    """Texto JSON -> dato de Python. Después se valida que sea una petición."""
    return json.loads(peticion)
