# src/server.py
import socket
import threading
import json
import random
import time
import signal
import struct
from typing import Dict, Any
import copy

from src.shared.game_state import GameState
from src.shared import config

game_state = GameState()
connections: Dict[str, socket.socket] = {}
clients_info: Dict[str, Dict[str, Any]] = {}
game_started = False
timer_thread_active = False
timer_thread_instance = None
shutdown_flag = False

game_events = [] 

last_merge_check_time = 0
MERGE_CHECK_INTERVAL = 0.2
BROADCAST_INTERVAL = 0.1
HEADER_SIZE = 4

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((config.SERVER_IP, config.SERVER_PORT))
server.listen()
server.settimeout(0.5)
print(f"Server listening on {config.SERVER_IP}:{config.SERVER_PORT}")

def signal_handler(signum, frame):
    global shutdown_flag
    print("\nCtrl+C detected. Shutting down...")
    server.close()
    shutdown_flag = True

signal.signal(signal.SIGINT, signal_handler)

class GameEvent:
    def __init__(self, event_type: str, data: Dict[str, Any], timestamp: float = None):
        self.event_type = event_type
        self.data = data
        self.timestamp = timestamp or time.time()
        self.id = random.randint(1000, 9999)

def add_game_event(event_type: str, data: Dict[str, Any]):
    global game_events
    event = GameEvent(event_type, data)
    game_events.append(event)
    current_time = time.time()
    game_events = [e for e in game_events if current_time - e.timestamp < 5.0]

def create_and_broadcast_state():
    state_dict = game_state.to_dict()
    state_dict["clients_info"] = clients_info
    state_dict["game_started"] = game_started
    
    # Filter visual events for events that happened recently and clear them from game_state
    state_dict["visual_effects"] = {"game_events": []}
    if "_visual_events" in state_dict: # game_state.to_dict() now provides _visual_events
        state_dict["visual_effects"]["game_events"].extend(state_dict["_visual_events"])
        del state_dict["_visual_events"] # Clean up after copying

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
    for player_id in player_ids:
        print(f"Cleaning up disconnected client: {player_id}")
        if player_id in connections:
            connections[player_id].close()
            del connections[player_id]
        if player_id in clients_info:
            del clients_info[player_id]
        game_state.remove_player(player_id) 
    
    if len(clients_info) == 0 and game_started:
        print("All players disconnected. Returning to lobby.")
        return_to_lobby()
    else:
        create_and_broadcast_state()

def restart_game():
    global game_state, timer_thread_active, timer_thread_instance, game_started, game_events
    if timer_thread_instance and timer_thread_instance.is_alive():
        print(f"Attempting to stop old timer thread. Active: {timer_thread_active}, Alive: {timer_thread_instance.is_alive()}")
        timer_thread_active = False
        timer_thread_instance.join(timeout=1.0)
        if timer_thread_instance.is_alive():
            print("Warning: Old timer thread did not terminate in time for restart.")

    game_state = GameState() # Reset game state
    game_started = True
    game_events = []
    print(f"Restarting game: game_started set to {game_started}") 

    game_state.initialize_stations() # Inisialisasi posisi stasiun

    # Generate satu order awal saat game dimulai
    game_state.generate_orders(len(clients_info)) 
    game_state.last_order_spawn_time = time.time() # Reset timer order spawn
    # Inisialisasi delay untuk order berikutnya
    game_state.next_order_spawn_delay = random.uniform(config.ORDER_SPAWN_INTERVAL_MIN, config.ORDER_SPAWN_INTERVAL_MAX)

    # Inisialisasi doorprize spawn time saat game restart
    game_state.doorprize_spawn_time = time.time() - game_state.next_doorprize_spawn_delay # Make it ready to spawn soon
    game_state.next_doorprize_spawn_delay = random.uniform(config.DOORPRIZE_SPAWN_INTERVAL_MIN, config.DOORPRIZE_SPAWN_INTERVAL_MAX)


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
    print(f"Game timer thread started. Initial game_started state: {game_started}") 
    
    create_and_broadcast_state()

    print("Game restarted with new state.")

def return_to_lobby():
    global game_started, timer_thread_active, game_state, game_events
    if timer_thread_instance and timer_thread_instance.is_alive():
        print(f"Attempting to stop old timer thread for lobby return. Active: {timer_thread_active}, Alive: {timer_thread_instance.is_alive()}")
        timer_thread_active = False
        timer_thread_instance.join(timeout=1.0)
        if timer_thread_instance.is_alive():
            print("Warning: Old timer thread did not terminate for lobby return.")
    
    game_started = False
    for player_id in clients_info:
        clients_info[player_id]["ready"] = False
    
    game_state = GameState()
    game_events = []
    print(f"Returning to lobby: game_started set to {game_started}") 
    create_and_broadcast_state()
    print("All players returned to lobby.")

def handle_client(conn: socket.socket, addr: Any):
    player_id = str(addr)
    connections[player_id] = conn
    clients_info[player_id] = {"username": f"Chef_{addr[1] % 1000}", "ready": False}
    print(f"Client {player_id} connected. Total players: {len(connections)}")
    
    try:
        initial_state_for_client = game_state.to_dict()
        initial_state_for_client["client_id"] = player_id
        initial_state_for_client["clients_info"] = clients_info
        initial_state_for_client["game_started"] = game_started
        
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

                while len(current_recv_buffer) >= HEADER_SIZE:
                    msg_len_from_header = struct.unpack('>I', current_recv_buffer[:HEADER_SIZE])[0]
                    
                    if len(current_recv_buffer) < HEADER_SIZE + msg_len_from_header:
                        break 
                    
                    actual_message_bytes = current_recv_buffer[HEADER_SIZE : HEADER_SIZE + msg_len_from_header]
                    current_recv_buffer = current_recv_buffer[HEADER_SIZE + msg_len_from_header:]
                    
                    msg = json.loads(actual_message_bytes.decode('utf-8'))
                    action = msg.get("action")
                    
                    if action == "return_to_lobby":
                        print(f"Client {player_id} sent return_to_lobby. game_started: {game_started}")
                        return_to_lobby()
                    
                    elif not game_started:
                        if action == "set_username":
                            clients_info[player_id]["username"] = msg.get("username", "Unknown")
                            print(f"Client {player_id} set username to {clients_info[player_id]['username']}. game_started: {game_started}")
                        elif action == "toggle_ready":
                            clients_info[player_id]["ready"] = not clients_info[player_id].get("ready", False)
                            print(f"Client {player_id} toggled ready. Status: {clients_info[player_id]['ready']}. game_started: {game_started}")
                        elif action == "start_game": 
                            print(f"Client {player_id} sent start_game. All ready: {all(c['ready'] for c in clients_info.values())}. game_started: {game_started}")
                            if all(c["ready"] for c in clients_info.values()) and len(clients_info) > 1:
                                restart_game()
                                continue
                        create_and_broadcast_state() 
                    else:
                        if game_state.timer > 0:
                            if action == "move":
                                game_state.move_player(player_id, msg.get("direction"))
                                print(f"Client {player_id} moved {msg.get('direction')}. Timer: {game_state.timer}. game_started: {game_started}")
                            elif action == "restart": 
                                print(f"Client {player_id} sent restart from in-game. game_started: {game_started}")
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
                                            add_game_event("ingredient_change", {"player_id": player_id, "old_ingredient": old_ing, "new_ingredient": new_ing})
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
        cleanup_disconnected_players([player_id])
        print(f"Client {player_id} handler stopped.")

def game_timer_thread():
    """Thread yang mengatur timer game, deteksi fusi, dan broadcast state."""
    global timer_thread_active, last_merge_check_time
    start_time = time.time()
    end_time = start_time + config.GAME_TIMER_SECONDS

    last_broadcast_time = time.time()

    print(f"Timer thread: Starting with timer_thread_active={timer_thread_active} and game_started={game_started}")

    while timer_thread_active and game_started:
        current_time = time.time()
        remaining = max(0, end_time - current_time)
        game_state.timer = int(remaining)

        game_state.check_for_merge()
        game_state.process_fusion_events()

        # Logika Doorprize Station
        # Hanya spawn jika tidak ada doorprize station aktif DAN sudah melewati waktu delay yang ditentukan
        if game_state.doorprize_station is None and \
           current_time - game_state.doorprize_spawn_time >= game_state.next_doorprize_spawn_delay:
            game_state.spawn_doorprize_station(current_time)
        elif game_state.doorprize_station is not None:
            game_state.check_doorprize_interaction() # Ini akan menghapus jika sudah expired dan mengatur timer berikutnya

        if current_time - game_state.last_order_spawn_time >= game_state.next_order_spawn_delay:
            if len(game_state.players) > 0:
                game_state.generate_orders(len(game_state.players))
                game_state.last_order_spawn_time = current_time 
                game_state.next_order_spawn_delay = random.uniform(config.ORDER_SPAWN_INTERVAL_MIN, config.ORDER_SPAWN_INTERVAL_MAX)
                print(f"DEBUG: Next order will spawn in {game_state.next_order_spawn_delay:.2f} seconds.")
            else:
                print("DEBUG: No active players, skipping order generation.")

        if current_time - last_broadcast_time >= BROADCAST_INTERVAL:
            create_and_broadcast_state()
            last_broadcast_time = current_time

        if remaining <= 0:
            print(f"Timer thread: Game timer finished. Final timer: {game_state.timer}. game_started: {game_started}")
            game_state.timer = 0
            create_and_broadcast_state()
            print("Game timer finished. Awaiting player action to return to lobby.")
            break

        time.sleep(0.01)

    print(f"Timer thread: Exiting loop. timer_thread_active={timer_thread_active}, game_started={game_started}")


def start():
    """Memulai server dan menunggu koneksi klien."""
    while not shutdown_flag:
        try:
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            thread.start()
        except socket.timeout:
            pass
        except Exception as e:
            if not shutdown_flag:
                print(f"Server loop error: {e}")
            break
    print("Server has shut down.")

if __name__ == "__main__":
    start()