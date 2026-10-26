# Estado del Proyecto: Rama `features-Alejandro`

**Estado de Git:** 21 commits por delante de `main` y ninguno por detrás. Hay un cambio sin *commitear* en `consumers_main.py`.  
**Compilación/Sintaxis:** Todo el código compila. Se revisó mediante lectura de archivos y pruebas puntuales de `crear_rta`. No se levantó el sistema completo al no haber un punto de entrada funcional (ver punto crítico).

---

## Resumen

El código ocupa aproximadamente **430 líneas**. Actualmente no es posible arrancar el sistema de punta a punta. Únicamente la capa de consumidores cuenta con un punto de entrada, pero no hay servicios activos al otro lado para procesar las solicitudes.

Se cuenta con una primera versión de:
* Mensajes y configuración comunes.
* Cliente y generador de carga.
* Gestor de Transacciones (GT).
* Lógica del servicio RMC (reservas, modificaciones y consultas).

El resto de los componentes está vacío.

---

## Lo Desarrollado

| Archivo | Líneas | Estado |
| :--- | :---: | :--- |
| `comun/mensajes.py` | 82 | **Completo en lo básico.** Define `Peticion` y `Respuesta` como `TypedDict`, los diccionarios de tipos, estados y motivos, `crear_req`, `crear_rta`, `codificar` y `decodificar` (JSON). |
| `comun/config.py` + `.env` | 20 / 14 | Carga *hosts* y puertos. `time_out_sockets` solo asigna `RCVTIMEO` de 3 s y `LINGER` en 0. |
| `capa_consumidores/cliente.py` | 85 | **Funcional.** Cliente con socket `REQ` hacia el GT, e implementación de `consultar_evento`, `reservar_evento` y `procesar_rta` (solo imprime respuestas de `FALLO`). |
| `capa_consumidores/carga_clientes.py` | 75 | Genera carga automática con 20 solicitudes por minuto y 60% de consultas. Reserva eventos `E1`–`E50` con 1–4 asientos y fechas correspondientes a enero de 2026. |
| `capa_servicios/gestor_transacciones/gestor_de_transacciones.py` | 59 | **Solo canal síncrono.** `ROUTER` (clientes, puerto 5555) y `DEALER` (RMC, puerto 5556) con un `Poller` que reenvía *frames* en ambos sentidos. |
| `capa_servicios/servicio_RMC/servicio_rmc.py` | 58 | **Parcial.** Contiene `Cliente_persistencia` (`REQ` hacia persistencia) y `Servicio_RMC`. `consultar_eventos` reenvía a persistencia. `crear_reserva` consulta disponibilidad y envía `AGREGAR_RESERVA`. `modificar_reserva` retorna "no implementado". |

---

## Cambios Recientes (En Desarrollo)

* **Últimos commits (24 y 25 de octubre):** Trabajo en la capa de consumidores: reescritura de `cliente.py` y creación de `consumers_main.py` (menú interactivo).
* **Eliminación de puntos de entrada:** Se eliminó `capa_servicios/main.py` (70 líneas, encargado del arranque de GT y RMC). Quedaron vacíos `service_main.py` y `persistence_main.py` (este último renombrado desde `main.py`).
* **Cambio pendiente (sin commit):** Se agregó `re.fullmatch(regex_fecha, mes)` en la Opción 1 del menú. Presenta dos problemas:
  1. El resultado de la validación se descarta.
  2. La *regex* valida un formato de fecha `YYYY-MM-DD`, pero la opción solicita un mes en texto (ej. `"noviembre"`).
* **Incompletitud en `consumers_main.py`:**
  * Opción 2 (*reservar*): solicita los datos pero no invoca `reservar_evento`.
  * La rama `len(sys.argv) == 2` está inconclusa (`...`).
  * `int(input())` carece de manejo de excepciones.
  * Si ocurre un *timeout*, `recv_string` lanza `zmq.Again` sin ser capturado.
* **Persistencia con SQLAlchemy:** Existe una guía en `Guias/`. Tras borrarse una versión previa completa (commit `236b145` borrado en `4545b5e`), se plantea reescribir la capa a mano.

---

## Pendientes

### Primera Entrega (Vencida: 11 de Octubre)
Exigía la arquitectura base funcional con consulta y reserva corriendo de punta a punta.

1. **Persistencia (`persistence_main.py` - 0 bytes):**
   * Implementar servicio `REP` en el puerto 5558.
   * Definir modelos SQLAlchemy y establecer conexión con PostgreSQL.
   * Carga inicial: 50 eventos en un mismo mes, 20 con dos ocurrencias y 100 asientos cada uno.
   * Manejadores para `CONSULTA`, `CONSULTA_DISPONIBILIDAD` y `AGREGAR_RESERVA`.
   * Lógica de liberación de asientos para cancelación.
2. **Punto de Entrada de Servicios (`service_main.py` - vacío):**
   * Implementar el arranque e inicialización de GT y RMC.
3. **Bucle del RMC:**
   * Configurar socket `REP` para conectar al `DEALER` del GT.
   * Despachar peticiones por tipo a los métodos correspondientes en `Servicio_RMC`.
4. **Cliente:**
   * Manejo de *timeouts*, visualización de resultados de consultas y corrección de la Opción 2 del menú.

### Segunda Entrega (22 de Noviembre - Faltan 28 días)

5. **Modificación de Reserva:**
   * Permitir cambio en el número de asientos o fecha de otra ocurrencia del mismo evento (operación atómica con *rollback* que preserve la reserva intacta en caso de rechazo).
6. **Cancelación Asíncrona y Notificación:**
   * Implementar la clase `Cancelacion_y_notificacion` (actualmente vacía).
   * Configurar el GT para enrutar `CANCELACION` vía `PUSH` (puerto 5557, `GT_PORT_CANC`) y retornar `ACK`.
   * Servicio de cancelación actuando como `PULL`, liberando asientos y notificando al cliente.
   * Cliente con socket `PULL` (o `SUB`), enviando datos de contacto en la solicitud.
7. **Escalabilidad:**
   * Despliegue de réplicas del servicio RMC y de la base de datos.
8. **Tolerancia a Fallos:**
   * Detección y sustitución transparente de caídas en GT y RMC.
9. **Generador de Carga:**
   * Soportar operaciones de modificación y cancelación.
   * Parametrización porcentual por tipo de operación (actualmente con parámetros fijos en código).
10. **Pruebas y Documentación:**
    * Pruebas de rendimiento con 3, 5 y 8 clientes simultáneos (duración 2–3 minutos) expuestas en tablas y gráficos.
    * Diagramas finales, informe de resultados, video demostrativo de 7 minutos y actualización del `README.md`.

---

## Errores Concretos Encontrados

1. **Invocación incorrecta de `crear_rta` (`servicio_rmc.py:54,56,59`):**  
   Se invoca `crear_rta` con 3 argumentos cuando su firma requiere 4 (`estado`, `peticion_realizada`, `motivo`, `datos`), lo que genera un `TypeError`. Cualquier rechazo por falta de cupo o evento inexistente rompe el proceso RMC.
2. **Deficiencias en `crear_rta` (`mensajes.py`):**  
   * Retorna `None` de forma silenciosa si un código no existe.
   * Exige un motivo válido inclusive en respuestas de éxito (`EXITO`). Al no existir un motivo tipo `"ninguno"`, las respuestas exitosas quedan etiquetadas erróneamente (por ejemplo, con `SIN_CUPO`).
3. **Manejo de excepciones en `crear_req` (`mensajes.py:49`):**  
   Si el tipo no existe, la sentencia `else` arroja `KeyError` en lugar de gestionar un rechazo estructurado.
4. **Ambigüedad en `crear_reserva` (`servicio_rmc.py:39`):**  
   Aplica `decodificar(peticion)` sobre un argumento sin tipo garantizado (`str` o `dict`), provocado por la ausencia del bucle de recepción.
5. **Incompatibilidad de formato de fecha:**  
   El cliente envía la fecha con formato `%Y/%m/%d`, mientras que la *regex* del menú valida `YYYY-MM-DD`.
6. **Error de asignación en `Cliente.__init__(nombre, id)`:**  
   En `carga_clientes.py:65`, `Cliente(1)` asigna `1` al parámetro `nombre` en lugar de `id`. El `id` coincide únicamente por el contador interno.
7. **Estado del Socket `REQ` tras Timeout:**  
   Al ocurrir un *timeout*, el socket `REQ` de ZeroMQ entra en un estado inválido y debe ser recreado, lógica que no está implementada.
8. **Gestión de Contextos en GT:**  
   Instancia dos objetos `zmq.Context()` independientes (uno por socket), no invoca `iniciar_poller()` y enruta el tráfico hacia el `DEALER` sin filtrar por tipo de mensaje.
9. **Ejecución al Importar (`carga_clientes.py:65`):**  
   Ejecuta `main_carga()` directamente en el cuerpo del archivo sin la cláusula `if __name__ == "__main__":`.
10. **Seguridad en `.env`:**  
    El archivo está versionado en Git conteniendo direcciones IP reales y *placeholders* (`*`) para `DB_URL` y `DB_PASSWD`.

---

## Estado del README

El archivo `README.md` indica que `service_main.py` "arranca GT o RMC", comportamiento previo al commit `17239e0`. Dado que el archivo se encuentra vacío, las instrucciones de ejecución para la capa de servicios no son funcionales. La tabla de estado general se mantiene correcta con excepción del punto mencionado.

---

## Orden de Trabajo Sugerido

1. **Persistencia:** Desarrollar `persistence_main.py` y la integración con la base de datos para desbloquear las pruebas de integración.
2. **Bucle de Servicio RMC y `service_main.py`:** Implementar el socket `REP` y el punto de entrada de la capa de servicios.
3. **Corrección de Mensajería y Cliente:** Ajustar `crear_rta`, corregir las firmas de llamada y finalizar el cliente para habilitar la prueba *end-to-end* de consulta y reserva.
4. **Modificación:** Implementar la lógica de actualización de reservas de forma atómica.
5. **Cancelación Asíncrona:** Configurar sockets `PUSH`/`PULL` y la clase de notificaciones.
6. **Escalabilidad y Tolerancia a Fallos:** Desplegar réplicas y manejo transparente de caídas.
7. **Pruebas de Carga y Documentación:** Ejecutar métricas de rendimiento, generar gráficos, redactar el informe y grabar el video demostrativo.