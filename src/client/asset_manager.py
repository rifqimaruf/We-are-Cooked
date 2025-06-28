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
                filename = ingredient.replace(' ', '') + '.png'
                path = os.path.join(sprite_path, filename)
                print(f"Loading sprite for {ingredient} from {path}")
                if os.path.exists(path):
                    sprite = pygame.image.load(path).convert_alpha()
                    self.sprites[ingredient] = pygame.transform.scale(sprite, sprite_dims)
                else:
                    self.sprites[ingredient] = None
            except pygame.error as e:
                print(f"Error loading sprite for {ingredient}: {e}")
        print(f"Loaded {len(self.sprites)} ingredient sprites.")

    def _load_images(self):
        try:
            start_jpg_path = os.path.join(self.base_path, 'images', 'start.jpg')
            if os.path.exists(start_jpg_path):
                start_image = pygame.image.load(start_jpg_path).convert()
                self.images['start_bg'] = start_image
                self.images['end_bg'] = start_image  
                print(f"Loaded background: start.jpg (used for start and default end screens)")
            else:
                self.images['start_bg'] = None
                self.images['end_bg'] = None
                print(f"Warning: start.jpg not found at {start_jpg_path}")
        except pygame.error as e:
            print(f"Warning: Could not load start.jpg: {e}")
            self.images['start_bg'] = None
            self.images['end_bg'] = None
        
        try:
            win_bg_path = os.path.join(self.base_path, 'images', 'end_win.jpg')
            if os.path.exists(win_bg_path):
                self.images['end_win_bg'] = pygame.image.load(win_bg_path).convert()
                print(f"Loaded background: end_win.jpg")
            else:
                self.images['end_win_bg'] = None
                print(f"Info: end_win.jpg not found - will use fallback for win screen")
        except pygame.error as e:
            print(f"Warning: Could not load end_win.jpg: {e}")
            self.images['end_win_bg'] = None
        
        try:
            lose_bg_path = os.path.join(self.base_path, 'images', 'end_lose.jpg')
            if os.path.exists(lose_bg_path):
                self.images['end_lose_bg'] = pygame.image.load(lose_bg_path).convert()
                print(f"Loaded background: end_lose.jpg")
            else:
                self.images['end_lose_bg'] = None
                print(f"Info: end_lose.jpg not found - will use fallback for lose screen")
        except pygame.error as e:
            print(f"Warning: Could not load end_lose.jpg: {e}")
            self.images['end_lose_bg'] = None
        
        try:
            game_bg_path = os.path.join(self.base_path, 'images', 'game_bg.png')
            if os.path.exists(game_bg_path):
                self.images['game_bg'] = pygame.image.load(game_bg_path).convert()
                print(f"Loaded background: game_bg.png")
            else:
                self.images['game_bg'] = None
        except pygame.error as e:
            self.images['game_bg'] = None
        
        try:
            stove_path = os.path.join(self.base_path, 'images', 'stove.png')
            if os.path.exists(stove_path):
                stove_image = pygame.image.load(stove_path).convert_alpha()
                stove_size = (self.tile_size * 2, self.tile_size * 2)
                self.images['stove'] = pygame.transform.scale(stove_image, stove_size)
                print(f"Loaded station image: stove.png")
            else:
                self.images['stove'] = None
                print(f"Warning: stove.png not found at {stove_path}")
        except pygame.error as e:
            print(f"Warning: Could not load stove.png: {e}")
            self.images['stove'] = None
        
        try:
            treasure_path = os.path.join(self.base_path, 'images', 'treasure.png')
            if os.path.exists(treasure_path):
                treasure_image = pygame.image.load(treasure_path).convert_alpha()
                treasure_size = (self.tile_size * 2, self.tile_size * 2)
                self.images['treasure'] = pygame.transform.scale(treasure_image, treasure_size)
                print(f"Loaded station image: treasure.png")
            else:
                self.images['treasure'] = None
                print(f"Warning: treasure.png not found at {treasure_path}")
        except pygame.error as e:
            print(f"Warning: Could not load treasure.png: {e}")
            self.images['treasure'] = None
        
        try:
            fridge_path = os.path.join(self.base_path, 'images', 'fridge.png')
            if os.path.exists(fridge_path):
                fridge_image = pygame.image.load(fridge_path).convert_alpha()
                fridge_size = (self.tile_size * 2, self.tile_size * 2)
                self.images['fridge'] = pygame.transform.scale(fridge_image, fridge_size)
                print(f"Loaded station image: fridge.png")
            else:
                self.images['fridge'] = None
                print(f"Warning: fridge.png not found at {fridge_path}")
        except pygame.error as e:
            print(f"Warning: Could not load fridge.png: {e}")
            self.images['fridge'] = None

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