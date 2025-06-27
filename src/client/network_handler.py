import threading
import json
import socket
import struct
import time
from src.shared import config

class NetworkHandler:
    HEADER_SIZE = 4

    def __init__(self, game_manager):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.game_manager = game_manager
        self.thread = None
        self.running = False
        self.sock.settimeout(1.0) # Timeout untuk operasi socket (connect, recv)

    def start(self):
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
        self.running = False
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
                self.sock.close()
            except OSError:
                pass
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        print("Network handler stopped.")

    def send_action(self, data):
        if not self.running:
            return
        try:
            encoded_data = json.dumps(data).encode('utf-8')
            header = struct.pack('>I', len(encoded_data))
            self.sock.sendall(header + encoded_data)
        except (socket.error, BrokenPipeError, OSError) as e:
            print(f"Failed to send action: {e}")
            self.game_manager.handle_disconnect()
            self.stop()

    def _recv_all(self, n):
        data = bytearray()
        while len(data) < n:
            try:
                packet = self.sock.recv(n - len(data))
                if not packet:
                    return None
                data.extend(packet)
            except (socket.timeout, BlockingIOError):
                raise socket.timeout # Re-raise timeout to be handled by receiver_thread
            except (socket.error, ConnectionResetError) as e:
                print(f"Network _recv_all error: {e}")
                return None
        return data
    
    def _receiver_thread(self):
        try:
            # Menerima state awal (blocking call pertama)
            header_data = self._recv_all(self.HEADER_SIZE)
            if not header_data:
                raise ConnectionError("Server closed connection on initial handshake.")
            
            msg_len = struct.unpack('>I', header_data)[0]
            data = self._recv_all(msg_len)
            if not data:
                raise ConnectionError("Failed to receive initial state.")
            
            initial_state = json.loads(data.decode('utf-8'))
            self.game_manager.update_state(initial_state)

        except (json.JSONDecodeError, struct.error, ConnectionError, socket.error, socket.timeout) as e:
            if self.running:
                print(f"Error receiving initial state, stopping: {type(e).__name__} - {e}")
            self.running = False
            self.game_manager.handle_disconnect()
            return
        except Exception as e:
            print(f"Unexpected error receiving initial state: {type(e).__name__} - {e}")
            self.running = False
            self.game_manager.handle_disconnect()
            return

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
            except (socket.timeout, BlockingIOError):
                pass
            except (json.JSONDecodeError, struct.error, ConnectionError, socket.error) as e:
                if self.running:
                    print(f"Error in receiver thread, stopping: {type(e).__name__} - {e}")
                self.running = False
                self.game_manager.handle_disconnect()
                break
            except Exception as e:
                print(f"Unexpected error in receiver thread: {type(e).__name__} - {e}")
                self.running = False
                self.game_manager.handle_disconnect()
                break