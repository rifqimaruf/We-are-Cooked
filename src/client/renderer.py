# src/client/renderer.py
import pygame
import math
from src.shared import config 
import time # Import time for calculating remaining time

class Renderer:
    def __init__(self, screen, asset_manager):
        self.screen = screen
        self.assets = asset_manager
        self.screen_width, self.screen_height = screen.get_size()
        self.ui_height = 60
        self.tile_size = 50
        self.interpolated_player_positions = {}
        self.ui_rects = {}
        self.show_almanac = False 

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
        bg_image = self.assets.get_image('game_bg')
        if bg_image:
            scaled_bg = pygame.transform.scale(bg_image, (self.screen_width, self.screen_height))
            self.screen.blit(scaled_bg, (0, 0))
        else:
            self.screen.fill((245, 245, 220))  
        
        state_data = game_manager.current_state
        if not state_data:
            return

        self._draw_stations(state_data)
        self._draw_doorprize_station(state_data) # Panggil fungsi baru ini

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

    def _draw_stations(self, state_data):
        fusion_stations = state_data.get("fusion_stations", [])
        stove_image = self.assets.get_image('stove')
        
        glow_time = time.time() * 2.5  
        glow_intensity = (math.sin(glow_time) + 1) / 2  
        
        pulse_time = time.time() * 4
        pulse_intensity = (math.sin(pulse_time) + 1) / 2
        
        for i, (sx, sy) in enumerate(fusion_stations):
            station_rect = pygame.Rect(sx * self.tile_size, sy * self.tile_size, 
                                     config.STATION_SIZE * self.tile_size, 
                                     config.STATION_SIZE * self.tile_size)
            
            base_alpha = 30 + int(50 * glow_intensity)
            glow_colors = [
                (255, 80, 0, max(20, int(base_alpha * 0.6))),    
                (255, 120, 20, max(30, int(base_alpha * 0.8))),  
                (255, 180, 60, max(40, int(base_alpha * 1.0))), 
                (255, 220, 120, max(25, int(base_alpha * 0.7 * pulse_intensity)))  
            ]
            
            glow_offsets = [16, 12, 6, 3]  
            
            for glow_color, offset in zip(glow_colors, glow_offsets):
                glow_rect = station_rect.inflate(offset * 2, offset * 2)
                glow_surface = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                pygame.draw.rect(glow_surface, glow_color, glow_surface.get_rect(), border_radius=offset//2 + 4)
                self.screen.blit(glow_surface, glow_rect.topleft)
            
            sparkle_time = time.time() * 6 + i * 2 
            for sparkle_idx in range(4): 
                angle = sparkle_time + sparkle_idx * (math.pi / 2)
                sparkle_distance = 30 + 10 * math.sin(sparkle_time * 2)
                sparkle_x = station_rect.centerx + math.cos(angle) * sparkle_distance
                sparkle_y = station_rect.centery + math.sin(angle) * sparkle_distance
                
                sparkle_alpha = int(150 * (math.sin(sparkle_time * 3 + sparkle_idx) + 1) / 2)
                sparkle_size = 3 + int(2 * (math.sin(sparkle_time * 4 + sparkle_idx) + 1) / 2)
                
                sparkle_color = (255, 200 + int(50 * glow_intensity), 100, sparkle_alpha)
                sparkle_surface = pygame.Surface((sparkle_size * 2, sparkle_size * 2), pygame.SRCALPHA)
                pygame.draw.circle(sparkle_surface, sparkle_color, (sparkle_size, sparkle_size), sparkle_size)
                self.screen.blit(sparkle_surface, (sparkle_x - sparkle_size, sparkle_y - sparkle_size))
            
            if stove_image:
                self.screen.blit(stove_image, station_rect)
                
                shimmer_alpha = int(30 * glow_intensity)
                shimmer_surface = pygame.Surface(station_rect.size, pygame.SRCALPHA)
                shimmer_color = (255, 100, 0, shimmer_alpha)
                pygame.draw.rect(shimmer_surface, shimmer_color, shimmer_surface.get_rect(), border_radius=4)
                self.screen.blit(shimmer_surface, station_rect.topleft)
            else:
                for row in range(config.STATION_SIZE):
                    for col in range(config.STATION_SIZE):
                        rect = pygame.Rect((sx + col) * self.tile_size, (sy + row) * self.tile_size, self.tile_size, self.tile_size)
                        pygame.draw.rect(self.screen, (255, 150, 150, 100), rect) 
                        pygame.draw.rect(self.screen, (200, 0, 0), rect, 2) 

            font = self.assets.get_font('default_18')
            text_surface = font.render(f"Fusion {i+1}", True, (255, 255, 255)) 
            text_rect = text_surface.get_rect(center=(
                (sx + config.STATION_SIZE/2) * self.tile_size, 
                (sy + config.STATION_SIZE - 0.2) * self.tile_size
            ))
            text_bg_rect = text_rect.inflate(6, 2)
            pygame.draw.rect(self.screen, (0, 0, 0, 128), text_bg_rect, border_radius=3)
            self.screen.blit(text_surface, text_rect)

        enter_station = state_data.get("enter_station")
        if enter_station:
            sx, sy = enter_station
            
            fridge_image = self.assets.get_image('fridge')
            
            station_rect = pygame.Rect(sx * self.tile_size, sy * self.tile_size, 
                                     config.STATION_SIZE * self.tile_size, 
                                     config.STATION_SIZE * self.tile_size)
            
            glow_time = time.time() * 2.0  
            glow_intensity = (math.sin(glow_time) + 1) / 2  
            
            pulse_time = time.time() * 3.5 
            pulse_intensity = (math.sin(pulse_time) + 1) / 2
            
            base_alpha = 40 + int(55 * glow_intensity)
            glow_colors = [
                (0, 150, 255, max(25, int(base_alpha * 0.5))),     
                (0, 200, 255, max(35, int(base_alpha * 0.7))),     
                (100, 220, 255, max(45, int(base_alpha * 0.9))),   
                (150, 255, 255, max(30, int(base_alpha * 0.6 * pulse_intensity))) 
            ]
            
            glow_offsets = [20, 15, 10, 5]  
            
            for glow_color, offset in zip(glow_colors, glow_offsets):
                glow_rect = station_rect.inflate(offset * 2, offset * 2)
                glow_surface = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                pygame.draw.rect(glow_surface, glow_color, glow_surface.get_rect(), border_radius=offset//2 + 8)
                self.screen.blit(glow_surface, glow_rect.topleft)
            
            frost_time = time.time() * 4 + sx * 2 + sy
            for frost_idx in range(8):
                angle = frost_time + frost_idx * (math.pi / 4)  
                frost_distance = 25 + 8 * math.sin(frost_time * 1.5)
                frost_x = station_rect.centerx + math.cos(angle) * frost_distance
                frost_y = station_rect.centery + math.sin(angle) * frost_distance
                
                frost_alpha = int(120 * (math.sin(frost_time * 3 + frost_idx) + 1) / 2)
                frost_size = 2 + int(2 * (math.sin(frost_time * 3.5 + frost_idx) + 1) / 2)
                
                frost_color = (150 + int(50 * glow_intensity), 255, 255, frost_alpha)
                frost_surface = pygame.Surface((frost_size * 2, frost_size * 2), pygame.SRCALPHA)
                pygame.draw.circle(frost_surface, frost_color, (frost_size, frost_size), frost_size)
                self.screen.blit(frost_surface, (frost_x - frost_size, frost_y - frost_size))
            
            if fridge_image:
                self.screen.blit(fridge_image, station_rect)
                
                shimmer_alpha = int(25 * glow_intensity)
                shimmer_surface = pygame.Surface(station_rect.size, pygame.SRCALPHA)
                shimmer_color = (100, 200, 255, shimmer_alpha)
                pygame.draw.rect(shimmer_surface, shimmer_color, shimmer_surface.get_rect(), border_radius=8)
                self.screen.blit(shimmer_surface, station_rect.topleft)
            else:
                for row in range(config.STATION_SIZE):
                    for col in range(config.STATION_SIZE):
                        rect = pygame.Rect((sx + col) * self.tile_size, (sy + row) * self.tile_size, self.tile_size, self.tile_size)
                        pygame.draw.rect(self.screen, (150, 255, 150, 100), rect) 
                        pygame.draw.rect(self.screen, (0, 200, 0), rect, 2) 
            
            font = self.assets.get_font('default_18')
            text_surface = font.render("Fridge", True, (255, 255, 255))
            text_rect = text_surface.get_rect(center=(
                (sx + config.STATION_SIZE/2) * self.tile_size, 
                (sy + config.STATION_SIZE - 0.2) * self.tile_size
            ))
            text_bg_rect = text_rect.inflate(6, 2)
            pygame.draw.rect(self.screen, (0, 0, 0, 120), text_bg_rect, border_radius=3)
            self.screen.blit(text_surface, text_rect)

    def _draw_doorprize_station(self, state_data):
        doorprize_station_pos = state_data.get("doorprize_station")
        if doorprize_station_pos:
            sx, sy = doorprize_station_pos
            doorprize_remaining_time = state_data.get("doorprize_remaining_time", 0)
            
            treasure_image = self.assets.get_image('treasure')
            
            station_rect = pygame.Rect(sx * self.tile_size, sy * self.tile_size, 
                                     config.STATION_SIZE * self.tile_size, 
                                     config.STATION_SIZE * self.tile_size)
            
            glow_time = time.time() * 3.0
            glow_intensity = (math.sin(glow_time) + 1) / 2  
            
            pulse_time = time.time() * 5  
            pulse_intensity = (math.sin(pulse_time) + 1) / 2
            
            urgency_multiplier = 1.0
            if doorprize_remaining_time < 5.0:  
                urgency_multiplier = 1.0 + (5.0 - doorprize_remaining_time) * 0.3
                glow_intensity = min(1.0, glow_intensity * urgency_multiplier)
            
            base_alpha = 35 + int(60 * glow_intensity)
            glow_colors = [
                (255, 215, 0, max(25, int(base_alpha * 0.6))),    
                (255, 140, 0, max(35, int(base_alpha * 0.8))),      
                (255, 255, 100, max(45, int(base_alpha * 1.0))), 
                (255, 255, 200, max(30, int(base_alpha * 0.7 * pulse_intensity))) 
            ]
            
            glow_offsets = [18, 14, 8, 4]  
            
            for glow_color, offset in zip(glow_colors, glow_offsets):
                glow_rect = station_rect.inflate(offset * 2, offset * 2)
                glow_surface = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                pygame.draw.rect(glow_surface, glow_color, glow_surface.get_rect(), border_radius=offset//2 + 6)
                self.screen.blit(glow_surface, glow_rect.topleft)
            
            sparkle_time = time.time() * 7 + sx + sy  
            for sparkle_idx in range(6): 
                angle = sparkle_time + sparkle_idx * (math.pi / 3)  
                sparkle_distance = 35 + 12 * math.sin(sparkle_time * 2.5)
                sparkle_x = station_rect.centerx + math.cos(angle) * sparkle_distance
                sparkle_y = station_rect.centery + math.sin(angle) * sparkle_distance
                
                sparkle_alpha = int(180 * (math.sin(sparkle_time * 4 + sparkle_idx) + 1) / 2)
                sparkle_size = 2 + int(3 * (math.sin(sparkle_time * 5 + sparkle_idx) + 1) / 2)
                
                sparkle_color = (255, 215 + int(40 * glow_intensity), 0, sparkle_alpha)
                sparkle_surface = pygame.Surface((sparkle_size * 2, sparkle_size * 2), pygame.SRCALPHA)
                pygame.draw.circle(sparkle_surface, sparkle_color, (sparkle_size, sparkle_size), sparkle_size)
                self.screen.blit(sparkle_surface, (sparkle_x - sparkle_size, sparkle_y - sparkle_size))
            
            if treasure_image:
                self.screen.blit(treasure_image, station_rect)
                
                shimmer_alpha = int(40 * glow_intensity)
                shimmer_surface = pygame.Surface(station_rect.size, pygame.SRCALPHA)
                shimmer_color = (255, 215, 0, shimmer_alpha)
                pygame.draw.rect(shimmer_surface, shimmer_color, shimmer_surface.get_rect(), border_radius=6)
                self.screen.blit(shimmer_surface, station_rect.topleft)
            else:
                for row in range(config.STATION_SIZE):
                    for col in range(config.STATION_SIZE):
                        rect = pygame.Rect((sx + col) * self.tile_size, (sy + row) * self.tile_size, self.tile_size, self.tile_size)
                        fill_color = (200, 100, 255, 150)
                        border_color = (150, 0, 200)
                        
                        if doorprize_remaining_time < 1.0:
                            blink_alpha = int(150 * (doorprize_remaining_time * 2 % 1)) + 50
                            fill_color = (200, 100, 255, blink_alpha)
                        
                        pygame.draw.rect(self.screen, fill_color, rect)
                        pygame.draw.rect(self.screen, border_color, rect, 2)
            
            # Draw "Doorprize!" text
            font = self.assets.get_font('default_18')
            text_surface = font.render("Doorprize!", True, (255, 255, 255))
            text_rect = text_surface.get_rect(center=(
                (sx + config.STATION_SIZE/2) * self.tile_size, 
                (sy + config.STATION_SIZE - 0.2) * self.tile_size
            ))
            text_bg_rect = text_rect.inflate(6, 2)
            pygame.draw.rect(self.screen, (0, 0, 0, 120), text_bg_rect, border_radius=3)
            self.screen.blit(text_surface, text_rect)

            # Draw remaining time
            timer_font = self.assets.get_font('default_18')
            timer_text_surface = timer_font.render(f"{doorprize_remaining_time:.1f}s", True, (255, 255, 0))
            timer_text_rect = timer_text_surface.get_rect(center=(
                (sx + config.STATION_SIZE/2) * self.tile_size, 
                (sy + config.STATION_SIZE + 0.3) * self.tile_size
            ))
            timer_bg_rect = timer_text_rect.inflate(6, 2)
            pygame.draw.rect(self.screen, (0, 0, 0, 120), timer_bg_rect, border_radius=3)
            self.screen.blit(timer_text_surface, timer_text_rect)


    def _draw_player(self, player_id, player_data, local_client_id):
        target_x, target_y = player_data["pos"]
        current_x, current_y = self.interpolated_player_positions.get(player_id, (target_x, target_y))
        
        interpolated_x = current_x + (target_x - current_x) * 0.5
        interpolated_y = current_y + (target_y - current_y) * 0.5
        self.interpolated_player_positions[player_id] = (interpolated_x, interpolated_y)
        
        rect = pygame.Rect(interpolated_x * self.tile_size, interpolated_y * self.tile_size, self.tile_size, self.tile_size)
        
        ingredient_name = player_data["ingredient"]
        glow_colors = self._get_ingredient_glow_colors(ingredient_name)
        
        glow_time = time.time() * 3.0 + hash(player_id) % 100  
        glow_intensity = (math.sin(glow_time) + 1) / 2
        
        pulse_time = time.time() * 4.5 + hash(player_id) % 50
        pulse_intensity = (math.sin(pulse_time) + 1) / 2
        
        base_alpha = 25 + int(35 * glow_intensity)
        glow_offsets = [12, 8, 4] 
        
        for i, offset in enumerate(glow_offsets):
            glow_rect = rect.inflate(offset * 2, offset * 2)
            glow_surface = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
            
            alpha_multiplier = (1.0 - i * 0.2) * (0.6 + 0.4 * pulse_intensity)
            glow_color = (*glow_colors[i % len(glow_colors)][:3], max(15, int(base_alpha * alpha_multiplier)))
            
            pygame.draw.ellipse(glow_surface, glow_color, glow_surface.get_rect())
            self.screen.blit(glow_surface, glow_rect.topleft)
        
        sparkle_time = time.time() * 5 + hash(player_id) % 30
        for sparkle_idx in range(3):  
            angle = sparkle_time + sparkle_idx * (math.pi * 2 / 3)
            sparkle_distance = 15 + 5 * math.sin(sparkle_time * 2)
            sparkle_x = rect.centerx + math.cos(angle) * sparkle_distance
            sparkle_y = rect.centery + math.sin(angle) * sparkle_distance
            
            sparkle_alpha = int(120 * (math.sin(sparkle_time * 3 + sparkle_idx) + 1) / 2)
            sparkle_size = 1 + int(2 * (math.sin(sparkle_time * 4 + sparkle_idx) + 1) / 2)
            
            sparkle_color = (*glow_colors[0][:3], sparkle_alpha)
            sparkle_surface = pygame.Surface((sparkle_size * 2, sparkle_size * 2), pygame.SRCALPHA)
            pygame.draw.circle(sparkle_surface, sparkle_color, (sparkle_size, sparkle_size), sparkle_size)
            self.screen.blit(sparkle_surface, (sparkle_x - sparkle_size, sparkle_y - sparkle_size))
        
        sprite = self.assets.get_sprite(ingredient_name)
        if sprite:
            sprite_rect = sprite.get_rect(center=rect.center)
            self.screen.blit(sprite, sprite_rect)
            
            shimmer_alpha = int(20 * glow_intensity)
            shimmer_surface = pygame.Surface(sprite_rect.size, pygame.SRCALPHA)
            shimmer_color = (*glow_colors[0][:3], shimmer_alpha)
            pygame.draw.rect(shimmer_surface, shimmer_color, shimmer_surface.get_rect(), border_radius=4)
            self.screen.blit(shimmer_surface, sprite_rect.topleft)
        else:
            #  print(f"[WARNING] Sprite for ingredient '{ingredient_name}' not found.")
            pygame.draw.rect(self.screen, (200, 100, 100), rect) 
        
        if player_id == local_client_id:
            border_glow_alpha = int(100 + 50 * glow_intensity)
            border_color = (0, 150, 255, border_glow_alpha)
            border_surface = pygame.Surface((rect.width + 6, rect.height + 6), pygame.SRCALPHA)
            pygame.draw.rect(border_surface, border_color, border_surface.get_rect(), 3, border_radius=3)
            self.screen.blit(border_surface, (rect.x - 3, rect.y - 3))
        else:
            pygame.draw.rect(self.screen, (0, 200, 0, 150), rect, 2)
        
        font = self.assets.get_font('default_18')
        text_surface = font.render(ingredient_name, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=(rect.centerx, rect.bottom + 10))
        
        text_bg_rect = text_rect.inflate(8, 4)
        text_bg_color = (*glow_colors[0][:3], 80)
        text_bg_surface = pygame.Surface((text_bg_rect.width, text_bg_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(text_bg_surface, text_bg_color, text_bg_surface.get_rect(), border_radius=4)
        self.screen.blit(text_bg_surface, text_bg_rect.topleft)
        self.screen.blit(text_surface, text_rect)

    def _get_ingredient_glow_colors(self, ingredient_name):
        """Return ingredient-specific glow colors for visual variety"""
        ingredient_colors = {
            'Rice': [(255, 255, 200), (255, 245, 150), (255, 235, 100)],         # Warm white/yellow
            'Salmon': [(255, 150, 120), (255, 100, 80), (255, 80, 60)],          # Salmon pink/orange
            'Tuna': [(200, 100, 150), (180, 80, 120), (160, 60, 100)],           # Deep red/pink
            'Shrimp': [(255, 180, 150), (255, 160, 120), (255, 140, 100)],       # Light orange/pink
            'Egg': [(255, 255, 150), (255, 240, 100), (255, 220, 80)],           # Bright yellow
            'Seaweed': [(100, 200, 150), (80, 180, 120), (60, 160, 100)],        # Green
            'Cucumber': [(150, 255, 150), (120, 240, 120), (100, 220, 100)],     # Bright green
            'Avocado': [(180, 220, 100), (160, 200, 80), (140, 180, 60)],        # Yellow-green
            'Crab Meat': [(255, 200, 150), (255, 180, 120), (255, 160, 100)],    # Light orange
            'Eel': [(120, 100, 80), (140, 120, 100), (160, 140, 120)],           # Brown
            'Cream Cheese': [(255, 255, 240), (250, 250, 220), (245, 245, 200)], # Cream white
            'Fish Roe': [(255, 180, 100), (255, 160, 80), (255, 140, 60)]        # Orange
        }
        
        return ingredient_colors.get(ingredient_name, [
            (255, 215, 0), (255, 180, 0), (255, 140, 0)  
        ])

    def _draw_almanac(self):
        """Draw the almanac overlay with game information"""
        overlay = pygame.Surface((self.screen_width, self.screen_height))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))
        
        almanac_width = min(800, self.screen_width - 60)
        almanac_height = min(600, self.screen_height - 60)
        almanac_rect = pygame.Rect(0, 0, almanac_width, almanac_height)
        almanac_rect.center = (self.screen_width // 2, self.screen_height // 2)
        
        pygame.draw.rect(self.screen, (40, 40, 60), almanac_rect, border_radius=15)
        pygame.draw.rect(self.screen, (200, 200, 200), almanac_rect, 3, border_radius=15)
        
        title_font = self.assets.get_font('default_48')
        title_text = title_font.render("FOLLOW THE RADIANT PATH TO VICTORY!", True, (255, 255, 255))
        title_rect = title_text.get_rect(centerx=almanac_rect.centerx, top=almanac_rect.top + 20)
        self.screen.blit(title_text, title_rect)
        
        close_button_size = 30
        close_x = almanac_rect.right - close_button_size - 10
        close_y = almanac_rect.top + 10
        self.ui_rects['almanac_close'] = pygame.Rect(close_x, close_y, close_button_size, close_button_size)
        pygame.draw.rect(self.screen, (200, 50, 50), self.ui_rects['almanac_close'], border_radius=5)
        close_font = self.assets.get_font('default_24')
        close_text = close_font.render("X", True, (255, 255, 255))
        close_text_rect = close_text.get_rect(center=self.ui_rects['almanac_close'].center)
        self.screen.blit(close_text, close_text_rect)
        
        content_y = title_rect.bottom + 20
        content_height = almanac_rect.bottom - content_y - 20
        
        self._draw_almanac_stations(almanac_rect, content_y, content_height // 2)
        
        ingredients_y = content_y + content_height // 2
        self._draw_almanac_ingredients(almanac_rect, ingredients_y, content_height // 2)

    def _draw_almanac_stations(self, almanac_rect, start_y, height):
        """Draw the stations section of the almanac"""
        section_font = self.assets.get_font('default_32')
        desc_font = self.assets.get_font('default_18')
        
        stations_title = section_font.render("Stations", True, (255, 255, 100))
        stations_title_rect = stations_title.get_rect(centerx=almanac_rect.centerx, top=start_y)
        self.screen.blit(stations_title, stations_title_rect)
        
        stations_data = [
            {
                'name': 'Fusion Stations',
                'image': 'stove',
                'description': 'Combine ingredients to create recipes.\nStand near with required ingredient.'
            },
            {
                'name': 'Fridge Station', 
                'image': 'fridge',
                'description': 'Change your current ingredient.\nPress ENTER when standing on it.'
            },
            {
                'name': 'Doorprize Station',
                'image': 'treasure', 
                'description': 'Collect bonus points when it appears.\nLimited time, hurry!'
            }
        ]
        
        station_y = stations_title_rect.bottom + 10
        station_width = (almanac_rect.width - 60) // 3
        station_height = height - 40
        
        for i, station in enumerate(stations_data):
            station_x = almanac_rect.left + 20 + i * (station_width + 10)
            station_rect = pygame.Rect(station_x, station_y, station_width, station_height)
            
            pygame.draw.rect(self.screen, (60, 60, 80), station_rect, border_radius=8)
            pygame.draw.rect(self.screen, (150, 150, 150), station_rect, 2, border_radius=8)
            
            station_image = self.assets.get_image(station['image'])
            if station_image:
                image_size = min(station_width - 20, 60)
                scaled_image = pygame.transform.scale(station_image, (image_size, image_size))
                image_rect = scaled_image.get_rect(centerx=station_rect.centerx, top=station_rect.top + 10)
                self.screen.blit(scaled_image, image_rect)
                text_start_y = image_rect.bottom + 10
            else:
                text_start_y = station_rect.top + 10
            
            name_text = self.assets.get_font('default_24').render(station['name'], True, (255, 255, 255))
            name_rect = name_text.get_rect(centerx=station_rect.centerx, top=text_start_y)
            self.screen.blit(name_text, name_rect)
            
            desc_lines = station['description'].split('\n')
            line_y = name_rect.bottom + 8
            for line in desc_lines:
                if line_y + 20 < station_rect.bottom:
                    line_text = desc_font.render(line, True, (200, 200, 200))
                    line_rect = line_text.get_rect(centerx=station_rect.centerx, top=line_y)
                    self.screen.blit(line_text, line_rect)
                    line_y += 22

    def _draw_almanac_ingredients(self, almanac_rect, start_y, height):
        """Draw the ingredients section of the almanac"""
        section_font = self.assets.get_font('default_32')
        
        ingredients_title = section_font.render("Available Ingredients", True, (255, 255, 100))
        ingredients_title_rect = ingredients_title.get_rect(centerx=almanac_rect.centerx, top=start_y)
        self.screen.blit(ingredients_title, ingredients_title_rect)
        
        content_start_y = ingredients_title_rect.bottom + 10
        content_height = height - (content_start_y - start_y) - 20
        
        ingredients_rect = pygame.Rect(almanac_rect.left + 10, content_start_y, almanac_rect.width - 20, content_height)
        pygame.draw.rect(self.screen, (50, 50, 70), ingredients_rect, border_radius=8)
        pygame.draw.rect(self.screen, (120, 120, 120), ingredients_rect, 1, border_radius=8)
        
        ingredients = [
            'Rice', 'Salmon', 'Tuna', 'Shrimp', 'Egg', 'Seaweed',
            'Cucumber', 'Avocado', 'Crab Meat', 'Eel', 'Cream Cheese', 'Fish Roe'
        ]
        
        grid_start_y = ingredients_rect.top + 10
        grid_available_height = ingredients_rect.height - 20
        
        cols = 6 
        rows = 2
        item_width = (ingredients_rect.width - 20) // cols
        item_height = grid_available_height // rows
        
        for i, ingredient in enumerate(ingredients):
            if i >= cols * rows:
                break
                
            col = i % cols
            row = i // cols
            
            item_x = ingredients_rect.left + 10 + col * item_width
            item_y = grid_start_y + row * item_height
            item_rect = pygame.Rect(item_x, item_y, item_width - 5, item_height - 5)
            
            glow_colors = self._get_ingredient_glow_colors(ingredient)
            bg_color = (*glow_colors[0][:3], 30)
            item_bg = pygame.Surface((item_rect.width, item_rect.height), pygame.SRCALPHA)
            pygame.draw.rect(item_bg, bg_color, item_bg.get_rect(), border_radius=5)
            self.screen.blit(item_bg, item_rect.topleft)
            pygame.draw.rect(self.screen, glow_colors[0][:3], item_rect, 1, border_radius=5)
            
            sprite = self.assets.get_sprite(ingredient)
            if sprite:
                sprite_size = min(item_width - 20, item_height - 25, 40) 
                scaled_sprite = pygame.transform.scale(sprite, (sprite_size, sprite_size))
                sprite_rect = scaled_sprite.get_rect(centerx=item_rect.centerx, top=item_rect.top + 5)
                self.screen.blit(scaled_sprite, sprite_rect)
                text_y = sprite_rect.bottom + 3
            else:
                text_y = item_rect.top + 10
            
            name_font = self.assets.get_font('default_18')
            name_text = name_font.render(ingredient, True, (255, 255, 255))
            name_rect = name_text.get_rect(centerx=item_rect.centerx, top=text_y)
            self.screen.blit(name_text, name_rect)

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
            orders_bg_rect = pygame.Rect(10, 10, 280, len(state_data["orders"][:3]) * 25 + 30) 
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
                
                order_text_surface = order_font.render(display_text, True, (255, 255, 0)) 
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
            
            total_players = len(game_manager.current_state["clients_info"])
            list_height = 50 + (total_players * 30) + 20 
            list_width = 400
            
            list_bg_rect = pygame.Rect(0, 0, list_width, list_height)
            list_bg_rect.center = (self.screen_width // 2, y_offset + (list_height // 2) - 25)
            list_bg_surface = pygame.Surface((list_bg_rect.width, list_bg_rect.height))
            list_bg_surface.set_alpha(128) 
            list_bg_surface.fill((0, 0, 0))  
            self.screen.blit(list_bg_surface, list_bg_rect)
            
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
        
        self.ui_rects['almanac_button'] = self._draw_button((self.screen_width // 2, self.screen_height * 3 // 4 + 70), "Almanac", (150, 40))
        
        if self.show_almanac:
            self._draw_almanac()
        
    def draw_end_screen(self, game_manager):
        from src.shared import config
        
        final_score = game_manager.final_score
        is_win = final_score >= config.WIN_SCORE_THRESHOLD
        
        if is_win:
            bg_image = self.assets.get_image('end_win_bg')
            if not bg_image:
                bg_image = self.assets.get_image('end_bg')  
        else:
            bg_image = self.assets.get_image('end_lose_bg')
            if not bg_image:
                bg_image = self.assets.get_image('end_bg') 
        

        if bg_image:
            scaled_bg = pygame.transform.scale(bg_image, (self.screen_width, self.screen_height))
            self.screen.blit(scaled_bg, (0, 0))
        else:
            fallback_color = (50, 100, 50) if is_win else (100, 50, 50) 
            self.screen.fill(fallback_color)
        
        overlay_surface = pygame.Surface((self.screen_width, 200))
        overlay_surface.set_alpha(128)  
        overlay_surface.fill((0, 0, 0))
        overlay_rect = overlay_surface.get_rect(center=(self.screen_width // 2, self.screen_height // 2))
        self.screen.blit(overlay_surface, overlay_rect)
        
        result_y_pos = self.screen_height * 0.35
        result_font = self.assets.get_font('default_72')
        if is_win:
            result_text = "MISSION COMPLETED!"
            result_color = (255, 215, 0) 
        else:
            result_text = "MISSION FAILED!"
            result_color = (255, 100, 100)  
        
        result_surface = result_font.render(result_text, True, result_color)
        result_rect = result_surface.get_rect(center=(self.screen_width // 2, result_y_pos))
        self.screen.blit(result_surface, result_rect)
        
        score_y_pos = self.screen_height * 0.50
        score_font = self.assets.get_font('default_48')
        if score_font:
            score_text_surface = score_font.render(f"Final Score: {final_score:,}", True, (255, 255, 255))
            score_rect = score_text_surface.get_rect(center=(self.screen_width // 2, score_y_pos))
            self.screen.blit(score_text_surface, score_rect)
        
        threshold_y_pos = self.screen_height * 0.58
        threshold_font = self.assets.get_font('default_28')
        threshold_text = f"Target: {config.WIN_SCORE_THRESHOLD:,}"
        threshold_color = (200, 200, 200)
        threshold_surface = threshold_font.render(threshold_text, True, threshold_color)
        threshold_rect = threshold_surface.get_rect(center=(self.screen_width // 2, threshold_y_pos))
        self.screen.blit(threshold_surface, threshold_rect)

        button_y_pos = self.screen_height * 0.75
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