"""Consumidor: solo se conecta al GT; no conoce PostgreSQL ni llama al RMC."""
import comun.mensajes as msjs
from comun.config import HOST_SERV, GT_PORT_CLI
import comun.config as conf
import zmq


class Cliente:
    def __init__(self, ID=1, nombre='Ramiro'):
        if type(ID) is not int or ID <= 0:
            raise ValueError('El ID del cliente debe ser un entero positivo')
        self.ID = ID
        self.nombre = nombre
        self.socket = None
        self.contexto = None

    # Una propiedad permite escribir cliente.ID mientras el dato se guarda en _ID.
    # getter: leer; setter: asignar. Se conservan las propiedades del diseño original.
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
        if self.contexto is None:
            self.contexto = zmq.Context()
        # connect debe apuntar a la IP real del GT. El GT es quien hace bind('*').
        self.socket = self.contexto.socket(zmq.REQ)
        conf.time_out_sockets(self.socket)
        self.socket.connect(f"tcp://{HOST_SERV}:{GT_PORT_CLI}")

    def enviar_peticion(self, peticion):
        """REQ: enviar una petición, esperar una respuesta y comprobar su UUID."""
        try:
            self.socket.send_string(msjs.codificar(peticion))
            respuesta = msjs.decodificar(self.socket.recv_string())
        except zmq.Again:
            # REQ queda esperando después de un timeout. Se reemplaza el socket
            # para próximas peticiones, sin reenviar la operación de resultado incierto.
            self.cerrar_socket()
            self.conectar_con_gt()
            return msjs.crear_rta('ER', 'T_A', {
                'razon': 'No llegó respuesta del GT; el resultado puede ser incierto. No repetir reservas automáticamente.'
            }, peticion['uuid'])
        if not isinstance(respuesta, dict) or respuesta.get('uuid') != peticion['uuid']:
            return msjs.crear_rta('ER', 'P_I', {'razon': 'Respuesta sin el UUID esperado'}, peticion['uuid'])
        return respuesta

    def consultar_evento(self, mes, anio=None):
        """Consulta el mes del contrato; puede precisar el año para no mezclar años."""
        mes = str(mes).strip().lower()
        if mes not in msjs.meses:
            return msjs.crear_rta('F', 'D_I', {'razon': 'Mes inválido'})
        datos = {'mes': mes}
        if anio is not None:
            datos['anio'] = anio
        return self.enviar_peticion(msjs.crear_req('CO', self.ID, datos))

    def reservar_evento(self, fecha, id_evento=0, n_asientos=1):
        # date no puede viajar directamente en JSON: strftime lo convierte a texto.
        datos = {'id_evento': id_evento, 'fecha': fecha.strftime('%Y/%m/%d'),
                 'n_asientos': n_asientos}
        return self.enviar_peticion(msjs.crear_req('R', self.ID, datos))

    def procesar_rta(self, respuesta):
        # La presencia de estado no significa fracaso; debemos mirar su VALOR.
        print('La petición fue exitosa' if respuesta['estado'] == msjs.estados_rta['E']
              else f"La petición no se confirmó: {respuesta['motivo']}")

    def cerrar_socket(self):
        if self.socket is not None:
            self.socket.close(linger=0)
            self.socket = None

    def terminar_contexto(self):
        if self.contexto is not None:
            self.contexto.term()
            self.contexto = None
