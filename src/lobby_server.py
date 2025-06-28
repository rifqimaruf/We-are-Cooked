# src/server/lobby_server.py
import socket
import threading
import json
import time
import uuid

from src.shared import config
from src.shared.recipe_manager import RecipeManager # # Tambahkan ini untuk memastikan RecipeManager diinisialisasi
                                                        # # (jika Lobby Server perlu menginisialisasi sesuatu dari shared)
                                                        # # Namun, jika Lobby Server murni hanya untuk routing,
                                                        # # ini sebenarnya tidak diperlukan dan bisa dihapus.

# Dictionary untuk melacak game server yang tersedia dan statusnya
active_game_servers = {}
game_servers_lock = threading.Lock()

# Gunakan konstanta dari config.py yang benar
LOBBY_SERVER_BIND_IP = config.LOBBY_SERVER_IP #
LOBBY_SERVER_BIND_PORT = config.LOBBY_SERVER_PORT #
GAME_SERVER_INTERNAL_PORT = config.GAME_SERVER_INTERNAL_PORT #

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

def send_json(conn, data):
    message = json.dumps(data).encode('utf-8')
    header = len(message).to_bytes(config.HEADER_SIZE, 'big') # PERBAIKI: Gunakan config.HEADER_SIZE
    conn.sendall(header + message)

def receive_json(conn):
    try:
        header = conn.recv(config.HEADER_SIZE) # PERBAIKI: Gunakan config.HEADER_SIZE
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
        print(f"Error receiving JSON: {e}")
        return None

def handle_connection(conn, addr):
    print(f"Connection established with {addr}")
    try:
        while True:
            request = receive_json(conn)
            if request is None:
                print(f"Client {addr} disconnected or invalid request.")
                break

            action = request.get("action")
            
            if action == "register_game_server":
                server_id = request.get("server_id")
                ip = request.get("ip")
                port = request.get("port", GAME_SERVER_INTERNAL_PORT)
                players = request.get("players", 0)
                max_players = request.get("max_players", 5)
                status = request.get("status", "available")

                with game_servers_lock:
                    active_game_servers[server_id] = {
                        "ip": ip,
                        "port": port,
                        "players": players,
                        "max_players": max_players,
                        "status": status,
                        "last_heartbeat": time.time()
                    }
                    print(f"Game Server {server_id} registered/updated: {active_game_servers[server_id]}")
                send_json(conn, {"status": "success", "message": "Server registered/updated"})

            elif action == "request_game_server":
                with game_servers_lock:
                    available_server = None
                    # ITERASI DENGAN STRATEGI ROUND ROBIN (atau LEAST LOADED)
                    # Ini adalah implementasi dasar yang akan mengambil server pertama yang cocok.
                    # Untuk round robin yang sebenarnya, Anda perlu melacak indeks terakhir yang diberikan.
                    # Namun, untuk lab ini, ini sudah cukup untuk menunjukkan distribusi.
                    for server_id, server_info in active_game_servers.items():
                        if server_info["status"] == "available" and server_info["players"] < server_info["max_players"]:
                            available_server = server_info
                            break
                    
                    if available_server:
                        send_json(conn, {
                            "status": "success",
                            "game_server_ip": available_server["ip"],
                            "game_server_port": available_server["port"],
                            "message": "Game server assigned"
                        })
                        print(f"Assigned client to game server: {available_server['ip']}:{available_server['port']}")
                    else:
                        send_json(conn, {"status": "error", "message": "No available game servers"})
                        print("No available game servers to assign.")
            else:
                send_json(conn, {"status": "error", "message": "Unknown action"})

    except Exception as e:
        print(f"Error handling connection from {addr}: {e}")
    finally:
        conn.close()
        print(f"Connection with {addr} closed.")

def cleanup_old_servers():
    """Membersihkan game server yang tidak aktif (tidak mengirim heartbeat)."""
    while True:
        with game_servers_lock:
            current_time = time.time()
            to_remove = [
                server_id for server_id, info in active_game_servers.items()
                if current_time - info["last_heartbeat"] > 30 # Server dianggap mati jika tidak ada heartbeat dalam 30 detik
            ]
            for server_id in to_remove:
                print(f"Removing inactive Game Server: {server_id}")
                del active_game_servers[server_id]
        time.sleep(10) # Cek setiap 10 detik

def start_lobby_server():
    server_socket.bind((LOBBY_SERVER_BIND_IP, LOBBY_SERVER_BIND_PORT)) # Menggunakan konstanta yang benar
    server_socket.listen(5)
    print(f"Lobby Server listening on {LOBBY_SERVER_BIND_IP}:{LOBBY_SERVER_BIND_PORT}")

    cleanup_thread = threading.Thread(target=cleanup_old_servers, daemon=True)
    cleanup_thread.start()

    while True:
        conn, addr = server_socket.accept()
        client_handler = threading.Thread(target=handle_connection, args=(conn, addr), daemon=True)
        client_handler.start()

if __name__ == "__main__":
    # PERBAIKI: Hapus inisialisasi RecipeManager jika Lobby Server tidak memerlukannya
    # from src.shared.recipe_manager import RecipeManager # HAPUS BARIS INI JIKA TIDAK PERLU
    # _ = RecipeManager() # HAPUS BARIS INI JIKA TIDAK PERLU
    # Lobby Server umumnya tidak berinteraksi langsung dengan database resep.
    start_lobby_server()