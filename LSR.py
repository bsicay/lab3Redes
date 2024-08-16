# LinkState.py
import json
import socket
import threading
import time
from RoutingTable import RoutingTable
from FloodingLSR import Flooding
from dijkstra import Dijkstra

class LinkStateRouting:
    def __init__(self):
        self.RT = RoutingTable()
        self.flooding = Flooding(self.RT)  
        self.actual_node = None
        self.node_ports = {}
        self.topology = {}

    def load_topology(self, filename):
        self.flooding.load_topology(filename)

    def load_ports(self, filename):
        with open(filename, 'r') as file:
            self.node_ports = json.load(file)
        self.flooding.node_ports = self.node_ports  # Compartir los puertos con Flooding

    def measure_weights_with_flooding(self):
        print("Midiendo pesos (delays) utilizando Flooding...")
        for neighbor in self.flooding.actual_node.get_neighbors():
            if neighbor.name != self.actual_node:
                self.flooding.send_echo(neighbor.name)
                delay = self.flooding.handle_echo({
                    'from': neighbor.name,
                    'type': 'echo',
                    'timestamp': time.time()  # Se utilizará el tiempo actual como simulación
                })
                weight = round((delay * 1000) + 1)  # Convertir delay en milisegundos
                print(f"Peso hacia {neighbor.name}: {weight} ms")
                if self.RT.contains(neighbor.name):
                    self.RT.update_info(neighbor.name, weight, neighbor.name)
                else:
                    self.RT.addNeighbor(neighbor.name, weight, neighbor.name)
                self.topology.setdefault(self.actual_node, {})[neighbor.name] = weight
        print("Pesos calculados y almacenados en la tabla de enrutamiento.")

    def calculate_routing_table(self):
        print("Calculando tabla de enrutamiento utilizando Dijkstra...")

        self.routing_table = Dijkstra.calculate_routing_table(self.flooding.topology, self.actual_node)
        print("Tabla de enrutamiento calculada:")
        for node, (path, cost) in self.routing_table.items():
            print(f"Destino: {node}, Ruta: {' -> '.join(path)}, Costo: {cost} ms")

    def start(self):
        print("")
        topology_file = "topologia.txt"
        ports_file = "ports.json"
        self.load_topology(topology_file)
        self.load_ports(ports_file)

        name = input("Nombre del nodo actual: ")

        # Configurar el nodo actual tanto en LSR como en Flooding
        self.actual_node = name.upper()
        self.flooding.actual_node = next((node for node in self.flooding.nodes if node.name == self.actual_node), None)

        if self.flooding.actual_node is None:
            print(f"Error: Nodo {self.actual_node} no encontrado en la topología.")
            return

        self.RT.addNeighbor(self.actual_node, 0, self.actual_node)


        # Iniciar el servidor para escuchar conexiones entrantes
        threading.Thread(target=self.start_server, daemon=True).start()

        # Iniciar LSR
        self.start_lsr()

    def start_lsr(self):
        print("Iniciando Link State Routing...")
        # Iniciar menú interno
        LSR_ = True
        while LSR_:
            opp = LSR_menu()
            if opp == 1:
                # # Medir pesos utilizando Flooding
                self.measure_weights_with_flooding()

                # Calcular la tabla de enrutamiento utilizando Dijkstra
                # self.calculate_routing_table()
            if opp == 2:
                #  self.flooding.start_flooding_topology()
                # Recalcular tabla de enrutamiento
                 self.calculate_routing_table()
            elif opp == 3:
                # Enviar información de enrutamiento a los vecinos
                self.writeJSON("info")
            elif opp == 4:
                # Recibir información o mensaje}
                self.flooding.start_flooding_topology()
                # self.receive_message()
            elif opp == 5:
                # Mostrar tabla de enrutamiento
                print(self.RT)
            elif opp == 6:
                # Salir
                LSR_ = False

    def send_message_to_neighbor(self, neighbor_name, message):
        port = self.node_ports.get(neighbor_name)
        if port:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(('localhost', port))
                s.sendall(message.encode('utf-8'))

    def handle_connection(self, conn, addr):
        with conn:
            message = conn.recv(1024).decode('utf-8')
            print(f"Mensaje recibido de {addr}: {message}")
            self.process_received_message(message)

    def process_received_message(self, message):
        jsonReceived = json.loads(message)
        mtype = jsonReceived["type"]

        if mtype == "echo":
            # Procesar el mensaje de echo como lo haría Flooding
            delay = self.flooding.handle_echo(jsonReceived)
            return  # No hay necesidad de propagar el echo

        if mtype == "info":
            if jsonReceived["headers"]["to"] == self.actual_node:
                otroRT = jsonReceived["payload"]
                from_ = jsonReceived["headers"]["from"]
                self.receiveRT(otroRT, from_)

        elif mtype == "message":
            if jsonReceived["headers"]["to"] != self.actual_node:
                # Reenvío
                destino = self.RT.get_info(jsonReceived["headers"]["to"])
                print(f"Enviar el mensaje a {destino[1]}")
                jsonReceived["headers"]["hop"] = destino[1]
                self.send_message_to_neighbor(destino[1], json.dumps(jsonReceived, indent=4))
            else:
                # Lectura
                from_ = jsonReceived["headers"]["from"]
                mess = jsonReceived["payload"]
                print("\n================================")
                print(f"Mensaje recibido de {from_}")
                print(f"{mess}")
                print("================================")

        elif mtype == "topology":
            self.flooding.handle_topology_message(jsonReceived)

    def receiveRT(self, rt, from_):
        for i in range(len(rt)):
            if self.RT.contains(rt[i][0]):
                # Actualizar si es menor
                wAcc = self.RT.get_info(rt[i][0])[0]
                weight = self.RT.get_info(from_)[0] + rt[i][1]

                if weight < wAcc:
                    # Actualizar si es menor
                    self.RT.update_info(rt[i][0], weight, from_)
            else:
                # Agregar
                weight = self.RT.get_info(from_)[0] + rt[i][1]
                self.RT.addNeighbor(rt[i][0], weight, from_)

    def writeJSON(self, type_):
        if type_ == "info":
            print("Enviando información a los vecinos...")
            payload = self.RT.TABLE

            for n in self.flooding.actual_node.get_neighbors():
                headers = {
                    "from": self.actual_node,
                    "to": n.name
                }

                message = {
                    "type": "info",
                    "headers": headers,
                    "payload": payload
                }

                jsonRes = json.dumps(message, indent=4)
                self.send_message_to_neighbor(n.name, jsonRes)
                print(f"Enviado a {n.name}:\n{jsonRes}")

    def start_server(self):
        port = self.node_ports[self.actual_node]
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', port))
            s.listen()
            print(f"Nodo {self.actual_node} escuchando en el puerto {port}...")
            while True:
                conn, addr = s.accept()
                threading.Thread(target=self.handle_connection, args=(conn, addr)).start()


def LSR_menu():
    while True:
        print()
        print("1) Obtener pesos iniciales")
        print("2) Calcular/Recalcular tabla de enrutamiento")
        print("3) Enviar info a vecinos")
        print("4) Flooding")
        print("5) Mostrar tabla de enrutamiento")
        print("6) Salir")

        op = input("No. de la opción: ")

        if op in ["1", "2", "3", "4", "5", "6"]:
            return int(op)
        else:
            print("\n[[Error, input inválido]]\n")
