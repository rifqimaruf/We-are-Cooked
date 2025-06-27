# src/client/network_handler.py
import threading
import json
import socket
import struct

from src.shared import config

class NetworkHandler:
    HEADER_SIZE = 4

    def __init__(self, game_manager):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.game_manager = game_manager
        self.thread = None
        self.running = False
        
    def start(self):
        """Mencoba terhubung ke server dan memulai thread penerima."""
        try:
            self.sock.connect((config.SERVER_IP, config.SERVER_PORT))
        except (socket.error, ConnectionRefusedError) as e:
            print(f"Connection to server failed: {e}")
            self.game_manager.handle_disconnect()
            return False

        self.running = True
        self.thread = threading.Thread(target=self._receiver_thread, daemon=True)
        self.thread.start()
        print("Network handler started and connected to server.")
        return True

    def stop(self):
        """Menghentikan thread dan menutup socket."""
        self.running = False
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
                self.sock.close()
            except OSError:
                pass # Socket sudah ditutup
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        print("Network handler stopped.")

    def send_action(self, data):
        """Meng-encode aksi, menambahkan header panjang, dan mengirim."""
        if not self.running:
            return
        try:
            encoded_data = json.dumps(data).encode('utf-8')
            header = struct.pack('>I', len(encoded_data))
            self.sock.sendall(header + encoded_data)
        except (socket.error, BrokenPipeError) as e:
            print(f"Failed to send action: {e}")
            self.game_manager.handle_disconnect()
            self.stop()

    def _recv_all(self, n):
        """Fungsi helper untuk memastikan kita menerima tepat N byte."""
        data = bytearray()
        while len(data) < n:
            try:
                packet = self.sock.recv(n - len(data))
                if not packet:
                    return None  # Koneksi ditutup oleh server
                data.extend(packet)
            except (socket.error, ConnectionResetError):
                return None
        return data
    
    def _receiver_thread(self):
        """Loop yang berjalan di background untuk menerima state dari server."""
        # Hal pertama yang diterima adalah state awal untuk mendapatkan client_id
        try:
            header_data = self._recv_all(self.HEADER_SIZE)
            if not header_data: raise ConnectionError("Server closed connection on initial handshake.")
            
            msg_len = struct.unpack('>I', header_data)[0]
            
            data = self._recv_all(msg_len)
            if not data: raise ConnectionError("Failed to receive initial state.")
            
            initial_state = json.loads(data.decode('utf-8'))
            self.game_manager.update_state(initial_state)

        except (json.JSONDecodeError, struct.error, ConnectionError, socket.error) as e:
            if self.running:
                print(f"Error receiving initial state, stopping: {e}")
            self.running = False
            self.game_manager.handle_disconnect()
            return

        # Loop utama untuk menerima broadcast state
        while self.running:
            try:
                header_data = self._recv_all(self.HEADER_SIZE)
                if not header_data:
                    raise ConnectionError("Server closed connection.")
                
                msg_len = struct.unpack('>I', header_data)[0]

                data = self._recv_all(msg_len)
                if not data:
                     raise ConnectionError("Failed to receive full message.")
                
                state = json.loads(data.decode('utf-8'))
                self.game_manager.update_state(state)
            except (json.JSONDecodeError, struct.error, ConnectionError, socket.error) as e:
                if self.running:
                    print(f"Error in receiver thread, stopping: {e}")
                self.running = False
                self.game_manager.handle_disconnect()
                break