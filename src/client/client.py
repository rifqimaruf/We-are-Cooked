import pygame
import sys
import os
import cProfile
import pstats
import time
import random
from src.shared import config
from src.client.asset_manager import AssetManager
from src.client.game_manager import GameManager
from src.client.renderer import Renderer
from src.client.input_handler import InputHandler
from src.client.network_handler import NetworkHandler

pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

def main():
    screen = pygame.display.set_mode((config.GRID_WIDTH * 50, (config.GRID_HEIGHT * 50) + 60))
    pygame.display.set_caption("We are Cooked")
    clock = pygame.time.Clock()

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    assets_path = os.path.join(project_root, 'assets')
    asset_manager = AssetManager(assets_path, 50)
    asset_manager.load_all()

    game_manager = GameManager()
    renderer = Renderer(screen, asset_manager)
    input_handler = InputHandler()

    try:
        network_handler = NetworkHandler(game_manager)
        network_handler.start()
    except (ConnectionRefusedError, FileNotFoundError) as e:
        print(f"Connection failed. Is the server running? Error: {e}")
        pygame.quit()
        sys.exit()

    profiler = cProfile.Profile()
    profiler.enable()

    running = True
    while running:
        actions = input_handler.handle_events(game_manager, renderer.ui_rects)
        for action in actions:
            if action['type'] == 'quit':
                running = False
            elif action['type'] == 'network':
                network_handler.send_action(action['data'])
            elif action['type'] == 'sfx':
                asset_manager.sound_manager.play_sfx(action['name'])

        game_manager.check_state_transitions(asset_manager)
        game_manager.check_game_events(asset_manager)
        renderer.draw_frame(game_manager)

        if game_manager.is_disconnected:
            running = False

        clock.tick(60)

    profiler.disable()
    stats_file = "client_profile.prof"
    profiler.dump_stats(stats_file)
    print(f"Profiling data saved to {stats_file}")
    
    stats = pstats.Stats(stats_file)
    stats.sort_stats(pstats.SortKey.TIME)
    stats.print_stats(20)

    network_handler.stop()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()