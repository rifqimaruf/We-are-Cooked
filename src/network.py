import socket
import json
from src.shared import config

class Network:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((config.SERVER_IP, config.SERVER_PORT))
        self.addr = self.sock.getsockname()

    def send(self, data):
        self.sock.sendall(json.dumps(data).encode())

    def receive(self):
        data = self.sock.recv(config.BUFFER_SIZE)
        return json.loads(data.decode())
        
    def get_addr(self):
        """Return the client's socket address as a string"""
        return self.addr
