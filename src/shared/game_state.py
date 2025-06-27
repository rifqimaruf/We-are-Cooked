# src/shared/game_state.py
import random
from . import config
from .recipe_manager import RecipeManager
import threading

class PlayerState:
    def __init__(self, player_id, ingredient, pos):
        self.player_id = player_id
        self.ingredient = ingredient
        self.pos = pos
        self.target_pos = pos

class GameState:
    def __init__(self):
        self.players = {}
        self.orders = []
        self.score = 0
        self.timer = config.GAME_TIMER_SECONDS
        self.recipe_manager = RecipeManager()
        self.clients_info = {}
        self._lock = threading.Lock()

    def add_player(self, player_id, ingredient, pos):
        with self._lock:
            self.players[player_id] = PlayerState(player_id, ingredient, pos)

    def remove_player(self, player_id):
        with self._lock:
            if player_id in self.players:
                del self.players[player_id]

    def move_player(self, player_id, direction):
        with self._lock:
            if player_id not in self.players: return
            p = self.players[player_id]
            x, y = p.pos
            new_x, new_y = x, y
            if direction == "UP": new_y -= config.PLAYER_SPEED
            elif direction == "DOWN": new_y += config.PLAYER_SPEED
            elif direction == "LEFT": new_x -= config.PLAYER_SPEED
            elif direction == "RIGHT": new_x += config.PLAYER_SPEED
            final_x = max(0.0, min(new_x, float(config.GRID_WIDTH - 1)))
            final_y = max(0.0, min(new_y, float(config.GRID_HEIGHT - 1)))
            p.pos = (final_x, final_y)
            p.target_pos = (final_x, final_y)
    
    def check_for_merge(self):
        with self._lock:
            positions_on_grid = {}
            for p in self.players.values():
                grid_x, grid_y = int(p.pos[0]), int(p.pos[1])
                positions_on_grid.setdefault((grid_x, grid_y), []).append(p)
            
            merged_results = []
            players_to_remove = set()
            orders_to_process = list(self.orders) 

            for pos_key, plist in positions_on_grid.items():
                if len(plist) > 1:
                    available_players_on_tile = {p.player_id: p for p in plist}
                    for order in orders_to_process: 
                        if order.get('fulfilled', False): continue
                        required_order_ingredients = list(order['ingredients']) 
                        potential_merge_player_ids = []
                        potential_merge_ingredient_names = []
                        temp_available_ingredients_map = {}
                        for p_id, p_obj in available_players_on_tile.items():
                            temp_available_ingredients_map.setdefault(p_obj.ingredient, []).append(p_id)
                        
                        all_ingredients_found_for_order = True
                        for required_ing in required_order_ingredients:
                            if required_ing in temp_available_ingredients_map and temp_available_ingredients_map[required_ing]:
                                p_id_for_this_ing = temp_available_ingredients_map[required_ing].pop(0)
                                potential_merge_player_ids.append(p_id_for_this_ing)
                                potential_merge_ingredient_names.append(required_ing)
                            else:
                                all_ingredients_found_for_order = False
                                break
                        
                        if all_ingredients_found_for_order and len(potential_merge_ingredient_names) == len(required_order_ingredients):
                            result_recipe = self.recipe_manager.check_merge(frozenset(potential_merge_ingredient_names))
                            if result_recipe and result_recipe['name'] == order['name']:
                                self.score += result_recipe["price"]
                                merged_results.append({"fusion": result_recipe, "pos": pos_key, "players_involved": potential_merge_player_ids})
                                players_to_remove.update(potential_merge_player_ids)
                                order['fulfilled'] = True 
                                for p_id in potential_merge_player_ids:
                                    if p_id in available_players_on_tile:
                                        del available_players_on_tile[p_id]
                                break 
            
            self.orders = [order for order in orders_to_process if not order.get('fulfilled', False)]
            if not self.orders and len(self.players) > 0: 
                self.generate_orders(len(self.players))
            
            players_to_respawn_data = []
            for p_id in list(players_to_remove):
                if p_id in self.players:
                    self.remove_player(p_id)
                    all_ingredients = ['Rice', 'Salmon', 'Tuna', 'Shrimp', 'Egg', 'Seaweed', 'Cucumber', 'Avocado', 'Crab Meat', 'Eel', 'Cream Cheese', 'Fish Roe']
                    new_ingredient = random.choice(all_ingredients)
                    new_pos = (float(random.randint(0, config.GRID_WIDTH - 1)), float(random.randint(0, config.GRID_HEIGHT - 1)))
                    players_to_respawn_data.append((p_id, new_ingredient, new_pos))

            for p_id, new_ingredient, new_pos in players_to_respawn_data:
                self.add_player(p_id, new_ingredient, new_pos)
            
            return merged_results if merged_results else None

    def to_dict(self):
        with self._lock:
            serializable_orders = [{"name": o.get("name"), "price": o.get("price"), "ingredients": o.get("ingredients", [])}
                                   for o in self.orders if not o.get('fulfilled', False)]
            return {
                "players": {pid: {"ingredient": p.ingredient, "pos": p.pos, "target_pos": p.target_pos} for pid, p in self.players.items()},
                "orders": serializable_orders,
                "score": self.score,
                "timer": self.timer
            }

    def generate_orders(self, num_active_players):
        with self._lock:
            if num_active_players == 0:
                self.orders = []
                return

            possible_recipes = self.recipe_manager.get_recipes_by_ingredient_count(max_ingredients=num_active_players)
            if not possible_recipes:
                self.orders = []
                return

            num_orders_to_generate = min(3, len(possible_recipes))
            selected_orders = random.sample(possible_recipes, num_orders_to_generate)
            
            self.orders = [{"name": o['name'], "price": o['price'], "ingredients": list(o['ingredients'])}
                           for o in selected_orders]