import sys
import socket
import threading
import time
import json
import uuid
import logging
from datetime import datetime
import random
from urllib.parse import parse_qs, urlparse

from src.shared.game_state import GameState
from src.shared import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('GameServer')

class HttpServer:
    def __init__(self):
        self.game_state = GameState()
        self.clients_info = {}
        self.game_started = False
        self.timer_thread_active = False
        self.timer_thread_instance = None
        self.game_events = []
        self.shutdown_flag = False
        
    def response(self, kode=200, message='OK', messagebody=bytes(), headers={}):
        """Generate HTTP response"""
        tanggal = datetime.now().strftime('%c')
        resp = []
        resp.append(f"HTTP/1.0 {kode} {message}\r\n")
        resp.append(f"Date: {tanggal}\r\n")
        resp.append("Connection: close\r\n")
        resp.append("Server: WeAreCooked/1.0\r\n")
        resp.append(f"Content-Length: {len(messagebody)}\r\n")
        
        # Add CORS headers for browser clients
        resp.append("Access-Control-Allow-Origin: *\r\n")
        resp.append("Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n")
        resp.append("Access-Control-Allow-Headers: Content-Type\r\n")
        
        for kk in headers:
            resp.append(f"{kk}: {headers[kk]}\r\n")
        resp.append("\r\n")

        response_headers = ''.join(resp)
        
        # Convert messagebody to bytes if it's not already
        if not isinstance(messagebody, bytes):
            messagebody = messagebody.encode()

        # Combine headers and body
        response = response_headers.encode() + messagebody
        return response

    def proses(self, data):
        """Process HTTP request data"""
        requests = data.split("\r\n")
        
        if not requests:
            return self.response(400, 'Bad Request', '', {})
            
        baris = requests[0]
        
        # Extract headers
        headers = {}
        for h in requests[1:]:
            if h == '':
                break
            if ': ' in h:
                k, v = h.split(': ', 1)
                headers[k.lower()] = v
        
        # Parse request line
        j = baris.split(" ")
        try:
            method = j[0].upper().strip()
            url = j[1].strip()
            
            # Parse URL
            parsed_url = urlparse(url)
            path = parsed_url.path
            query = parse_qs(parsed_url.query)
            
            # Handle different HTTP methods
            if method == 'GET':
                return self.http_get(path, query, headers)
            elif method == 'POST':
                # Find the request body
                body = ""
                content_length = int(headers.get('content-length', 0))
                
                # Find the body in the request
                empty_line_found = False
                for i, line in enumerate(requests):
                    if line == '' and i < len(requests) - 1:
                        empty_line_found = True
                        body_lines = requests[i+1:]
                        body = '\r\n'.join(body_lines)
                        break
                
                # If we couldn't find the body using the empty line method,
                # try to extract it based on content-length
                if not empty_line_found and content_length > 0:
                    # Find the double CRLF that separates headers from body
                    raw_data = data
                    body_start = raw_data.find('\r\n\r\n')
                    if body_start != -1:
                        body = raw_data[body_start + 4:]
                
                return self.http_post(path, query, body, headers)
            elif method == 'OPTIONS':
                return self.http_options(path, query, headers)
            else:
                return self.response(405, 'Method Not Allowed', '', {})
        except IndexError:
            return self.response(400, 'Bad Request', '', {})

    def http_get(self, path, query, headers):
        """Handle GET requests"""
        if path == '/game_state':
            # Return the current game state
            state_dict = self.game_state.to_dict()
            state_dict["clients_info"] = self.clients_info
            state_dict["game_started"] = self.game_started
            
            # Add visual effects
            state_dict["visual_effects"] = {"game_events": []}
            if "_visual_events" in state_dict:
                state_dict["visual_effects"]["game_events"].extend(state_dict["_visual_events"])
                del state_dict["_visual_events"]
            
            # Extract client_id from query parameters if present
            client_id = query.get('client_id', [None])[0]
            if client_id:
                state_dict["client_id"] = client_id
            
            return self.response(200, 'OK', json.dumps(state_dict), {'Content-Type': 'application/json'})
        
        elif path == '/health':
            # Simple health check endpoint
            return self.response(200, 'OK', json.dumps({"status": "ok", "players": len(self.clients_info)}), 
                                {'Content-Type': 'application/json'})
            
        else:
            # Handle 404 for unknown paths
            return self.response(404, 'Not Found', json.dumps({"error": "Not found"}), 
                                {'Content-Type': 'application/json'})

    def http_post(self, path, query, body, headers):
        """Handle POST requests"""
        try:
            data = json.loads(body)
            action = data.get("action")
            client_id = data.get("client_id")
            
            # Register new client if this is a connection request
            if path == '/connect':
                if not client_id:
                    client_id = str(uuid.uuid4())
                    self.register_client(client_id)
                
                response = {
                    "client_id": client_id,
                    "status": "connected",
                    "game_state": self.game_state.to_dict(),
                    "clients_info": self.clients_info,
                    "game_started": self.game_started
                }
                return self.response(200, 'OK', json.dumps(response), {'Content-Type': 'application/json'})
            
            # Handle client actions
            if path == '/action':
                if not client_id or client_id not in self.clients_info:
                    return self.response(400, 'Bad Request', json.dumps({"error": "Invalid client ID"}), 
                                        {'Content-Type': 'application/json'})
                
                # Process the action based on game state
                if action == "return_to_lobby":
                    self.return_to_lobby()
                
                elif not self.game_started:
                    if action == "set_username":
                        username = data.get("username", "Unknown")
                        self.clients_info[client_id]["username"] = username
                        logger.info(f"Client {client_id} set username to {username}")
                    
                    elif action == "toggle_ready":
                        self.clients_info[client_id]["ready"] = not self.clients_info[client_id].get("ready", False)
                        logger.info(f"Client {client_id} toggled ready. Status: {self.clients_info[client_id]['ready']}")
                    
                    elif action == "start_game":
                        if all(c["ready"] for c in self.clients_info.values()) and len(self.clients_info) > 1:
                            self.restart_game()
                
                else:
                    if self.game_state.timer > 0:
                        if action == "move":
                            direction = data.get("direction")
                            self.game_state.move_player(client_id, direction)
                            logger.info(f"Client {client_id} moved {direction}")
                        
                        elif action == "restart":
                            self.restart_game()
                        
                        elif action == "change_ingredient":
                            if self.game_state.can_player_change_ingredient(client_id):
                                self.change_player_ingredient(client_id)
                
                # Return success response
                return self.response(200, 'OK', json.dumps({"status": "success"}), {'Content-Type': 'application/json'})
            
            # Handle disconnect
            if path == '/disconnect':
                if client_id in self.clients_info:
                    self.cleanup_disconnected_players([client_id])
                    logger.info(f"Client {client_id} disconnected")
                
                return self.response(200, 'OK', json.dumps({"status": "disconnected"}), {'Content-Type': 'application/json'})
            
            # Handle unknown paths
            return self.response(404, 'Not Found', json.dumps({"error": "Not found"}), {'Content-Type': 'application/json'})
            
        except json.JSONDecodeError:
            return self.response(400, 'Bad Request', json.dumps({"error": "Invalid JSON"}), {'Content-Type': 'application/json'})
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            return self.response(500, 'Internal Server Error', json.dumps({"error": str(e)}), {'Content-Type': 'application/json'})

    def http_options(self, path, query, headers):
        """Handle OPTIONS requests for CORS preflight"""
        return self.response(200, 'OK', '', {
            'Content-Type': 'text/plain',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        })

    def register_client(self, client_id):
        """Register a new client connection"""
        self.clients_info[client_id] = {"username": f"Chef_{client_id[:5]}", "ready": False}
        logger.info(f"Client {client_id} connected. Total players: {len(self.clients_info)}")
    
    def cleanup_disconnected_players(self, player_ids):
        """Remove disconnected players from the game"""
        for player_id in player_ids:
            logger.info(f"Cleaning up disconnected client: {player_id}")
            if player_id in self.clients_info:
                del self.clients_info[player_id]
            self.game_state.remove_player(player_id)
        
        if len(self.clients_info) == 0 and self.game_started:
            logger.info("All players disconnected. Returning to lobby.")
            self.return_to_lobby()
    
    def return_to_lobby(self):
        """Return all players to the lobby"""
        if self.timer_thread_instance and self.timer_thread_instance.is_alive():
            logger.info("Stopping timer thread for lobby return")
            self.timer_thread_active = False
            self.timer_thread_instance.join(timeout=1.0)
        
        self.game_started = False
        for player_id in self.clients_info:
            self.clients_info[player_id]["ready"] = False
        
        self.game_state = GameState()
        self.game_events = []
        logger.info("All players returned to lobby")
    
    def restart_game(self):
        """Restart the game with current players"""
        if self.timer_thread_instance and self.timer_thread_instance.is_alive():
            logger.info("Stopping old timer thread")
            self.timer_thread_active = False
            self.timer_thread_instance.join(timeout=1.0)

        self.game_state = GameState()
        self.game_started = True
        self.game_events = []
        logger.info("Restarting game")

        # Initialize game elements
        self.game_state.initialize_stations()
        self.game_state.generate_orders(len(self.clients_info))
        self.game_state.last_order_spawn_time = time.time()
        self.game_state.next_order_spawn_delay = self._random_range(
            config.ORDER_SPAWN_INTERVAL_MIN, 
            config.ORDER_SPAWN_INTERVAL_MAX
        )
        
        # Initialize doorprize timing
        self.game_state.doorprize_spawn_time = time.time() - self.game_state.next_doorprize_spawn_delay
        self.game_state.next_doorprize_spawn_delay = self._random_range(
            config.DOORPRIZE_SPAWN_INTERVAL_MIN, 
            config.DOORPRIZE_SPAWN_INTERVAL_MAX
        )

        # Assign ingredients to players
        self._assign_ingredients_to_players()
        
        # Start the game timer
        self.timer_thread_active = True
        self.timer_thread_instance = threading.Thread(target=self._game_timer_thread, daemon=True)
        self.timer_thread_instance.start()
        logger.info("Game timer thread started")
    
    def _assign_ingredients_to_players(self):
        """Assign ingredients to players at game start"""
        all_possible_ingredients = [
            'Rice', 'Salmon', 'Tuna', 'Shrimp', 'Egg', 'Seaweed', 
            'Cucumber', 'Avocado', 'Crab Meat', 'Eel', 'Cream Cheese', 'Fish Roe'
        ]
        
        # Get ingredients from current orders
        required_ingredients_pool = []
        for order in self.game_state.orders:
            required_ingredients_pool.extend(order['ingredients'])
        random.shuffle(required_ingredients_pool)
        
        # Assign ingredients to players
        ingredients_to_assign = []
        temp_required_pool = list(required_ingredients_pool)
        
        for player_id in self.clients_info.keys():
            ingredient = None
            if temp_required_pool:
                ingredient = temp_required_pool.pop(0)
            else:
                ingredient = random.choice(all_possible_ingredients)
            ingredients_to_assign.append((player_id, ingredient))
        
        random.shuffle(ingredients_to_assign)
        
        # Add players to game state with assigned ingredients
        for player_id, ingredient in ingredients_to_assign:
            pos = (random.randint(0, config.GRID_WIDTH - 1), random.randint(0, config.GRID_HEIGHT - 1))
            self.game_state.add_player(player_id, ingredient, pos)
            logger.info(f"Added player {player_id} as {ingredient} to game state at {pos}")
    
    def change_player_ingredient(self, player_id):
        """Change a player's ingredient at an Enter Station"""
        all_possible_ingredients = [
            'Rice', 'Salmon', 'Tuna', 'Shrimp', 'Egg', 'Seaweed',
            'Cucumber', 'Avocado', 'Crab Meat', 'Eel', 'Cream Cheese', 'Fish Roe'
        ]
        
        with self.game_state._lock:
            player = self.game_state.players.get(player_id)
            if player:
                old_ing = player.ingredient
                new_ing = random.choice([i for i in all_possible_ingredients if i != old_ing])
                player.ingredient = new_ing
                logger.info(f"Player {player_id} changed ingredient from {old_ing} to {new_ing}")
                self._add_game_event("ingredient_change", {
                    "player_id": player_id, 
                    "old_ingredient": old_ing, 
                    "new_ingredient": new_ing
                })

    def _add_game_event(self, event_type, data):
        """Add a game event to the event queue"""
        class GameEvent:
            def __init__(self, event_type, data, timestamp=None):
                self.event_type = event_type
                self.data = data
                self.timestamp = timestamp or time.time()
                self.id = uuid.uuid4().hex[:8]
        
        event = GameEvent(event_type, data)
        self.game_events.append(event)
        
        # Clean up old events
        current_time = time.time()
        self.game_events = [e for e in self.game_events if current_time - e.timestamp < 5.0]
    
    def _random_range(self, min_val, max_val):
        """Generate a random value in the given range"""
        return random.uniform(min_val, max_val)
    
    def _game_timer_thread(self):
        """Thread that manages the game timer, fusion detection, and game state updates"""
        start_time = time.time()
        end_time = start_time + config.GAME_TIMER_SECONDS
        
        logger.info(f"Timer thread: Starting with timer_thread_active={self.timer_thread_active}")
        
        while self.timer_thread_active and self.game_started:
            current_time = time.time()
            remaining = max(0, end_time - current_time)
            self.game_state.timer = int(remaining)
            
            # Check for recipe combinations and process fusion events
            self.game_state.check_for_merge()
            self.game_state.process_fusion_events()
            
            # Handle doorprize station logic
            if self.game_state.doorprize_station is None and \
               current_time - self.game_state.doorprize_spawn_time >= self.game_state.next_doorprize_spawn_delay:
                self.game_state.spawn_doorprize_station(current_time)
            elif self.game_state.doorprize_station is not None:
                self.game_state.check_doorprize_interaction()
            
            # Generate new orders as needed
            if current_time - self.game_state.last_order_spawn_time >= self.game_state.next_order_spawn_delay:
                if len(self.game_state.players) > 0:
                    self.game_state.generate_orders(len(self.game_state.players))
                    self.game_state.last_order_spawn_time = current_time
                    self.game_state.next_order_spawn_delay = self._random_range(
                        config.ORDER_SPAWN_INTERVAL_MIN, 
                        config.ORDER_SPAWN_INTERVAL_MAX
                    )
                    logger.info(f"Next order will spawn in {self.game_state.next_order_spawn_delay:.2f} seconds")
            
            # Check if game timer has expired
            if remaining <= 0:
                logger.info("Game timer finished")
                self.game_state.timer = 0
                break
            
            time.sleep(0.01)
        
        logger.info(f"Timer thread: Exiting loop. timer_thread_active={self.timer_thread_active}")

def ProcessTheClient(connection, address, server):
    """Process client connection in a separate thread"""
    try:
        rcv = ""
        while True:
            data = connection.recv(4096)
            if data:
                # Convert bytes to string for processing
                d = data.decode()
                rcv += d
                
                # Check if we've received a complete HTTP request
                if "\r\n\r\n" in rcv:
                    # Process the request
                    hasil = server.proses(rcv)
                    
                    # Send the response
                    connection.sendall(hasil)
                    
                    # Close the connection (HTTP/1.0 style)
                    connection.close()
                    break
            else:
                # No more data, close connection
                connection.close()
                break
    except Exception as e:
        logger.error(f"Error processing client {address}: {e}")
    finally:
        connection.close()

def run_server(host='0.0.0.0', port=8000):
    """Run the HTTP game server using raw sockets"""
    # Create server socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(5)
    
    logger.info(f"Starting HTTP game server on {host}:{port}")
    
    # Create server instance
    server = HttpServer()
    
    # Thread pool for client connections
    client_threads = []
    
    try:
        while True:
            # Accept client connection
            client_socket, client_address = server_socket.accept()
            logger.info(f"Connection from {client_address}")
            
            # Create thread to handle client
            client_thread = threading.Thread(
                target=ProcessTheClient,
                args=(client_socket, client_address, server),
                daemon=True
            )
            client_thread.start()
            
            # Add to thread pool and clean up completed threads
            client_threads.append(client_thread)
            client_threads = [t for t in client_threads if t.is_alive()]
            
    except KeyboardInterrupt:
        logger.info("Server shutting down")
    finally:
        server_socket.close()
        
        # Wait for client threads to finish
        for thread in client_threads:
            thread.join(timeout=1.0)

if __name__ == "__main__":
    run_server(host=config.SERVER_IP, port=config.SERVER_PORT)
