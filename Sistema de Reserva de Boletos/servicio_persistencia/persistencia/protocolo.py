"""Formato compartido de errores; no importa bibliotecas de base de datos."""


def respuesta_error(codigo, mensaje, id=None, operacion=None):
    return {"id": id, "operacion": operacion, "ok": False,
            "codigo": codigo, "mensaje": mensaje, "datos": {}}
