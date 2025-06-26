from src.shared import config
from src.shared.recipe_manager import recipe_manager

class PlayerState:
    def __init__(self, player_id, ingredient, pos):
        self.player_id = player_id
        self.ingredient = ingredient
        self.pos = pos # Posisi aktual pemain (bisa float)
        self.target_pos = pos # Posisi tujuan pemain (jika sedang bergerak)

class GameState:
    def __init__(self):
        self.players = {} 
        self.orders = [recipe_manager.get_random_order() for _ in range(3)]
        self.score = 0
        self.timer = config.GAME_TIMER_SECONDS

    def add_player(self, player_id, ingredient, pos):
        self.players[player_id] = PlayerState(player_id, ingredient, pos)

    def move_player(self, player_id, direction):
        p = self.players[player_id]
        x, y = p.pos # Ambil posisi float saat ini

        # Hitung posisi baru berdasarkan kecepatan
        new_x, new_y = x, y
        if direction == "UP":
            new_y -= config.PLAYER_SPEED
        elif direction == "DOWN":
            new_y += config.PLAYER_SPEED
        elif direction == "LEFT":
            new_x -= config.PLAYER_SPEED
        elif direction == "RIGHT":
            new_x += config.PLAYER_SPEED
        # Hapus baris 'p.pos = (x, y)' yang tidak perlu jika ada di bawah 'elif "RIGHT"':
        # p.pos = (x, y) # Ini tidak diperlukan lagi

        # Cek batas maksimum grid
        # Gunakan int() untuk memastikan perbandingan dengan batas grid yang integer
        final_x = max(0.0, min(new_x, float(config.GRID_WIDTH - 1)))
        final_y = max(0.0, min(new_y, float(config.GRID_HEIGHT - 1)))

        # Perbarui nilai posisi pemain (tetap float)
        p.pos = (final_x, final_y)
        # target_pos akan sama dengan pos karena klien akan menginterpolasi
        # dari posisi lama ke posisi baru yang diterima dari server
        p.target_pos = (final_x, final_y) # Update target_pos juga

    def check_for_merge(self):
        positions = {}
        for p in self.players.values():
            positions.setdefault(p.pos, []).append(p)

        for pos, plist in positions.items():
            if len(plist) > 1:
                ingredients = [p.ingredient for p in plist]
                result = recipe_manager.check_merge(ingredients)
                if result:
                    self.score += result["price"]
                    print(f"Fusion at {pos}: {result['name']} served! +{result['price']} cuan")
                    return {"fusion": result, "pos": pos}
        return None

    def to_dict(self):
        return {
            "players": {pid: {"ingredient": p.ingredient, "pos": p.pos, "target_pos": p.target_pos} for pid, p in self.players.items()},
            "orders": self.orders,
            "score": self.score,
            "timer": self.timer
        }

    def remove_player(self, player_id):
        if player_id in self.players:
            del self.players[player_id]
