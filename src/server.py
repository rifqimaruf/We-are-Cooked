import socket
import threading
import json
import random

from src.shared.game_state import GameState
from src.shared import config

game_state = GameState()

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((config.SERVER_IP, config.SERVER_PORT))
server.listen()

print(f"RecipeManager initialized and recipes cached.")
print(f"Server listening on {config.SERVER_IP}:{config.SERVER_PORT}")

def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr} connected.")

    player_id = str(addr) 
    ingredient = random.choice([
        'Rice', 'Salmon', 'Tuna', 'Shrimp', 'Egg', 'Seaweed',
        'Cucumber', 'Avocado', 'Crab Meat', 'Eel', 'Cream Cheese', 'Fish Roe'
    ])
    pos = (random.randint(0, config.GRID_WIDTH - 1), random.randint(0, config.GRID_HEIGHT - 1))
    
    game_state.add_player(player_id, ingredient, pos)

    conn.sendall(json.dumps(game_state.to_dict()).encode())

    try:
        while True:
            data = conn.recv(config.BUFFER_SIZE)
            if not data:
                break

            msg = json.loads(data.decode())

            if msg.get("action") == "move":
                direction = msg.get("direction")
                game_state.move_player(player_id, direction)

                merge_result = game_state.check_for_merge()
                if merge_result:
                    print(f"[MERGE] {merge_result}")

            conn.sendall(json.dumps(game_state.to_dict()).encode())

    except Exception as e:
        print(f"[ERROR] Connection with {addr} ended unexpectedly: {e}")
    finally:
        conn.close()
        game_state.remove_player(player_id)
        print(f"[DISCONNECT] {addr} disconnected.")

def start():
    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()

if __name__ == "__main__":
    start()
