import comun.mensajes as msjs
import comun.config as conf
import zmq
import json


class Cliente:
    def __init__(self, ID=0, nombre='Ramiro'):
        self.ID = ID
        self.nombre = nombre

    @property
    def ID(self):
        return self.ID

    @ID.setter
    def ID(self, ID):
        self.ID = ID

    @property
    def nombre(self):
        return self.nombre

    @nombre.setter
    def nombre(self, nombre):
        self.nombre = nombre

    @property
    def socket(self):
        return self.socket

    @socket.setter
    def socket(self, socket):
        self.socket = socket

    @property
    def contexto(self):
        return self.socket

    @contexto.setter
    def contexto(self, socket):
        self.socket = socket


    def conectar_con_gt(self):
        self.contexto = zmq.Context()
        socket = self.contexto.socket(zmq.REQ)
        socket.bind(conf.armar_direccion('cliente'))
        self.socket = socket


    def enviar_peticion(self,datos_peticion):
        peticion_texto = json.dumps(datos_peticion)
        self.socket.send_string(peticion_texto)
        respuesta_texto = self.socket.recv_string()
        respuesta_dict = json.loads(respuesta_texto)

        return respuesta_dict


    def consultar_evento(self, mes, n_peticion=0):
        if mes in msjs.meses:
            datos = {
                    'mes': mes
            }
            peticion = msjs.crear_req(n_peticion, 'CO', self.ID, datos)
            respuesta = self.enviar_peticion(self.socket,peticion)

            return respuesta
        else:
            # deberia enviarle la respuesta al cliente, no se como
            return msjs.crear_rta(n_peticion,'R', 'el mes para el que busca eventos no existe', {})


    def reservar_evento(self, fecha, n_peticion=0, id_evento=0, n_asientos=1):
        datos = {
            'id_evento': id_evento,
            'fecha': fecha,
            'n_asientos': n_asientos
        }
        peticion = msjs.crear_req(n_peticion, 'R', self.ID, datos)
        respuesta = self.enviar_peticion(self.socket, peticion)

        return respuesta


    def procesar_rta(self, respuesta):
        if 'estado' in respuesta:
            print('la peticion fracaso')


    def cerrar_socket(self):
        self.socket.close()


    def terminar_contexto(self):
        self.contexto.term()