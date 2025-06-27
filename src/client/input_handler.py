import pygame
from src.shared import config

class InputHandler:
    def handle_events(self, game_manager, ui_rects):
        actions = []
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                actions.append({'type': 'quit'})
                continue

            state = game_manager.game_screen_state
            
            if state == config.GAME_STATE_START_SCREEN:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if ui_rects.get('ready_button') and ui_rects['ready_button'].collidepoint(event.pos):
                        actions.append({'type': 'network', 'data': {'action': 'toggle_ready'}})
                        actions.append({'type': 'sfx', 'name': 'Splash Sound'})
                    
                    if ui_rects.get('start_button') and ui_rects['start_button'].collidepoint(event.pos):
                        if game_manager.current_state and \
                           all(c.get("ready", False) for c in game_manager.current_state.get("clients_info", {}).values()) and \
                           len(game_manager.current_state.get("clients_info", {})) > 0:
                            actions.append({'type': 'network', 'data': {'action': 'start_game'}})
                            actions.append({'type': 'sfx', 'name': 'Splash Sound'})

            elif state == config.GAME_STATE_PLAYING:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if ui_rects.get('restart_button') and ui_rects['restart_button'].collidepoint(event.pos):
                        actions.append({'type': 'network', 'data': {'action': 'restart'}})
                        actions.append({'type': 'sfx', 'name': 'Splash Sound'})

            elif state == config.GAME_STATE_END_SCREEN:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if ui_rects.get('play_again_button') and ui_rects['play_again_button'].collidepoint(event.pos):
                        actions.append({'type': 'network', 'data': {'action': 'return_to_lobby'}})
                        actions.append({'type': 'sfx', 'name': 'Splash Sound'})
        
        if game_manager.game_screen_state == config.GAME_STATE_PLAYING:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_UP]: actions.append({'type': 'network', 'data': {'action': 'move', 'direction': 'UP'}})
            elif keys[pygame.K_DOWN]: actions.append({'type': 'network', 'data': {'action': 'move', 'direction': 'DOWN'}})
            elif keys[pygame.K_LEFT]: actions.append({'type': 'network', 'data': {'action': 'move', 'direction': 'LEFT'}})
            elif keys[pygame.K_RIGHT]: actions.append({'type': 'network', 'data': {'action': 'move', 'direction': 'RIGHT'}})
            
        return actions