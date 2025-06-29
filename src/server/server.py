"""
HTTP Server implementation for We are Cooked game
This replaces the socket-based server with an HTTP-based implementation
"""

import sys
import logging
from src.shared import config
from src.server.http import run_server

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    logger = logging.getLogger('GameServerMain')
    
    # Print startup message
    logger.info("Starting We are Cooked HTTP Game Server")
    logger.info(f"Server will listen on {config.SERVER_IP}:{config.SERVER_PORT}")
    
    try:
        # Run the HTTP server
        run_server(host=config.SERVER_IP, port=config.SERVER_PORT)
    except KeyboardInterrupt:
        logger.info("Server shutting down due to keyboard interrupt")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)
