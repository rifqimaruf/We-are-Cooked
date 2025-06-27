import pygame
from src.shared import config # Pastikan ini diimpor

class Renderer:
    def __init__(self, screen, asset_manager):
        self.screen = screen
        self.assets = asset_manager
        self.screen_width, self.screen_height = screen.get_size()
        self.ui_height = 60
        self.tile_size = 50
        self.interpolated_player_positions = {}
        self.ui_rects = {}

    def format_time(self, seconds):
        seconds = int(seconds); minutes = seconds // 60; seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    def draw_frame(self, game_manager):
        state = game_manager.game_screen_state
        if game_manager.is_disconnected:
            self.draw_disconnected_screen()
        elif state == config.GAME_STATE_START_SCREEN:
            self.draw_start_screen(game_manager)
        elif state == config.GAME_STATE_PLAYING:
            self.draw_game_screen(game_manager)
        elif state == config.GAME_STATE_END_SCREEN:
            self.draw_end_screen(game_manager)
        pygame.display.flip()

    def draw_game_screen(self, game_manager):
        self.screen.fill((240, 240, 240))
        state_data = game_manager.current_state
        if not state_data:
            return

        # --- PENAMBAHAN KODE BARU DI SINI ---
        self._draw_stations(state_data)
        # --- AKHIR PENAMBAHAN ---

        for player_id, player in state_data["players"].items():
            self._draw_player(player_id, player, game_manager.client_id)
        
        self._draw_ui(state_data)
        
        restart_button_width, restart_button_height = 100, 40
        restart_button_x = self.screen_width - restart_button_width - 10
        restart_button_y = self.screen_height - self.ui_height + (self.ui_height - restart_button_height) // 2
        
        self.ui_rects['restart_button'] = self._draw_button(
            (restart_button_x + restart_button_width // 2, restart_button_y + restart_button_height // 2), 
            "Restart", 
            (restart_button_width, restart_button_height)
        )

    # --- PENAMBAHAN KODE BARU DI SINI ---
    def _draw_stations(self, state_data):
        # Draw Fusion Stations
        fusion_stations = state_data.get("fusion_stations", [])
        for i, (sx, sy) in enumerate(fusion_stations):
            for row in range(config.STATION_SIZE):
                for col in range(config.STATION_SIZE):
                    rect = pygame.Rect((sx + col) * self.tile_size, (sy + row) * self.tile_size, self.tile_size, self.tile_size)
                    pygame.draw.rect(self.screen, (255, 150, 150, 100), rect) # Warna merah muda transparan
                    pygame.draw.rect(self.screen, (200, 0, 0), rect, 2) # Border merah

            font = self.assets.get_font('default_18')
            text_surface = font.render(f"Fusion {i+1}", True, (50, 50, 50))
            text_rect = text_surface.get_rect(topleft=(sx * self.tile_size + 5, sy * self.tile_size + 5))
            self.screen.blit(text_surface, text_rect)

        # Draw Enter Station
        enter_station = state_data.get("enter_station")
        if enter_station:
            sx, sy = enter_station
            for row in range(config.STATION_SIZE):
                for col in range(config.STATION_SIZE):
                    rect = pygame.Rect((sx + col) * self.tile_size, (sy + row) * self.tile_size, self.tile_size, self.tile_size)
                    pygame.draw.rect(self.screen, (150, 255, 150, 100), rect) # Warna hijau muda transparan
                    pygame.draw.rect(self.screen, (0, 200, 0), rect, 2) # Border hijau
            
            font = self.assets.get_font('default_18')
            text_surface = font.render("Enter", True, (50, 50, 50))
            text_rect = text_surface.get_rect(topleft=(sx * self.tile_size + 5, sy * self.tile_size + 5))
            self.screen.blit(text_surface, text_rect)
    # --- AKHIR PENAMBAHAN ---

    def _draw_player(self, player_id, player_data, local_client_id):
        target_x, target_y = player_data["pos"]
        current_x, current_y = self.interpolated_player_positions.get(player_id, (target_x, target_y))
        
        interpolated_x = current_x + (target_x - current_x) * 0.5
        interpolated_y = current_y + (target_y - current_y) * 0.5
        self.interpolated_player_positions[player_id] = (interpolated_x, interpolated_y)
        
        rect = pygame.Rect(interpolated_x * self.tile_size, interpolated_y * self.tile_size, self.tile_size, self.tile_size)
        
        sprite = self.assets.get_sprite(player_data["ingredient"])
        if sprite:
            sprite_rect = sprite.get_rect(center=rect.center)
            self.screen.blit(sprite, sprite_rect)
        else:
             pygame.draw.rect(self.screen, (200, 100, 100), rect) 
        
        if player_id == local_client_id:
            pygame.draw.rect(self.screen, (0, 150, 255, 150), rect, 3)
        else:
            pygame.draw.rect(self.screen, (0, 200, 0, 150), rect, 2)
        
        ingredient_name = player_data["ingredient"]
        font = self.assets.get_font('default_18')
        text_surface = font.render(ingredient_name, True, (0, 0, 0))
        
        text_rect = text_surface.get_rect(center=(rect.centerx, rect.bottom + 5))
        self.screen.blit(text_surface, text_rect)

    def _draw_ui(self, state_data):
        ui_area = pygame.Rect(0, self.screen_height - self.ui_height, self.screen_width, self.ui_height)
        pygame.draw.rect(self.screen, (50, 50, 50), ui_area)

        score_text = self.assets.get_font('default_28').render(f"Score: {state_data['score']}", True, (255, 255, 255))
        self.screen.blit(score_text, (20, self.screen_height - self.ui_height + 20))
        
        timer_val = state_data.get('timer', 0)
        timer_color = (255, 0, 0) if timer_val < 11 else (255, 255, 0) if timer_val < 30 else (255, 255, 255)
        timer_text = self.assets.get_font('default_28').render(f"Time: {self.format_time(timer_val)}", True, timer_color)
        timer_rect = timer_text.get_rect(midtop=(self.screen_width // 2, self.screen_height - self.ui_height + 10))
        self.screen.blit(timer_text, timer_rect)

        if "orders" in state_data and state_data["orders"]:
            orders_bg_rect = pygame.Rect(10, 10, 280, len(state_data["orders"][:3]) * 25 + 30) # Adjusted height
            pygame.draw.rect(self.screen, (50, 50, 50), orders_bg_rect, border_radius=5)
            pygame.draw.rect(self.screen, (100, 100, 100), orders_bg_rect, 2, border_radius=5)
            
            orders_title_font = self.assets.get_font('default_18')
            orders_text = orders_title_font.render(f"Orders:", True, (200, 200, 200))
            self.screen.blit(orders_text, (orders_bg_rect.x + 10, orders_bg_rect.y + 8))

            order_font = self.assets.get_font('default_24')
            for i, order in enumerate(state_data["orders"][:3]):
                order_name = order["name"]
                ingredients_list = ", ".join(order.get("ingredients", []))
                display_text = f"{order_name} ({ingredients_list})"
                
                order_text_surface = order_font.render(display_text, True, (255, 255, 0)) # Warna kuning terang
                self.screen.blit(order_text_surface, (orders_bg_rect.x + 10, orders_bg_rect.y + 30 + i * 25))

    def draw_start_screen(self, game_manager):
        bg_image = self.assets.get_image('start_bg')
        if bg_image:
            scaled_bg = pygame.transform.scale(bg_image, (self.screen_width, self.screen_height))
            self.screen.blit(scaled_bg, (0, 0))
        else:
            self.screen.fill((30, 30, 50))
        
        title_text = self.assets.get_font('default_72').render("We are Cooked!", True, (255, 220, 100))
        title_rect = title_text.get_rect(center=(self.screen_width // 2, self.screen_height // 6))
        
        title_bg_rect = title_rect.inflate(40, 20) 
        title_bg_surface = pygame.Surface((title_bg_rect.width, title_bg_rect.height))
        title_bg_surface.set_alpha(150)  
        title_bg_surface.fill((0, 0, 0))  
        self.screen.blit(title_bg_surface, title_bg_rect)
        self.screen.blit(title_text, title_rect)
        
        if game_manager.current_state and "clients_info" in game_manager.current_state:
            y_offset = self.screen_height // 2 - 40
            players_title = self.assets.get_font('default_36').render("Players in Lobby:", True, (200, 200, 200))
            players_title_rect = players_title.get_rect(center=(self.screen_width // 2, y_offset))
            
            # Calculate total height needed for players list
            total_players = len(game_manager.current_state["clients_info"])
            list_height = 50 + (total_players * 30) + 20  # title + players + padding
            list_width = 400
            
            # Create semi-transparent background for players list
            list_bg_rect = pygame.Rect(0, 0, list_width, list_height)
            list_bg_rect.center = (self.screen_width // 2, y_offset + (list_height // 2) - 25)
            list_bg_surface = pygame.Surface((list_bg_rect.width, list_bg_rect.height))
            list_bg_surface.set_alpha(128)  # 50% transparency
            list_bg_surface.fill((0, 0, 0))  # Black background
            self.screen.blit(list_bg_surface, list_bg_rect)
            
            # Draw players title and list
            self.screen.blit(players_title, players_title_rect)
            y_offset += 50

            for player_id, info in game_manager.current_state["clients_info"].items():
                player_name = info.get("username", "Unknown")
                ready_status = "Ready" if info.get("ready", False) else "Not Ready"
                text_color = (255, 255, 100) if player_id == game_manager.client_id else (255, 255, 255)
                player_label = self.assets.get_font('default_28').render(f"{player_name} - {ready_status}", True, text_color)
                player_label_rect = player_label.get_rect(center=(self.screen_width // 2, y_offset))
                self.screen.blit(player_label, player_label_rect)
                y_offset += 30
        
        is_ready = game_manager.current_state and game_manager.client_id in game_manager.current_state.get("clients_info", {}) and game_manager.current_state["clients_info"][game_manager.client_id].get("ready", False)
        all_ready = game_manager.current_state and len(game_manager.current_state.get("clients_info", {})) > 0 and all(c.get("ready", False) for c in game_manager.current_state.get("clients_info", {}).values())

        self.ui_rects['ready_button'] = self._draw_button((self.screen_width // 4, self.screen_height * 3 // 4), "Cancel" if is_ready else "Ready", (200, 50))
        self.ui_rects['start_button'] = self._draw_button((self.screen_width * 3 // 4, self.screen_height * 3 // 4), "Start Game", (200, 50), enabled=all_ready)
        
    def draw_end_screen(self, game_manager):
        bg_image = self.assets.get_image('end_bg')
        if bg_image:
            self.screen.blit(pygame.transform.scale(bg_image, self.screen.get_size()), (0, 0))
        else:
            self.screen.fill((255, 255, 255)) 
        
        score_y_pos = self.screen_height * 0.60

        score_font = self.assets.get_font('default_48')
        if score_font:
            score_text_surface = score_font.render(f"Final Score: {game_manager.final_score}", True, (0, 0, 0)) 
            score_rect = score_text_surface.get_rect(center=(self.screen_width // 2, score_y_pos))
            self.screen.blit(score_text_surface, score_rect)

        button_y_pos = score_y_pos + 80 

        self.ui_rects['play_again_button'] = self._draw_button(
            center_pos=(self.screen_width // 2, button_y_pos), 
            text="Play Again", 
            size=(200, 60)
        )

    def draw_disconnected_screen(self):
        self.screen.fill((50, 30, 30))
        msg_text = self.assets.get_font('default_48').render("Disconnected from server", True, (255, 255, 255))
        msg_rect = msg_text.get_rect(center=(self.screen_width // 2, self.screen_height // 2))
        self.screen.blit(msg_text, msg_rect)

    def _draw_button(self, center_pos, text, size, enabled=True):
        rect = pygame.Rect(0, 0, size[0], size[1]); rect.center = center_pos
        hover = rect.collidepoint(pygame.mouse.get_pos())
        color = ((100, 200, 100) if hover else (80, 180, 80)) if enabled else (100, 100, 100)
        text_color = (255, 255, 255) if enabled else (180, 180, 180)
        pygame.draw.rect(self.screen, color, rect, border_radius=10)
        text_surf = self.assets.get_font('default_36').render(text, True, text_color)
        text_rect = text_surf.get_rect(center=rect.center)
        self.screen.blit(text_surf, text_rect)
        return rect