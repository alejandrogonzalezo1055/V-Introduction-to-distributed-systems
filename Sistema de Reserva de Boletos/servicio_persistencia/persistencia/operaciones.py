"""Las cuatro funciones que atiende persistencia. Solo este módulo modifica reservas."""

from datetime import date, datetime
import logging

import psycopg

from persistencia.base_datos import limites_mes
from persistencia.protocolo import respuesta_error


class ErrorPeticion(Exception):
    def __init__(self, codigo, mensaje):
        super().__init__(mensaje)
        self.codigo = codigo


def entero(datos, campo, maximo=2147483647):
    valor = datos.get(campo)
    if type(valor) is not int or not 1 <= valor <= maximo:
        raise ErrorPeticion("DATOS_INVALIDOS", f"{campo} debe ser un entero positivo hasta {maximo}.")
    return valor


def texto(datos, campo):
    valor = datos.get(campo)
    if not isinstance(valor, str) or not valor.strip() or len(valor) > 128:
        raise ErrorPeticion("DATOS_INVALIDOS", f"{campo} debe ser un texto de 1 a 128 caracteres.")
    return valor


def buscar_reserva(conexion, peticion, bloquear=False):
    id_reserva = entero(peticion, "id_reserva", 9223372036854775807)
    id_cliente = entero(peticion, "id_cliente", 9223372036854775807)
    consulta = "SELECT * FROM reservas WHERE id_reserva = %s"
    if bloquear:
        consulta += " FOR UPDATE"
    reserva = conexion.execute(consulta, (id_reserva,)).fetchone()
    # No revelar reservas de otro cliente. La autenticación corresponde a negocio.
    if reserva is None or reserva["id_cliente"] != id_cliente:
        raise ErrorPeticion("RESERVA_NO_ENCONTRADA", "No existe esa reserva para el cliente indicado.")
    return reserva


def consultar(conexion, peticion):
    """Consulta eventos de un mes, una ocurrencia o una reserva del cliente."""
    tipo = peticion.get("tipo", "eventos")
    if tipo == "reserva":
        # Lectura consistente de la reserva y su fecha en la misma consulta.
        id_reserva = entero(peticion, "id_reserva", 9223372036854775807)
        id_cliente = entero(peticion, "id_cliente", 9223372036854775807)
        reserva = conexion.execute("""
            SELECT r.*, o.fecha FROM reservas r JOIN ocurrencias o
            ON r.id_evento = o.id_evento AND r.ocurrencia = o.numero
            WHERE r.id_reserva = %s AND r.id_cliente = %s
        """, (id_reserva, id_cliente)).fetchone()
        if reserva is None:
            raise ErrorPeticion("RESERVA_NO_ENCONTRADA", "No existe esa reserva para el cliente indicado.")
        return {"reserva": reserva}
    if tipo == "disponibilidad":
        evento = texto(peticion, "id_evento")
        ocurrencia = entero(peticion, "ocurrencia")
        fila = conexion.execute("""
            SELECT id_evento, numero AS ocurrencia, fecha, capacidad, ocupados,
                   capacidad - ocupados AS libres
            FROM ocurrencias WHERE id_evento = %s AND numero = %s
        """, (evento, ocurrencia)).fetchone()
        if fila is None:
            raise ErrorPeticion("OCURRENCIA_NO_ENCONTRADA", "No existe esa ocurrencia del evento.")
        return {"ocurrencia": fila}
    if tipo != "eventos":
        raise ErrorPeticion("DATOS_INVALIDOS", "tipo debe ser eventos, disponibilidad o reserva.")
    try:
        inicio, fin = limites_mes(peticion.get("mes"))
    except ValueError as exc:
        raise ErrorPeticion("MES_INVALIDO", str(exc)) from exc
    filas = conexion.execute("""
        SELECT e.id_evento, e.nombre, e.tipo_evento, o.numero AS ocurrencia,
               o.fecha, o.capacidad, o.ocupados, o.capacidad - o.ocupados AS libres
        FROM eventos e JOIN ocurrencias o USING (id_evento)
        WHERE o.fecha >= %s AND o.fecha < %s ORDER BY o.fecha, e.id_evento, o.numero
    """, (inicio, fin)).fetchall()
    return {"ocurrencias": filas}


def reservar(conexion, peticion):
    """Comprueba el cupo, crea la reserva y ocupa puestos en una transacción."""
    cliente = entero(peticion, "id_cliente", 9223372036854775807)
    evento = texto(peticion, "id_evento")
    ocurrencia = entero(peticion, "ocurrencia")
    cantidad = entero(peticion, "cantidad_asientos")
    with conexion.transaction():
        fila = conexion.execute("""
            SELECT * FROM ocurrencias WHERE id_evento = %s AND numero = %s FOR UPDATE
        """, (evento, ocurrencia)).fetchone()
        if fila is None:
            raise ErrorPeticion("OCURRENCIA_NO_ENCONTRADA", "No existe esa ocurrencia del evento.")
        libres = fila["capacidad"] - fila["ocupados"]
        if cantidad > libres:
            raise ErrorPeticion("SIN_CUPO", f"Solo quedan {libres} asientos.")
        conexion.execute("""
            UPDATE ocurrencias SET ocupados = ocupados + %s WHERE id_evento = %s AND numero = %s
        """, (cantidad, evento, ocurrencia))
        reserva = conexion.execute("""
            INSERT INTO reservas (id_cliente, id_evento, ocurrencia, cantidad_asientos)
            VALUES (%s, %s, %s, %s) RETURNING *
        """, (cliente, evento, ocurrencia, cantidad)).fetchone()
        reserva["fecha"] = fila["fecha"]
    # El bloque ya ejecutó COMMIT; recién ahora se puede responder éxito.
    return {"reserva": reserva, "libres": libres - cantidad}


def modificar(conexion, peticion):
    """Cambia cantidad O fecha; si se rechaza, conserva la reserva completa."""
    cambia_cantidad = "cantidad_asientos" in peticion
    cambia_fecha = "ocurrencia" in peticion
    if cambia_cantidad == cambia_fecha:
        raise ErrorPeticion("CAMBIO_INVALIDO", "Envíe cantidad_asientos u ocurrencia, solo uno.")
    if cambia_cantidad:
        cantidad = entero(peticion, "cantidad_asientos")
    else:
        destino = entero(peticion, "ocurrencia")
    with conexion.transaction():
        reserva = buscar_reserva(conexion, peticion, bloquear=True)
        evento = reserva["id_evento"]
        if "id_evento" in peticion and peticion["id_evento"] != evento:
            raise ErrorPeticion("CAMBIO_INVALIDO", "No se puede cambiar a otro evento.")
        origen = reserva["ocurrencia"]
        if cambia_cantidad:
            destino = origen
        else:
            cantidad = reserva["cantidad_asientos"]
        # Orden fijo para evitar bloqueos cruzados al mover dos reservas a la vez.
        filas = conexion.execute("""
            SELECT * FROM ocurrencias WHERE id_evento = %s AND numero IN (%s, %s)
            ORDER BY numero FOR UPDATE
        """, (evento, origen, destino)).fetchall()
        ocurrencias = {fila["numero"]: fila for fila in filas}
        if destino not in ocurrencias:
            raise ErrorPeticion("OCURRENCIA_NO_ENCONTRADA", "No existe esa ocurrencia del mismo evento.")
        anterior, nueva = ocurrencias[origen], ocurrencias[destino]
        if (anterior["fecha"].year, anterior["fecha"].month) != (nueva["fecha"].year, nueva["fecha"].month):
            raise ErrorPeticion("CAMBIO_INVALIDO", "La nueva fecha debe estar en el mismo mes y año.")
        libres = nueva["capacidad"] - nueva["ocupados"]
        necesarios = cantidad - reserva["cantidad_asientos"] if origen == destino else cantidad
        if necesarios > libres:
            raise ErrorPeticion("SIN_CUPO", "No hay cupo para el cambio; se conserva la reserva.")
        if origen == destino:
            conexion.execute("""
                UPDATE ocurrencias SET ocupados = ocupados + %s WHERE id_evento = %s AND numero = %s
            """, (necesarios, evento, origen))
        else:
            conexion.execute("""
                UPDATE ocurrencias SET ocupados = ocupados - %s WHERE id_evento = %s AND numero = %s
            """, (reserva["cantidad_asientos"], evento, origen))
            conexion.execute("""
                UPDATE ocurrencias SET ocupados = ocupados + %s WHERE id_evento = %s AND numero = %s
            """, (cantidad, evento, destino))
        modificada = conexion.execute("""
            UPDATE reservas SET ocurrencia = %s, cantidad_asientos = %s
            WHERE id_reserva = %s RETURNING *
        """, (destino, cantidad, reserva["id_reserva"])).fetchone()
        modificada["fecha"] = nueva["fecha"]
    return {"reserva": modificada, "libres": libres - necesarios}


def cancelar(conexion, peticion):
    """Elimina la reserva y libera los asientos. Cancelaciones notificará al cliente."""
    with conexion.transaction():
        reserva = buscar_reserva(conexion, peticion, bloquear=True)
        fila = conexion.execute("""
            SELECT * FROM ocurrencias WHERE id_evento = %s AND numero = %s FOR UPDATE
        """, (reserva["id_evento"], reserva["ocurrencia"])).fetchone()
        conexion.execute("""
            UPDATE ocurrencias SET ocupados = ocupados - %s WHERE id_evento = %s AND numero = %s
        """, (reserva["cantidad_asientos"], reserva["id_evento"], reserva["ocurrencia"]))
        conexion.execute("DELETE FROM reservas WHERE id_reserva = %s", (reserva["id_reserva"],))
    return {"id_reserva": reserva["id_reserva"], "estado": "cancelada",
            "asientos_liberados": reserva["cantidad_asientos"],
            "libres": fila["capacidad"] - fila["ocupados"] + reserva["cantidad_asientos"]}


FUNCIONES = {"consulta": consultar, "reserva": reservar, "modificacion": modificar, "cancelacion": cancelar}


def serializable(valor):
    """Convierte únicamente las fechas de PostgreSQL a texto JSON."""
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    if isinstance(valor, dict):
        return {clave: serializable(dato) for clave, dato in valor.items()}
    if isinstance(valor, list):
        return [serializable(dato) for dato in valor]
    return valor


def procesar(conexion, peticion):
    """Selecciona la función y construye una respuesta uniforme para los servicios."""
    identificador = None
    operacion = None
    try:
        if not isinstance(peticion, dict):
            raise ErrorPeticion("MENSAJE_INVALIDO", "La petición debe ser un objeto JSON.")
        identificador = texto(peticion, "id")
        operacion = texto(peticion, "operacion")
        if operacion not in FUNCIONES:
            raise ErrorPeticion("OPERACION_INVALIDA", "Use consulta, reserva, modificacion o cancelacion.")
        datos = FUNCIONES[operacion](conexion, peticion)
        return {"id": identificador, "operacion": operacion, "ok": True,
                "codigo": "OK", "mensaje": "Operación completada.", "datos": serializable(datos)}
    except ErrorPeticion as exc:
        return respuesta_error(exc.codigo, str(exc), identificador, operacion)
    except psycopg.Error as exc:
        # Los bloques transaction revierten cambios. No exponer SQL ni credenciales.
        logging.error("Fallo PostgreSQL id=%s tipo=%s", identificador, type(exc).__name__)
        return respuesta_error("ERROR_BD", "No se pudo completar la operación en PostgreSQL.",
                               identificador, operacion)
