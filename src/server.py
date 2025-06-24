import socket
import threading
import json
import random
from shared.game_state import GameState
import config

game_state = GameState()

def client_thread(conn, addr, player_id):
    print(f"Player {player_id} connected from {addr}")
    ingredient = random.choice([
        "Salmon", "Tuna", "Rice", "Shrimp", "Avocado", "Crab Meat", 
        "Eel", "Seaweed", "Cucumber", "Cream Cheese", "Fish Roe", "Egg"
    ])
    pos = (random.randint(0, config.GRID_WIDTH - 1), random.randint(0, config.GRID_HEIGHT - 1))
    game_state.add_player(player_id, ingredient, pos)

    conn.sendall(json.dumps(game_state.to_dict()).encode())

    while True:
        try:
            data = conn.recv(config.BUFFER_SIZE)
            if not data:
                break
            msg = json.loads(data.decode())
            if msg.get("action") == "move":
                game_state.move_player(player_id, msg["direction"])
                fusion_result = game_state.check_for_merge()
                # TODO: Remove merged players / respawn (expand logic)
            
            response = json.dumps(game_state.to_dict()).encode()
            conn.sendall(response)
        except:
            break

    print(f"Player {player_id} disconnected")
    conn.close()
    del game_state.players[player_id]

def start_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((config.SERVER_IP, config.SERVER_PORT))
    s.listen()
    print(f"Server listening on {config.SERVER_IP}:{config.SERVER_PORT}")

    player_id = 0
    while True:
        conn, addr = s.accept()
        threading.Thread(target=client_thread, args=(conn, addr, player_id)).start()
        player_id += 1

if __name__ == "__main__":
    start_server()
