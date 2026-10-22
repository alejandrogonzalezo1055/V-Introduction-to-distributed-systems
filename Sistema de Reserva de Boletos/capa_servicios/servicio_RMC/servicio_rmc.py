"""RMC recibe diccionarios del GT y delega datos a persistencia por REQ/REP."""
from abc import ABC, abstractmethod
import zmq
from comun.config import HOST_PERS, SP_PORT, TIMEOUT_PERSISTENCIA_MS, time_out_sockets
import comun.mensajes as msjs


class I_Servicio_RMC(ABC):
    # La interfaz enumera métodos obligatorios; no ejecuta peticiones por sí misma.
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
    """Cliente interno del RMC, distinto del usuario de capa_consumidores."""
    def __init__(self):
        # Conservar el contexto permite cerrarlo junto al socket al detener el RMC.
        self.contexto = zmq.Context()
        self.socket = None
        self._conectar()

    def _conectar(self):
        self.socket = self.contexto.socket(zmq.REQ)
        time_out_sockets(self.socket, TIMEOUT_PERSISTENCIA_MS)
        self.socket.connect(f"tcp://{HOST_PERS}:{SP_PORT}")

    def enviar(self, peticion):
        try:
            self.socket.send_string(msjs.codificar(peticion))
            respuesta = msjs.decodificar(self.socket.recv_string())
        except zmq.Again:
            # Cerrar y recrear el REQ permite atender una petición posterior.
            # No es tolerancia a fallos ni implica repetir esta escritura.
            self.socket.close(linger=0)
            self._conectar()
            return msjs.crear_rta('ER', 'T_A', {
                'razon': 'Persistencia no respondió; resultado incierto si se envió una escritura.'
            }, peticion['uuid'])
        if not isinstance(respuesta, dict) or respuesta.get('uuid') != peticion['uuid']:
            return msjs.crear_rta('ER', 'P_I', {'razon': 'Respuesta de persistencia sin UUID esperado'}, peticion['uuid'])
        return respuesta

    def cerrar(self):
        self.socket.close(linger=0)
        self.contexto.term()


class Servicio_RMC(I_Servicio_RMC):
    def __init__(self, mensajero_persistencia):
        self.mensajero_persistencia = mensajero_persistencia

    def consultar_eventos(self, peticion):
        return self.mensajero_persistencia.enviar(peticion)

    def crear_reserva(self, peticion):
        # main.py ya decodificó el JSON: peticion es dict, no otro texto JSON.
        datos = peticion['datos']
        cantidad = datos.get('n_asientos')
        if type(cantidad) is not int or not 1 <= cantidad <= 2147483647:
            return msjs.crear_rta('F', 'D_I', {'razon': 'n_asientos debe ser un entero positivo'}, peticion['uuid'])
        consulta = msjs.crear_req('CO_D', peticion['id_cliente'],
                                  {'id_evento': datos.get('id_evento'), 'fecha': datos.get('fecha')},
                                  peticion['uuid'])
        respuesta = self.mensajero_persistencia.enviar(consulta)
        if respuesta['estado'] != msjs.estados_rta['E']:
            # Conservar el motivo original: no confundir un timeout con NO_EXISTE.
            return respuesta
        disponibles = respuesta['datos']['capacidad_total'] - respuesta['datos']['ocupacion']
        if cantidad > disponibles:
            return msjs.crear_rta('F', 'S_C', {'razon': f'Solo hay {disponibles} puestos disponibles'}, peticion['uuid'])
        agregar = msjs.crear_req('A_R', peticion['id_cliente'], datos, peticion['uuid'])
        # El cupo pudo cambiar después de consultarlo: persistencia vuelve a
        # comprobarlo en la misma transacción que ocupa puestos e inserta la reserva.
        return self.mensajero_persistencia.enviar(agregar)

    def modificar_reserva(self, peticion):
        # Se conserva pendiente: no era una operación exigida para la primera entrega.
        return msjs.crear_rta('F', 'N_I', {'razon': 'Modificación no implementada'}, peticion['uuid'])
