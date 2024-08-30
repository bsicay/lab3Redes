# Laboratorio 3 - Algoritmos de enrutamiento

## Contenido
- [Descripción](https://github.com/bsicay/lab3Redes?tab=readme-ov-file#descripci%C3%B3n)
- [Objetivos](https://github.com/bsicay/lab3Redes?tab=readme-ov-file#objetivos)
- [Temas vistos](https://github.com/bsicay/lab3Redes?tab=readme-ov-file#temas-vistos)
- [Organización](https://github.com/bsicay/lab3Redes?tab=readme-ov-file#organizaci%C3%B3n)
- [Compilación](https://github.com/bsicay/lab3Redes?tab=readme-ov-file#compilaci%C3%B3n)
- [Informe](https://github.com/bsicay/lab3Redes?tab=readme-ov-file#informe)
- [Integrantes](https://github.com/bsicay/lab3Redes?tab=readme-ov-file#integrantes)

## Descripción
Para cualquier router es trivial conocer a dónde se envian los mensajes, únicamente es necesario que se conozca el destino final y se reenvía al vecino que puede proveer la mejor ruta al destino, al final toda esta información es almacenada en las tablas de enrutamiento.

Para que pueda funcionar el internet se espera que tenga cierto dinamismo, y es necesario que las tablas de enrutamiento se puedan actualizar y acomodar a diversos cambios que sufra la infraestructura. Los algoritmos que hacen estas actualizaciones para las tablas de enrutamiento se conocen como `Algoritmos de enrutamiento`

## Objetivos
Conocer los algoritmos de enrutamiento utilizados en las implementaciones actuales de Internet.
- Comprender cómo funcionan las tablas de enrutamiento.
- Implementar los algoritmos de enrutamiento en una red simulada sobre el protocolo XMPP.
- Analizar el funcionamiento de los algoritmos de enrutamiento
  
## Temas vistos
- Algoritmos de enrutamiento
     - Dijkstra
     - Flooding
     - Link State Routing
     - Distance Vector Routing
- Tablas de enrutamiento
- Envío de mensajes
- Protocolo XMPP
- Topología
- Simulación de red

## Organización

|-- dijkstra

|-- DistanceVector

|-- Flooding

|-- FloogingLSR

|-- SLR

|-- main

|-- node

|-- ports

|-- RoutingTable

|-- topologia

## Compilación
Para correr el laboratorio se necesita crear una terminal por cada nodo de la topología, en donde se debe ejecutar `main.py`

## Informe
[Informe hecho para la práctica](https://docs.google.com/document/d/1oajd_Rplzeuf2QwlmoDx9Z3dLMxj9uxG9pMMjFpUjVY/edit?usp=sharing)

## Integrantes
Diana Lucía Fernández Villatoro - 21747

Brandon Rolando Sicay Cumes - 21757

Daniel Esteban Morales Urizar - 21785

Jennifer Michelle Toxcón Ordoñez - 21276
