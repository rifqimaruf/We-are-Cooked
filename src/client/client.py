import threading
import json
import time
import requests
import logging
from src.shared import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('GameClient')

class HttpNetworkHandler:
    def __init__(self, game_manager):
        self.game_manager = game_manager
        # Awalnya, klien terhubung ke Lobby Server
        self.lobby_url = f"http://{config.LOBBY_SERVER_IP}:{config.LOBBY_SERVER_PORT}"
        self.game_server_url = None # Akan diisi setelah mendapatkan dari lobby
        self.client_id = None
        self.thread = None
        self.running = False
        self.poll_interval = 0.1
        self.session = requests.Session()
        logger.info(f"HTTP client initialized. Connecting to lobby URL: {self.lobby_url}")
    
    def start(self):
        """Connect to the lobby server to get a game server, then connect to the game server."""
        try:
            # 1. Connect to Lobby Server to get a Game Server address
            logger.info(f"Requesting available game server from lobby at {self.lobby_url}/available_servers")
            lobby_response = self.session.get(f"{self.lobby_url}/available_servers", timeout=5.0)
            
            if lobby_response.status_code != 200:
                logger.error(f"Failed to get available server from lobby: {lobby_response.status_code} - {lobby_response.text}")
                self.game_manager.handle_disconnect()
                return False
            
            lobby_data = lobby_response.json()
            game_server_ip = lobby_data.get("server_ip")
            game_server_port = lobby_data.get("server_port")

            if not game_server_ip or not game_server_port:
                logger.error("Lobby did not provide a valid game server address.")
                self.game_manager.handle_disconnect()
                return False

            self.game_server_url = f"http://{game_server_ip}:{game_server_port}"
            logger.info(f"Lobby assigned game server: {self.game_server_url}")

            # 2. Connect to the assigned Game Server and get initial state
            logger.info(f"Connecting to game server at {self.game_server_url}/connect")
            response = self.session.post(
                f"{self.game_server_url}/connect",
                json={"action": "connect"}, # Kirim action connect ke game server
                timeout=5.0
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to connect to game server: {response.status_code} - {response.text}")
                self.game_manager.handle_disconnect()
                return False
            
            data = response.json()
            self.client_id = data.get("client_id")
            
            if not self.client_id:
                logger.error("No client ID received from game server")
                self.game_manager.handle_disconnect()
                return False
            
            # Update the game state with initial data
            self.game_manager.update_state(data)
            
            # Start the polling thread
            self.running = True
            self.thread = threading.Thread(target=self._polling_thread, daemon=True)
            self.thread.start()
            
            logger.info(f"Connected to game server {self.game_server_url} with client ID: {self.client_id}")
            return True
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection to lobby or game server failed: {e}")
            self.game_manager.handle_disconnect()
            return False
        except Exception as e:
            logger.error(f"Error during connection process: {e}")
            self.game_manager.handle_disconnect()
            return False
    
    def stop(self):
        """Stop the polling thread and disconnect from the server"""
        self.running = False
        
        # Send disconnect message to server
        if self.client_id and self.game_server_url: # Pastikan ada game_server_url
            try:
                self.session.post(
                    f"{self.game_server_url}/disconnect",
                    json={"client_id": self.client_id}
                )
            except:
                pass # Ignore errors during disconnect
        
        # Wait for polling thread to stop
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        
        # Close the session
        self.session.close()
        logger.info("Network handler stopped")
    
    def send_action(self, data):
        """Send an action to the game server"""
        if not self.running or not self.client_id or not self.game_server_url: # Pastikan ada game_server_url
            return
        
        try:
            data["client_id"] = self.client_id
            
            response = self.session.post(
                f"{self.game_server_url}/action", # Kirim ke game_server_url
                json=data,
                timeout=2.0
            )
            
            if response.status_code != 200:
                logger.warning(f"Game server returned error for action: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send action to game server: {e}")
            self.game_manager.handle_disconnect()
            self.stop()
    
    def _polling_thread(self):
        """Thread that polls the game server for game state updates"""
        while self.running:
            try:
                if not self.game_server_url or not self.client_id: # Pastikan sudah terhubung ke game server
                    time.sleep(0.1) # Tunggu sebentar
                    continue

                response = self.session.get(
                    f"{self.game_server_url}/game_state", # Poll game_server_url
                    params={"client_id": self.client_id},
                    timeout=2.0
                )
                
                if response.status_code == 200:
                    state = response.json()
                    self.game_manager.update_state(state)
                else:
                    logger.warning(f"Game server returned error during polling: {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                if self.running:
                    logger.error(f"Error in polling thread from game server: {e}")
                    self.running = False
                    self.game_manager.handle_disconnect()
                    break
            except Exception as e:
                logger.error(f"Unexpected error in polling thread from game server: {e}")
                if self.running:
                    self.running = False
                    self.game_manager.handle_disconnect()
                    break
            
            time.sleep(self.poll_interval)