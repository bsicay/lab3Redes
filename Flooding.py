"""
Universidad del Valle de Guatemala
Algoritmos de Enrutamiento
"""

import json
from node import Node

class Flooding():
    def __init__(self):
        self.nodes = []

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
        
    def flood(self, source_node, message):
        message_data = json.loads(message)
        message_type = message_data["type"]
        headers = message_data["headers"]
        
        if(source_node.name not in headers["receivers"]):
            headers["receivers"].append(source_node.name)
        
            for neighbor in source_node.get_neighbors():   
                if(neighbor.name not in headers["receivers"]):
                    if(neighbor.name != headers["to"]):
                        headers["receivers"].append(neighbor.name)
                    if headers['hop_count'] > 0:
                        print(f"Reenvía este paquete a: {neighbor.name}")
                        headers['hop_count'] -= 1
                        message = json.dumps(message_data, indent=4)
                        print(message)
                        print()
                        self.flood(neighbor, message)
                    else:
                        print(f"El hop count ha expirado para el mensaje a {headers['to']} en {neighbor.name}")


    def initiate_flood(self, source_node, message_data, destiny, hc):
        message = self.create_message(source_node, message_data, destiny, hc)
        self.flood(source_node, message)
            
    def create_message(self, source_node, message_data, destiny, hc):
        headers = {
            "from": source_node.name,
            "to": destiny.name,
            "hop_count": hc,
            "receivers": []
        }
        
        payload = message_data

        message = {
            "type": "message",
            "headers": headers,
            "payload": payload
        }
        
        return json.dumps(message, indent=4)
    
    def process_message(self, message, receiving_node):
        message_data = json.loads(message)
        message_type = message_data["type"]
        headers = message_data["headers"]

        if(receiving_node.name == headers['to']):
            if(message_type == "info"):
                print("Mensaje de información recibida:", headers)
                print()
            elif(message_type == "message"):
                print(f"({receiving_node.name}) Mensaje entrante de: {headers['from']}")
                print(message_data["payload"], "\n")

        for neighbor in receiving_node.get_neighbors():  
            if(neighbor.name not in headers["receivers"]):
                if(neighbor.name != headers["to"]):
                    headers["receivers"].append(neighbor.name)
                if headers['hop_count'] > 0:
                    print(f"Reenvía este paquete a: {neighbor.name}")
                    headers['hop_count'] -= 1
                    message = json.dumps(message_data, indent=4)
                    print(message)
                    print()
                    self.flood(neighbor, json.dumps(message_data, indent=4))
                else:
                    print(f"El hop count ha expirado para el mensaje a {headers['to']} en {neighbor.name}")
            
    def start(self):
        print()
        topology_file = input("Ingrese el nombre del archivo de topología (e.g., topo-1.txt): ")
        self.load_topology(topology_file)

        name = input("Nombre del nodo actual: ")
        actual_node = None

        # Encontrar el nodo correspondiente al nombre dado
        for node in self.nodes:
            if node.name == name.upper():
                actual_node = node
                break

        if actual_node is None:
            print(f"Error: Nodo {name} no encontrado en la topología.")
            return

        print("\nDatos cargados de la topología\n")
        for el in self.nodes:
            print(el)

        ver2 = False
        while(not ver2):
            print("\n1) Enviar mensaje")
            print("2) Recibir mensaje")
            print("3) Salir")
            op = int(input("Ingresa opción: "))
            
            match op:
                case 1:
                    sour = actual_node
                    dest = input("Nombre de nodo destino: ")
                    msg = input("Ingresa el mensaje que deseas enviar: ")
                    hc = int(input("Ingresa el hop_count: "))
                    
                    print()
                    
                    node_dest = Node(dest.upper())
                    self.initiate_flood(sour, msg, node_dest, hc)
                    
                case 2:
                    print("Ingresa el mensaje recibido (Doble Enter para confirmar)")
                    lines = []
                    while True:
                        line = input()
                        if line == "":
                            break
                        lines.append(line)
                    message_json = "\n".join(lines)   
                    self.process_message(message_json, actual_node)         
                    
                case 3:
                    print("Entendido, saliendo...")
                    ver2 = True
