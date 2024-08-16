import json
import socket
import threading
from node import Node
import time


class Flooding():
    def __init__(self, routing_table):
        self.RT = routing_table
        self.nodes = []
        self.node_ports = {}
        self.actual_node = None
        self.echo_times = {} 
        self.topology = {}  #  diccionario para almacenar la topología


    def add_node(self, node):
        self.nodes.append(node)

    def load_topology(self, filename):
        with open(filename, 'r') as file:
            topology_data = json.load(file)
            config = topology_data['config']
            node_dict = {}

            # Crear nodos
            for node_name in config:
                if node_name not in node_dict:
                    node_dict[node_name] = Node(node_name)
                current_node = node_dict[node_name]

                # Crear vecinos y conexiones
                for neighbor_name in config[node_name]:
                    if neighbor_name not in node_dict:
                        node_dict[neighbor_name] = Node(neighbor_name)
                    neighbor_node = node_dict[neighbor_name]
                    current_node.add_neighbor(neighbor_node)

            # Guardar todos los nodos creados
            self.nodes = list(node_dict.values())

    def load_ports(self, filename):
        with open(filename, 'r') as file:
            self.node_ports = json.load(file)

    def flood(self, source_node, message):
        message_data = json.loads(message)
        message_type = message_data["type"]
        headers = message_data["headers"]

        if source_node.name not in headers["receivers"]:
            headers["receivers"].append(source_node.name)

            for neighbor in source_node.get_neighbors():
                if neighbor.name not in headers["receivers"]:
                    if neighbor.name != message_data["to"]:
                        headers["receivers"].append(neighbor.name)
                    if message_data['hop_count'] > 0:
                        print(f"Reenvía este paquete a: {neighbor.name}")
                        message_data['hop_count'] -= 1
                        message = json.dumps(message_data, indent=4)
                        print(message)
                        self.send_message(neighbor.name, message)
                    else:
                        print(f"El hop count ha expirado para el mensaje a {message_data['to']} en {neighbor.name}")

    def initiate_flood(self, source_node, message_data, destiny, hc):
        message = self.create_message(source_node, message_data, destiny, hc)
        self.flood(source_node, message)

    def create_message(self, source_node, message_data, destiny, hc):
        headers = {
            "receivers": []
        }

        payload = message_data
        print(source_node)
        message = {
            "type": "message",
            "from": source_node.name,
            "to": destiny.name,
            "hop_count": hc,
            "headers": headers,
            "payload": payload
        }

        return json.dumps(message, indent=4)
    
    def create_echo_message(self, source_node, message_data, destiny, hc):
        headers = {
            "receivers": []
        }

        payload = message_data
        print(source_node)
        message = {
            "type": "echo",
            "from": source_node.name,
            "to": destiny.name,
            "hop_count": hc,
            "headers": headers,
            "payload": payload
        }

        return json.dumps(message, indent=4)

    def process_message(self, message, receiving_node):
        message_data = json.loads(message)
        message_type = message_data["type"]

        if message_type == "echo":
            self.handle_echo(message_data)
            return  # No hay necesidad de propagar un echo

        if receiving_node.name == message_data['to']:
            if message_type == "info":
                print("Mensaje de información recibida:", message_data)
            elif message_type == "message":
                print(f"({receiving_node.name}) Mensaje entrante de: {message_data['from']}")
                print(message_data["payload"], "\n")

        for neighbor in receiving_node.get_neighbors():
            if neighbor.name not in message_data["headers"]["receivers"]:
                if neighbor.name != message_data["to"]:
                    message_data["headers"]["receivers"].append(neighbor.name)
                if message_data['hop_count'] > 0:
                    print(f"Reenvía este paquete a: {neighbor.name}")
                    message_data['hop_count'] -= 1
                    message = json.dumps(message_data, indent=4)
                    self.send_message(neighbor.name, message)
                else:
                    print(f"El hop count ha expirado para el mensaje a {message_data['to']} en {neighbor.name}")

    def send_message(self, neighbor_name, message):
        print(neighbor_name)
        print(message)
        port = self.node_ports.get(neighbor_name)
        if port:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(('localhost', port))
                s.sendall(message.encode('utf-8'))

    def handle_connection(self, conn, addr):
        print('Handle from Flodding')
        with conn:
            message = conn.recv(1024).decode('utf-8')
            print(f"Mensaje recibido de {addr}: {message}")
            self.process_message(message, self.actual_node)

    def start_server(self):
        port = self.node_ports[self.actual_node.name]
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', port))
            s.listen()
            print(f"Nodo {self.actual_node.name} escuchando en el puerto {port}...")
            while True:
                conn, addr = s.accept()
                threading.Thread(target=self.handle_connection, args=(conn, addr)).start()

    def send_echo(self, neighbor_name):
        start_time = time.time()
        self.echo_times[neighbor_name] = start_time  # Guardar el tiempo de inicio

        message_data = {"type": "echo", "timestamp": start_time}
        message = self.create_echo_message(self.actual_node, message_data, Node(neighbor_name), 1)
        self.send_message(neighbor_name, message)

    def handle_echo(self, message_data):
        origin = message_data['from']
        if origin in self.echo_times:
            end_time = time.time()
            start_time = self.echo_times[origin]
            delay = end_time - start_time  # Calcular el delay
            print(f"Echo recibido desde {origin} con un delay de {delay*1000:.2f} ms")
            return delay
        else:
            print("Echo recibido sin tiempo de inicio registrado.")

    def start_flooding_topology(self):
        """
        Inicia el proceso de flooding para recopilar la topología completa.
        """
        self._send_flooding_message()

    def _send_flooding_message(self):
        origen = self.actual_node.name
        neighbors_with_weights = {
            n.name: self.topology.get(n.name, self.RT.get_info(n.name)[0])
            for n in self.actual_node.get_neighbors()
        }
        message = {
            "type": "topology",
            "headers": {
                "origen": origen,
                "intermediarios": [origen]
            },
            "payload": {
                "neighbors": neighbors_with_weights
            }
        }

        message = json.dumps(message)
        self._send_message_neighbors(message)

    def _send_message_neighbors(self, message):
        for n in self.actual_node.get_neighbors():
            self.send_message(n.name, message)

    def handle_topology_message(self, message):
        origin = message['headers']['origen']
        topology_update = message['payload']['neighbors']

        # Actualiza la topología global con la nueva información recibida
        if origin not in self.topology:
            self.topology[origin] = {}

        for neighbor, weight in topology_update.items():
            self.topology[origin][neighbor] = weight

        # Continúa el flooding a otros vecinos
        for neighbor in self.actual_node.get_neighbors():
            if neighbor.name not in message['headers']['intermediarios']:
                message['headers']['intermediarios'].append(self.actual_node.name)
                self.send_message(neighbor.name, json.dumps(message))


    def start(self):
        # topology_file = input("Ingrese el nombre del archivo de topología (e.g., topo-1.txt): ")
        # ports_file = input("Ingrese el nombre del archivo de puertos (e.g., ports.json): ")
        topology_file = "topologia.txt"
        ports_file =  "ports.json"
        self.load_topology(topology_file)
        self.load_ports(ports_file)

        name = input("Nombre del nodo actual: ")
        self.actual_node = None

        # Encontrar el nodo correspondiente al nombre dado
        for node in self.nodes:
            if node.name == name.upper():
                self.actual_node = node
                break

        if self.actual_node is None:
            print(f"Error: Nodo {name} no encontrado en la topología.")
            return

        # Iniciar el servidor para este nodo en un hilo separado
        threading.Thread(target=self.start_server, daemon=True).start()

        print("\nDatos cargados de la topología\n")
        # for el in self.nodes:
        #     print(el)

        ver2 = False
        while not ver2:
            print("\n1) Enviar mensaje")
            print("2) Salir")
            op = int(input("Ingresa opción: "))

            match op:
                case 1:
                    sour = self.actual_node
                    dest = input("Nombre de nodo destino: ")
                    msg = input("Ingresa el mensaje que deseas enviar: ")
                    hc = int(input("Ingresa el hop_count: "))

                    node_dest = Node(dest.upper())
                    self.initiate_flood(sour, msg, node_dest, hc)

                case 2:
                    print("Entendido, saliendo...")
                    ver2 = True
