import socket
import threading
import json
import random
import time

from src.shared.game_state import GameState
from src.shared import config

game_state = GameState()
connections = []
clients_info = {}
game_started = False
timer_thread_active = True
timer_thread_instance = None
restart_lock = threading.Lock()

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((config.SERVER_IP, config.SERVER_PORT))
server.listen()

print(f"RecipeManager initialized and recipes cached.")
print(f"Server listening on {config.SERVER_IP}:{config.SERVER_PORT}")

def broadcast_state():
    state_dict = game_state.to_dict()
    # Add connected clients info to the state
    state_dict["clients_info"] = clients_info
    state_dict["game_started"] = game_started
    
    state_json = json.dumps(state_dict).encode()
    dead_conns = []
    for c in connections:
        try:
            c.sendall(state_json)
        except Exception as e:
            print(f"Error broadcasting to client: {e}")
            dead_conns.append(c)
    
    for dc in dead_conns:
        try:
            connections.remove(dc)
            dc.close()
        except:
            pass
    
    # print(f"Broadcast state: game_started={game_started}, players={len(game_state.players)}, clients={len(clients_info)}")

def restart_game():
    global game_state, timer_thread_active, timer_thread_instance, game_started

    with restart_lock: # Pastikan semua operasi kritis ada di dalam lock
        if timer_thread_instance and timer_thread_instance.is_alive():
            timer_thread_active = False # Memberi sinyal ke thread lama untuk berhenti
            timer_thread_instance.join(timeout=1.0) # Tunggu thread lama berhenti
            if timer_thread_instance.is_alive():
                print("Warning: Old timer thread did not terminate in time.")

        # Pastikan inisialisasi game_state dan game_started juga di dalam lock
        game_state = GameState()
        game_started = True
        print(f"Setting game_started to {game_started}")

        num_connected_clients = len(clients_info)
        game_state.generate_orders(num_connected_clients) # Mengirim jumlah klien untuk filter resep
        print(f"Generated orders: {[o['name'] for o in game_state.orders]}")

        # Langkah 2: Kumpulkan semua bahan yang dibutuhkan oleh pesanan aktif
        required_ingredients_pool = []
        for order in game_state.orders:
            required_ingredients_pool.extend(order['ingredients'])

        # Jika ada duplikat bahan yang dibutuhkan (misal: 2 onigiri butuh 2 rice), pertahankan duplikatnya.
        # Kita akan shuffle pool ini untuk penugasan yang lebih adil antar pemain.
        random.shuffle(required_ingredients_pool)
        print(f"Required ingredients pool: {required_ingredients_pool}")

        # Daftar semua bahan yang mungkin (untuk pemain yang tidak mendapatkan bahan utama)
        all_possible_ingredients = [
            'Rice', 'Salmon', 'Tuna', 'Shrimp', 'Egg', 'Seaweed',
            'Cucumber', 'Avocado', 'Crab Meat', 'Eel', 'Cream Cheese', 'Fish Roe'
        ]

        # Add players to the game state
        # Daftar bahan yang akan diberikan ke setiap pemain.
        # Ukurannya akan sama dengan jumlah pemain yang terhubung.
        ingredients_to_assign = []

        # Prioritaskan bahan dari required_ingredients_pool
        # Pastikan setiap pemain mendapatkan setidaknya satu bahan dari pool jika memungkinkan
        temp_required_pool = list(required_ingredients_pool) # Buat salinan untuk dimanipulasi

        # Langkah 3: Tugaskan bahan ke pemain
        # Iterasi koneksi untuk memastikan urutan pemain yang stabil
        for conn_index, conn in enumerate(connections):
            try:
                addr = conn.getpeername()
                player_id = str(addr)
                if player_id in clients_info: # Hanya untuk klien yang valid
                    ingredient = None
                    if temp_required_pool:
                        # Coba berikan bahan dari pool yang dibutuhkan
                        ingredient = temp_required_pool.pop(0)
                    else:
                        # Jika pool kosong, berikan bahan acak dari semua kemungkinan bahan
                        ingredient = random.choice(all_possible_ingredients)

                    ingredients_to_assign.append((player_id, ingredient))

            except Exception as e:
                print(f"Error preparing ingredient for player: {e}")
                # Jika ada error, setidaknya pastikan ada ingredient untuk pemain ini
                ingredients_to_assign.append((player_id, random.choice(all_possible_ingredients)))
                continue

        # Sekarang, acak urutan penugasan agar bahan tidak selalu berurutan (misal: Rice, Seaweed, Rice, Seaweed)
        random.shuffle(ingredients_to_assign)

        # Langkah 4: Tambahkan pemain ke game state dengan bahan dan posisi yang ditugaskan
        for player_id, ingredient in ingredients_to_assign:
            pos = (random.randint(0, config.GRID_WIDTH - 1), random.randint(0, config.GRID_HEIGHT - 1))
            game_state.add_player(player_id, ingredient, pos)
            print(f"Added player {player_id} as {ingredient} to game state at {pos}")
        
        timer_thread_active = True # Atur flag untuk thread baru
        timer_thread_instance = threading.Thread(target=timer_thread, daemon=True)
        timer_thread_instance.start()

        broadcast_state()

        print("Game started with new state")

def return_to_lobby():
    """Return all players to the lobby without restarting the game"""
    global game_started, game_state
    
    # Reset game state
    game_started = False
    
    # Reset all players' ready status
    for player_id in clients_info:
        clients_info[player_id]["ready"] = False
    
    # Create a fresh game state but don't start the timer
    game_state = GameState()
    
    broadcast_state()
    print("All players returned to lobby, game state reset")

def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr} connected.")
    connections.append(conn)

    player_id = str(addr)
    # Default username is Player + last digits of their address
    default_username = f"Player{addr[1] % 1000}"
    clients_info[player_id] = {"username": default_username, "ready": False}
    
    broadcast_state()

    try:
        conn.sendall(json.dumps({"client_id": player_id, **game_state.to_dict(), 
                                "clients_info": clients_info, 
                                "game_started": game_started}).encode())

        while True:
            data = conn.recv(config.BUFFER_SIZE)
            if not data:
                break

            msg = json.loads(data.decode())

            if msg.get("action") == "set_username":
                username = msg.get("username", default_username)
                clients_info[player_id]["username"] = username
                print(f"Player {player_id} set username to {username}")
                broadcast_state()
                
            elif msg.get("action") == "toggle_ready":
                clients_info[player_id]["ready"] = not clients_info[player_id].get("ready", False)
                ready_status = "ready" if clients_info[player_id]["ready"] else "not ready"
                print(f"Player {player_id} toggled ready status to {ready_status}")
                broadcast_state()
                
            elif msg.get("action") == "start_game" and not game_started:
                # Check if all players are ready
                all_ready = all(client["ready"] for client in clients_info.values())
                print(f"Start game requested by {player_id}. All players ready: {all_ready}")
                if all_ready and len(clients_info) > 0:
                    restart_game()
            
            elif msg.get("action") == "return_to_lobby":
                # print(f"Return to lobby requested by {addr}")
                return_to_lobby()
                
            elif msg.get("action") == "move" and game_started:
                direction = msg["direction"]
                game_state.move_player(player_id, direction)

                fusion_result = game_state.check_for_merge()
                if fusion_result:
                    print(f"Fusion at {fusion_result['pos']}: {fusion_result['fusion']['name']} served!")

                broadcast_state()
            
            elif msg.get("action") == "restart":
                print(f"Restart requested by {addr}")
                restart_game()

    except Exception as e:
        print(f"[ERROR] Connection with {addr} ended unexpectedly: {e}")
    finally:
        if player_id in clients_info:
            del clients_info[player_id]
        game_state.remove_player(player_id)
        if conn in connections:
            connections.remove(conn)
        broadcast_state()
        conn.close()
        print(f"[DISCONNECT] {addr} disconnected.")

def timer_thread():
    """Update the game timer using a simple countdown approach"""
    global timer_thread_active, game_started
    
    start_time = time.time()
    game_duration = game_state.timer
    end_time = start_time + game_duration
    
    # Broadcast intervals
    broadcast_interval = 1.0  # Start with 1-second intervals
    next_broadcast_time = start_time
    
    while timer_thread_active:
        current_time = time.time()
        remaining = max(0, end_time - current_time)
        
        # Update the game state timer
        game_state.timer = int(remaining)
        
        # Broadcast at regular intervals
        if current_time >= next_broadcast_time:
            broadcast_state()
            
            # Adjust broadcast frequency based on remaining time
            if remaining <= 10:
                broadcast_interval = 1.0  # More frequent updates in final countdown
            else:
                broadcast_interval = 2.0  # Normal update frequency
                
            next_broadcast_time = current_time + broadcast_interval
        
        # Game over condition
        if remaining <= 0:
            game_state.timer = 0
            game_started = False
            broadcast_state()
            print(f"Game Over! Final Score: {game_state.score}")
            break
                
        time.sleep(0.1)  # Small sleep to prevent CPU hogging

def start():
    global timer_thread_instance, game_started
    game_started = False
    
    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
        thread.start()

if __name__ == "__main__":
    start()
