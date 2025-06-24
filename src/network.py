import socket
import json
import config

class Network:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((config.SERVER_IP, config.SERVER_PORT))

    def send(self, data):
        self.sock.sendall(json.dumps(data).encode())

    def receive(self):
        data = self.sock.recv(config.BUFFER_SIZE)
        return json.loads(data.decode())
