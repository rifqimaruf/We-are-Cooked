import socket
import threading
import json
import random

from src.shared.game_state import GameState
from src.shared import config

game_state = GameState()
connections = []

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((config.SERVER_IP, config.SERVER_PORT))
server.listen()

print(f"RecipeManager initialized and recipes cached.")
print(f"Server listening on {config.SERVER_IP}:{config.SERVER_PORT}")

def broadcast_state():
    state_json = json.dumps(game_state.to_dict()).encode()
    dead_conns = []
    for c in connections:
        try:
            c.sendall(state_json)
        except:
            dead_conns.append(c)
    for dc in dead_conns:
        connections.remove(dc)
        dc.close()

def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr} connected.")
    connections.append(conn)

    player_id = str(addr) 
    ingredient = random.choice([
        'Rice', 'Salmon', 'Tuna', 'Shrimp', 'Egg', 'Seaweed',
        'Cucumber', 'Avocado', 'Crab Meat', 'Eel', 'Cream Cheese', 'Fish Roe'
    ])
    pos = (random.randint(0, config.GRID_WIDTH - 1), random.randint(0, config.GRID_HEIGHT - 1))
    game_state.add_player(player_id, ingredient, pos)

    try:
        conn.sendall(json.dumps(game_state.to_dict()).encode())

        while True:
            data = conn.recv(config.BUFFER_SIZE)
            if not data:
                break

            msg = json.loads(data.decode())

            if msg.get("action") == "move":
                direction = msg["direction"]
                game_state.move_player(player_id, direction)

                fusion_result = game_state.check_for_merge()
                if fusion_result:
                    print(f"Fusion at {fusion_result['pos']}: {fusion_result['fusion']['name']} served!")

                broadcast_state()

    except Exception as e:
        print(f"[ERROR] Connection with {addr} ended unexpectedly: {e}")
    finally:
        game_state.remove_player(player_id)
        connections.remove(conn)
        broadcast_state()
        conn.close()
        print(f"[DISCONNECT] {addr} disconnected.")

def start():
    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
        thread.start()

if __name__ == "__main__":
    start()
