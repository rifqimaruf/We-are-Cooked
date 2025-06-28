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
                name_without_ext = os.path.splitext(filename)[0]
                
                # Normalisasi nama untuk konsistensi
                # Jika nama file di disk adalah "CoinPlus.mp3", maka name_without_ext akan jadi "CoinPlus"
                # Jika nama file di disk adalah "splash sound.mp3", name_without_ext akan jadi "splash sound"
                # Kita akan menggunakan nama ini sebagai kunci utama di dictionary self.sounds

                # Anda bisa menambahkan normalisasi khusus jika ada perbedaan nama yang sering terjadi
                if name_without_ext.lower() == "succes order":
                    key_name = "Success Order"
                elif name_without_ext.lower() == "coinplus":
                    key_name = "CoinPlus"
                elif name_without_ext.lower() == "splash sound":
                    key_name = "Splash Sound"
                elif name_without_ext.lower() == "realisticwatersplash": # Asumsi ini nama untuk SFX baru Anda
                    key_name = "RealisticWaterSplash"
                else:
                    key_name = name_without_ext # Gunakan nama asli jika tidak ada normalisasi khusus
                
                try:
                    self.sounds[key_name] = pygame.mixer.Sound(os.path.join(self.sfx_path, filename))
                    print(f"Loaded SFX: '{key_name}' from file '{filename}'") # Debugging: Konfirmasi suara yang dimuat
                except pygame.error as e:
                    print(f"Error loading sound '{filename}': {e}")
        print(f"Finished loading {len(self.sounds)} SFX.") # Debugging: Jumlah SFX yang dimuat

    def play_sfx(self, name: str, volume: float = 0.5):
        if not self.enabled:
            return
        
        sound = self.sounds.get(name) # Coba cari dengan nama persis yang diminta

        # Jika tidak ditemukan, coba cari dengan nama yang mungkin dinormalisasi (opsional, tapi bisa membantu)
        if sound is None:
            if name.lower() == "success order":
                sound = self.sounds.get("Success Order")
            elif name.lower() == "coinplus":
                sound = self.sounds.get("CoinPlus")
            # Tambahkan logika pencarian untuk RealisticWaterSplash jika itu masalah kapitalisasi/penamaan
            elif name.lower() == "realisticwatersplash" or name.lower() == "splash sound":
                sound = self.sounds.get("RealisticWaterSplash") or self.sounds.get("Splash Sound")


        if sound:
            sound.set_volume(volume)
            sound.play()
            # print(f"DEBUG: Played SFX '{name}'") # Debugging: Konfirmasi suara diputar
        else:
            print(f"Warning: SFX '{name}' not found in loaded sounds. Available sounds: {list(self.sounds.keys())}") # Debugging: Daftar suara yang tersedia
            

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