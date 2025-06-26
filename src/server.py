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
    """Reset the game state and start a new timer thread"""
    global game_state, timer_thread_active, timer_thread_instance, game_started

    with restart_lock:
        if timer_thread_instance and timer_thread_instance.is_alive():
            timer_thread_active = False
            timer_thread_instance.join(timeout=1.0)

        game_state = GameState()
        game_started = True
        print(f"Setting game_started to {game_started}")
        # Langkah 1: Hasilkan pesanan terlebih dahulu agar kita tahu bahan yang dibutuhkan
        # Ini penting dilakukan sebelum menambahkan pemain karena penugasan bahan
        # akan bergantung pada pesanan yang ada.
        num_connected_clients = len(clients_info)
        game_state.generate_orders(num_connected_clients) # Mengirim jumlah klien untuk filter resep
        print(f"Generated orders: {[o['name'] for o in game_state.orders]}")

        # Langkah 2: Kumpulkan semua bahan yang dibutuhkan oleh pesanan aktif
        required_ingredients_pool = []
        for order in game_state.orders:
            # Ambil bahan dari recipe_manager karena order hanya punya nama & harga
            # Asumsi recipe_manager punya cara untuk mendapatkan detail resep dari nama
            # (Kita akan tambahkan ini jika belum ada)
            recipe_detail = game_state.recipe_manager.check_merge(order['ingredients']) # Ini akan butuh update pada struktur order yang disimpan
            if recipe_detail:
                required_ingredients_pool.extend(list(recipe_detail['ingredients']))
            else:
                print(f"Warning: Recipe detail not found for order {order['name']}")

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
        for conn in connections:
            try:
                addr = conn.getpeername()
                player_id = str(addr)
                if player_id in clients_info:
                    # Ambil bahan dari pool yang dibutuhkan, jika masih ada
                    if required_ingredients_pool:
                        ingredient = required_ingredients_pool.pop(0) # Ambil bahan pertama dari pool
                    else:
                        # Jika pool bahan yang dibutuhkan kosong, berikan bahan acak
                        ingredient = random.choice(all_possible_ingredients)

                    pos = (random.randint(0, config.GRID_WIDTH - 1), random.randint(0, config.GRID_HEIGHT - 1))
                    game_state.add_player(player_id, ingredient, pos)
                    print(f"Added player {player_id} as {ingredient} to game state at {pos}")
            except Exception as e:
                print(f"Error adding player to game: {e}")
                continue

        # --- Akhir perubahan untuk penugasan bahan yang cerdas ---

        timer_thread_active = True
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
