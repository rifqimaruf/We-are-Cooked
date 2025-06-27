import socket
import json
import struct
from . import config

class Network:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((config.SERVER_IP, config.SERVER_PORT))
        self.addr = self.sock.getsockname()
        self.header_size = 4

    def send(self, data):
        encoded_data = json.dumps(data).encode('utf-8')
        header = struct.pack('>I', len(encoded_data))
        self.sock.sendall(header + encoded_data)

    def receive(self):
        header_data = self._recv_all(self.header_size)
        if not header_data:
            return None
        msg_len = struct.unpack('>I', header_data)[0]
        return json.loads(self._recv_all(msg_len).decode('utf-8'))

    def _recv_all(self, n):
        data = bytearray()
        while len(data) < n:
            try:
                packet = self.sock.recv(n - len(data))
                if not packet:
                    return None
                data.extend(packet)
            except (socket.error, ConnectionResetError) as e:
                print(f"Network recv error: {e}")
                return None
        return data

    def get_addr(self):
        return self.addr