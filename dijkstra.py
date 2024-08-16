# Dijkstra.py
import heapq

class Dijkstra:
    @staticmethod
    def calculate_routing_table(topology, start_node):
        distances = {}
        previous = {}
        queue = []
        
        for node in topology:
            if node == start_node:
                distances[node] = 0
                heapq.heappush(queue, (0, node))
            else:
                distances[node] = float("inf")
                heapq.heappush(queue, (float("inf"), node))
            previous[node] = None
        
        while queue:
            u = heapq.heappop(queue)[1]
            for v, weight in topology[u].items():
                alt = distances[u] + weight
                if alt < distances[v]:
                    distances[v] = alt
                    previous[v] = u
                    for i in range(len(queue)):
                        if queue[i][1] == v:
                            queue[i] = (alt, v)
                            heapq.heapify(queue)
        
        routing_table = {}
        for node, previous_node in previous.items():
            if previous_node is not None:
                path = Dijkstra.get_path(previous, node)
                routing_table[node] = (path, distances[node])
        
        return routing_table
    
    @staticmethod
    def get_path(previous, destination):
        path = [destination]
        while destination in previous and previous[destination] is not None:
            destination = previous[destination]
            path.insert(0, destination)
        
        return path
