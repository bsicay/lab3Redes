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

        self.traza_mensajes = []
        self.compartido = []


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

            print("\n\n----- NOTIFICACION: COMPARTIENDO VECTOR DISTANCIA -----")

            #-----> Enviar a vecinos vector inicial
            for key in self.topologia[self.graph]:

                if key != self.graph:
                    await self.broadcast_table(key)       # Enviar mensaje con librería slixmpp
            
            print("--------------------------------")

            #-----> Generado por ChatGPT
            xmpp_menu_task = asyncio.create_task(self.xmpp_menu())          # Creación de hilo para manejar el menú de comunicación
            #---------------------------
            
            await xmpp_menu_task            

        except Exception as e:
            print(f"Error: {e}")

    
    #-------------------------------------------------------------------------------------------------------------------
    '''
    xmpp_menu: Función que muestra el menú de comunicación y ejecuta las funciones correspondientes a cada opción.
    '''

    async def xmpp_menu(self):
        self.logged_in = True
        await asyncio.sleep(5)

        opcion_comunicacion = 0
        while opcion_comunicacion != 3:

            opcion_comunicacion = await self.mostrar_menu_comunicacion()

            if opcion_comunicacion == 1:
                # Mostrar tabla de enrutamiento
                print("\n----- VECTOR DISTANCIA -----")
                print(self.tabla)

                print("\n----- ENLACES -----")
                print(self.enlaces)
                await asyncio.sleep(1)

            elif opcion_comunicacion == 2:
                # Enviar mensaje a un usuario
                await self.send_msg_to_user()
                await asyncio.sleep(1)

            elif opcion_comunicacion == 3:
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

        user_input = await aioconsole.ainput("Mensaje: ")                            # Obtener el mensaje a enviar

        tabla = {"type":"message",
                "headers": {"from": f"{self.graph}", "to": f"{node_name}", "hop_count": 1},
                "payload": user_input}
        
        tabla_send = json.dumps(tabla)  # Se envía el paquete de información
        
        keys_temp = list(self.keys.keys())
        camino = self.enlaces[keys_temp.index(node_name)]
        print(f"\n--> Camino más corto a través de: {camino}")

        recipient_jid = self.keys[camino]                                        # Obtener el JID del destinatario

        self.send_message(mto=recipient_jid, mbody=tabla_send, mtype='chat')         # Enviar mensaje con librería slixmpp
        print(f"--> Mensaje enviado a {camino}, con destino a {node_name}.")
        print("----------------------")

    #-------------------------------------------------------------------------------------------------------------------
    '''
    message: Función que se ejecuta de forma asincrónica al recibir un mensaje.
    '''

    async def message(self, msg):
        print("\n\n---------- MENSAJES / NOTIFICACIONES ----------")

        if self.old:
            return
        
        if msg['type'] == 'chat' and "info" in msg['body']:

            # BELLMAN FORD - DISTANCE VECTOR
            info = await self.convert_to_dict(msg['body'])

            mensaje = info["payload"].replace("'", '"')
            received_table = json.loads(mensaje)
            origin = info["headers"]["from"]

            print(f"\n--> Vector de distancia recibido de {origin}.")

            keys_temp = list(self.keys.keys())

            # Costo del nodo actual al nodo origen
            cost_to_origin = self.tabla[keys_temp.index(origin)]
            updates_occurred = False

            # Revisa con Bellman-Ford si el costo total es menor al costo actual
            for i, new_cost in enumerate(received_table):
                total_cost = cost_to_origin + new_cost

                if total_cost < self.tabla[i]:
                    self.tabla[i] = total_cost
                    self.enlaces[i] = origin
                    updates_occurred = True

            # Comparte las tablas de enrutamiento que tiene que compartir
            if updates_occurred:
                print("--> Se han realizado cambios en la tabla de enrutamiento.")

                vecinos = self.topologia[self.graph]

                for key in vecinos:
                    if key != self.graph:
                        await self.broadcast_table(key)
                        await asyncio.sleep(1)

            elif not updates_occurred and info["headers"]["hop_count"] == 2:
                print("--> No se han realizado cambios en la tabla de enrutamiento.")

            else:
                print("--> No se han realizado cambios en la tabla de enrutamiento. Enviando tabla de regreso.")
                await self.broadcast_table(origin, hop_count=2)

        elif msg['type'] == 'chat' and "message" in msg['body']:
            person = msg['from'].bare                                               # Si se recibe un mensaje, se obtiene el nombre de usuario
            info = await self.convert_to_dict(msg['body'])
            mensaje = info["payload"].replace("'", '"')
            origen = info["headers"]["from"]
            destino = info["headers"]["to"]

            if destino == self.graph:
                email_origen = self.keys[origen]

                print("\n\n----------- MENSAJE -----------")
                print(f"--> {email_origen} ha enviado un mensaje: {mensaje}")
                print("--------------------------------")
                return
            
            else:
                keys_temp = list(self.keys.keys())

                camino = self.enlaces[keys_temp.index(destino)]
                print(f"\n--> Camino más corto a través de: {camino}")

                recipient_jid = self.keys[camino]                                        # Obtener el JID del destinatario
                tabla = {"type":"message",
                        "headers": {"from": f"{origen}", "to": f"{destino}", "hop_count": 1},
                        "payload": mensaje}
                
                tabla_send = json.dumps(tabla)

                self.send_message(mto=recipient_jid, mbody=tabla_send, mtype='chat')         # Enviar mensaje con librería slixmpp

                print("\n\n----------- MENSAJE -----------")
                print(f"--> {person} ha enviado un mensaje para retransmitir a {camino}, con destino a {destino}.")
                print("--------------------------------")

        self.traza_mensajes.append(msg)

    #-------------------------------------------------------------------------------------------------------------------
    async def mostrar_menu_comunicacion(self):
        print("\n----- MENÚ DE COMUNICACIÓN -----")
        print("1) Revisar vector distancia")
        print("2) Enviar mensaje")
        print("3) Salir")

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

        self.graph = None
        for key, value in self.keys.items():
            if value == self.email:
                self.graph = key

        array_topologia = [9999 for _ in range(len(self.keys))]
        self.enlaces = ["" for _ in range(len(self.keys))]

        keys_temp = list(self.keys.keys())

        for key in self.topologia[self.graph]:
                array_topologia[keys_temp.index(key)] = 1
                self.enlaces[keys_temp.index(key)] = key

        if array_topologia[keys_temp.index(self.graph)] == 9999:
            array_topologia[keys_temp.index(self.graph)] = 0


        print(f"\nVECTOR DE DISTANCIA INICIAL:\n {array_topologia}")

        return array_topologia

    '''
        Le envia a sus vecinos su vector de distancia por broadcast
    '''
    async def broadcast_table(self, element=None, hop_count=1):

        # Imprime las tablas de enrutamiento que tiene que compartir   

        # Nodo seleccionado
        nodo_email = self.keys[element]

        # Se crea el primer paquete de información
        string_array = str(self.tabla)
        tabla = {"type":"info", 
            "headers": {"from": f"{self.graph}", "to": f"{element}", "hop_count": hop_count},
            "payload": string_array}
        
        tabla_send = json.dumps(tabla)  # Se envía el paquete de información
    
        print(f"--> Enviando tabla a {element}...")

        self.send_message(mto=nodo_email, mbody=tabla_send, mtype='chat')         # Enviar mensaje con librería slixmpp

# ------------ MENUS y HERRAMIENTAS ------------
    async def convert_to_dict(self, paquete):
        try:
            input_str = paquete.replace("'", '"')
            data = json.loads(input_str)
            return data
        except json.JSONDecodeError as err:
            print(err)
            return None

    async def are_nested_arrays_equal(self, arr1, arr2):
        if len(arr1) != len(arr2):
            return False
        
        for i in range(len(arr1)):
            if isinstance(arr1[i], list) and isinstance(arr2[i], list):
                if not await self.are_nested_arrays_equal(arr1[i], arr2[i]):
                    return False
            else:
                if arr1[i] != arr2[i]:
                    return False
        
        return True


def select_node():
    with open('names.txt', 'r') as file:
        data = file.read().replace('\n', '').replace("'", '"')
    data = json.loads(data)
    data = data["config"]

    while True:
        print("\n---DISTANCE VECTOR---\nSeleccione un nodo de la lista: ")
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