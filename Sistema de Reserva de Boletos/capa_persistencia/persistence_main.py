from capa_persistencia.servicio_persistencia import Servicio_Persistencia as SP


def main():
    servicio_persistencia = SP()
    servicio_persistencia.conectar_con_bd()


if __name__ == "__main__":
    main()