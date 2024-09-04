import json
from slixmpp.exceptions import IqError, IqTimeout
from slixmpp.xmlstream import ElementBase, ET, register_stanza_plugin
import slixmpp
import threading
import asyncio
import aioconsole 
import base64
import time

class Server(slixmpp.ClientXMPP):


    def __init__(self, jid, password):
        self.email = jid
        self.old = True

        super().__init__(jid, password)
        self.register_plugin('xep_0030')                               
        self.register_plugin('xep_0045')                                 
        self.register_plugin('xep_0085')                              
        self.register_plugin('xep_0199')                                  
        self.register_plugin('xep_0353')                                
        #-------------------------------

        self.add_event_handler("session_start", self.start)                 
        self.add_event_handler("message", self.message)                   

        self.logged_in = False
        self.topologia = None

        self.traza_mensajes = []


    async def start(self, event):
        try:
            self.send_presence()                                           
            self.get_roster()                                             

            await asyncio.sleep(2)
            self.old = False
            
            xmpp_menu_task = asyncio.create_task(self.xmpp_menu())     
        
            await xmpp_menu_task            

        except Exception as e:
            print(f"Error: {e}")


    async def xmpp_menu(self):
        self.logged_in = True

        # Buscar llave de correo actual
        self.keys = self.getAvailableNodes()

        for key, value in self.keys.items():
            if value == self.email:
                self.graph = key

        print("\n---------- MENSAJES / NOTIFICACIONES ----------")
        await asyncio.sleep(5)

        opcion_comunicacion = 0
        while opcion_comunicacion != 4:

            opcion_comunicacion = await self.mostrar_menu_comunicacion()

            if opcion_comunicacion == 1:
                # Enviar mensaje a un usuario
                await self.send_msg_to_user()
                await asyncio.sleep(1)

            elif opcion_comunicacion == 2:
                print("\n--> Sesión cerrada. Hasta luego.")
                self.disconnect()
                exit()

    async def send_msg_to_user(self):
        print("\n----- ENVIAR MENSAJE A USUARIO -----")

        node_name = None
        while True:
            print("Seleccione un nodo de la lista: ")
            nodes = self.keys

            keys = list(value for key, value in nodes.items())
            keys_names = list(key for key, value in nodes.items())
            for i, key in enumerate(keys):
                print(f"{i+1}. {key}")

            try:
                node = await aioconsole.ainput("Ingrese el número del nodo: ")
                node = int(node)
                if node > 0 and node <= len(nodes):
                    if self.graph == keys_names[node-1]:
                        print("--> No puede enviar un mensaje a sí mismo.\n")
                        continue
                    else:
                        node_name = keys_names[node-1]
                        break
                else:
                    print("Ingrese un número válido")

            except ValueError:
                print("Ingrese un número válido")

        user_input = await aioconsole.ainput("Mensaje: ")                              
        
        visited_nodes = [self.graph]                    

        tabla = {
            "type": "message",
            "headers": {
                "from": self.graph,
                "to": node_name,
                "visited": visited_nodes
            },
            "payload": user_input
        }
        tabla_send = json.dumps(tabla)   

        print("\n----- ENVIANDO MENSAJE -----")

        vecinos = self.getNeighbors(self.graph)      
        for vecino in vecinos:
            if vecino == self.email:
                continue

            if (vecino not in visited_nodes):
                recipient_jid = vecino                                               
                self.send_message(mto=recipient_jid, mbody=tabla_send, mtype='chat')     # Enviar mensaje con librería slixmpp
                print(f"--> Mensaje enviado a {vecino}.")
                print("----------------------")
                await asyncio.sleep(1)
            
    #-------------------------------------------------------------------------------------------------------------------
    def getAvailableNodes(self):
        with open('names.txt', 'r') as file:
            data = json.load(file)
        
        data = data["config"]
        return data

    #-------------------------------------------------------------------------------------------------------------------
    def getNeighbors(self, node):
        with open('topo.txt', 'r') as file:
            data = json.load(file)

        data = data["config"]
        neighbors = list(data[node])

        list_neighbors = []
        for n in neighbors:
            list_neighbors.append(self.keys[n])

        return list_neighbors
    
    #-------------------------------------------------------------------------------------------------------------------
    async def convert_to_dict(self, paquete):
        try:
            input_str = paquete.replace("'", '"')
            data = json.loads(input_str)
            return data
        except json.JSONDecodeError as err:
            print(err)
            return None
    
     #-------------------------------------------------------------------------------------------------------------------
    
    '''
    message: Función que se ejecuta de forma asincrónica al recibir un mensaje.
    '''
    async def message(self, msg):

        if self.old:
            return
        
        if msg['type'] == 'chat' and "message" in msg['body']:
            person = msg['from'].bare                                               # Si se recibe un mensaje, se obtiene el nombre de usuario
            info = await self.convert_to_dict(msg['body'].replace("'", '"'))

            mensaje = info["payload"]
            origen = info["headers"]["from"]
            destino = info["headers"]["to"]

            current_msg = str(origen+","+destino+","+mensaje)

            # Lleva registro de mensajes que han entrado
            if current_msg in self.traza_mensajes:
                # Si ya había entrado, no retransmite
                self.traza_mensajes.append(current_msg)
                return            
            else:
                # Si no había entrado, retransmite
                self.traza_mensajes.append(current_msg)

            visited_nodes = []
            for element in info["headers"]["visited"]:
                visited_nodes.append(element)

            if self.graph in visited_nodes:
                return

            if destino == self.graph:
                print("\n\n----------- MENSAJE -----------")
                print(f"--> {origen} ha enviado un mensaje: {mensaje}")
                print("--------------------------------")
                return
            
            else:
                visited_nodes.append(self.graph)
                tabla = {
                    "type": "message",
                    "headers": {
                        "from": origen,
                        "to": destino,
                        "visited": visited_nodes
                    },
                    "payload": mensaje
                }
                tabla_send = json.dumps(tabla)

                print("\n\n----- RETRANSMITIENDO MENSAJE -----")
                retransmitir = True
                
                vecinos = self.getNeighbors(self.graph)
                for vecino in vecinos:

                    vecino_name = ""    # Consigue nombre del nodo vecino
                    for key, value in self.keys.items():
                        if value == vecino:
                            vecino_name = key

                    if vecino == self.email or vecino_name == origen or vecino_name in visited_nodes:
                        continue

                    else:
                        recipient_jid = vecino                                                   # Obtener el JID del destinatario
                        self.send_message(mto=recipient_jid, mbody=tabla_send, mtype='chat')     # Enviar mensaje con librería slixmpp
                        print(f"--> Retransmitiendo mensaje a {vecino}.")
                        print("-----------------------------------")
                        retransmitir = False
                        await asyncio.sleep(1)

                if retransmitir:
                    print("--> No hay nodos a los que retransmitir el mensaje.")
                    print("------------------------------------------------------")
            
    #-------------------------------------------------------------------------------------------------------------------
    async def mostrar_menu_comunicacion(self):
        print("\n----- MENÚ DE COMUNICACIÓN -----")
        print("1) Enviar mensaje")
        print("2) Salir")

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
    async def mostrar_menu_comunicacion(self):
        print("\n----- MENÚ DE COMUNICACIÓN -----")
        print("1) Enviar mensaje")
        print("2) Salir")

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
def select_node():
    with open('names.txt', 'r') as file:
        data = file.read().replace('\n', '').replace("'", '"')
    data = json.loads(data)
    data = data["config"]

    while True:
        print("\n---FLOODING--\nSeleccione un nodo de la lista: ")
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