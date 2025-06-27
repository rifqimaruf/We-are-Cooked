import threading
import json
import socket
from src.shared.network import Network

class NetworkHandler:
    def __init__(self, game_manager):
        self.network = Network()
        self.game_manager = game_manager
        self.thread = None
        self.running = False
        
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._receiver_thread, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)

    def send_action(self, data):
        try:
            self.network.send(data)
        except (socket.error, BrokenPipeError) as e:
            print(f"Failed to send action: {e}")
            self.stop()
    
    def _receiver_thread(self):
        while self.running:
            try:
                state = self.network.receive()
                self.game_manager.update_state(state)
            except (json.JSONDecodeError, socket.error, ConnectionResetError) as e:
                print(f"Error in receiver thread, stopping: {e}")
                self.running = False
                self.game_manager.handle_disconnect()
                break