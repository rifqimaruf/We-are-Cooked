# src/lobby/lobby_server.py

import sys
import os # Tidak lagi diperlukan untuk sys.path.insert di sini
import json
import threading
import time
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse
import requests

# Import config secara absolut
from src.shared import config 

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('LobbyServer')

class LobbyHttpHandler(BaseHTTPRequestHandler):
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
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        if path == '/available_servers':
            available_server = self.server.get_available_game_server()
            if available_server:
                response = {"status": "success", "server_ip": available_server["ip"], "server_port": available_server["port"]}
                self._set_headers(200)
            else:
                response = {"status": "error", "message": "No available game servers at the moment."}
                self._set_headers(503) # Service Unavailable
            self.wfile.write(json.dumps(response).encode())
            return
        elif path == '/health':
            self._set_headers(200)
            self.wfile.write(json.dumps({"status": "Lobby OK", "game_servers_status": self.server.game_servers}).encode())
            return
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Not found"}).encode())

    def do_POST(self):
        # Untuk kasus ini, POST tidak terlalu diperlukan di Lobby Server,
        # tapi bisa ditambahkan jika ada fungsionalitas lain (misal, register server baru)
        self._set_headers(405) # Method Not Allowed
        self.wfile.write(json.dumps({"error": "Method not allowed"}).encode())


class LobbyServer(ThreadingMixIn, HTTPServer):
    def __init__(self, server_address, RequestHandlerClass):
        super().__init__(server_address, RequestHandlerClass)
        self.game_servers = {} # { "ip:port": {"ip": "...", "port": ..., "game_started": False, "player_count": 0, "last_checked": time.time()} }
        self.polling_thread = None
        self.running = False
        self._lock = threading.Lock() # Untuk mengamankan akses ke self.game_servers
        self.initialize_game_servers()
        logger.info("LobbyServer initialized.")

    def initialize_game_servers(self):
        # Game Server URLs harus sesuai dengan IP Docker internal atau IP eksternal yang di-expose
        # Untuk lab Anda:
        game_server_configs = [
            {"ip": "127.0.0.1", "port": 5555}, # Mesin 1
            {"ip": "127.0.0.1", "port": 5556}  # Mesin 2
        ]
        
        for srv_cfg in game_server_configs:
            addr = f"{srv_cfg['ip']}:{srv_cfg['port']}"
            self.game_servers[addr] = {
                "ip": srv_cfg['ip'],
                "port": srv_cfg['port'],
                "game_started": False,
                "player_count": 0,
                "is_full": False,
                "last_checked": time.time() # Untuk mencegah server yang mati terlalu lama
            }
            logger.info(f"Registered game server: {addr}")

    def start_polling(self):
        self.running = True
        self.polling_thread = threading.Thread(target=self._poll_game_servers, daemon=True)
        self.polling_thread.start()
        logger.info("Game server polling thread started.")

    def stop_polling(self):
        self.running = False
        if self.polling_thread and self.polling_thread.is_alive():
            self.polling_thread.join(timeout=2.0)
            logger.info("Game server polling thread stopped.")

    def _poll_game_servers(self):
        while self.running:
            with self._lock:
                for addr, server_info in self.game_servers.items():
                    url = f"http://{server_info['ip']}:{server_info['port']}/status"
                    try:
                        response = requests.get(url, timeout=1.0)
                        if response.status_code == 200:
                            status_data = response.json()
                            server_info["game_started"] = status_data.get("game_started", False)
                            server_info["player_count"] = status_data.get("player_count", 0)
                            server_info["is_full"] = status_data.get("is_full", False) # Ambil status 'is_full'
                            server_info["last_checked"] = time.time()
                            logger.debug(f"Polled {addr}: game_started={server_info['game_started']}, players={server_info['player_count']}, is_full={server_info['is_full']}")
                        else:
                            logger.warning(f"Failed to get status from {addr}: {response.status_code}")
                            server_info["game_started"] = True # Assume busy if not reachable
                            server_info["is_full"] = True # Assume full
                    except requests.exceptions.RequestException as e:
                        logger.error(f"Error polling {addr}: {e}")
                        server_info["game_started"] = True # Assume busy if not reachable
                        server_info["is_full"] = True # Assume full

            time.sleep(config.POLL_INTERVAL_LOBBY) 

    def get_available_game_server(self):
        with self._lock:
            # Prioritaskan server yang tidak sedang berjalan game
            available_idle_servers = [
                srv for srv in self.game_servers.values()
                if not srv["game_started"] and not srv["is_full"]
            ]
            if available_idle_servers:
                # Jika ada server idle, pilih salah satu secara acak
                return available_idle_servers[0] 
            
            # Jika semua server sedang berjalan game, cari yang belum penuh
            available_running_servers = [
                srv for srv in self.game_servers.values()
                if srv["game_started"] and not srv["is_full"]
            ]
            if available_running_servers:
                # Pilih server yang paling sedikit pemainnya jika ada
                return min(available_running_servers, key=lambda s: s["player_count"])

            logger.warning("No available game servers found.")
            return None

def run_lobby_server(host='0.0.0.0', port=5050):
    server_address = (host, port)
    httpd = LobbyServer(server_address, LobbyHttpHandler)
    
    # Start polling thread
    httpd.start_polling()

    logger.info(f"Starting Lobby Server on {host}:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Lobby Server shutting down")
    finally:
        httpd.stop_polling()
        httpd.server_close()
