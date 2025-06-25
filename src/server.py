import socket
import threading
import json
import random
import time

from src.shared.game_state import GameState
from src.shared import config

game_state = GameState()
connections = []
timer_thread_active = True
timer_thread_instance = None
restart_lock = threading.Lock()

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

def restart_game():
    """Reset the game state and start a new timer thread"""
    global game_state, timer_thread_active, timer_thread_instance
    
    with restart_lock:
        if timer_thread_instance and timer_thread_instance.is_alive():
            timer_thread_active = False
            timer_thread_instance.join(timeout=1.0)
        
        game_state = GameState()
        
        for conn in connections:
            try:
                addr = conn.getpeername()
                player_id = str(addr)
                ingredient = random.choice([
                    'Rice', 'Salmon', 'Tuna', 'Shrimp', 'Egg', 'Seaweed',
                    'Cucumber', 'Avocado', 'Crab Meat', 'Eel', 'Cream Cheese', 'Fish Roe'
                ])
                pos = (random.randint(0, config.GRID_WIDTH - 1), random.randint(0, config.GRID_HEIGHT - 1))
                game_state.add_player(player_id, ingredient, pos)
            except:
                continue
        
        timer_thread_active = True
        timer_thread_instance = threading.Thread(target=timer_thread, daemon=True)
        timer_thread_instance.start()
        
        broadcast_state()
        
        print("Game restarted with new state")

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
            
            elif msg.get("action") == "restart":
                print(f"Restart requested by {addr}")
                restart_game()
                conn.sendall(json.dumps(game_state.to_dict()).encode())

    except Exception as e:
        print(f"[ERROR] Connection with {addr} ended unexpectedly: {e}")
    finally:
        game_state.remove_player(player_id)
        connections.remove(conn)
        broadcast_state()
        conn.close()
        print(f"[DISCONNECT] {addr} disconnected.")

def timer_thread():
    """Update the game timer using a simple countdown approach"""
    global timer_thread_active
    
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
            broadcast_state()
            print(f"Game Over! Final Score: {game_state.score}")
            break
                
        time.sleep(0.1)  # Small sleep to prevent CPU hogging

def start():
    global timer_thread_instance
    # Start the timer thread
    timer_thread_active = True
    timer_thread_instance = threading.Thread(target=timer_thread, daemon=True)
    timer_thread_instance.start()
    
    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
        thread.start()

if __name__ == "__main__":
    start()
