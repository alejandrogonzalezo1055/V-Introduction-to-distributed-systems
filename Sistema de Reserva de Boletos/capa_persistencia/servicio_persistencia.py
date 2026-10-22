"""Lógica de la capa de almacenamiento: recibe peticiones (dict) y devuelve respuestas (dict).

Aquí no hay sockets: eso lo maneja main.py. Cada método respeta el contrato
que el RMC ya espera (ver comun/mensajes.py y la guía del equipo).
"""
from abc import ABC, abstractmethod

from sqlalchemy import extract, func, select, update

import comun.mensajes as msjs
from capa_persistencia.conexion_bd import SessionLocal
from capa_persistencia.modelos import Evento, Ocurrencia, Reserva
from capa_persistencia.utilidades import escribir_fecha, leer_fecha, numero_mes

# Valores tomados del contrato, para no escribirlos a mano
EXITO = msjs.estados_rta['E']
FALLO = msjs.estados_rta['F']
ERROR = msjs.estados_rta['ER']
SIN_CUPO = msjs.motivos_rechazo['S_C']
NO_EXISTE = msjs.motivos_rechazo['N_E']
DATO_INVALIDO = msjs.motivos_rechazo['D_I']
PETICION_INVALIDA = msjs.motivos_rechazo['P_I']
NO_IMPLEMENTADO = msjs.motivos_rechazo['N_I']


def responder(peticion, estado, motivo=None, datos=None):
    """Arma una Respuesta con el MISMO uuid de la petición que responde."""
    uuid_peticion = peticion.get('uuid', '') if isinstance(peticion, dict) else ''
    return {'uuid': uuid_peticion, 'estado': estado, 'motivo': motivo, 'datos': datos or {}}


class I_Servicio_persistencia(ABC):
    @abstractmethod
    def consultar_eventos(self, peticion): ...

    @abstractmethod
    def consultar_disponibilidad(self, peticion): ...

    @abstractmethod
    def agregar_reserva(self, peticion): ...

    @abstractmethod
    def modificar_reserva(self, peticion): ...

    @abstractmethod
    def eliminar_reserva(self, peticion): ...


class Servicio_persistencia(I_Servicio_persistencia):

    # ---------- CONSULTA: {"mes": "noviembre"} ----------
    def consultar_eventos(self, peticion):
        try:
            mes = numero_mes(peticion['datos']['mes'])
        except (KeyError, TypeError, ValueError):
            return responder(peticion, FALLO, DATO_INVALIDO, {'razon': 'mes inválido o ausente'})

        with SessionLocal() as session:
            filas = session.execute(
                select(Evento.id, Evento.nombre, Evento.tipo_evento,
                       Ocurrencia.fecha, Ocurrencia.capacidad, Ocurrencia.puestos_ocupados)
                .join(Evento.ocurrencias)
                .where(extract('month', Ocurrencia.fecha) == mes)
                .order_by(Ocurrencia.fecha, Evento.id)
            ).all()

            eventos = [
                {'id_evento': f.id, 'nombre': f.nombre, 'tipo_evento': f.tipo_evento,
                 'fecha': escribir_fecha(f.fecha), 'capacidad': f.capacidad,
                 'puestos_ocupados': f.puestos_ocupados}
                for f in filas
            ]
        return responder(peticion, EXITO, None, {'eventos': eventos})

    # ---------- CONSULTA_DISPONIBILIDAD: {"id_evento": "E1", "fecha": "2026/11/07"} ----------
    def consultar_disponibilidad(self, peticion):
        try:
            id_evento, fecha = self._leer_evento_y_fecha(peticion)
        except (KeyError, TypeError, ValueError):
            return responder(peticion, FALLO, DATO_INVALIDO, {'razon': 'id_evento o fecha inválidos'})

        with SessionLocal() as session:
            oc = session.scalars(
                select(Ocurrencia).where(Ocurrencia.evento_id == id_evento,
                                         Ocurrencia.fecha == fecha)
            ).first()
            if oc is None:
                return responder(peticion, FALLO, NO_EXISTE,
                                 {'razon': f'no existe {id_evento} el {escribir_fecha(fecha)}'})
            # nombres EXACTOS que lee el RMC
            return responder(peticion, EXITO, None,
                             {'capacidad_total': oc.capacidad, 'ocupacion': oc.puestos_ocupados})

    # ---------- AGREGAR_RESERVA: {"id_evento", "fecha", "n_asientos"} ----------
    def agregar_reserva(self, peticion):
        try:
            id_evento, fecha = self._leer_evento_y_fecha(peticion)
            n = int(peticion['datos']['n_asientos'])
            id_cliente = int(peticion['id_cliente'])
            if n <= 0:
                raise ValueError('n_asientos debe ser positivo')
        except (KeyError, TypeError, ValueError):
            return responder(peticion, FALLO, DATO_INVALIDO, {'razon': 'datos de la reserva inválidos'})

        with SessionLocal.begin() as session:    # una transacción: todo o nada
            oc_id = session.scalars(
                select(Ocurrencia.id).where(Ocurrencia.evento_id == id_evento,
                                            Ocurrencia.fecha == fecha)
            ).first()
            if oc_id is None:
                return responder(peticion, FALLO, NO_EXISTE,
                                 {'razon': f'no existe {id_evento} el {escribir_fecha(fecha)}'})

            # Suma SOLO si caben. La base decide, así dos réplicas no pueden sobrevender.
            resultado = session.execute(
                update(Ocurrencia)
                .where(Ocurrencia.id == oc_id,
                       Ocurrencia.puestos_ocupados + n <= Ocurrencia.capacidad)
                .values(puestos_ocupados=Ocurrencia.puestos_ocupados + n)
            )
            if resultado.rowcount == 0:
                return responder(peticion, FALLO, SIN_CUPO, {'razon': f'no hay {n} puestos libres'})

            reserva = Reserva(id_cliente=id_cliente, ocurrencia_id=oc_id, numero_puestos=n)
            session.add(reserva)
            session.flush()                       # asigna reserva.id sin cerrar la transacción
            return responder(peticion, EXITO, None,
                             {'id_reserva': reserva.id, 'id_evento': id_evento,
                              'fecha': escribir_fecha(fecha), 'n_asientos': n})

    # ---------- Fuera de la primera entrega ----------
    def modificar_reserva(self, peticion):
        return responder(peticion, FALLO, NO_IMPLEMENTADO, {'razon': 'modificación no implementada'})

    def eliminar_reserva(self, peticion):
        return responder(peticion, FALLO, NO_IMPLEMENTADO, {'razon': 'cancelación no implementada'})

    # ---------- Apoyo ----------
    def imprimir_estado(self):
        """Muestra cada ocurrencia con sus puestos: el enunciado pide ver la BD durante la sustentación."""
        with SessionLocal() as session:
            filas = session.execute(
                select(Ocurrencia.evento_id, Ocurrencia.fecha,
                       Ocurrencia.puestos_ocupados, Ocurrencia.capacidad)
                .order_by(Ocurrencia.evento_id, Ocurrencia.fecha)
            ).all()
            total_reservas = session.scalar(select(func.count()).select_from(Reserva))
        print(f"\n[BD] {len(filas)} ocurrencias, {total_reservas} reservas")
        print(f"{'evento':<8}{'fecha':<12}{'ocupados':>9}{'capacidad':>10}")
        for f in filas:
            print(f"{f.evento_id:<8}{escribir_fecha(f.fecha):<12}{f.puestos_ocupados:>9}{f.capacidad:>10}")
        print()

    @staticmethod
    def _leer_evento_y_fecha(peticion):
        datos = peticion['datos']
        return str(datos['id_evento']), leer_fecha(datos['fecha'])
