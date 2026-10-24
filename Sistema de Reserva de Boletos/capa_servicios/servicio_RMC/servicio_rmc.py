from abc import ABC, abstractmethod
import zmq
from comun.config import HOST_PERS, PS_PORT
import comun.mensajes as msjs

class I_Servicio_RMC(ABC):
    @abstractmethod
    def crear_reserva(self, peticion):
        pass

    @abstractmethod
    def modificar_reserva(self, peticion):
        pass

    @abstractmethod
    def consultar_eventos(self, peticion):
        pass

class Cliente_persistencia:
    def __init__(self):
        zmq_context = zmq.Context()
        self.socket = zmq_context.socket(zmq.REQ)
        self.socket.connect(f"tcp://{HOST_PERS}:{PS_PORT}")

    def enviar(self, peticion):
        self.socket.send_string(msjs.codificar(peticion))
        respuesta = self.socket.recv_string()

        return msjs.decodificar(respuesta)

class Servicio_RMC(I_Servicio_RMC):
    def __init__(self, mensajero_persistencia):
        self.mensajero_persistencia = mensajero_persistencia

    def consultar_eventos(self, peticion):
        return self.mensajero_persistencia.enviar(peticion)

    def crear_reserva(self, peticion):
        json_mensaje = msjs.decodificar(peticion)
        datos = {
            'id_evento': json_mensaje['datos']['id_evento'],
            'fecha': json_mensaje['datos']['fecha']
        }
        consultar_disp = msjs.crear_req('CO_D', json_mensaje['id_cliente'], datos, json_mensaje['uuid'])
        respuesta = self.mensajero_persistencia.enviar(consultar_disp)

        if respuesta['estado'] == 'EXITO':
            puestos_disp = respuesta['datos']['capacidad_total'] - respuesta['datos']['ocupacion']
            if puestos_disp >= json_mensaje['datos']['n_asientos']:
                agregar_reserva = msjs.crear_req('A_R', json_mensaje['id_cliente'], json_mensaje['datos'], json_mensaje['uuid'])

                return self.mensajero_persistencia.enviar(agregar_reserva)
            else:
                return msjs.crear_rta('ER', 'S_C', {'razon': f'habia {puestos_disp} puestos disponibles, menos de los necesarios para su reserva'})
        else:
            return msjs.crear_rta('ER', 'N_E', {'razon':'no existe el evento'})

    def modificar_reserva(self, peticion):
        return msjs.crear_rta('F', 'N_I', {'razon': 'no ha sido implementado aun'})