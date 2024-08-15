"""
Universidad del Valle de Guatemala

"""

import json


class Node:
    def __init__(self, name):
        self.name = name.upper()
        self.neighbors = []

    def add_neighbor(self, neighbor):
        self.neighbors.append(neighbor)

    def get_neighbors(self):
        return self.neighbors

    def __repr__(self):
        return f"Nodo: {self.name}{(' | Vecinos: '+str(self.neighbors)) if len(self.neighbors)>0 else ''}"
        
    def __str__(self):
        return f"Nodo: {self.name}{(' | Vecinos: '+str(self.neighbors)) if len(self.neighbors)>0 else ''}"