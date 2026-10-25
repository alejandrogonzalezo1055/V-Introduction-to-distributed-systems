import comun.mensajes as msjs
from comun.config import HOST_SERV, GT_PORT_CLI
import comun.config as conf
import zmq


class Cliente:
    numero_clientes = 0

    def __init__(self, nombre='Ramiro', id=0):
        if id == 0:
            Cliente.numero_clientes += 1
            self.id = self.numero_clientes
        else:
            self.id = id
        self.nombre = nombre
        self.req_socket = None

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, id):
        self._id = id

    @property
    def nombre(self):
        return self._nombre

    @nombre.setter
    def nombre(self, nombre):
        self._nombre = nombre

    @property
    def req_socket(self):
        return self._req_socket

    @req_socket.setter
    def req_socket(self, socket):
        self._req_socket = socket


    def conectar_con_gt(self):
        self.req_socket = zmq.Context().socket(zmq.REQ)
        conf.time_out_sockets(self.req_socket)
        self.req_socket.connect(f"tcp://{HOST_SERV}:{GT_PORT_CLI}")

    def cerrar_socket(self):
        self.req_socket.close()


    def enviar_peticion(self,peticion):
        peticion_texto = msjs.codificar(peticion)
        self.req_socket.send_string(peticion_texto)
        respuesta_texto = self.req_socket.recv_string()
        respuesta_json = msjs.decodificar(respuesta_texto)

        return respuesta_json


    def consultar_evento(self, mes):
        datos = {
                'mes': mes
        }
        peticion = msjs.crear_req('CO', self.id, datos)
        respuesta = self.enviar_peticion(peticion)

        return respuesta


    def reservar_evento(self, fecha, id_evento=0, n_asientos=1):
        datos = {
            'id_evento': id_evento,
            'fecha': fecha.strftime('%Y/%m/%d'),
            'n_asientos': n_asientos
        }
        peticion = msjs.crear_req('R', self.id, datos)
        respuesta = self.enviar_peticion(peticion)

        return respuesta


    def procesar_rta(self, respuesta):
        if respuesta['estado'] == 'FALLO':
            print(respuesta)