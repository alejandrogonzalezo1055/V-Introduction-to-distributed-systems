# Sistema de Reserva de Boletos: entender, ejecutar y probar

Este documento explica **el código que está en esta carpeta**, conservando sus
clases, sus tres capas y su contrato JSON. El objetivo de esta corrección es que
funcionen consulta y reserva y que puedas explicar su recorrido. No se añadieron
otras arquitecturas ni funcionalidades de la segunda entrega.

## 1. Qué hay actualmente y qué pide la primera entrega

El enunciado y la rúbrica están en `../EnunciadoProyecto_sdp_Reserva de boletas.pdf`.
Para la primera entrega se pide la arquitectura base con consulta y reserva,
README, código y el informe de diseño. La rúbrica de esa entrega asigna 1 punto
al diseño, 1 a documentación, 1 a implementación y 2 a sustentación, sobre 5.
Por eso entender el recorrido y poder explicar el código importa tanto como
mostrar una reserva. El despliegue solicitado distribuye las capas entre tres
máquinas físicas o virtuales.

Este código implementa la cadena síncrona de consulta y reserva. Modificación
responde `NO_IMPLEMENTADO`; cancelación/notificación sigue como clase pendiente.
El GT actual es un puente al RMC: todavía no separa un canal de cancelaciones.
Que exista un archivo o una constante de cancelación no significa que esa
funcionalidad ya opere. Tampoco hay sustitución automática de GT/RMC ni réplicas.
El informe diseña más de lo que esta versión ejecuta: hay que reconocerlo al sustentar.

## 2. Las tres capas y sus conexiones

```text
CONSUMIDORES                  SERVICIOS                      PERSISTENCIA
Cliente REQ -> 5555 ROUTER [GT] DEALER 5556 <- REP [RMC]
                                                   REQ -> 5558 REP -> PostgreSQL 5432
```

La flecha GT/RMC tiene una particularidad: **RMC inicia la conexión TCP hacia el
DEALER del GT**, pero el trabajo viaja desde GT hacia RMC. Quién inicia una conexión
no determina quién solicita el trabajo.

| Puerto | Quién escucha con bind | Quién conecta con connect | Capa |
| --- | --- | --- | --- |
| 5555 | ROUTER del GT | REQ del cliente | Entrada a negocio |
| 5556 | DEALER del GT | REP del RMC | Comunicación local dentro de negocio |
| 5558 | REP de persistencia | REQ del RMC | Negocio → almacenamiento |
| 5432 | PostgreSQL | SQLAlchemy/psycopg de persistencia | Dentro de almacenamiento |
| 5557 | Nadie actualmente | Nadie actualmente | Reservado para cancelaciones futuras |

`bind("tcp://*:5555")` significa escuchar en las interfaces de **esa máquina**.
`connect("tcp://10.0.0.20:5555")` significa buscar al servidor en esa dirección.
`*` y `0.0.0.0` no son destinos que deba anunciar el servidor a los clientes.
`127.0.0.1` siempre significa la máquina desde la que se está ejecutando el programa;
no permite llegar a una VM distinta.

## 3. Problemas encontrados y correcciones

| Problema verificado | Consecuencia | Corrección |
| --- | --- | --- |
| `DB_URL=*` en `comun/.env` | Persistencia falla antes de iniciar | URL PostgreSQL local coherente con compose |
| IP de las VM guardadas como configuración del portátil | Las pruebas locales buscan otras máquinas | `.env` local; se pueden exportar IP reales para las VM |
| `main_carga()` fuera de la condición `__main__` | Importar consumidores ya intenta conectarse y generar carga | Ejecutar carga solo si se invoca el módulo |
| RMC aplica `json.loads` a una petición ya decodificada | La reserva termina en error antes de consultar disponibilidad | Usar directamente el diccionario recibido |
| RMC espera persistencia sin timeout | Una IP incorrecta detiene el flujo indefinidamente | Límite de espera y respuesta `TIEMPO_AGOTADO` |
| Respuestas de rechazo con otro UUID | El consumidor no puede asociarlas correctamente | Conservar el UUID original en todo el recorrido |
| Demostración pedía E1 el 7 de noviembre | Esa ocurrencia no se genera: E1 está el 1 y el 15 | Elegir una fecha que devuelve la consulta |
| Carga reservaba fechas aleatorias de enero | Casi todo se rechazaba por evento/fecha inexistentes | Elegir evento y fecha juntos del catálogo consultado |
| Conversión `int(True)` o `int(1.5)` | Aceptaba cantidades que no son enteros del contrato | Validar el tipo y el rango sin convertirlos silenciosamente |
| Cargar datos borraba las tablas siempre | Repetir el comando borraba las reservas | Borrado únicamente con `--reiniciar` explícito |

Estos son problemas reproducibles del código/configuración. Sin las VM y sus
logs no se puede afirmar si también hubo firewall, IP equivocada o aislamiento
de red en la presentación.

## 4. Prueba automática local: no necesitas tres VM

La carpeta actual es:

```bash
cd '/home/mai/Documents/Trabajo/V-Introduction-to-distributed-systems/Sistema de Reserva de Boletos'
```

Ya se preparó un entorno `.venv` en este equipo. Actívalo:

```bash
source .venv/bin/activate
python -m unittest discover -s tests -v
```

Para una instalación nueva:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

Las pruebas necesitan Docker funcionando. Crean un PostgreSQL 16 temporal con
puerto libre y datos en memoria, arrancan **los mismos main.py** de persistencia,
GT y RMC en procesos separados y conectan los consumidores reales. Al terminar,
cierran los procesos y eliminan su contenedor. No usan `srb-postgres`, su volumen
ni su base de demostración. Solo generan archivos temporales fuera del proyecto.

Hay 11 pruebas: contrato/UUID, importación sin carga automática, datos iniciales,
consulta por mes y año, reserva y rechazo sin cambios, validaciones, clientes
concurrentes, mensajes malformados, rollback de una escritura fallida, protección
de carga inicial, comandos de demostración/carga/estado y desconexión de persistencia.
Varios casos se agrupan dentro de una misma prueba.

Un resultado `OK` sin omisiones confirma la prueba. Si aparece `skipped` porque
falta Docker, la integración no se ejecutó y no se debe presentarlo como éxito.
El mensaje de PostgreSQL inducido en la prueba de rollback es parte de esa prueba.

**Qué demuestra:** contrato compatible, mensajes que recorren las tres capas,
base real, rechazo coherente, cupo consistente y espera limitada.
**Qué todavía no demuestra:** IP y firewall de la Universidad, tres hosts aislados,
latencias entre VM, escalabilidad ni recuperación transparente ante fallos.

## 5. Demostración manual local en cuatro terminales

Desde la carpeta anterior, activa `.venv` en **cada terminal**. Los servidores
permanecen abiertos hasta pulsar `Ctrl+C`.

### Preparar PostgreSQL una sola vez

El `compose.yaml` ya describe la base local. Si tienes Docker Compose:

```bash
docker compose up -d db
```

En este equipo Docker está disponible pero el comando `docker compose` no estaba
instalado durante la revisión. Puedes usar directamente el equivalente:

```bash
docker run -d --name srb-postgres \
  -e POSTGRES_USER=srb -e POSTGRES_PASSWORD=srb -e POSTGRES_DB=srb \
  -p 127.0.0.1:5432:5432 \
  -v srb_pgdata_local:/var/lib/postgresql/data postgres:16
```

Usa una sola alternativa. Si ya existe ese contenedor, arráncalo con
`docker start srb-postgres`. Si proviene de una instalación anterior, sus
credenciales deben coincidir con las de `DB_URL`; cambiar variables no cambia
la contraseña de un volumen que ya estaba inicializado.

```bash
docker exec srb-postgres pg_isready -U srb -d srb
python -m capa_persistencia.cargar_datos
```

La carga genera `datos/eventos.json` si falta y lo importa: 50 eventos, 20 dobles,
70 ocurrencias y 100 asientos por ocurrencia. El mes predeterminado es noviembre
de 2026. Puedes entregar otro JSON con el mismo formato para los casos del profesor.
Si hay eventos existentes, se detiene conservando los datos.

### Terminal 1: almacenamiento

```bash
python -m capa_persistencia.main
```

Debe mostrar el estado inicial y `[PERSISTENCIA] escuchando en :5558`.
Si solo quieres ver el estado, sin iniciar un segundo servidor:

```bash
python -m capa_persistencia.main --estado
```

### Terminal 2: negocio GT

```bash
python -m capa_servicios.main gt
```

### Terminal 3: negocio RMC

```bash
python -m capa_servicios.main rmc
```

### Terminal 4: consumidor

```bash
python -m capa_consumidores.main caso
```

En una base nueva: consulta de noviembre → reserva de 2 puestos en una fecha
existente → rechazo de una reserva superior a capacidad → consulta de nuevo.
El primer evento devuelto es E1 el `2026/11/01`: debe quedar con 2 ocupados,
98 libres y una reserva persistida. La prueba rechazada no crea otra reserva.
Repetir `caso` crea otra reserva exitosa; el UUID todavía no evita duplicados.

Desde una terminal adicional, o después de terminar `caso`, compara el estado:

```bash
python -m capa_persistencia.main --estado
```

Para reiniciar deliberadamente la demostración, detener primero los servidores:

```bash
python -m capa_persistencia.cargar_datos --reiniciar
```

Ese comando borra las tablas de reserva/eventos/ocurrencias y las vuelve a cargar.
No se ejecuta automáticamente durante el funcionamiento del sistema.

## 6. El mensaje exacto y la respuesta

Petición de reserva del cliente:

```json
{
  "uuid": "identificador-unico-de-la-peticion",
  "tipo": "RESERVA",
  "id_cliente": 1,
  "datos": {
    "id_evento": "E1",
    "fecha": "2026/11/01",
    "n_asientos": 2
  }
}
```

Respuesta de éxito en una base nueva:

```json
{
  "uuid": "identificador-unico-de-la-peticion",
  "estado": "EXITO",
  "motivo": null,
  "datos": {
    "id_reserva": 1,
    "id_evento": "E1",
    "fecha": "2026/11/01",
    "n_asientos": 2
  }
}
```

El ID de reserva puede ser otro. `uuid` identifica la solicitud completa;
`id_cliente` al consumidor y `id_reserva` a la fila guardada. Son cosas distintas.
RMC conserva el UUID al cambiar `tipo` a `CONSULTA_DISPONIBILIDAD` y después a
`AGREGAR_RESERVA`. El valor del UUID permite seguir el flujo en los cuatro logs.

`EXITO` significa operación confirmada; `FALLO` es rechazo de negocio como
`SIN_CUPO`; `ERROR` representa problemas como petición inválida o timeout.
`motivo: null` corresponde a éxito sin causa de rechazo.

## 7. Cómo estudiar el código, función por función

Los archivos contienen comentarios junto a los bloques importantes. Conviene
leerlos en el orden siguiente y seguir una sola reserva antes de estudiar la carga.

### 7.1 `comun/mensajes.py`: el contrato

`peticiones`, `estados_rta` y `motivos_rechazo` son diccionarios de constantes:
por ejemplo, `peticiones['R']` devuelve el texto `RESERVA` que viaja por la red.
No son servidores ni ejecutan operaciones.

`Peticion` y `Respuesta` heredan de `TypedDict`. Describen al editor los nombres
y tipos esperados; no crean una validación automática. Por eso existe además
`validar_peticion`, que revisa los datos realmente recibidos.

`crear_req` construye el diccionario y genera un UUID cuando todavía no hay uno.
El parámetro `uuID` permite conservar el UUID original entre capas.
`crear_rta` traduce las constantes cortas y conserva ese mismo UUID.
`codificar` usa `json.dumps`: diccionario → texto. `decodificar` usa `json.loads`:
texto → dato Python. Decodificar dos veces era el error de reserva del RMC.

### 7.2 `comun/config.py` y `comun/.env`: dónde está cada proceso

`Path(__file__).with_name('.env')` busca el archivo junto a `config.py`, aunque
la terminal cambie de ubicación. `load_dotenv(..., override=False)` carga sus
valores y respeta variables ya exportadas en la terminal.

`os.getenv` lee cada variable. Los `HOST_*` son IP de destinos; los puertos indican
el proceso destino. `DB_URL` es una URL de PostgreSQL, no un endpoint de ZeroMQ.
`DB_PASSWD` se conserva por compatibilidad pero no se utiliza: la URL contiene
las credenciales. `HOST_CLI` y `GT_PORT_CANC` tampoco abren nada por sí mismos.

`time_out_sockets` configura milisegundos de envío y recepción y `LINGER=0`.
Este último permite cerrar un socket sin esperar mensajes pendientes. El cliente
espera 10000 ms y cada llamada RMC→persistencia, 3000 ms por defecto. Estas esperas
se pueden ajustar con `TIMEOUT_CLIENTE_MS` y `TIMEOUT_PERSISTENCIA_MS`.
No se aplican esos timeouts al servidor que simplemente espera el próximo trabajo.

### 7.3 `capa_consumidores/cliente.py`: el consumidor

El constructor guarda ID, nombre y recursos inicialmente vacíos. `@property`
define cómo leer una propiedad y `@...setter` cómo asignarla; por ejemplo, `ID`
se almacena en `_ID`. El prefijo `_` es una convención de uso interno.

`conectar_con_gt` crea un contexto y un socket REQ. El contexto administra
recursos de ZeroMQ; el socket es el canal concreto. `connect` establece como
destino al GT. Una llamada a `connect` por sí sola no demuestra que el servidor
esté atendiendo: ZeroMQ puede poner mensajes en cola mientras se conecta.

`enviar_peticion` convierte el dict a texto, envía y espera la respuesta. Después
comprueba su UUID. Si vence la espera, responde `TIEMPO_AGOTADO` y reemplaza el
REQ porque ese socket había quedado esperando. No repite la reserva: podría
haberse guardado y haberse perdido solo la respuesta.

`consultar_evento` crea `CONSULTA` con mes y, opcionalmente, año.
`reservar_evento` crea `RESERVA` y convierte `date` a `YYYY/MM/DD` con `strftime`.
`cerrar_socket` y `terminar_contexto` liberan recursos al finalizar.
`procesar_rta` mira el valor de `estado`; la mera presencia de ese campo no indica fallo.

### 7.4 `capa_servicios/gestor_transacciones/gestor_de_transacciones.py`: el GT

`iniciar_sockets` crea ROUTER para consumidores y DEALER para RMC. Ambos hacen
`bind`, por eso se conectan a la máquina de negocio. `Poller` permite esperar
actividad de cualquiera de los dos sockets.

`iniciar_gestor` recibe mensajes multipartes con `recv_multipart` y los reenvía
con `send_multipart`. No traduce ni altera el JSON. Cuando llega una petición,
ROUTER agrega una identidad de conexión; es la ruta de regreso al cliente.

El mensaje tiene la envoltura `[identidad_cliente, separador_vacío, cuerpo_JSON]`.
Conservar todos los frames permite que REP guarde la ruta y que GT entregue
la respuesta al consumidor correcto. Enviar únicamente `frames[-1]` perdería
esa información. La identidad del socket no es el UUID del JSON.

El GT no consulta SQL, no decide cupo y no crea reservas. Tampoco esta versión
activa todavía el canal de cancelaciones: es un puente síncrono hacia RMC.

### 7.5 `capa_servicios/main.py`: arrancar los procesos de negocio

`arrancar_gt` crea el objeto gestor y entra en su bucle. `arrancar_rmc` conecta
un REP al DEALER del GT y crea el mensajero que hablará con persistencia.
El diccionario `operaciones` selecciona el método según `tipo`.

Cada recepción se decodifica una vez y se valida. El REP siempre envía una
respuesta, aun si el JSON es inválido; de lo contrario no podría recibir la
siguiente petición. `finally` libera los recursos tanto si hay error como si
el usuario interrumpe con `Ctrl+C`.

### 7.6 `capa_servicios/servicio_RMC/servicio_rmc.py`: negocio

`I_Servicio_RMC` hereda de `ABC`: declara los métodos obligatorios del servicio.
`@abstractmethod` impide instanciar una subclase que no los implemente. `pass`
solo marca un cuerpo vacío dentro de la interfaz.

`Cliente_persistencia` es un cliente interno de RMC. Su REQ conecta con la IP
real de almacenamiento. No es el cliente del usuario y no conoce credenciales SQL.
`enviar` codifica la petición, espera una respuesta y verifica el UUID. Ante
timeout devuelve error, sin inventar que el evento no existe.

`Servicio_RMC.consultar_eventos` reenvía la consulta. `crear_reserva` usa el
**diccionario ya recibido**, valida la cantidad y consulta disponibilidad. Si
hay cupo, envía `AGREGAR_RESERVA`. Consultar cupo y reservar son dos mensajes,
por lo que otra solicitud podría ocupar asientos entre ambos. La escritura
final en persistencia debe volver a comprobarlo de forma atómica.

`modificar_reserva` devuelve `NO_IMPLEMENTADO`: no modifica nada. El archivo
`cancelacion_y_notificacion.py` también es un marcador pendiente.

### 7.7 `capa_persistencia/modelos.py`: tablas y relaciones

`Base` es la base declarativa de SQLAlchemy. Su metadata contiene la definición
de las tablas. `Mapped[T]` declara el tipo Python; `mapped_column` describe cómo
se almacena la columna. `primary_key=True` identifica una fila de manera única.

`Evento` guarda la actividad. `Ocurrencia` guarda una fecha de ese evento, capacidad
y ocupados. `Reserva` enlaza cliente, ocurrencia y número de puestos.
`ForeignKey` hace cumplir las referencias entre tablas. `relationship` permite
trabajar con esos vínculos como objetos Python; no crea otra conexión de red.

`UniqueConstraint` impide duplicar evento/fecha. `CheckConstraint` impide ocupados
negativos o superiores al cupo y reservas con cantidad no positiva. Las validaciones
Python dan errores comprensibles; las restricciones SQL protegen la integridad.
El campo `estado` de reserva está preparado para un uso futuro, no activa cancelaciones.

### 7.8 `conexion_bd.py` y `utilidades.py`

`create_engine` configura el acceso a PostgreSQL; no es una nueva base.
`sessionmaker(engine)` fabrica sesiones para las operaciones. `esperar_bd`
intenta un `SELECT 1` hasta que PostgreSQL esté disponible. No crea tablas ni datos.

`numero_mes` traduce noviembre a 11. `leer_fecha` convierte texto con barras a
un `date`; `escribir_fecha` vuelve al texto que JSON puede transportar. La base
trabaja con una fecha real, no con cadenas para calcular el mes.

### 7.9 `capa_persistencia/servicio_persistencia.py`: las consultas y la transacción

`responder` conserva el UUID recibido y construye el formato compartido.
La clase abstracta declara las operaciones; `Servicio_persistencia` las concreta.

`consultar_eventos` valida el mes/año y usa `select` para elegir columnas,
`join` para relacionar evento y ocurrencia, `where` para filtrar y `order_by`
para ordenar. `.all()` obtiene las filas y una comprensión de lista las convierte
a diccionarios. Una fila representa una ocurrencia: por eso hay 70 filas para
50 eventos iniciales. Si se omite año, conserva el comportamiento del contrato
original y devuelve ese mes de todos los años almacenados.

`consultar_disponibilidad` busca evento/fecha; `.scalars(...).first()` obtiene
un objeto `Ocurrencia` o `None`. Devuelve exactamente `capacidad_total` y
`ocupacion`, los nombres que espera RMC.

`agregar_reserva` valida cantidad, cliente, evento y fecha. Dentro de
`SessionLocal.begin()` obtiene la ocurrencia y ejecuta un UPDATE condicional:
solo suma ocupados **si los puestos todavía caben**. `rowcount == 0` significa
que no se actualizó ninguna fila y devuelve `SIN_CUPO`.

Después crea `Reserva`, la añade con `session.add` y ejecuta `session.flush`.
`flush` envía el INSERT y obtiene el ID generado; **todavía no es COMMIT**.
Al salir del bloque `begin`, COMMIT confirma tanto el aumento de ocupados como
la reserva. Si el INSERT o COMMIT falla, la transacción se revierte. La respuesta
de éxito se devuelve después de ese bloque. No debe quedar un aumento de
ocupados sin su correspondiente reserva guardada.

`imprimir_estado` muestra las ocurrencias y el total de reservas para revisar
antes/después. `_leer_evento_y_fecha` comparte validación entre operaciones;
`@staticmethod` significa que no necesita usar el estado del objeto `self`.

### 7.10 `capa_persistencia/main.py`: servidor de almacenamiento

Este proceso espera la base, comprueba las tablas y abre REP en 5558. Recibe
bytes, decodifica JSON, valida la envoltura y elige el método en `operaciones`.
Ante errores de SQLAlchemy responde `ERROR_BD`; los rechazos de negocio conservan
su motivo. Siempre responde una vez por recepción. El modo `--estado` imprime
una foto administrativa y termina sin abrir otro socket en el mismo puerto.

### 7.11 `cargar_datos.py`, consumidores `main.py` y `carga_clientes.py`

`generar` crea datos de muestra; `cargar` lee el JSON y guarda los eventos y sus
fechas. Es una herramienta administrativa de preparación, no un servicio de negocio.
Las tablas solo se borran con `--reiniciar`. Durante la ejecución ordinaria no se
reinicializa la base entre solicitudes.

El `main.py` del consumidor interpreta argumentos. El modo `caso` elige una fecha
que realmente existe; el modo `carga` llama al generador con parámetros explícitos.
`if __name__ == '__main__'` diferencia ejecutar un archivo de importarlo: evita
que importar la función de carga comience conexiones por sorpresa.

La carga hace una consulta inicial de catálogo, fuera de su ventana de trabajo.
Con ese catálogo elige parejas válidas de evento/fecha. `time.perf_counter`
mide intervalos; `time.sleep` espera hasta el siguiente instante previsto.
La pausa se calcula como `60 / solicitudes_por_minuto`. Cada cliente espera su
respuesta; si el servidor es lento, el ritmo solicitado puede no alcanzarse.

Los porcentajes se eligen de forma probabilística: 60% consulta no garantiza
exactamente 12 consultas entre 20 mensajes en una sola corrida. El resumen cuenta
enviadas, éxitos, fallos y errores. Eso ayuda a probar, pero todavía no reemplaza
el informe de rendimiento final con promedio, desviación, TPM y gráficos.

## 8. Pruebas de carga que puedes ejecutar solo

Con las cuatro terminales de servicios/BD funcionando, un cliente durante un minuto:

```bash
python -m capa_consumidores.main carga --id-cliente 1 --rpm 20 --porcentaje-consulta 60 --minutos 1
```

Para tres clientes simultáneos, abre tres terminales de consumidores y ejecútalos
consecutivamente lo más cerca posible:

```bash
python -m capa_consumidores.main carga --id-cliente 1 --rpm 20 --porcentaje-consulta 100 --minutos 2
```

```bash
python -m capa_consumidores.main carga --id-cliente 2 --rpm 20 --porcentaje-consulta 100 --minutos 2
```

```bash
python -m capa_consumidores.main carga --id-cliente 3 --rpm 20 --porcentaje-consulta 50 --minutos 2
```

Cada terminal crea otro proceso de cliente. Dos solo consultan y el tercero mezcla
consulta y reserva, como el escenario de 3 clientes del enunciado. Para medir
formalmente se necesitará coordinar la ventana y registrar las métricas previstas.
Los escenarios finales de 5/8 clientes incluyen modificación y no están completos
con esta versión. No basta aumentar el número de procesos para afirmar escalabilidad.

## 9. Pasar el mismo código a tres VM

Antes de copiar nada, registra la IP actual de cada VM con `ip -br address`.
Las direcciones siguientes son **ejemplos** que se reemplazan por las reales:

| VM | Capa y procesos | Ejemplo de IP |
| --- | --- | --- |
| A | Consumidores | 10.0.0.10 |
| B | Servicios: GT y RMC, dos terminales | 10.0.0.20 |
| C | Persistencia y PostgreSQL | 10.0.0.30 |

Copiar el mismo código a cada VM y crear su `.venv` allí con `requirements.txt`.
No copiar el entorno virtual del portátil: contiene rutas/binarios de otra instalación.
Desde la carpeta `Sistema de Reserva de Boletos`, activar el entorno en cada terminal.

### VM C: preparar base y arrancar almacenamiento

Iniciar PostgreSQL con el compose o comando Docker de la sección 5. La base queda
local en C y solo su persistencia tiene acceso a ella. En la terminal de persistencia:

```bash
export HOST_CAPA_PERSISTENCIA=10.0.0.30
export DB_URL='postgresql+psycopg://srb:srb@127.0.0.1:5432/srb'
python -m capa_persistencia.cargar_datos
python -m capa_persistencia.main
```

Si la base ya estaba cargada, omitir `cargar_datos`. El primer comando no borra
reservas existentes. Para un caso nuevo, decidir explícitamente si se reinicia.
La dirección de DB usa `127.0.0.1` porque PostgreSQL y persistencia viven en C.

### VM B: dos terminales para GT y RMC

En ambas terminales:

```bash
export HOST_CAPA_SERVICIOS=10.0.0.20
export HOST_CAPA_PERSISTENCIA=10.0.0.30
```

En una, `python -m capa_servicios.main gt`; en otra,
`python -m capa_servicios.main rmc`. Son dos procesos de la misma capa.
GT escucha en las interfaces de B; RMC se conecta a GT en B y a persistencia en C.
Las variables exportadas tienen prioridad sobre el `.env` de demostración local.

### VM A: consumidores

```bash
export HOST_CAPA_SERVICIOS=10.0.0.20
python -m capa_consumidores.main caso
```

El consumidor no necesita credenciales SQL ni conectarse a 5432. Tampoco conecta
con persistencia directamente. Puede ejecutar carga con los parámetros de la sección 8.

### Comprobar la red antes del caso completo

Desde A, comprobar el puerto del GT en B:

```bash
python -c 'import socket; s = socket.create_connection(("10.0.0.20", 5555), 3); print("TCP al GT correcto"); s.close()'
```

Desde B, comprobar persistencia en C:

```bash
python -c 'import socket; s = socket.create_connection(("10.0.0.30", 5558), 3); print("TCP a persistencia correcto"); s.close()'
```

Son comprobaciones de conexión TCP; no envían peticiones ZeroMQ ni prueban el
contrato JSON. Después hay que ejecutar `caso` y comprobar los cuatro logs.
`ping` por sí solo no demuestra que un puerto de aplicación esté accesible.

En B y C, `ss -ltn` permite ver si alguien escucha en 5555/5556 y 5558,
respectivamente. Si la conexión TCP falla, comprobar: IP actual, servidor iniciado,
bind correcto, puertos iguales y reglas de firewall entre las VM.
El puerto 5432 puede quedar local en C; 5556 conecta procesos dentro de B.

| Síntoma | Qué revisar |
| --- | --- |
| `ModuleNotFoundError` | Estar en la carpeta correcta y usar `python -m`, con `.venv` activo |
| `Falta DB_URL` | Variable de conexión y archivo `comun/.env` |
| `[BD] no disponible` | Contenedor, puerto, usuario/clave y base indicados por DB_URL |
| Cliente agota espera y GT no imprime petición | Dirección/puerto cliente→GT y firewall A→B |
| GT imprime petición pero RMC no la recibe | RMC activo y conectado al 5556 del GT |
| RMC devuelve `TIEMPO_AGOTADO` | IP/puerto de persistencia, servidor iniciado y firewall B→C |
| `NO_EXISTE` al reservar | Pareja evento/fecha: consultar el catálogo antes de elegir |
| `Address already in use` | Ya hay otro proceso escuchando en ese puerto |

## 10. Qué explicar en la sustentación

Puedes apoyar tu explicación en esta reserva concreta:

“Un cliente pide dos puestos en E1 el 1 de noviembre. Construye una petición con
UUID y la envía por REQ al GT. GT conserva la ruta del cliente y la reenvía por
DEALER al REP del RMC. RMC consulta disponibilidad a persistencia y solicita la
reserva. Persistencia vuelve a comprobar cupo al actualizar ocupados, guarda la
reserva en la misma transacción y confirma. La respuesta vuelve por RMC y GT con
el mismo UUID. Si no hay cupo, se rechaza sin crear la reserva.”

Después demuestra: base inicial, consulta, reserva confirmada, rechazo, base final.
Señala en el código `flush` y salida del bloque de transacción. Explica qué cambia
entre portátil y VM: IP de destino y ubicación de los procesos, conservando el
protocolo. Distingue timeout de recuperación: estas correcciones limitan la espera,
pero no implementan todavía la tolerancia a fallos de la segunda entrega.
