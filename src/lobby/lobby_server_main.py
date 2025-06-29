import sys
import os
import logging

# Pastikan direktori 'src' ada di sys.path
# Ini akan memungkinkan Python menemukan 'src.shared'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

# Sekarang Anda bisa mengimpor dengan jalur lengkap
from src.shared import config
from src.lobby.lobby_server import run_lobby_server # Asumsi lobby_server.py juga ada di src/lobby

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    logger = logging.getLogger('LobbyServerMain')
    
    logger.info("Starting We are Cooked HTTP Lobby Server")
    logger.info(f"Lobby Server will listen on {config.LOBBY_SERVER_IP}:{config.LOBBY_SERVER_PORT}")
    
    try:
        run_lobby_server(host=config.LOBBY_SERVER_IP, port=config.LOBBY_SERVER_PORT)
    except KeyboardInterrupt:
        logger.info("Lobby Server shutting down due to keyboard interrupt")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Lobby Server error: {e}")
        sys.exit(1)