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
import sys
import os



class Server(slixmpp.ClientXMPP):

    sys.stderr = open(os.devnull, 'w')

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


    async def periodic_broadcast_weights(self):
        """Envia la tabla de pesos cada 3 segundos de forma periódica."""
        while True:
            await self.broadcast_weights()
            await asyncio.sleep(3)  # Esperar 3 segundos antes del siguiente broadcast


    async def send_echo(self, neighbor):
            """Envía un mensaje tipo echo a un vecino."""
            message = {"type": "echo", "from": self.graph}
            self.echo_times[neighbor] = time.time()  # Registrar el tiempo de envío
            recipient_jid = self.keys[neighbor]
            self.send_message(mto=recipient_jid, mbody=json.dumps(message), mtype='chat')
            print(f"Echo enviado a {neighbor}.")
            # return None

    async def handle_echo(self, content, sender_jid):
            """Manejo de recepción de echo, responder con echo_response."""
            response = {"type": "echo_response", "from": self.graph}
            self.send_message(mto=sender_jid, mbody=json.dumps(response), mtype='chat')
            print(sender_jid)
            print(content)
            # print(f"Echo recibido de {sender_jid}. Echo_response enviado a {sender_jid}.")
            return None

    async def handle_echo_response(self, content, sender_jid):
        """Manejo de recepción de echo_response, calcular tiempo y actualizar tabla de pesos."""
        sender_node = [k for k, v in self.keys.items() if v == sender_jid][0]
        end_time = time.time()
        round_trip_time = end_time - self.echo_times[sender_node]
        print(f"Echo_response recibido de {sender_node}. Tiempo de ida y vuelta: {round_trip_time:.4f} segundos.")


    # Asegurar que nuestro vector de distancias está inicializado
        my_node = self.graph
        if my_node not in self.weights_table:
            self.weights_table[my_node] = {node: float('inf') for node in self.keys}
            self.weights_table[my_node][my_node] = 0  # Distancia a sí mismo es 0

    # Actualizar la distancia al vecino directo
        self.weights_table[my_node][sender_node] = round_trip_time
        # Iniciar la tarea de broadcast periódica
        asyncio.create_task(self.periodic_broadcast_weights())
        # await self.broadcast_weights()

    async def broadcast_weights(self):
        """Envía la tabla de pesos actualizada a todos los vecinos."""
        # print("TABLA")
        # print(self.graph)
        my_node = self.graph
        message = {
            "type": "weights",
            "table": self.weights_table[my_node],
            "version": 0,
            "from": self.graph
        }
        for neighbor in self.topologia[self.graph]:
            recipient_jid = self.keys[neighbor]
            self.send_message(mto=recipient_jid, mbody=json.dumps(message), mtype='chat')
        # print(f"Tabla de pesos enviada a los vecinos: {self.weights_table}")


    # async def handle_weights(self, content):
    #     """Manejo de recepción de una tabla de pesos utilizando lógica de Vector de Distancias."""
    #     source = content["from"]
    #     received_table = content["table"]  # Tabla de pesos recibida

    #     # Obtener la tabla de pesos actual y el vector de distancias para el nodo actual
    #     my_node = self.graph
    #     current_table = self.weights_table

    #     # Inicializar la tabla si está vacía (distancia infinita a todos los nodos excepto a sí mismo)
    #     if my_node not in current_table:
    #         current_table[my_node] = {node: float('inf') for node in self.keys}
    #         current_table[my_node][my_node] = 0  # Distancia al propio nodo es 0

    #     my_vector = current_table[my_node]  # Vector de distancias del nodo actual
    #     table_changed = False  # Indicador de si la tabla cambió

    #     # Calcular la distancia al nodo fuente
    #     distance_to_source = my_vector.get(source, float('inf'))

    #     # Revisar y actualizar distancias para cada nodo en la tabla recibida
    #     for node, source_to_node in received_table.items():
    #         if node not in self.keys:
    #             continue  # Saltar nodos desconocidos

    #         # Extraer la distancia correcta (si es lista, obtener el valor de distancia)
    #         if isinstance(source_to_node, list):
    #             source_to_node = source_to_node[0]

    #         # Verificar que source_to_node sea un valor numérico
    #         if isinstance(source_to_node, (int, float)):
    #             current_distance = my_vector.get(node, float('inf'))

    #             # Actualizar la distancia si se encuentra una mejor ruta
    #             if distance_to_source + source_to_node < current_distance:
    #                 # Actualizar la tabla de distancias
    #                 if node != source:
    #                     my_vector[node] = [distance_to_source + source_to_node, source]  # Ruta indirecta
    #                 else:
    #                     my_vector[node] = distance_to_source + source_to_node  # Ruta directa
    #                 table_changed = True

    #     # Si la tabla ha cambiado, propagar los cambios a los vecinos
    #     if table_changed:
    #         await self.broadcast_weights()

    #     print(f"Tabla de pesos actualizada para {my_node}: {self.weights_table[my_node]}")

    # async def handle_weights(self, content):
    #     """Manejo de recepción de una tabla de pesos utilizando lógica de Vector de Distancias."""
    #     source = content["from"]
    #     received_vector = content["table"]  # Vector de distancias recibido del vecino
    #     my_node = self.graph

    #     # Guardar el vector de distancias del nodo fuente
    #     self.weights_table[source] = received_vector

    #     # Asegurar que nuestro vector de distancias está inicializado
    #     if my_node not in self.weights_table:
    #         self.weights_table[my_node] = {node: float('inf') for node in self.keys}
    #         self.weights_table[my_node][my_node] = 0  # Distancia a sí mismo es 0

    #     my_vector = self.weights_table[my_node]
    #     table_changed = False

    #     # Obtener la distancia actual al nodo fuente
    #     distance_to_source = my_vector.get(source, float('inf'))

    #     # Si no conocemos la distancia al nodo fuente, no podemos actualizar rutas a través de él
    #     if distance_to_source == float('inf'):
    #         print(f"No conocemos la distancia a {source}, no podemos actualizar rutas a través de él.")
    #         return

    #     # Actualizar distancias a otros nodos a través del nodo fuente
    #     for dest_node in self.keys:
    #         if dest_node == my_node:
    #             continue  # Saltar a sí mismo

    #         # Distancia del nodo fuente al destino
    #         source_to_dest = received_vector.get(dest_node, float('inf'))

    #         # Calcular distancia total a dest_node pasando por source
    #         new_distance = distance_to_source + source_to_dest

    #         # Si encontramos una distancia mejorada, actualizamos
    #         if new_distance < my_vector.get(dest_node, float('inf')):
    #             if dest_node != source:
    #                 my_vector[dest_node] = [new_distance, source] 
    #             else:
    #                 my_vector[dest_node] = new_distance
    #             table_changed = True

    #     if table_changed:
    #         await self.broadcast_weights()

        # print(f"Tabla de pesos actualizada para {my_node}: {my_vector}")

    async def handle_weights(self, content):
        """Manejo de recepción de una tabla de pesos utilizando lógica de Vector de Distancias."""
        source = content["from"]
        received_vector = content["table"]  # Vector de distancias recibido del vecino
        my_node = self.graph

        # Guardar el vector de distancias del nodo fuente
        self.weights_table[source] = received_vector

        # Asegurar que nuestro vector de distancias está inicializado
        if my_node not in self.weights_table:
            self.weights_table[my_node] = {node: float('inf') for node in self.keys}
            self.weights_table[my_node][my_node] = 0  # Distancia a sí mismo es 0

        my_vector = self.weights_table[my_node]
        table_changed = False

        # Obtener la distancia actual al nodo fuente
        distance_to_source = my_vector.get(source, float('inf'))

        # Si no conocemos la distancia al nodo fuente, no podemos actualizar rutas a través de él
        if distance_to_source == float('inf'):
            # print(f"No conocemos la distancia a {source}, no podemos actualizar rutas a través de él.")
            return

        # Actualizar distancias a otros nodos a través del nodo fuente
        for dest_node in self.keys:
            if dest_node == my_node:
                continue  # Saltar a sí mismo

            # Distancia del nodo fuente al destino
            source_to_dest = received_vector.get(dest_node, float('inf'))

            # Calcular distancia total a dest_node pasando por source
            new_distance = distance_to_source + source_to_dest

            # Obtener la distancia actual en mi tabla de enrutamiento
            current_entry = my_vector.get(dest_node, float('inf'))

            # Si la entrada actual es una lista (ruta indirecta), extraer solo la distancia
            if isinstance(current_entry, list):
                current_distance = current_entry[0]
            else:
                current_distance = current_entry

            # Si encontramos una distancia mejorada, actualizamos
            if new_distance < current_distance:
                if dest_node != source:
                    my_vector[dest_node] = [new_distance, source]  # Ruta indirecta
                else:
                    my_vector[dest_node] = new_distance  # Ruta directa
                table_changed = True

        if table_changed:
            await self.broadcast_weights()

    # print(f"Tabla de pesos actualizada para {my_node}: {my_vector}")



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


    async def send_routing_message(self, destination, message_data):
        """Envía un mensaje `send_routing` a un nodo destino, con soporte para rutas indirectas."""
        
        # Verificar si el destino está en la tabla de enrutamiento
        if destination not in self.weights_table[self.graph]:
            # print(f"Destino {destination} no encontrado en la tabla de enrutamiento.")
            return

        # Obtener la entrada correspondiente al destino en la tabla de enrutamiento
        route_info = self.weights_table[self.graph].get(destination)
        
        # Verificar si es una ruta directa o si hay un nodo intermediario
        if isinstance(route_info, (int, float)):
            # Ruta directa
            next_hop = destination
        else:
            # Ruta indirecta, obtener el nodo intermediario
            next_hop = route_info[1]

        # Preparar el mensaje para reenviar
        message = {
            "type": "send_routing",
            "to": destination,
            "from": self.graph,
            "data": message_data,
            "hops": len(self.keys) 
        }

        # Obtener el JID del siguiente salto (vecino o intermediario)
        recipient_jid = self.keys[next_hop]
        
        # Enviar el mensaje al siguiente salto
        self.send_message(mto=recipient_jid, mbody=json.dumps(message), mtype='chat')
        print(f"Mensaje `send_routing` enviado a {next_hop}, con destino a {destination}.")

    #-------------------------------------------------------------------------------------------------------------------
    '''
    xmpp_menu: Función que muestra el menú de comunicación y ejecuta las funciones correspondientes a cada opción.
    '''

    async def xmpp_menu(self):
        self.logged_in = True
        await asyncio.sleep(3)

        opcion_comunicacion = 0
        while opcion_comunicacion != 4:

            opcion_comunicacion = await self.mostrar_menu_comunicacion()

            if opcion_comunicacion == 1:
                # Mostrar tabla de enrutamiento
                print("\n----- TABLA DE ENRUTAMIENTO -----")
                print(self.weights_table)
                await asyncio.sleep(1)

            elif opcion_comunicacion == 2:
                # Enviar mensaje a un usuario
                await self.send_msg_to_user()
                await asyncio.sleep(1)

            elif opcion_comunicacion == 3:
                print("\n\n----- NOTIFICACION: ECHO -----")
                for neighbor in self.topologia[self.graph]:
                    await self.send_echo(neighbor)
                await asyncio.sleep(1)
                print("\nEcho enviados, regresando al menú.")
            elif opcion_comunicacion == 4:
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

        # Esperar a que la tabla de enrutamiento se actualice
        try:
            print("Esperando a que la tabla de enrutamiento se actualice...")
            table = await self.wait_for_table_update(self.graph, node_name)
            my_vector = table[self.graph]
            destination_node = node_name

            # Determinar el siguiente salto en la ruta
            if isinstance(my_vector[destination_node], (int, float)):  # Si es un número, el destino es directo
                next_hop = destination_node
            else:  # Si es una lista, obtener el siguiente salto
                next_hop = my_vector[destination_node][1]  # Nodo intermediario

            # Enviar el mensaje al siguiente salto
            message = {
                "type": "send_routing",
                "to": destination_node,
                "from": self.graph,
                "data": user_input,
                "hops": len(self.keys)
            }

            recipient_jid = self.keys[next_hop]
            self.send_message(mto=recipient_jid, mbody=json.dumps(message), mtype='chat')
            print(f"Mensaje enviado a {next_hop}, con destino a {destination_node}.")

        except TimeoutError as e:
            print(f"Error: {e}")


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
        print("2) Enviar mensaje")
        print("3) Send Echo")
        print("4) Salir")

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


    async def wait_for_table_update(self, start_node, destination_node, timeout=100):
        """
        Espera hasta que la tabla de enrutamiento tenga una ruta válida al destino.
        """
        start_time = time.time()
        while True:
            current_time = time.time()
            if current_time - start_time >= timeout:
                raise TimeoutError(f"Timeout: La tabla de enrutamiento no se ha poblado para el nodo {start_node} en {timeout}ms.")
            
            # Revisar si la tabla de enrutamiento tiene una ruta válida
            if self.weights_table.get(start_node) and destination_node in self.weights_table[start_node]:
                return self.weights_table
            
            # Esperar un intervalo antes de revisar de nuevo
            await asyncio.sleep(0.1)


def select_node():
    with open('names.txt', 'r') as file:
        data = file.read().replace('\n', '').replace("'", '"')
    data = json.loads(data)
    data = data["config"]

    while True:
        print("Seleccione un nodo de la lista: ")
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