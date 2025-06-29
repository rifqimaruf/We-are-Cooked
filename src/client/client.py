"""
HTTP Client implementation for We are Cooked game
This replaces the socket-based client with an HTTP-based implementation
"""

import pygame
import sys
import os
import cProfile
import pstats
import logging
from src.shared import config
from src.client.asset_manager import AssetManager
from src.client.game_manager import GameManager
from src.client.renderer import Renderer
from src.client.input_handler import InputHandler
from src.client.http import HttpNetworkHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('GameClientMain')

def main():
    # Initialize Pygame
    pygame.init()
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    
    # Create game window
    screen = pygame.display.set_mode((config.GRID_WIDTH * 50, (config.GRID_HEIGHT * 50) + 60))
    pygame.display.set_caption("We are Cooked (HTTP)")
    clock = pygame.time.Clock()
    
    # Load assets
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    assets_path = os.path.join(project_root, 'assets')
    asset_manager = AssetManager(assets_path, 50)
    asset_manager.load_all()
    
    # Initialize game components
    game_manager = GameManager()
    renderer = Renderer(screen, asset_manager)
    input_handler = InputHandler()
    
    # Connect to server
    try:
        network_handler = HttpNetworkHandler(game_manager)
        if not network_handler.start():
            logger.error("Failed to connect to server")
            pygame.quit()
            sys.exit(1)
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        pygame.quit()
        sys.exit(1)
    
    # Start profiling
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Main game loop
    running = True
    while running:
        # Handle user input
        actions = input_handler.handle_events(game_manager, renderer.ui_rects)
        for action in actions:
            if action['type'] == 'quit':
                running = False
            elif action['type'] == 'network':
                network_handler.send_action(action['data'])
            elif action['type'] == 'sfx':
                asset_manager.sound_manager.play_sfx(action['name'])
            elif action['type'] == 'toggle_almanac':
                renderer.show_almanac = not renderer.show_almanac
            elif action['type'] == 'close_almanac':
                renderer.show_almanac = False
        
        # Update game state
        game_manager.check_state_transitions(asset_manager)
        game_manager.check_game_events(asset_manager)
        
        # Render the game
        renderer.draw_frame(game_manager)
        
        # Check for disconnection
        if game_manager.is_disconnected:
            running = False
        
        # Cap the frame rate
        clock.tick(60)
    
    # Stop profiling and save results
    profiler.disable()
    stats_file = "client_profile.prof"
    profiler.dump_stats(stats_file)
    logger.info(f"Profiling data saved to {stats_file}")
    
    stats = pstats.Stats(stats_file)
    stats.sort_stats(pstats.SortKey.TIME)
    stats.print_stats(20)
    
    # Clean up and exit
    network_handler.stop()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
