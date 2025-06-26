from src.shared import config
from src.shared.recipe_manager import recipe_manager
import random

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
        self.single_player_ingredients = [
            'Salmon', 'Tuna', 'Shrimp', 'Crab Meat', "Eel"
        ]

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

        # Check boundaries
        final_x = max(0, min(new_x, config.GRID_WIDTH - 1))
        final_y = max(0, min(new_y, config.GRID_HEIGHT - 1))

        # Update position
        p.pos = (final_x, final_y)
        
        # Check for single player bottom grid collision
        if len(self.players) == 1 and final_y == config.GRID_HEIGHT - 1:
            return self.check_single_player_merge(player_id)
        
        return None

    def check_single_player_merge(self, player_id):
        """Special merge handling for single player mode when hitting bottom grid"""
        player = self.players[player_id]
        
        current_ingredient = player.ingredient
        ingredients_list = [current_ingredient, current_ingredient]
        
        result = recipe_manager.check_merge(ingredients_list)
        print(f"Checking single player merge for {ingredients_list}: {result}")
        
        if result:
            self.score += result["price"]
            print(f"Single player fusion: {current_ingredient} = {result['name']} served! +{result['price']} points")
            
            player.ingredient = random.choice(self.single_player_ingredients)
            
            player.pos = (random.randint(0, config.GRID_WIDTH - 1), 0)
            
            return {"fusion": result, "pos": player.pos, "single_player": True}
        
        return None

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
                    print(f"Fusion at {pos}: {result['name']} served! +{result['price']} points")
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
