from src.shared import config
from src.shared.recipe_manager import recipe_manager

class PlayerState:
    def __init__(self, player_id, ingredient, pos):
        self.player_id = player_id
        self.ingredient = ingredient
        self.pos = pos 

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
        x, y = p.pos

        new_x, new_y = x, y
        if direction == "UP":
            new_y -= config.PLAYER_SPEED
        elif direction == "DOWN":
            new_y += config.PLAYER_SPEED
        elif direction == "LEFT":
            new_x -= config.PLAYER_SPEED
        elif direction == "RIGHT":
            new_x += config.PLAYER_SPEED
            p.pos = (x, y)

        # cek batas maks
        final_x = max (0, min(new_x, config.GRID_WIDTH - 1))
        final_y = max (0, min(new_y, config.GRID_HEIGHT -1))

        # perbarui nilai posisi
        p.pos = (final_x, final_y)

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
            "players": {pid: {"ingredient": p.ingredient, "pos": p.pos} for pid, p in self.players.items()},
            "orders": self.orders,
            "score": self.score,
            "timer": self.timer
        }

    def remove_player(self, player_id):
        if player_id in self.players:
            del self.players[player_id]
