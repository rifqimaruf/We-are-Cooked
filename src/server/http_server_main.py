# src/server/http_server_main.py

import sys
import os
import logging
# Pastikan project root ditambahkan ke sys.path agar import berhasil
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)
from src.shared import config
from src.server.http_server import run_server

logging.basicConfig(
    level=logging.INFO, # Bisa diubah ke DEBUG jika ingin log lebih detail
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('GameServerMain')

if __name__ == "__main__":
    # Izinkan port diberikan sebagai argumen command-line
    port_to_run = config.SERVER_PORT # Default port
    if len(sys.argv) > 1:
        try:
            port_to_run = int(sys.argv[1])
        except ValueError:
            logger.warning(f"Invalid port argument: {sys.argv[1]}. Using default {config.SERVER_PORT}.")

    logger.info("Starting We are Cooked HTTP Game Server")
    logger.info(f"Server will listen on {config.SERVER_IP}:{port_to_run}")
    
    try:
        run_server(host=config.SERVER_IP, port=port_to_run) # Pass port yang sudah disesuaikan
    except KeyboardInterrupt:
        logger.info("Server shutting down due to keyboard interrupt")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)