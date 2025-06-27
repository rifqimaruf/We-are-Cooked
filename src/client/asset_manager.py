import pygame
import os
from .visual_assets import SoundManager

class AssetManager:
    def __init__(self, base_path: str, tile_size: int):
        self.base_path = base_path
        self.tile_size = tile_size
        self.sound_manager = SoundManager(self.base_path)
        self.sprites = {}
        self.images = {}
        self.fonts = {}

    def load_all(self):
        print("--- Loading All Assets ---")
        self._load_sounds()
        self._load_sprites()
        self._load_images()
        self._load_fonts()
        print("--- All Assets Loaded ---")

    def _load_sounds(self):
        self.sound_manager.load_sounds()

    def _load_sprites(self):
        sprite_path = os.path.join(self.base_path, 'sprites', 'ingredients')
        if not os.path.isdir(sprite_path):
            print(f"Warning: Sprite directory not found: {sprite_path}")
            return
        ingredients = [
            'Rice', 'Salmon', 'Tuna', 'Shrimp', 'Egg', 'Seaweed',
            'Cucumber', 'Avocado', 'Crab Meat', 'Eel', 'Cream Cheese', 'Fish Roe'
        ]
        sprite_dims = (int(self.tile_size * 0.8), int(self.tile_size * 0.8))
        for ingredient in ingredients:
            try:
                filename = ingredient.lower().replace(' ', '_') + '.png'
                path = os.path.join(sprite_path, filename)
                if os.path.exists(path):
                    sprite = pygame.image.load(path).convert_alpha()
                    self.sprites[ingredient] = pygame.transform.scale(sprite, sprite_dims)
                else:
                    self.sprites[ingredient] = None
            except pygame.error as e:
                print(f"Error loading sprite for {ingredient}: {e}")

    def _load_images(self):
        try:
            end_bg_path = os.path.join(self.base_path, 'images', 'end_bg.png')
            if os.path.exists(end_bg_path):
                self.images['end_bg'] = pygame.image.load(end_bg_path).convert()
                print(f"Loaded background: end_bg.png")
            else:
                self.images['end_bg'] = None
        except pygame.error as e:
            print(f"Warning: Could not load end_bg.png: {e}")
            self.images['end_bg'] = None
        
        try:
            start_bg_path = os.path.join(self.base_path, 'images', 'start.jpg')
            if os.path.exists(start_bg_path):
                self.images['start_bg'] = pygame.image.load(start_bg_path).convert()
                print(f"Loaded background: start.jpg")
            else:
                self.images['start_bg'] = None
                print(f"Warning: start.jpg not found at {start_bg_path}")
        except pygame.error as e:
            print(f"Warning: Could not load start.jpg: {e}")
            self.images['start_bg'] = None
        
        try:
            game_bg_path = os.path.join(self.base_path, 'images', 'game_bg.png')
            if os.path.exists(game_bg_path):
                self.images['game_bg'] = pygame.image.load(game_bg_path).convert()
                print(f"Loaded background: game_bg.png")
            else:
                self.images['game_bg'] = None
        except pygame.error as e:
            self.images['game_bg'] = None

    def _load_fonts(self):
        self.fonts['default_72'] = pygame.font.SysFont(None, 72)
        self.fonts['default_48'] = pygame.font.SysFont(None, 48)
        self.fonts['default_36'] = pygame.font.SysFont(None, 36)
        self.fonts['default_32'] = pygame.font.SysFont(None, 32)
        self.fonts['default_28'] = pygame.font.SysFont(None, 28)
        self.fonts['default_24'] = pygame.font.SysFont(None, 24)
        self.fonts['default_18'] = pygame.font.SysFont(None, 18)

    def get_sprite(self, name):
        return self.sprites.get(name)

    def get_image(self, name):
        return self.images.get(name)

    def get_font(self, name):
        return self.fonts.get(name)