import heapq
import json

def readFile(archivo):
    with open(archivo, 'r') as file:
        contenido = file.read()
    
    # Reemplazar comillas simples por comillas dobles para un JSON válido
    contenido = contenido.replace("'", '"')
    
    # Parsear el contenido JSON
    data = json.loads(contenido)
    
    tipo = data.get('type')
    configuracion = data.get('config')
    
    return tipo, configuracion

def dijkstra(graph, start):
    # Inicialización
    dist = {node: float('inf') for node in graph}
    dist[start] = 0
    prev = {node: None for node in graph}
    queue = [(0, start)]
    
    while queue:
        current_dist, current_node = heapq.heappop(queue)
        
        # Si la distancia actual es mayor que la registrada, se omite
        if current_dist > dist[current_node]:
            continue
        
        # Recorre los vecinos del nodo actual
        for neighbor, weight in graph[current_node]:
            distance = current_dist + weight
            
            # Si se encuentra una distancia más corta
            if distance < dist[neighbor]:
                dist[neighbor] = distance
                prev[neighbor] = current_node
                heapq.heappush(queue, (distance, neighbor))
    
    return dist, prev

tipo, configuracion = readFile("topologia.txt")

print("Tipo:", tipo)
print("Configuración:", configuracion)

# Ejemplo de uso
# graph = {
#     'A': [('B', 30), ('C', 8)],
#     'B': [('A', 4), ('C', 3), ('D', 5)],
#     'C': [('B', 5)],
#     'D': [('C', 3)]
# }

# start_node = 'A'
# distances, previous_nodes = dijkstra(graph, start_node)

# print("Distancias desde el nodo de inicio:")
# for node, distance in distances.items():
#     print(f"Distancia a {node}: {distance}")
