import json
from slixmpp.exceptions import IqError, IqTimeout
from slixmpp.xmlstream import ElementBase, ET, register_stanza_plugin
import slixmpp
import prettytable
import threading
import asyncio
import aioconsole 
import base64
import time



class Server(slixmpp.ClientXMPP):

    '''
    init: Constructor de la clase Server. Inicializa los handlers de eventos y el estado de logged_in.
    '''

    def __init__(self, jid, password):
        self.email = jid
        self.old = True

        super().__init__(jid, password)
        #-----> Plugins generados por GitHub Copilot
        self.register_plugin('xep_0030')                                   # Registrar plugin: Service Discovery
        self.register_plugin('xep_0045')                                   # Registrar plugin: Multi-User Chat
        self.register_plugin('xep_0085')                                   # Registrar plugin: Chat State Notifications
        self.register_plugin('xep_0199')                                   # Registrar plugin: XMPP Ping
        self.register_plugin('xep_0353')                                   # Registrar plugin: Chat Markers
        #-------------------------------

        #-----> Handlers de eventos
        self.add_event_handler("session_start", self.start)                 # Handler para cuando se inicia sesión
        self.add_event_handler("message", self.message)                     # Handler para cuando se recibe un mensaje

        self.logged_in = False
        self.topologia = None

        self.echo_send = []
        self.echoed = []

        self.echo_times = {}  # Para guardar los tiempos de envío de echo
        self.weights_table = {}  # Tabla de pesos
        self.version = 1  # Versión inicial de la tabla de pesos

        self.traza_mensajes = []

    #-------------------------------------------------------------------------------------------------------------------
    '''
    start: Función que se ejecuta al iniciar sesión en el servidor de forma asincrónica.
    '''

    async def start(self, event):
        try:
            self.send_presence()                                            # Enviar presencia  
            self.get_roster()                                               # Obtener roster   

            await asyncio.sleep(2)
            self.old = False
            self.tabla = await self.tabla_enrutamiento()             # Generar tabla de enrutamiento

            xmpp_menu_task = asyncio.create_task(self.xmpp_menu())          # Creación de hilo para manejar el menú de comunicación
            #---------------------------
            
            await xmpp_menu_task            

        except Exception as e:
            print(f"Error: {e}")


    async def send_echo(self, neighbor):
            """Envía un mensaje tipo echo a un vecino."""
            message = {"type": "echo", "from": self.graph}
            self.echo_times[neighbor] = time.time()  # Registrar el tiempo de envío
            recipient_jid = self.keys[neighbor]
            self.send_message(mto=recipient_jid, mbody=json.dumps(message), mtype='chat')
            print(f"Echo enviado a {neighbor}.")
            # return None

    async def message(self, msg):
        """Manejo de todos los mensajes entrantes."""
        if msg['type'] == 'chat':
            content = json.loads(msg['body'])
            if content['type'] == 'echo':
                print("ECHO MESSGE /////")
                print(msg)
                await self.handle_echo(content, msg['from'].bare)
            elif content['type'] == 'echo_response':
                await self.handle_echo_response(content, msg['from'].bare)
            elif content['type'] == 'weights':
                await self.handle_weights(content)

    async def handle_echo(self, content, sender_jid):
            """Manejo de recepción de echo, responder con echo_response."""
            response = {"type": "echo_response", "from": self.graph}
            self.send_message(mto=sender_jid, mbody=json.dumps(response), mtype='chat')
            print(f"Echo recibido de {content['from']}. Echo_response enviado a {sender_jid}.")
            return None

    async def handle_echo_response(self, content, sender_jid):
        """Manejo de recepción de echo_response, calcular tiempo y actualizar tabla de pesos."""
        sender_node = [k for k, v in self.keys.items() if v == sender_jid][0]
        end_time = time.time()
        round_trip_time = end_time - self.echo_times[sender_node]
        print(f"Echo_response recibido de {sender_node}. Tiempo de ida y vuelta: {round_trip_time:.4f} segundos.")

        # Actualizar la tabla de pesos
        self.weights_table[sender_node] = round_trip_time
        await self.broadcast_weights()

    async def broadcast_weights(self):
        """Envía la tabla de pesos actualizada a todos los vecinos."""
        message = {
            "type": "weights",
            "table": self.weights_table,
            "version": self.version,
            "from": self.graph
        }
        for neighbor in self.topologia[self.graph]:
            recipient_jid = self.keys[neighbor]
            self.send_message(mto=recipient_jid, mbody=json.dumps(message), mtype='chat')
        print(f"Tabla de pesos enviada a los vecinos: {self.weights_table}")
        self.version += 1
        return None

    async def handle_weights(self, content):
        """Manejo de recepción de una tabla de pesos."""
        received_version = content["version"]
        if received_version > self.version:
            print(f"Tabla de pesos recibida de {content['from']} con versión {received_version}.")
            self.weights_table.update(content["table"])
            self.version = received_version
            # Propagar la tabla a otros nodos
            await self.broadcast_weights()
            return None
        else:
            print(f"Tabla de pesos recibida de {content['from']} ignorada por versión antigua.")
            return None


    async def send_routing_message(self, destination, message_data):
        """Envía un mensaje `send_routing` a un nodo destino."""
        if destination not in self.keys:
            print("Destino no válido.")
            return

        path = await self.pathfinding(destination)
        if not path or len(path) < 2:
            print(f"No se pudo encontrar una ruta hacia {destination}.")
            return

        next_hop = path[1]  # El siguiente nodo en la ruta
        message = {
            "type": "send_routing",
            "to": destination,
            "from": self.graph,
            "data": message_data,
            "hops": len(self.keys)
        }

        recipient_jid = self.keys[next_hop]
        self.send_message(mto=recipient_jid, mbody=json.dumps(message), mtype='chat')
        print(f"Mensaje `send_routing` enviado a {next_hop}, con destino a {destination}.")


    async def handle_send_routing(self, content, sender_jid):
        """Manejo de recepción de un mensaje `send_routing`."""
        destination = content["to"]
        if destination == self.graph:
            # Convertir el mensaje en formato `message` y manejarlo directamente
            direct_message = {
                "type": "message",
                "from": content["from"],
                "data": content["data"]
            }
            await self.handle_direct_message(direct_message)
        else:
            # Continuar enviando el mensaje hasta el destino final
            await self.send_routing_message(destination, content["data"])


    #-------------------------------------------------------------------------------------------------------------------
    '''
    xmpp_menu: Función que muestra el menú de comunicación y ejecuta las funciones correspondientes a cada opción.
    '''

    async def xmpp_menu(self):
        self.logged_in = True
        await asyncio.sleep(3)

        opcion_comunicacion = 0
        while opcion_comunicacion != 5:

            opcion_comunicacion = await self.mostrar_menu_comunicacion()

            if opcion_comunicacion == 1:
                # Mostrar tabla de enrutamiento
                print("\n----- TABLA DE ENRUTAMIENTO -----")
                print(self.tabla)
                await asyncio.sleep(1)

            elif opcion_comunicacion == 2:
                await self.dijkstra()
                await asyncio.sleep(1)

            elif opcion_comunicacion == 3:
                # Enviar mensaje a un usuario
                await self.send_msg_to_user()
                await asyncio.sleep(1)

            elif opcion_comunicacion == 4:
                print("\n\n----- NOTIFICACION: ECHO -----")
                for neighbor in self.topologia[self.graph]:
                    await self.send_echo(neighbor)
                await asyncio.sleep(1)
                print("\nEcho enviados, regresando al menú.")
            elif opcion_comunicacion == 5:
                # Cerrar sesión con una cuenta
                print("\n--> Sesión cerrada. Hasta luego.")
                self.disconnect()
                exit()

    #-------------------------------------------------------------------------------------------------------------------
    '''
    send_msg_to_user: Función que envía un mensaje a un usuario.
    '''

    async def send_msg_to_user(self):
        print("\n----- ENVIAR MENSAJE A USUARIO -----")

        node_name = None
        while True:
            print("Seleccione un nodo de la lista: ")
            keys = list(value for key, value in self.keys.items())
            keys_nodes = list(key for key, value in self.keys.items())

            for i, key in enumerate(keys):
                print(f"{i+1}. {key}")

            try:
                node = await aioconsole.ainput("Ingrese el número del nodo: ")
                node = int(node)
                if node > 0 and node <= len(self.keys):
                    if self.graph == keys_nodes[node-1]:
                        print("--> No puede enviar un mensaje a sí mismo.\n")
                        continue
                    else:
                        node_name = keys_nodes[node-1]
                        break
                else:
                    print("Ingrese un número válido")

            except ValueError:
                print("Ingrese un número válido")

        user_input = await aioconsole.ainput("Mensaje: ")  # Obtener el mensaje a enviar

        # Asegurarse de que Dijkstra se ha ejecutado y las rutas están calculadas
        await self.dijkstra()

        # Enviar el mensaje utilizando el formato `send_routing`
        await self.send_routing_message(node_name, user_input)


    async def handle_direct_message(self, content):
        """Manejo de un mensaje `message` directo al nodo destino."""
        if 'from' in content and 'data' in content:
            print(f"Mensaje recibido desde {content['from']}: {content['data']}")
        else:
            print("Mensaje recibido con formato incorrecto:", content)


    #-------------------------------------------------------------------------------------------------------------------
    '''
    message: Función que se ejecuta de forma asincrónica al recibir un mensaje.
    '''


    async def message(self, msg):
        """Manejo de todos los mensajes entrantes."""
        if msg['type'] == 'chat':
            content = json.loads(msg['body'])
            if content['type'] == 'echo':
                await self.handle_echo(content, msg['from'].bare)
            elif content['type'] == 'echo_response':
                await self.handle_echo_response(content, msg['from'].bare)
            elif content['type'] == 'weights':
                await self.handle_weights(content)
            elif content['type'] == 'send_routing':
                await self.handle_send_routing(content, msg['from'].bare)
            elif content['type'] == 'message':
                await self.handle_direct_message(content)

    #-------------------------------------------------------------------------------------------------------------------
    async def mostrar_menu_comunicacion(self):
        print("\n----- MENÚ DE COMUNICACIÓN -----")
        print("1) Revisar tabla enrutamiento")
        print("2) Calcular rutas más cortas (Dijkstra)")
        print("3) Enviar mensaje")
        print("4) Send Echo")
        print("5) Salir")

        while True:
            try:
                opcion = int(await aioconsole.ainput("Ingrese el número de la opción deseada: "))
                if opcion in range(1, 10):
                    return opcion
                else:
                    print("\n--> Opción no válida. Por favor, ingrese un número del 1 al 9.\n")
            except ValueError:
                print("\n--> Entrada inválida. Por favor, ingrese un número entero.\n")


    #-------------------------------------------------------------------------------------------------------------------
    #-------------------------------------------------------------------------------------------------------------------
    #-------------------------------------------------------------------------------------------------------------------

    '''
        Genera la tabla de enrutamiento de cada nodo. 
            - Almacena los pesos de cada relación entre nodos. 
            - Se va llenando por broadcast
    '''
    async def tabla_enrutamiento(self):
        with open('topo.txt', 'r') as file:
            topologia = file.read().replace('\n', '').replace("'", '"')
        self.topologia = json.loads(topologia)["config"]

        with open('names.txt', 'r') as file:
            data = file.read().replace('\n', '').replace("'", '"')
        data = json.loads(data)
        self.keys = data["config"]

        # Buscar llave de correo actual y asignar a self.graph
        for key, value in self.keys.items():
            if value == self.email:
                self.graph = key

        # Se genera la tabla de enrutamiento
        num_nodos = len(self.keys)
        array_topologia = [[9999 for _ in range(num_nodos)] for _ in range(num_nodos)]

        keys_temp = list(self.keys.keys())

        # Llenar tabla de enrutamiento inicial
        for key in self.topologia[self.graph]:
            array_topologia[keys_temp.index(self.graph)][keys_temp.index(key)] = 1

        array_topologia[keys_temp.index(self.graph)][keys_temp.index(self.graph)] = 0

        print(f"\nTABLA DE ENRUTAMIENTO INICIAL:\n {array_topologia}")

        return array_topologia



    '''
        Después de haber calculado las distancias más cortas, se genera el camino más corto
    '''
    async def pathfinding(self, destination):
        """Encuentra la ruta más corta hacia el nodo destino utilizando Dijkstra."""
        if not hasattr(self, 'previous_node'):
            # Si la tabla no está disponible, ejecuta Dijkstra para calcular las rutas
            await self.dijkstra()

        keys = list(self.keys.keys())
        dest_index = keys.index(destination)
        path = []

        while dest_index != -1:
            path.insert(0, keys[dest_index])
            dest_index = self.previous_node[dest_index]

        return path


    '''
        Recibe información de las tablas de enrutamiento y las actualiza. 
            - Si las tablas ya están llenas, con Dijkstra calcula las distancias más cortas.
    '''
    async def dijkstra(self):
        """Calcula las rutas más cortas desde el nodo actual a todos los demás nodos."""
        print("\n-----------  DIJKSTRA  -----------")
        print(f"TABLA ACTUAL: {self.weights_table}")

        keys = list(self.keys.keys())
        start_index = keys.index(self.graph)

        num_nodes = len(keys)
        visited = [False] * num_nodes
        min_distance = [float('inf')] * num_nodes
        previous_node = [-1] * num_nodes
        min_distance[start_index] = 0

        for _ in range(num_nodes):
            min_value = float('inf')
            min_node = -1

            for node in range(num_nodes):
                if not visited[node] and min_distance[node] < min_value:
                    min_value = min_distance[node]
                    min_node = node

            if min_node == -1:
                break

            visited[min_node] = True

            for neighbor in self.topologia[keys[min_node]]:
                neighbor_index = keys.index(neighbor)
                weight = self.weights_table.get(neighbor, float('inf'))
                if not visited[neighbor_index] and min_distance[min_node] + weight < min_distance[neighbor_index]:
                    min_distance[neighbor_index] = min_distance[min_node] + weight
                    previous_node[neighbor_index] = min_node

        self.previous_node = previous_node
        self.min_distance = min_distance
        print("Rutas calculadas y actualizadas.")


# # ------------ MENUS y HERRAMIENTAS ------------
#     async def convert_to_dict(self, paquete):
#         try:
#             input_str = paquete.replace("'", '"')
#             data = json.loads(input_str)
#             return data
#         except json.JSONDecodeError as err:
#             print(err)
#             return None

#     async def are_nested_arrays_equal(self, arr1, arr2):
#         if len(arr1) != len(arr2):
#             return False
        
#         for i in range(len(arr1)):
#             if isinstance(arr1[i], list) and isinstance(arr2[i], list):
#                 if not await self.are_nested_arrays_equal(arr1[i], arr2[i]):
#                     return False
#             else:
#                 if arr1[i] != arr2[i]:
#                     return False
        
#         return True

def select_node():
    with open('names.txt', 'r') as file:
        data = file.read().replace('\n', '').replace("'", '"')
    data = json.loads(data)
    data = data["config"]

    while True:
        print("\n---DIJKSTRA---\nSeleccione un nodo de la lista: ")
        keys = list(value for key, value in data.items())
        for i, key in enumerate(keys):
            print(f"{i+1}. {key}")

        try:
            node = int(input("Ingrese el número del nodo: "))
            if node > 0 and node <= len(data):
                return keys[node-1]
            else:
                print("Ingrese un número válido")

        except ValueError:
            print("Ingrese un número válido")


# Para evitar el error de que el evento no se puede ejecutar en Windows
#asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy()) 

usuario = select_node()
server = Server(usuario, "kinalkinal")         
server.connect(disable_starttls=True)   
server.process(forever=False)             