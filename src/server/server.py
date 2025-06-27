import socket
import threading
import json
import random
import time
import signal
import struct
from typing import Dict, Any

from src.shared.game_state import GameState
from src.shared import config

game_state = GameState()
connections = {} 
clients_info = {}
game_started = False
timer_thread_active = True
timer_thread_instance = None
restart_lock = threading.Lock()
shutdown_flag = False
game_events = []
last_merge_check_time = 0
MERGE_CHECK_INTERVAL = 0.1
BROADCAST_INTERVAL = 0.05
HEADER_SIZE = 4  

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((config.SERVER_IP, config.SERVER_PORT))
server.listen()
print(f"Server listening on {config.SERVER_IP}:{config.SERVER_PORT}")


def signal_handler(signum, frame):
    global shutdown_flag
    print("\nCtrl+C detected. Shutting down...")
    shutdown_flag = True
    server.close()

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
    state_dict["visual_effects"] = {"game_events": [{"id": e.id, "type": e.event_type, "data": e.data} for e in game_events[-10:]]}

    encoded_data = json.dumps(state_dict).encode('utf-8')
    header = struct.pack('>I', len(encoded_data))
    message_to_send = header + encoded_data

    disconnected_players = []
    for player_id, conn in list(connections.items()):
        try:
            conn.sendall(message_to_send)
        except (socket.error, BrokenPipeError):
            disconnected_players.append(player_id)

    if disconnected_players:
        cleanup_disconnected_players(disconnected_players)

def cleanup_disconnected_players(player_ids):
    for player_id in player_ids:
        print(f"Client {player_id} detected as disconnected during broadcast.")
        if player_id in connections:
            connections[player_id].close()
            del connections[player_id]
        if player_id in clients_info:
            del clients_info[player_id]
        if player_id in game_state.players:
            game_state.remove_player(player_id)
    
    if len(clients_info) == 0 and game_started:
        print("All players disconnected. Returning to lobby.")
        return_to_lobby()
    else:
        create_and_broadcast_state()


def restart_game():
    global game_state, timer_thread_active, timer_thread_instance, game_started, game_events
    with restart_lock:
        if timer_thread_instance and timer_thread_instance.is_alive():
            timer_thread_active = False
            timer_thread_instance.join(timeout=1.0)

        game_state = GameState()
        game_started = True
        game_events = []
        num_players = len(clients_info)
        game_state.generate_orders(num_players)

        all_ingredients = ['Rice', 'Salmon', 'Tuna', 'Shrimp', 'Egg', 'Seaweed']
        for player_id in clients_info.keys():
            ingredient = random.choice(all_ingredients)
            pos = (random.randint(1, config.GRID_WIDTH - 2), random.randint(1, config.GRID_HEIGHT - 2))
            game_state.add_player(player_id, ingredient, pos)

        timer_thread_active = True
        timer_thread_instance = threading.Thread(target=game_timer_thread, daemon=True)
        timer_thread_instance.start()
        print("Game restarted with new timer thread.")
        create_and_broadcast_state()

def return_to_lobby():
    global game_started, timer_thread_active, game_state, game_events
    with restart_lock:
        if timer_thread_instance and timer_thread_instance.is_alive():
            timer_thread_active = False
            timer_thread_instance.join(timeout=1.0)
        
        game_started = False
        for player_id in clients_info:
            clients_info[player_id]["ready"] = False
        
        game_state = GameState()
        game_events = []
        print("All players returned to lobby.")
        create_and_broadcast_state()

def handle_client(conn, addr):
    player_id = str(addr)
    connections[player_id] = conn
    clients_info[player_id] = {"username": f"Chef_{addr[1] % 1000}", "ready": False}
    print(f"Client {player_id} connected. Total players: {len(connections)}")
    
    create_and_broadcast_state()

    player_disconnected = False
    while not shutdown_flag and not player_disconnected:
        try:
            header_data = conn.recv(HEADER_SIZE)
            if not header_data:
                break
            msg_len = struct.unpack('>I', header_data)[0]
            
            data = conn.recv(msg_len)
            if not data:
                break

            msg = json.loads(data.decode('utf-8'))
            action = msg.get("action")
            
            if action == "return_to_lobby":
                return_to_lobby()
                continue

            if not game_started:
                if action == "set_username":
                    clients_info[player_id]["username"] = msg.get("username", "Unknown")
                elif action == "toggle_ready":
                    clients_info[player_id]["ready"] = not clients_info[player_id].get("ready", False)
                elif action == "start_game" and all(c["ready"] for c in clients_info.values()) and len(clients_info) > 0:
                    restart_game()
                    continue
                create_and_broadcast_state()
            else:
                if game_state.timer > 0 and action == "move":
                    game_state.move_player(player_id, msg.get("direction"))

        except (ConnectionResetError, json.JSONDecodeError, struct.error, socket.error):
            player_disconnected = True
        except Exception as e:
            print(f"Error with client {player_id}: {type(e).__name__} - {e}")
            player_disconnected = True

    cleanup_disconnected_players([player_id])

def game_timer_thread():
    global timer_thread_active, last_merge_check_time
    start_time = time.time()
    end_time = start_time + config.GAME_TIMER_SECONDS

    while timer_thread_active and game_started:
        current_time = time.time()
        remaining = max(0, end_time - current_time)
        game_state.timer = int(remaining)

        if remaining > 0 and current_time - last_merge_check_time >= MERGE_CHECK_INTERVAL:
            fusion_result = game_state.check_for_merge()
            if fusion_result:
                for res in fusion_result:
                    add_game_event("recipe_fusion", {"recipe_name": res['fusion']['name']})
            last_merge_check_time = current_time
        
        create_and_broadcast_state()

        if remaining <= 0:
            print("Game timer finished. Awaiting player action to return to lobby.")
            break
            
        time.sleep(BROADCAST_INTERVAL)

def start():
    while not shutdown_flag:
        try:
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            thread.start()
        except Exception as e:
            if not shutdown_flag:
                print(f"Server loop error: {e}")
            break
    print("Server has shut down.")

if __name__ == "__main__":
    start()