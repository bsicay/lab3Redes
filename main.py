"""
Universidad del Valle de Guatemala
Algoritmos de Enrutamiento
"""

# Imports 
from Flooding import Flooding

# Programa principal
def main():

    # Bienvenida al usuario

    # Inicio del programa
    running = True
    while(running):
        
        op_MM = mainMenu()

        if (op_MM == 1):
            # Dijkstra
            print("Dijkstra")


        elif (op_MM == 2):
            # Flooding
            flooding = Flooding()
            flooding.start()

        elif (op_MM == 3):
            # Distance Vector Routing
            print("Distance Vector Routing")
      

        elif (op_MM == 4):
            # Salir del programa
            print("\nExit.\\n")
            running = False



def mainMenu():
    
    while(True):

        print("\n==================================")
        print("Elija el algoritmo a utilizar")
        print("1) Dijkstra")
        print("2) Flooding")
        print("3) Distance Vector Routing")
        print("4) Salir ")
        print("__________________________________")

        op = input("Número de la opción: ")

        if op not in [str(x + 1) for x in range(4)]:
            print("\n[[Error, input inválido]]\n")

        else:
            return int(op)


if __name__ == "__main__":
    main()


