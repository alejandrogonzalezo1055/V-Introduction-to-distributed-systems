import comun.mensajes as msjs
from comun.config import HOST_SERV, GT_PORT_CLI
import comun.config as conf
import zmq
import json


class Cliente:
    def __init__(self, ID=0, nombre='Ramiro'):
        self.ID = ID
        self.nombre = nombre
        self.socket = None
        self.contexto = None

    @property
    def ID(self):
        return self._ID

    @ID.setter
    def ID(self, ID):
        self._ID = ID

    @property
    def nombre(self):
        return self._nombre

    @nombre.setter
    def nombre(self, nombre):
        self._nombre = nombre

    @property
    def socket(self):
        return self._socket

    @socket.setter
    def socket(self, socket):
        self._socket = socket

    @property
    def contexto(self):
        return self._contexto

    @contexto.setter
    def contexto(self, contexto):
        self._contexto = contexto


    def conectar_con_gt(self):
        self.contexto = zmq.Context()
        socket = self.contexto.socket(zmq.REQ)
        socket.connect(f"tcp://{HOST_SERV}:{GT_PORT_CLI}")
        self.socket = socket
        conf.time_out_sockets(self.socket)


    def enviar_peticion(self,peticion):
        peticion_texto = msjs.codificar(peticion)
        self.socket.send_string(peticion_texto)
        respuesta_texto = self.socket.recv_string()
        respuesta_dict = msjs.decodificar(respuesta_texto)

        return respuesta_dict


    def consultar_evento(self, mes):
        if mes in msjs.meses:
            datos = {
                    'mes': mes
            }
            peticion = msjs.crear_req('CO', self.ID, datos)
            respuesta = self.enviar_peticion(peticion)

            return respuesta
        else:
            # deberia enviarle la respuesta al cliente, no se como
            return msjs.crear_rta('F', 'N_E', {})


    def reservar_evento(self, fecha, id_evento=0, n_asientos=1):
        datos = {
            'id_evento': id_evento,
            'fecha': fecha.strftime('%Y/%m/%d'),
            'n_asientos': n_asientos
        }
        peticion = msjs.crear_req('R', self.ID, datos)
        respuesta = self.enviar_peticion(peticion)

        return respuesta


    def procesar_rta(self, respuesta):
        if 'estado' in respuesta:
            print('la peticion fracaso')


    def cerrar_socket(self):
        self.socket.close()


    def terminar_contexto(self):
        self.contexto.term()