import socket
import pickle

### SERVER Changes occasionally, check on server computer to get IP
### Commands 'C' returns confirmation, queries 'Q' return objects in pickle form
### Need Exception handling
 
HEADER = 64
PORT = 5051
FORMAT = 'utf-8'
SERVER = "130.238.197.165"
ADDR = (SERVER, PORT)

def send(msg):
    """Sends commands to the Astrol server"""
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(ADDR)
    message = msg.encode(FORMAT)
    msg_length = len(message)
    send_length = str(msg_length).encode(FORMAT)
    send_length += b' ' * (HEADER - len(send_length))
    client.send(send_length)
    client.send(message)
    if msg.split(' ')[0] == 'C':
        returnMsg = client.recv(2048).decode(FORMAT)
    elif msg.split(' ')[0] == 'Q':
        returnMsg = pickle.loads(client.recv(2048))
    client.close()
    return returnMsg