import threading
import json
import time
import requests
import logging
from src.shared import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('GameClient')

class HttpNetworkHandler:
    """HTTP-based network handler for the game client"""
    
    def __init__(self, game_manager, port=None):
        self.game_manager = game_manager
        server_port = port if port is not None else config.SERVER_PORT
        self.server_url = f"http://{config.SERVER_IP}:{server_port}"
        self.client_id = None
        self.thread = None
        self.running = False
        self.poll_interval = 0.1  # How often to poll for updates (seconds)
        self.session = requests.Session()
        logger.info(f"HTTP client initialized with server URL: {self.server_url}")
    
    def start(self):
        """Connect to the server and start the polling thread"""
        try:
            # Connect to the server and get initial state
            logger.info(f"Connecting to server at {self.server_url}/connect")
            response = self.session.post(
                f"{self.server_url}/connect",
                json={"action": "connect"},
                timeout=5.0  # Increase timeout for initial connection
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to connect to server: {response.status_code}")
                self.game_manager.handle_disconnect()
                return False
            
            # Parse the response and update game state
            data = response.json()
            self.client_id = data.get("client_id")
            
            if not self.client_id:
                logger.error("No client ID received from server")
                self.game_manager.handle_disconnect()
                return False
            
            # Update the game state with initial data
            self.game_manager.update_state(data)
            
            # Start the polling thread
            self.running = True
            self.thread = threading.Thread(target=self._polling_thread, daemon=True)
            self.thread.start()
            
            logger.info(f"Connected to server with client ID: {self.client_id}")
            return True
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection to server failed: {e}")
            self.game_manager.handle_disconnect()
            return False
        except Exception as e:
            logger.error(f"Error connecting to server: {e}")
            self.game_manager.handle_disconnect()
            return False
    
    def stop(self):
        """Stop the polling thread and disconnect from the server"""
        self.running = False
        
        # Send disconnect message to server
        if self.client_id:
            try:
                self.session.post(
                    f"{self.server_url}/disconnect",
                    json={"client_id": self.client_id}
                )
            except:
                pass  # Ignore errors during disconnect
        
        # Wait for polling thread to stop
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        
        # Close the session
        self.session.close()
        logger.info("Network handler stopped")
    
    def send_action(self, data):
        """Send an action to the server"""
        if not self.running or not self.client_id:
            return
        
        try:
            # Add client ID to the action data
            data["client_id"] = self.client_id
            
            # Send the action to the server
            response = self.session.post(
                f"{self.server_url}/action",
                json=data,
                timeout=2.0
            )
            
            if response.status_code != 200:
                logger.warning(f"Server returned error: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send action: {e}")
            self.game_manager.handle_disconnect()
            self.stop()
    
    def _polling_thread(self):
        """Thread that polls the server for game state updates"""
        while self.running:
            try:
                # Poll for game state updates
                response = self.session.get(
                    f"{self.server_url}/game_state",
                    params={"client_id": self.client_id},
                    timeout=2.0
                )
                
                if response.status_code == 200:
                    # Update the game state with the new data
                    state = response.json()
                    self.game_manager.update_state(state)
                else:
                    logger.warning(f"Server returned error during polling: {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                if self.running:
                    logger.error(f"Error in polling thread: {e}")
                    self.running = False
                    self.game_manager.handle_disconnect()
                    break
            except Exception as e:
                logger.error(f"Unexpected error in polling thread: {e}")
                if self.running:
                    self.running = False
                    self.game_manager.handle_disconnect()
                    break
            
            # Sleep before next poll
            time.sleep(self.poll_interval)
