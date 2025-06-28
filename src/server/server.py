# src/server/server.py (Ini adalah Game Server)
import socket
import threading
import json
import random
import time
import signal
import struct
import copy
import uuid # Diperlukan untuk menghasilkan ID unik server
import os   # Diperlukan untuk mengakses environment variables

from typing import Dict, Any
from src.shared.game_state import GameState # Asumsi GameState sudah memiliki game_outcome dan game_started
from src.shared import config
from src.shared.recipe_manager import RecipeManager # Diperlukan untuk inisialisasi RecipeManager

# --- Game Server Identification ---
GAME_SERVER_ID = str(uuid.uuid4()) # ID unik untuk Game Server ini
# IP internal Lobby Server di dalam jaringan Docker (harus sesuai dengan konfigurasi docker-compose.yml)
LOBBY_SERVER_INTERNAL_IP = "172.16.16.104"
LOBBY_SERVER_PORT_FOR_GAME_SERVER = config.LOBBY_SERVER_PORT
HEARTBEAT_INTERVAL = 5 # Detik, seberapa sering Game Server melaporkan status ke Lobby Server

# --- IP Host Eksternal dan Port yang Diekspos ---
# Ini adalah IP host Windows Anda (atau IP WSL jika klien berjalan di WSL)
# yang dapat diakses oleh klien. Sesuaikan dengan IP aktual Anda!
CLIENT_ACCESSIBLE_HOST_IP = "192.168.1.65" # <<< PENTING: GANTI DENGAN IP HOST ANDA YANG BENAR >>>

# Dapatkan port eksternal Game Server ini dari Environment Variable yang diset di docker-compose.yml
# Ini adalah port yang diekspos Docker ke host (misal: 5555, 5556, atau 5557)
GAME_SERVER_EXTERNAL_PORT = int(os.environ.get("GAME_SERVER_EXTERNAL_PORT", str(config.GAME_SERVER_INTERNAL_PORT)))
if GAME_SERVER_EXTERNAL_PORT == config.GAME_SERVER_INTERNAL_PORT:
    print("WARNING: GAME_SERVER_EXTERNAL_PORT not set via ENV. Defaulting to internal port. Client connection might fail from host.")


# --- Global Game State and Connections ---
game_state = GameState()
connections: Dict[str, socket.socket] = {} # Koneksi klien yang terhubung ke Game Server ini
clients_info: Dict[str, Dict[str, Any]] = {} # Informasi klien (username, status ready)

timer_thread_active = False
timer_thread_instance = None
shutdown_flag = False

last_merge_check_time = 0
MERGE_CHECK_INTERVAL = 0.2
BROADCAST_INTERVAL = 0.1

# --- Game Server Socket (Ini adalah socket yang akan didengarkan Game Server untuk klien yang DIARAHKAN oleh Lobby) ---
game_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
game_server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
# Bind ke 0.0.0.0 agar bisa diakses dari jaringan Docker internal
game_server_socket.bind((config.LOBBY_SERVER_IP, config.GAME_SERVER_INTERNAL_PORT))
game_server_socket.listen()
game_server_socket.settimeout(0.5)
print(f"Game Server (ID: {GAME_SERVER_ID}) listening on {config.LOBBY_SERVER_IP}:{config.GAME_SERVER_INTERNAL_PORT}")

def signal_handler(signum, frame):
    global shutdown_flag
    print("\nCtrl+C detected. Shutting down...")
    game_server_socket.close()
    shutdown_flag = True

signal.signal(signal.SIGINT, signal_handler)

# --- Helper Functions for JSON Communication (untuk komunikasi antar Server dan Server-Klien) ---
def send_json(conn, data):
    message = json.dumps(data).encode('utf-8')
    header = len(message).to_bytes(config.HEADER_SIZE, 'big') # Menggunakan HEADER_SIZE dari config.py
    conn.sendall(header + message)

def receive_json(conn):
    try:
        header = conn.recv(config.HEADER_SIZE) # Menggunakan HEADER_SIZE dari config.py
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
        # Menghilangkan log error timeout agar tidak terlalu berisik
        # print(f"Error receiving JSON: {e}")
        return None

# --- Heartbeat Function to Lobby Server ---
def send_heartbeat_to_lobby():
    try:
        lobby_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        lobby_conn.settimeout(5) # Timeout koneksi ke Lobby Server
        lobby_conn.connect((LOBBY_SERVER_INTERNAL_IP, LOBBY_SERVER_PORT_FOR_GAME_SERVER))
        
        # IP dan Port yang akan dilaporkan ke Lobby Server agar klien dapat terhubung
        # Ini adalah IP Host dan Port Eksternal yang diekspos Docker
        ip_to_report_to_lobby = CLIENT_ACCESSIBLE_HOST_IP
        port_to_report_to_lobby = GAME_SERVER_EXTERNAL_PORT
        
        with game_state._lock: # Mengunci game_state saat mengakses data pemain
            player_count = len(game_state.players)
            current_game_status = "available"
            if game_state.game_started: # Menggunakan game_state.game_started (dari objek)
                if player_count >= 5: # Asumsi maksimum pemain per Game Server adalah 5
                    current_game_status = "playing" # Game sedang berjalan dan sudah penuh
                else:
                    current_game_status = "in_progress" # Game dimulai tapi belum penuh
            
        heartbeat_data = {
            "action": "register_game_server",
            "server_id": GAME_SERVER_ID,
            "ip": ip_to_report_to_lobby, # Ini adalah IP Host yang dapat diakses klien
            "port": port_to_report_to_lobby, # Ini adalah port yang diekspos ke Host
            "players": player_count,
            "max_players": 5, # Konfigurasi maksimum pemain per Game Server
            "status": current_game_status
        }
        send_json(lobby_conn, heartbeat_data)
        response = receive_json(lobby_conn)
        if response and response.get("status") == "success":
            pass # Heartbeat berhasil, tidak perlu log terlalu banyak
        else:
            print(f"Heartbeat failed or unexpected response from lobby: {response}")
    except Exception as e:
        print(f"Could not connect to Lobby Server at {LOBBY_SERVER_INTERNAL_IP}:{LOBBY_SERVER_PORT_FOR_GAME_SERVER}: {e}")
    finally:
        if 'lobby_conn' in locals() and lobby_conn: # Pastikan objek socket ada sebelum mencoba menutup
            lobby_conn.close()

# Thread untuk mengirim heartbeat secara berkala ke Lobby Server
def heartbeat_thread():
    time.sleep(2) # Beri waktu Lobby Server untuk start up
    while not shutdown_flag:
        send_heartbeat_to_lobby()
        time.sleep(HEARTBEAT_INTERVAL)

# --- FUNGSI GLOBAL UTAMA GAME SERVER ---

def create_and_broadcast_state():
    state_dict = game_state.to_dict()
    state_dict["clients_info"] = clients_info
    state_dict["game_started"] = game_state.game_started # Gunakan game_state.game_started
    
    encoded_datas = {}
    for player_id in connections.keys():
        state_dict_with_id = copy.deepcopy(state_dict)
        state_dict_with_id["client_id"] = player_id
        encoded_data = json.dumps(state_dict_with_id).encode('utf-8')
        header = struct.pack('>I', len(encoded_data))
        encoded_datas[player_id] = header + encoded_data

    disconnected_players = []
    for player_id, conn in list(connections.items()):
        try:
            conn.sendall(encoded_datas[player_id])
        except (socket.error, BrokenPipeError, OSError) as e:
            print(f"Client {player_id} detected as disconnected during broadcast: {e}")
            disconnected_players.append(player_id)

    if disconnected_players:
        cleanup_disconnected_players(disconnected_players)


def cleanup_disconnected_players(player_ids: list):
    global clients_info # Pastikan clients_info dideklarasikan sebagai global jika diubah
    for player_id in player_ids:
        print(f"Cleaning up disconnected client: {player_id}")
        if player_id in connections:
            connections[player_id].close()
            del connections[player_id]
        if player_id in clients_info:
            del clients_info[player_id]
        game_state.remove_player(player_id)
    
    send_heartbeat_to_lobby() # Kirim heartbeat untuk update jumlah pemain setelah cleanup


def restart_game():
    global game_state, timer_thread_active, timer_thread_instance, clients_info
    if timer_thread_instance and timer_thread_instance.is_alive():
        print(f"Attempting to stop old timer thread. Active: {timer_thread_active}, Alive: {timer_thread_instance.is_alive()}")
        timer_thread_active = False
        timer_thread_instance.join(timeout=1.0)
        if timer_thread_instance.is_alive():
            print("Warning: Old timer thread did not terminate in time for restart.")

    game_state = GameState() # Reset game state
    game_state.game_started = True # Pastikan game_state.game_started diatur ke True
    print(f"Restarting game: game_state.game_started set to {game_state.game_started}") 

    game_state.initialize_stations() # Inisialisasi posisi stasiun
    game_state.generate_orders(len(clients_info)) # Generate order awal
    
    # Inisialisasi doorprize spawn time
    game_state.doorprize_spawn_time = time.time() - game_state.next_doorprize_spawn_delay
    game_state.next_doorprize_spawn_delay = random.uniform(config.DOORPRIZE_SPAWN_INTERVAL_MIN, config.DOORPRIZE_SPAWN_INTERVAL_MAX)

    # Inisialisasi pemain dengan bahan dan posisi acak
    num_players_connected = len(clients_info)
    required_ingredients_pool = []
    for order in game_state.orders:
        required_ingredients_pool.extend(order['ingredients'])
    random.shuffle(required_ingredients_pool)
    all_possible_ingredients = ['Rice', 'Salmon', 'Tuna', 'Shrimp', 'Egg', 'Seaweed', 
                                'Cucumber', 'Avocado', 'Crab Meat', 'Eel', 'Cream Cheese', 'Fish Roe']
    ingredients_to_assign = []
    temp_required_pool = list(required_ingredients_pool)
    for player_id in clients_info.keys():
        ingredient = None
        if temp_required_pool:
            ingredient = temp_required_pool.pop(0)
        else:
            ingredient = random.choice(all_possible_ingredients)
        ingredients_to_assign.append((player_id, ingredient))
    random.shuffle(ingredients_to_assign)
    for player_id, ingredient in ingredients_to_assign:
        pos = (random.randint(0, config.GRID_WIDTH - 1), random.randint(0, config.GRID_HEIGHT - 1))
        game_state.add_player(player_id, ingredient, pos) 
        print(f"Added player {player_id} as {ingredient} to game state at {pos}")
    
    timer_thread_active = True
    timer_thread_instance = threading.Thread(target=game_timer_thread, daemon=True)
    timer_thread_instance.start()
    print(f"Game timer thread started. Initial game_started state: {game_state.game_started}") 
    
    send_heartbeat_to_lobby() # Kirim heartbeat setelah game di-restart
    create_and_broadcast_state()
    print("Game restarted with new state.")

def return_to_lobby():
    global game_state, timer_thread_active, timer_thread_instance, clients_info
    if timer_thread_instance and timer_thread_instance.is_alive():
        print(f"Attempting to stop old timer thread for lobby return. Active: {timer_thread_active}, Alive: {timer_thread_instance.is_alive()}")
        timer_thread_active = False
        timer_thread_instance.join(timeout=1.0)
        if timer_thread_instance.is_alive():
            print("Warning: Old timer thread did not terminate for lobby return.")
    
    game_state.game_started = False # Atur game_state.game_started ke False
    for player_id in clients_info:
        clients_info[player_id]["ready"] = False
    
    game_state = GameState() # Reset game state sepenuhnya
    print(f"Returning to lobby: game_state.game_started set to {game_state.game_started}") 

    send_heartbeat_to_lobby() # Kirim heartbeat setelah kembali ke lobby
    create_and_broadcast_state()
    print("All players returned to lobby.")

def handle_client(conn: socket.socket, addr: Any):
    player_id = str(addr)
    connections[player_id] = conn
    clients_info[player_id] = {"username": f"Chef_{addr[1] % 1000}", "ready": False}
    print(f"Client {player_id} connected. Total players: {len(connections)}")
    send_heartbeat_to_lobby() # Kirim heartbeat saat klien baru terhubung

    try:
        # Kirim state awal ke klien yang baru terhubung
        initial_state_for_client = game_state.to_dict()
        initial_state_for_client["client_id"] = player_id
        initial_state_for_client["clients_info"] = clients_info
        initial_state_for_client["game_started"] = game_state.game_started # Gunakan game_state.game_started
        
        msg_json = json.dumps(initial_state_for_client).encode('utf-8')
        msg_length = len(msg_json)
        header = struct.pack('>I', msg_length)
        conn.sendall(header + msg_json)

        current_recv_buffer = bytearray() 
        conn.settimeout(0.5)

        while not shutdown_flag:
            try:
                chunk = conn.recv(config.BUFFER_SIZE)
                if not chunk:
                    print(f"Client {player_id} closed connection gracefully.")
                    break
                
                current_recv_buffer.extend(chunk)

                while len(current_recv_buffer) >= config.HEADER_SIZE:
                    msg_len_from_header = struct.unpack('>I', current_recv_buffer[:config.HEADER_SIZE])[0]
                    
                    if len(current_recv_buffer) < config.HEADER_SIZE + msg_len_from_header:
                        break 
                    
                    actual_message_bytes = current_recv_buffer[config.HEADER_SIZE : config.HEADER_SIZE + msg_len_from_header]
                    current_recv_buffer = current_recv_buffer[config.HEADER_SIZE + msg_len_from_header:]
                    
                    msg = json.loads(actual_message_bytes.decode('utf-8'))
                    action = msg.get("action")
                    
                    if action == "return_to_lobby":
                        print(f"Client {player_id} sent return_to_lobby. game_state.game_started: {game_state.game_started}")
                        return_to_lobby()
                        break # Putuskan koneksi klien dari Game Server ini
                    
                    elif not game_state.game_started: # Ini adalah fase lobby di dalam Game Server
                        if action == "set_username":
                            clients_info[player_id]["username"] = msg.get("username", "Unknown")
                            print(f"Client {player_id} set username to {clients_info[player_id]['username']}. game_state.game_started: {game_state.game_started}")
                        elif action == "toggle_ready":
                            clients_info[player_id]["ready"] = not clients_info[player_id].get("ready", False)
                            print(f"Client {player_id} toggled ready. Status: {clients_info[player_id]['ready']}. game_state.game_started: {game_state.game_started}")
                        elif action == "start_game": 
                            print(f"Client {player_id} sent start_game. All ready: {all(c['ready'] for c in clients_info.values())}. game_state.game_started: {game_state.game_started}")
                            if all(c["ready"] for c in clients_info.values()) and len(clients_info) > 0: # Minimal 1 pemain untuk memulai game
                                restart_game()
                                continue
                        create_and_broadcast_state() 
                        send_heartbeat_to_lobby() # Update lobby status setiap ada perubahan ready/username
                    else: # Game sedang berjalan
                        if game_state.timer > 0:
                            if action == "move":
                                game_state.move_player(player_id, msg.get("direction"))
                            elif action == "restart": 
                                print(f"Client {player_id} sent restart from in-game. game_state.game_started: {game_state.game_started}")
                                restart_game()
                                continue
                            elif action == "change_ingredient":
                                if game_state.can_player_change_ingredient(player_id):
                                    all_possible_ingredients = ['Rice', 'Salmon', 'Tuna', 'Shrimp', 'Egg', 'Seaweed',
                                        'Cucumber', 'Avocado', 'Crab Meat', 'Eel', 'Cream Cheese', 'Fish Roe']
                                    with game_state._lock:
                                        player = game_state.players.get(player_id)
                                        if player:
                                            old_ing = player.ingredient
                                            new_ing = random.choice([i for i in all_possible_ingredients if i != old_ing])
                                            player.ingredient = new_ing
                                            print(f"Player {player_id} changed ingredient from {old_ing} to {new_ing} at Enter Station.")
                                else:
                                    print(f"Player {player_id} tried to change ingredient but not on Enter Station.")

            except socket.timeout:
                pass 
            except (json.JSONDecodeError, struct.error) as e:
                print(f"Error parsing data from {player_id}: {type(e).__name__} - {e}. Raw buffer: {current_recv_buffer.decode(errors='ignore')}")
                break 
            except (ConnectionResetError, BrokenPipeError, OSError) as e:
                print(f"Client {player_id} disconnected unexpectedly: {e}")
                break
            except Exception as e:
                print(f"Unhandled error in handle_client for {player_id}: {type(e).__name__} - {e}")
                break
    finally:
        cleanup_disconnected_players([player_id]) # Membersihkan pemain yang terputus
        send_heartbeat_to_lobby() # Kirim heartbeat terakhir setelah pemain putus
        print(f"Client {player_id} handler stopped.")

def game_timer_thread():
    """Thread yang mengatur timer game, deteksi fusi, dan broadcast state."""
    global timer_thread_active, last_merge_check_time, game_state # Pastikan game_state diakses sebagai global
    
    start_time = time.time()
    end_time = start_time + config.GAME_TIMER_SECONDS

    last_broadcast_time = time.time()

    print(f"Timer thread: Starting with timer_thread_active={timer_thread_active} and game_state.game_started={game_state.game_started}")

    # Loop ini berjalan selama timer_thread_active TRUE dan game_state.game_started TRUE
    while timer_thread_active and game_state.game_started:
        current_time = time.time()
        remaining = max(0, end_time - current_time)
        game_state.timer = int(remaining) # Update timer game_state

        game_state.check_for_merge() # Cek fusi bahan
        game_state.process_fusion_events() # Proses event fusi yang terjadi

        # --- Logika Doorprize Station ---
        # Ini akan memunculkan doorprize jika sudah waktunya dan belum ada doorprize aktif
        if game_state.doorprize_station is None and \
           current_time - game_state.doorprize_spawn_time >= game_state.next_doorprize_spawn_delay:
            game_state.spawn_doorprize_station(current_time)
        elif game_state.doorprize_station is not None:
            game_state.check_doorprize_interaction() # Cek interaksi pemain dan kadaluarsa doorprize

        # --- LOGIKA KUNCI: PEMBANGKITAN ORDER BARU ---
        # Pesanan baru akan dibuat jika:
        # 1. Sudah lewat waktu 'next_order_spawn_delay' sejak pesanan terakhir dibuat.
        # 2. Ada pemain aktif di Game Server ini (minimal 1 pemain).
        # 3. Jumlah pesanan yang aktif saat ini kurang dari batas maksimum (misal 3).
        if current_time - game_state.last_order_spawn_time >= game_state.next_order_spawn_delay:
            num_active_players_on_this_server = len(game_state.players) # Jumlah pemain di Game Server ini
            
            if num_active_players_on_this_server > 0 and len(game_state.orders) < 3: # Misal max 3 order aktif
                print(f"DEBUG: Attempting to generate new order. Current orders: {len(game_state.orders)}. Active players: {num_active_players_on_this_server}")
                game_state.generate_orders(num_active_players_on_this_server) # Panggil fungsi generate_orders
                game_state.last_order_spawn_time = current_time # Reset waktu spawn order terakhir
                # Set delay acak untuk order berikutnya
                game_state.next_order_spawn_delay = random.uniform(config.ORDER_SPAWN_INTERVAL_MIN, config.ORDER_SPAWN_INTERVAL_MAX)
                print(f"DEBUG: Next order will spawn in {game_state.next_order_spawn_delay:.2f} seconds.")
            elif num_active_players_on_this_server == 0:
                print("DEBUG: No active players found on this Game Server, skipping order generation.")
            else: # Jika len(game_state.orders) >= 3
                print(f"DEBUG: Max active orders reached ({len(game_state.orders)}). Waiting for orders to be fulfilled.")
        # --- AKHIR LOGIKA PEMBANGKITAN ORDER BARU ---

        # Kirim state game ke semua klien secara berkala
        if current_time - last_broadcast_time >= BROADCAST_INTERVAL:
            create_and_broadcast_state()
            last_broadcast_time = current_time

        # Jika timer game habis
        if remaining <= 0:
            print(f"Timer thread: Game timer finished. Final timer: {game_state.timer}. game_state.game_started: {game_state.game_started}")
            game_state.timer = 0 # Pastikan timer menjadi 0
            
            # --- LOGIKA PENENTUAN KEMENANGAN/KEKALAHAN ---
            if game_state.score >= config.WIN_SCORE_THRESHOLD:
                game_state.game_outcome = "WIN"
                print(f"Game Over: WIN! Final Score: {game_state.score}")
            else:
                game_state.game_outcome = "LOSE"
                print(f"Game Over: LOSE! Final Score: {game_state.score}")
            # --- AKHIR LOGIKA PENENTUAN KEMENANGAN/KEKALAHAN ---

            create_and_broadcast_state() # Broadcast state terakhir dengan outcome
            print("Game timer finished. Awaiting player action to return to lobby.")
            break # Hentikan loop thread timer

        time.sleep(0.01) # Jeda sebentar agar tidak membebani CPU

    print(f"Timer thread: Exiting loop. timer_thread_active={timer_thread_active}, game_state.game_started={game_state.game_started}")

def start_game_server():
    """Memulai Game Server dan thread heartbeat ke Lobby."""
    # Start heartbeat thread di awal
    heartbeat_thread_instance = threading.Thread(target=heartbeat_thread, daemon=True)
    heartbeat_thread_instance.start()
    
    # Main loop untuk menerima koneksi klien
    while not shutdown_flag:
        try:
            conn, addr = game_server_socket.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            thread.start()
        except socket.timeout:
            pass # Timeout adalah hal normal, tidak perlu error
        except Exception as e:
            if not shutdown_flag: # Hanya log error jika server belum dimatikan
                print(f"Game Server loop error: {e}")
            break
    print("Game Server has shut down.")

if __name__ == "__main__":
    # Inisialisasi RecipeManager satu kali saat Game Server dimulai
    # Ini penting karena GameState membutuhkan RecipeManager
    _ = RecipeManager()
    start_game_server()