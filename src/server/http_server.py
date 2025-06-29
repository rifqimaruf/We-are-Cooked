import sys
import os.path
import uuid
import json
import threading
import time
import logging
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import parse_qs, urlparse

from src.shared.game_state import GameState
from src.shared import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('GameServer')

class GameHttpHandler(BaseHTTPRequestHandler):
    """
    HTTP request handler for the game server.
    Handles GET and POST requests for game state and actions.
    """
    # These class variables will be accessed through self.server
    # No need to override __init__ which causes the error

    def _set_headers(self, status_code=200, content_type='application/json'):
        self.send_response(status_code)
        self.send_header('Content-Type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers()

    def do_GET(self):
        """Handle GET requests - used for clients to get game state updates"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == '/game_state':
            # Return the current game state
            state_dict = self.server.game_state.to_dict()
            state_dict["clients_info"] = self.server.clients_info
            state_dict["game_started"] = self.server.game_started
            
            # Add visual effects
            state_dict["visual_effects"] = {"game_events": []}
            if "_visual_events" in state_dict:
                state_dict["visual_effects"]["game_events"].extend(state_dict["_visual_events"])
                del state_dict["_visual_events"]
            
            # Extract client_id from query parameters if present
            query_params = parse_qs(parsed_path.query)
            client_id = query_params.get('client_id', [None])[0]
            if client_id:
                state_dict["client_id"] = client_id
            
            self._set_headers()
            self.wfile.write(json.dumps(state_dict).encode())
            return
        
        elif path == '/status':
            # Endpoint baru untuk Lobby Server menanyakan status
            status_data = {
                "game_started": self.server.game_started,
                "player_count": len(self.server.clients_info),
                "is_full": len(self.server.clients_info) >= config.MAX_PLAYERS_PER_SERVER 
            }
            self._set_headers(200)
            self.wfile.write(json.dumps(status_data).encode())
            return
        
        elif path == '/health':
            # Simple health check endpoint
            self._set_headers()
            self.wfile.write(json.dumps({"status": "ok", "players": len(self.server.clients_info)}).encode())
            return
            
        else:
            # Handle 404 for unknown paths
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Not found"}).encode())

    def do_POST(self):
        """Handle POST requests - used for client actions"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
            action = data.get("action")
            client_id = data.get("client_id")
            
            # Register new client if this is a connection request
            if self.path == '/connect':
                if not client_id:
                    client_id = str(uuid.uuid4())
                    self.server.register_client(client_id)
                
                response = {
                    "client_id": client_id,
                    "status": "connected",
                    "game_state": self.server.game_state.to_dict(),
                    "clients_info": self.server.clients_info,
                    "game_started": self.server.game_started
                }
                self._set_headers(200)
                self.wfile.write(json.dumps(response).encode())
                return
            
            # Handle client actions
            if self.path == '/action':
                if not client_id or client_id not in self.server.clients_info:
                    self._set_headers(400)
                    self.wfile.write(json.dumps({"error": "Invalid client ID"}).encode())
                    return
                
                # Process the action based on game state
                if action == "return_to_lobby":
                    self.server.return_to_lobby()
                
                elif not self.server.game_started:
                    if action == "set_username":
                        username = data.get("username", "Unknown")
                        self.server.clients_info[client_id]["username"] = username
                        logger.info(f"Client {client_id} set username to {username}")
                    
                    elif action == "toggle_ready":
                        self.server.clients_info[client_id]["ready"] = not self.server.clients_info[client_id].get("ready", False)
                        logger.info(f"Client {client_id} toggled ready. Status: {self.server.clients_info[client_id]['ready']}")
                    
                    elif action == "start_game":
                        if all(c["ready"] for c in self.server.clients_info.values()) and len(self.server.clients_info) > 1:
                            self.server.restart_game()
                
                else:
                    if self.server.game_state.timer > 0:
                        if action == "move":
                            direction = data.get("direction")
                            self.server.game_state.move_player(client_id, direction)
                            logger.info(f"Client {client_id} moved {direction}")
                        
                        elif action == "restart":
                            self.server.restart_game()
                        
                        elif action == "change_ingredient":
                            if self.server.game_state.can_player_change_ingredient(client_id):
                                self.server.change_player_ingredient(client_id)
                
                # Return success response
                self._set_headers(200)
                self.wfile.write(json.dumps({"status": "success"}).encode())
                return
            
            # Handle disconnect
            if self.path == '/disconnect':
                if client_id in self.server.clients_info:
                    self.server.cleanup_disconnected_players([client_id])
                    logger.info(f"Client {client_id} disconnected")
                
                self._set_headers(200)
                self.wfile.write(json.dumps({"status": "disconnected"}).encode())
                return
            
            # Handle unknown paths
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Not found"}).encode())
            
        except json.JSONDecodeError:
            self._set_headers(400)
            self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode())
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            self._set_headers(500)
            self.wfile.write(json.dumps({"error": str(e)}).encode())

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
    def __init__(self, server_address, RequestHandlerClass):
        super().__init__(server_address, RequestHandlerClass)
        self.game_state = GameState()
        self.clients_info = {}
        self.game_started = False
        self.timer_thread_active = False
        self.timer_thread_instance = None
        self.game_events = []
        self.shutdown_flag = False
        
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
        import random
        
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
        import random
        
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
        import random
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

def run_server(host='0.0.0.0', port=8000):
    """Run the HTTP game server"""
    server_address = (host, port)
    httpd = ThreadedHTTPServer(server_address, GameHttpHandler)
    logger.info(f"Starting HTTP game server on {host}:{port}")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server shutting down")
        httpd.shutdown_flag = True
        httpd.server_close()

if __name__ == "__main__":
    run_server(host=config.SERVER_IP, port=config.SERVER_PORT)
