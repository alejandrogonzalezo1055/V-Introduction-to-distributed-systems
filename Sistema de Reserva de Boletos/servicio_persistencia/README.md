# Servicio de persistencia del grupo

Este componente implementa tu responsabilidad: recibir peticiones de los servicios
de reserva, consulta, modificación (RMC) y cancelación; trabajar con PostgreSQL;
y devolver el resultado por ZeroMQ. Se basa en los diagramas del informe del grupo.

```text
RMC (reserva / consulta / modificación) ──REQ──┐
                                            ├── ROUTER: persistencia ── PostgreSQL
Servicio de cancelaciones ──────────────REQ───┘
```

Los servicios envían solicitudes; persistencia escucha y responde al mismo emisor.
El socket ROUTER usa la identidad de transporte de cada REQ. El campo JSON `id`
sirve para correlacionar la petición y la respuesta. Son identificadores distintos.

## 1. Archivos y funciones

| Archivo | Qué hace |
| --- | --- |
| `persistencia/operaciones.py` | Las funciones `consultar`, `reservar`, `modificar` y `cancelar`, con SQL |
| `persistencia/servidor.py` | Recibe JSON por ROUTER, llama a la función correspondiente y devuelve JSON |
| `persistencia/cliente.py` | Funciones que importan RMC y cancelaciones para enviar sus mensajes por REQ |
| `persistencia/protocolo.py` | Formato común de errores |
| `persistencia/base_datos.py` | Conexión PostgreSQL, datos iniciales y estado administrativo |
| `persistencia/esquema.sql` | Tablas y restricciones |
| `ejemplos/*.json` | Mensajes listos para probar cada operación |
| `demo_servicios.py` | Simula las llamadas de RMC y cancelaciones a persistencia |
| `tests/test_persistencia.py` | Pruebas funcionales, transacciones, concurrencia y ZeroMQ |
| `probar_con_docker.py` | Ejecuta las pruebas con una base PostgreSQL temporal |

Hay dos conjuntos de cuatro funciones con el mismo nombre porque cumplen papeles
distintos: **cliente.py envía por red; operaciones.py ejecuta SQL en el servidor**.
Tus compañeros solo necesitan importar las de `persistencia.cliente`.

Esta carpeta es independiente del prototipo anterior `srb/`, que usaba SQLite
y otros nombres de campos. El nuevo componente sigue PostgreSQL y los nombres
`id_cliente`, `id_evento`, `ocurrencia` y `cantidad_asientos` del código del grupo.
No se han migrado los datos ni modificado el prototipo anterior.

## 2. Preparar Python

Desde una terminal:

```bash
cd '/home/mai/Documents/Trabajo/SistemasDistribuidos/Proyecto/V-Introduction-to-distributed-systems/Sistema de Reserva de Boletos/servicio_persistencia'
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Se requiere Python 3.10 o posterior. `pyzmq` maneja los mensajes y `psycopg`
conecta con PostgreSQL. El servidor PostgreSQL se ejecuta aparte de Python.

## 3. Preparar PostgreSQL

Si el grupo ya tiene PostgreSQL y una base dedicada a este componente, configura
su host, puerto, base, usuario y contraseña con las variables siguientes.
Solo la máquina de persistencia necesita estas credenciales.

Para una demostración local con Docker, puedes crear una base independiente:

```bash
export POSTGRES_PASSWORD='clave_local_de_demostracion'
docker run -d --name srb-postgres \
  -e POSTGRES_DB=boletos \
  -e POSTGRES_USER=boletos \
  -e POSTGRES_PASSWORD \
  -p 127.0.0.1:5432:5432 \
  -v srb-postgres-datos:/var/lib/postgresql/data \
  postgres:17-alpine
docker exec srb-postgres pg_isready -U boletos -d boletos
```

Esperar a que indique `accepting connections`. Docker Compose no es necesario.
El volumen conserva datos al detener el contenedor. Si ya existe este contenedor,
usa `docker start srb-postgres`. Para detenerlo: `docker stop srb-postgres`.
Si el puerto 5432 está ocupado, usa otro puerto local y ajusta `PGPORT`.

En la terminal donde iniciarás persistencia:

```bash
export PGHOST=127.0.0.1
export PGPORT=5432
export PGDATABASE=boletos
export PGUSER=boletos
export PGPASSWORD='clave_local_de_demostracion'
python -m persistencia.base_datos iniciar --mes 2026-10
```

Estos valores son de la demostración; para el servidor del grupo usa sus valores
reales. También se admite `SRB_DATABASE_URL` como cadena de conexión PostgreSQL.
No guardar credenciales reales en los archivos JSON ni en el repositorio.

La carga predeterminada crea 50 eventos; E1–E20 tienen dos ocurrencias y E21–E50
una. Cada ocurrencia tiene 100 asientos. El comando no borra ni reemplaza eventos
existentes. Puedes cambiar `--eventos`, `--dobles`, `--capacidad` y `--mes`.

## 4. Ejecutar la comunicación

En la terminal con las variables de PostgreSQL configuradas:

```bash
python -m persistencia.servidor
```

En una segunda terminal, desde esta misma carpeta, activa el entorno y ejecuta:

```bash
source .venv/bin/activate
python demo_servicios.py
```

La demo realiza por ZeroMQ: disponibilidad → reserva de 3 puestos → consulta
de esa reserva → modificación a 5 puestos → cambio a la segunda ocurrencia →
cancelación. Lee el ID que devuelve la reserva, por lo que no presupone que es 1.
Necesita cupo en E1, ocurrencias 1 y 2. Crea una reserva real y la elimina al
final; si un paso falla, se detiene y muestra el resultado para revisar el estado.

También puedes probar mensajes individuales:

```bash
python -m persistencia.cliente ejemplos/consulta_eventos.json
python -m persistencia.cliente ejemplos/consulta_disponibilidad.json
python -m persistencia.cliente ejemplos/reserva.json
```

Después de reservar, copia el `id_reserva` devuelto en los JSON de consulta,
modificación y cancelación. El valor 1 de los archivos es solo un ejemplo:

```bash
python -m persistencia.cliente ejemplos/consulta_reserva.json
python -m persistencia.cliente ejemplos/modificacion_cantidad.json
python -m persistencia.cliente ejemplos/modificacion_fecha.json
python -m persistencia.cliente ejemplos/cancelacion.json
```

Para ver las tablas antes o después, desde la máquina de almacenamiento con
las variables de PostgreSQL configuradas:

```bash
python -m persistencia.base_datos estado
```

## 5. Integración para tus compañeros

Desde esta carpeta se puede importar el paquete `persistencia`. Si el proceso
del compañero se inicia desde otra carpeta, debe agregar `servicio_persistencia`
al `PYTHONPATH`, o incorporar el paquete en la raíz común del proyecto.
En otra máquina, solo necesita el cliente, protocolo y pyzmq; el cliente no importa
psycopg ni abre conexiones de base de datos.

Ejemplo de llamadas **dentro del RMC**:

```python
from persistencia.cliente import consultar, reservar, modificar

direccion = "tcp://127.0.0.1:5557"

respuesta = reservar({
    "id": "solicitud-001",
    "id_cliente": 1,
    "id_evento": "E1",
    "ocurrencia": 1,
    "cantidad_asientos": 3,
}, direccion)

if respuesta["ok"]:
    id_reserva = respuesta["datos"]["reserva"]["id_reserva"]
    consulta = consultar({
        "id": "solicitud-002",
        "tipo": "reserva",
        "id_cliente": 1,
        "id_reserva": id_reserva,
    }, direccion)
    cambio = modificar({
        "id": "solicitud-003",
        "id_cliente": 1,
        "id_reserva": id_reserva,
        "cantidad_asientos": 5,
    }, direccion)
```

Ejemplo **dentro del servicio de cancelaciones**, una vez recibida la petición
por su canal PUSH/PULL:

```python
from persistencia.cliente import cancelar

respuesta = cancelar({
    "id": "solicitud-004",
    "id_cliente": 1,
    "id_reserva": 1,  # Usar el ID de la petición recibida.
}, "tcp://127.0.0.1:5557")

if respuesta["ok"]:
    # Aquí cancelaciones puede notificar al receptor del usuario:
    # persistencia ya confirmó COMMIT y liberó los puestos.
    print("Cancelación confirmada:", respuesta["datos"])
else:
    print("La cancelación no está confirmada:", respuesta["codigo"])
```

Las funciones agregan `operacion` y generan `id` si falta. Si el GT ya asignó un
ID, pásalo para conservarlo durante todo el recorrido. También puedes usar
`enviar_peticion(peticion, direccion)` con el JSON completo recibido del GT,
si respeta el contrato de la sección siguiente.

El gestor, los servidores completos de RMC/cancelaciones y el envío de
notificaciones siguen perteneciendo a sus componentes. `demo_servicios.py` es
un emisor para probar esta conexión; no sustituye esos servicios del grupo.

## 6. Contrato JSON

Campos comunes: `id` (texto no vacío, máximo 128 caracteres) y `operacion`.
Operaciones admitidas: `consulta`, `reserva`, `modificacion`, `cancelacion`.

| Petición | Campos adicionales |
| --- | --- |
| Consulta de eventos | `tipo: "eventos"`, `mes: "2026-10"` |
| Consulta de disponibilidad | `tipo: "disponibilidad"`, `id_evento`, `ocurrencia` |
| Consulta de una reserva | `tipo: "reserva"`, `id_cliente`, `id_reserva` |
| Reserva | `id_cliente`, `id_evento`, `ocurrencia`, `cantidad_asientos` |
| Modificar cantidad | `id_cliente`, `id_reserva`, `cantidad_asientos` |
| Modificar fecha | `id_cliente`, `id_reserva`, `ocurrencia` de destino |
| Cancelar | `id_cliente`, `id_reserva` |

`tipo` por defecto es `eventos`. `id_cliente` e `id_reserva` son enteros positivos;
`id_evento` es texto como `E1`; `ocurrencia` y `cantidad_asientos` son enteros
positivos. No se acepta `true` como si fuera el número 1. El mes incluye año:
`"octubre"` por sí solo no identifica el mes del calendario.

La modificación de fecha mantiene el evento. Si también se envía `id_evento`,
debe coincidir con el de la reserva; cambiarlo se rechaza. La fecha se obtiene
de la ocurrencia, así que no se envía una fecha suelta.

Todas las respuestas tienen `id`, `operacion`, `ok`, `codigo`, `mensaje` y `datos`.
Ejemplo de cancelación efectiva de una reserva de 5 puestos, con cupo total 100:

```json
{
  "id": "solicitud-004",
  "operacion": "cancelacion",
  "ok": true,
  "codigo": "OK",
  "mensaje": "Operación completada.",
  "datos": {
    "id_reserva": 1,
    "estado": "cancelada",
    "asientos_liberados": 5,
    "libres": 100
  }
}
```

Los errores devuelven `ok: false`, un código y `datos: {}`. Ejemplos de código:
`SIN_CUPO`, `RESERVA_NO_ENCONTRADA`, `OCURRENCIA_NO_ENCONTRADA`, `CAMBIO_INVALIDO`,
`DATOS_INVALIDOS`, `MES_INVALIDO`, `ERROR_BD` y `TIEMPO_AGOTADO`.

Los mensajes de reserva/modificación devuelven la reserva completa en
`datos.reserva` y los puestos libres en `datos.libres`. Las consultas devuelven
`datos.ocurrencias`, `datos.ocurrencia` o `datos.reserva`, según el tipo.

El archivo del grupo `ZeroMQ examples/CARGA_CLIENTES.py` aún contiene errores
de sintaxis y nombres de funciones, y usa meses sin año. Esta implementación
entrega el contrato para integrarlo; ese generador no se ejecutó ni se modificó.

## 7. Cómo se asegura la consistencia

- **Consultar:** lee eventos, disponibilidad o una reserva correspondiente al cliente.
- **Reservar:** bloquea la ocurrencia con `SELECT ... FOR UPDATE`, comprueba cupo,
  incrementa ocupados e inserta la reserva en la misma transacción.
- **Modificar:** bloquea la reserva y las ocurrencias en orden; cambia cantidad
  o fecha. Para cambiar fecha exige mismo evento, mes y año, conservando la cantidad.
  Un rechazo revierte la operación y conserva el estado anterior.
- **Cancelar:** bloquea la reserva y su ocurrencia, libera puestos y elimina la
  reserva en una sola transacción, como indica la secuencia del informe. Una
  segunda cancelación no encuentra la reserva y no vuelve a liberar puestos.

`with conexion.transaction()` confirma al terminar y revierte ante una excepción.
La respuesta de éxito se construye después de salir del bloque. Una consulta
previa de cupo no garantiza disponibilidad futura: reservar/modificar vuelven a
comprobarla dentro de su propia transacción.

No se conserva historial de reservas canceladas: se usa `DELETE`, como en el
diagrama de secuencia. La reserva activa tampoco necesita almacenar una fecha
duplicada: su fecha se obtiene de la ocurrencia. El nombre del cliente queda
fuera de este componente; solo se almacena su identificador.

Referencias técnicas: [transacciones en Psycopg](https://www.psycopg.org/psycopg3/docs/basic/transactions.html)
y [bloqueos de PostgreSQL](https://www.postgresql.org/docs/current/explicit-locking.html).

## 8. Probar automáticamente

Con Docker disponible, desde esta carpeta y con el entorno activo:

```bash
python probar_con_docker.py
```

El script crea un contenedor temporal, con puerto libre y datos en memoria,
ejecuta las pruebas y lo elimina al terminar. No usa la base de demostración
ni la base del grupo. Incluye un servidor ZeroMQ real y ejecuta la demo completa.

Alternativa con un PostgreSQL de pruebas ya existente:

```bash
export SRB_TEST_DATABASE_URL='postgresql://usuario:clave@127.0.0.1:5432/base_pruebas'
python -m unittest discover -s tests -v
```

Cada caso crea un esquema temporal con nombre aleatorio y lo elimina al terminar.
El usuario necesita permiso para crear esquemas. Si falta la variable, `unittest`
omite estas pruebas; esa omisión no demuestra que la integración funcione.

Se prueban las cuatro operaciones, propiedad de la reserva, cambios rechazados,
fechas de otro mes/año, errores de escritura con rollback, reservas concurrentes
sin sobreventa, cancelaciones simultáneas, datos confirmados visibles desde otra
conexión, JSON inválido y respuestas dirigidas al emisor correcto.

## 9. Uso entre máquinas y límites del componente

En la máquina de almacenamiento:

```bash
python -m persistencia.servidor --bind tcp://0.0.0.0:5557
```

RMC y cancelaciones usan `tcp://IP_DE_ALMACENAMIENTO:5557` como destino.
PostgreSQL puede permanecer en `127.0.0.1:5432` de esa máquina. Permitir acceso
al 5557 desde la máquina de negocio; los consumidores finales se conectan al GT.

El servidor actual atiende una petición de base de datos a la vez. ROUTER permite
identificar y atender varios emisores, pero este bucle por sí solo no ejecuta
consultas en paralelo. Los bloqueos se probaron también con conexiones PostgreSQL
concurrentes independientes.

El chequeo de `id_cliente` comprueba pertenencia respecto al identificador enviado;
no autentica al usuario. El GT/RMC deben establecer su identidad antes de reenviar.

El `id` de solicitud sirve para correlación; aún no hay tabla de deduplicación.
Ante timeout o pérdida de respuesta, no reintentar una reserva automáticamente:
puede haberse confirmado. Si se pierde la conexión con PostgreSQL, se debe revisar
la base y reiniciar el servicio. Recuperación transparente, colas durables y
deduplicación pertenecen a la etapa de tolerancia a fallos.

La llamada cancelaciones → persistencia es síncrona para saber cuándo se confirmó
el cambio. Lo asíncrono es el flujo completo del usuario: GT acepta, cancelaciones
procesa después y notifica. Este componente devuelve la confirmación de base de
datos; no envía la notificación al consumidor.
