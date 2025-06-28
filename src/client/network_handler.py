# src/client/network_handler.py
import threading
import json
import socket
import struct
import time
from src.shared import config

class NetworkHandler:
    def __init__(self, game_manager):
        self.lobby_sock = None
        self.game_sock = None
        self.game_manager = game_manager
        self.thread = None
        self.running = False

    def start(self):
        # --- PHASE 1: Connect to Lobby Server ---
        self.lobby_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.lobby_sock.settimeout(5.0)

        # IP host Windows Anda. Klien di Windows akan terhubung ke IP ini.
        # Jika klien dijalankan di WSL, ini harus IP eth0 WSL (misal: 172.25.231.123)
        CLIENT_HOST_IP_FOR_LOBBY = "192.168.1.65" # GANTI DENGAN IP HOST ANDA YANG SEBENARNYA!

        try:
            print(f"Connecting to Lobby Server at {CLIENT_HOST_IP_FOR_LOBBY}:{config.LOBBY_SERVER_PORT}")
            self.lobby_sock.connect((CLIENT_HOST_IP_FOR_LOBBY, config.LOBBY_SERVER_PORT))
            print("Connected to Lobby Server. Requesting game server...")
            
            self._send_json(self.lobby_sock, {"action": "request_game_server"})
            response = self._receive_json(self.lobby_sock)

            if response and response.get("status") == "success":
                game_server_ip = response.get("game_server_ip")
                game_server_port = response.get("game_server_port")
                print(f"Received game server details: {game_server_ip}:{game_server_port}")
                self.lobby_sock.close()
                self.lobby_sock = None
            else:
                print(f"Failed to get game server from Lobby: {response.get('message', 'Unknown error')}")
                self.game_manager.handle_disconnect()
                return False

        except (socket.error, ConnectionRefusedError, socket.timeout) as e:
            print(f"Connection to Lobby Server failed: {e}")
            self.game_manager.handle_disconnect()
            return False
        except Exception as e:
            print(f"Unhandled error during Lobby Server connection: {e}")
            self.game_manager.handle_disconnect()
            return False

        # --- PHASE 2: Connect to Assigned Game Server ---
        self.game_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.game_sock.settimeout(1.0)

        try:
            print(f"Connecting to Game Server at {game_server_ip}:{game_server_port}")
            self.game_sock.connect((game_server_ip, game_server_port))
            print("Connected to Game Server.")
        except (socket.error, ConnectionRefusedError, socket.timeout) as e:
            print(f"Connection to Game Server failed: {e}")
            self.game_manager.handle_disconnect()
            return False
        except Exception as e:
            print(f"Unhandled error during Game Server connection: {e}")
            self.game_manager.handle_disconnect()
            return False

        self.running = True
        self.thread = threading.Thread(target=self._receiver_thread, daemon=True)
        self.thread.start()
        print("Network handler started and connected to game server.")
        return True

    def stop(self):
        self.running = False
        if self.game_sock:
            try:
                self.game_sock.shutdown(socket.SHUT_RDWR)
                self.game_sock.close()
            except OSError:
                pass
        if self.lobby_sock:
            try:
                self.lobby_sock.shutdown(socket.SHUT_RDWR)
                self.lobby_sock.close()
            except OSError:
                pass
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        print("Network handler stopped.")

    def send_action(self, data):
        if not self.running or not self.game_sock:
            return
        try:
            encoded_data = json.dumps(data).encode('utf-8')
            header = struct.pack('>I', len(encoded_data))
            self.game_sock.sendall(header + encoded_data)
        except (socket.error, BrokenPipeError, OSError) as e:
            print(f"Failed to send action to game server: {e}")
            self.game_manager.handle_disconnect()
            self.stop()

    def _recv_all(self, n, sock):
        data = bytearray()
        while len(data) < n:
            try:
                packet = sock.recv(n - len(data))
                if not packet:
                    return None
                data.extend(packet)
            except (socket.timeout, BlockingIOError):
                raise socket.timeout
            except (socket.error, ConnectionResetError) as e:
                print(f"Network _recv_all error from {sock.getpeername()}: {e}")
                return None
        return data
    
    def _receiver_thread(self):
        try:
            # Menerima state awal dari Game Server
            header_data = self._recv_all(config.HEADER_SIZE, self.game_sock)
            if not header_data:
                raise ConnectionError("Game Server closed connection on initial handshake.")
            
            msg_len = struct.unpack('>I', header_data)[0]
            data = self._recv_all(msg_len, self.game_sock)
            if not data:
                raise ConnectionError("Failed to receive initial state from Game Server.")
            
            initial_state = json.loads(data.decode('utf-8'))
            self.game_manager.update_state(initial_state)

        except (json.JSONDecodeError, struct.error, ConnectionError, socket.error, socket.timeout) as e:
            if self.running:
                print(f"Error receiving initial state from Game Server, stopping: {type(e).__name__} - {e}")
            self.running = False
            self.game_manager.handle_disconnect()
            return
        except Exception as e:
            print(f"Unexpected error receiving initial state from Game Server: {type(e).__name__} - {e}")
            self.running = False
            self.game_manager.handle_disconnect()
            return

        while self.running:
            try:
                header_data = self._recv_all(config.HEADER_SIZE, self.game_sock)
                if not header_data:
                    raise ConnectionError("Game Server closed connection.")
                
                msg_len = struct.unpack('>I', header_data)[0]
                data = self._recv_all(msg_len, self.game_sock)
                if not data:
                    raise ConnectionError("Failed to receive full message from Game Server.")
                
                state = json.loads(data.decode('utf-8'))
                self.game_manager.update_state(state)
            except (socket.timeout, BlockingIOError):
                pass
            except (json.JSONDecodeError, struct.error, ConnectionError, socket.error) as e:
                if self.running:
                    print(f"Error in receiver thread from Game Server, stopping: {type(e).__name__} - {e}")
                self.running = False
                self.game_manager.handle_disconnect()
                break
            except Exception as e:
                print(f"Unexpected error in receiver thread from Game Server: {type(e).__name__} - {e}")
                self.running = False
                self.game_manager.handle_disconnect()
                break

    def _send_json(self, conn, data):
        message = json.dumps(data).encode('utf-8')
        header = len(message).to_bytes(config.HEADER_SIZE, 'big')
        conn.sendall(header + message)

    def _receive_json(self, conn):
        try:
            header = conn.recv(config.HEADER_SIZE)
            if not header:
                return None
            msg_len = int.from_bytes(header, 'big')
            
            data = bytearray()
            while len(data) < msg_len:
                packet = conn.recv(msg_len - len(data))
                if not packet:
                    return None
                data.extend(packet)
            return json.loads(data.decode('utf-8'))
        except (socket.timeout, ConnectionResetError, BrokenPipeError, json.JSONDecodeError, ValueError) as e:
            return None