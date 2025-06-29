import threading
import json
import socket
import struct
import logging
from src.shared import config

logger = logging.getLogger('NetworkHandler')

class NetworkHandler:
    """Socket-based network handler for the game client"""
    
    HEADER_SIZE = 4  # Size of the message length header in bytes

    def __init__(self, game_manager):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.game_manager = game_manager
        self.thread = None
        self.running = False
        self.sock.settimeout(1.0)  # Timeout for socket operations (connect, recv)
        logger.info("Network handler initialized")

    def start(self):
        """Connect to the server and start the receiver thread"""
        try:
            logger.info(f"Connecting to server at {config.SERVER_IP}:{config.SERVER_PORT}")
            self.sock.connect((config.SERVER_IP, config.SERVER_PORT))
        except (socket.error, ConnectionRefusedError) as e:
            logger.error(f"Connection to server failed: {e}")
            self.game_manager.handle_disconnect()
            return False
            
        self.running = True
        self.thread = threading.Thread(target=self._receiver_thread, daemon=True)
        self.thread.start()
        logger.info("Network handler started and connected to server")
        return True

    def stop(self):
        """Stop the receiver thread and close the socket"""
        self.running = False
        if self.sock:
            try:
                # Try to send a disconnect message
                try:
                    self.send_action({"action": "disconnect"})
                except:
                    pass
                    
                # Close the socket
                self.sock.shutdown(socket.SHUT_RDWR)
                self.sock.close()
            except OSError:
                pass
                
        # Wait for the receiver thread to finish
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
            
        logger.info("Network handler stopped")

    def send_action(self, data):
        """Send an action to the server"""
        if not self.running:
            return
            
        try:
            # Encode the data as JSON and then to bytes
            encoded_data = json.dumps(data).encode('utf-8')
            
            # Create a header with the message length
            header = struct.pack('>I', len(encoded_data))
            
            # Send the header followed by the data
            self.sock.sendall(header + encoded_data)
            logger.debug(f"Sent action: {data['action'] if 'action' in data else data}")
        except (socket.error, BrokenPipeError, OSError) as e:
            logger.error(f"Failed to send action: {e}")
            self.game_manager.handle_disconnect()
            self.stop()

    def _recv_all(self, n):
        """Receive exactly n bytes from the socket"""
        data = bytearray()
        while len(data) < n:
            try:
                packet = self.sock.recv(n - len(data))
                if not packet:
                    return None
                data.extend(packet)
            except (socket.timeout, BlockingIOError):
                # Re-raise timeout to be handled by receiver_thread
                raise socket.timeout
            except (socket.error, ConnectionResetError) as e:
                logger.error(f"Network _recv_all error: {e}")
                return None
        return data
    
    def _receiver_thread(self):
        """Thread that receives game state updates from the server"""
        try:
            # Receive initial state (first blocking call)
            header_data = self._recv_all(self.HEADER_SIZE)
            if not header_data:
                raise ConnectionError("Server closed connection on initial handshake")
            
            msg_len = struct.unpack('>I', header_data)[0]
            data = self._recv_all(msg_len)
            if not data:
                raise ConnectionError("Failed to receive initial state")
            
            initial_state = json.loads(data.decode('utf-8'))
            self.game_manager.update_state(initial_state)
            logger.info("Received initial game state")

        except (json.JSONDecodeError, struct.error, ConnectionError, socket.error, socket.timeout) as e:
            if self.running:
                logger.error(f"Error receiving initial state: {type(e).__name__} - {e}")
            self.running = False
            self.game_manager.handle_disconnect()
            return
        except Exception as e:
            logger.error(f"Unexpected error receiving initial state: {type(e).__name__} - {e}")
            self.running = False
            self.game_manager.handle_disconnect()
            return

        # Main receiver loop
        while self.running:
            try:
                # Receive message header (4 bytes containing message length)
                header_data = self._recv_all(self.HEADER_SIZE)
                if not header_data:
                    raise ConnectionError("Server closed connection")
                
                # Unpack the message length
                msg_len = struct.unpack('>I', header_data)[0]
                
                # Receive the full message
                data = self._recv_all(msg_len)
                if not data:
                    raise ConnectionError("Failed to receive full message")
                
                # Parse the message and update game state
                state = json.loads(data.decode('utf-8'))
                self.game_manager.update_state(state)
                
            except (socket.timeout, BlockingIOError):
                # Timeout is expected, just continue the loop
                pass
            except (json.JSONDecodeError, struct.error, ConnectionError, socket.error) as e:
                if self.running:
                    logger.error(f"Error in receiver thread: {type(e).__name__} - {e}")
                self.running = False
                self.game_manager.handle_disconnect()
                break
            except Exception as e:
                logger.error(f"Unexpected error in receiver thread: {type(e).__name__} - {e}")
                self.running = False
                self.game_manager.handle_disconnect()
                break
