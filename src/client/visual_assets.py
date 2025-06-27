# src/client/visual_assets.py
import pygame
import os

class SoundManager:
    def __init__(self, assets_path: str):
        self.sounds = {}
        self.enabled = True
        self.sfx_path = os.path.join(assets_path, 'sounds', 'sfx')
        self.music_path = os.path.join(assets_path, 'sounds', 'music')
        self.current_music = None

    def load_sounds(self):
        if not os.path.isdir(self.sfx_path):
            print(f"Warning: SFX directory not found: {self.sfx_path}")
            return
        print(f"Loading SFX from: {self.sfx_path}")
        for filename in os.listdir(self.sfx_path):
            if filename.endswith(('.mp3', '.wav', '.ogg')):
                name = os.path.splitext(filename)[0]
                if name.lower() == "succes order":
                    name = "Success Order"
                try:
                    self.sounds[name] = pygame.mixer.Sound(os.path.join(self.sfx_path, filename))
                except pygame.error as e:
                    print(f"Error loading sound {filename}: {e}")

    def play_sfx(self, name: str, volume: float = 0.5):
        if not self.enabled:
            return
        sound = self.sounds.get(name) or self.sounds.get(name.replace("Success", "Succes")) 
        if sound:
            sound.set_volume(volume)
            sound.play()
        else:
            print(f"Warning: SFX '{name}' not found.")

    def play_music(self, filename: str, loops: int = -1, volume: float = 0.4):
        if not self.enabled or self.current_music == filename:
            return
        self.stop_music()
        music_file_path = os.path.join(self.music_path, filename)
        if os.path.exists(music_file_path):
            try:
                pygame.mixer.music.load(music_file_path)
                pygame.mixer.music.set_volume(volume)
                pygame.mixer.music.play(loops)
                self.current_music = filename
            except pygame.error as e:
                print(f"Error playing music {filename}: {e}")
        else:
            print(f"Warning: Music file not found: {music_file_path}")

    def stop_music(self):
        if self.current_music:
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
            self.current_music = None