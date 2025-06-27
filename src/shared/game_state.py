import random
import threading
import time
from . import config
from .recipe_manager import RecipeManager

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
        self._fusion_event_queue = []
        self._visual_events = []

    def add_player(self, player_id, ingredient, pos):
        with self._lock:
            self.players[player_id] = PlayerState(player_id, ingredient, pos)

    def remove_player(self, player_id):
        with self._lock:
            if player_id in self.players:
                del self.players[player_id]

    def move_player(self, player_id, direction):
        with self._lock:
            p = self.players.get(player_id)
            if not p:
                return
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
            temp_players_processed_in_merge_cycle = set() 
            for pos_key, plist in positions_on_grid.items():
                if len(plist) > 1:
                    current_players_on_tile_available = {p.player_id: p for p in plist if p.player_id not in temp_players_processed_in_merge_cycle}
                    if len(current_players_on_tile_available) < 2:
                        continue
                    orders_to_check = list(self.orders)
                    for order_index, order in enumerate(orders_to_check):
                        if order.get('fulfilled', False):
                            continue
                        required_order_ingredients = list(order['ingredients'])
                        potential_merge_player_ids = []
                        potential_merge_ingredient_names = []
                        temp_available_ingredients_map = {}
                        for p_id, p_obj in current_players_on_tile_available.items():
                            temp_available_ingredients_map.setdefault(p_obj.ingredient, []).append(p_id)
                        all_ingredients_found_for_order = True
                        for required_ing in required_order_ingredients:
                            if required_ing in temp_available_ingredients_map and \
                            temp_available_ingredients_map[required_ing]:
                                p_id_for_this_ing = temp_available_ingredients_map[required_ing].pop(0)
                                potential_merge_player_ids.append(p_id_for_this_ing)
                                potential_merge_ingredient_names.append(required_ing)
                            else:
                                all_ingredients_found_for_order = False
                                break
                        if all_ingredients_found_for_order and \
                        len(potential_merge_ingredient_names) == len(required_order_ingredients):
                            result_recipe = self.recipe_manager.check_merge(frozenset(potential_merge_ingredient_names))
                            if result_recipe and result_recipe['name'] == order['name']:
                                self._fusion_event_queue.append({
                                    "recipe": result_recipe,
                                    "pos": pos_key,
                                    "players_involved": potential_merge_player_ids,
                                    "order_name_fulfilled": order['name']
                                })
                                print(f"Fusion event detected: {result_recipe['name']} at {pos_key}")
                                temp_players_processed_in_merge_cycle.update(potential_merge_player_ids)
                                order['fulfilled'] = True
                                break
            return True

    def process_fusion_events(self):
        with self._lock:
            events_to_process = list(self._fusion_event_queue)
            self._fusion_event_queue.clear()
            all_players_for_ingredient_change_data = []
            self.orders = [order for order in self.orders if not order.get('fulfilled', False)]
            for event in events_to_process:
                recipe = event['recipe']
                pos = event['pos']
                players_involved = event['players_involved']
                order_name_fulfilled = event['order_name_fulfilled']
                self.score += recipe["price"]
                print(f"Processing Fusion: {recipe['name']} served! +{recipe['price']} cuan at {pos}")
                players_for_ingredient_change_local = []
                players_removed_this_event = set()
                all_ingredients = ['Rice', 'Salmon', 'Tuna', 'Shrimp', 'Egg', 'Seaweed',
                'Cucumber', 'Avocado', 'Crab Meat', 'Eel', 'Cream Cheese', 'Fish Roe']
                for i, p_id in enumerate(players_involved):
                    if p_id in self.players and p_id not in players_removed_this_event:
                        self.remove_player(p_id)
                        players_removed_this_event.add(p_id)
                        new_ingredient = random.choice(all_ingredients)
                        players_for_ingredient_change_local.append({
                            "player_id": p_id,
                            "new_ingredient": new_ingredient,
                            "pos": pos,
                            "delay_factor": i
                        })
                        print(f"Prepared ingredient change for Player {p_id} as {new_ingredient} at {pos} with delay factor {i}")
                self._visual_events.append({
                    "type": "ingredient_change_sequence",
                    "changes": players_for_ingredient_change_local,
                    "start_time": time.time()
                })
                all_players_for_ingredient_change_data.extend(players_for_ingredient_change_local)
                for order_obj in self.orders:
                    if order_obj['name'] == order_name_fulfilled:
                        order_obj['fulfilled'] = True
                        break
                print(f"Order '{order_name_fulfilled}' fulfilled.")
            self.orders = [order for order in self.orders if not order.get('fulfilled', False)]
            if not self.orders and len(self.players) > 0:
                self.generate_orders(len(self.players))
                print("All orders fulfilled, generating new ones.")
            for change_data in all_players_for_ingredient_change_data:
                self.add_player(change_data["player_id"], change_data["new_ingredient"], change_data["pos"])

    def to_dict(self):
        with self._lock:
            players_copy = {pid: {"ingredient": p.ingredient, "pos": p.pos, "target_pos": p.target_pos}
                            for pid, p in self.players.items()}
            serializable_orders_copy = []
            for order in self.orders:
                if not order.get('fulfilled', False):
                    serializable_orders_copy.append({
                        "name": order.get("name"),
                        "price": order.get("price"),
                        "ingredients": list(order.get("ingredients", []))
                    })
            score_copy = self.score
            timer_copy = self.timer
            visual_events_copy = list(self._visual_events)
            self._visual_events.clear()
        return {
            "players": players_copy,
            "orders": serializable_orders_copy,
            "score": score_copy,
            "timer": timer_copy,
            "visual_events": visual_events_copy
        }

    def generate_orders(self, num_active_players):
        with self._lock:
            if num_active_players == 0:
                self.orders = []
                print("No active players, cannot generate orders.")
                return
            possible_recipes = self.recipe_manager.get_recipes_by_ingredient_count(max_ingredients=num_active_players)
            if not possible_recipes:
                print("Warning: No suitable recipes found for current number of players.")
                self.orders = []
                return
            num_orders_to_generate = min(3, len(possible_recipes))
            selected_orders = random.sample(possible_recipes, num_orders_to_generate)
            self.orders = []
            for o in selected_orders:
                self.orders.append({
                    "name": o['name'],
                    "price": o['price'],
                    "ingredients": list(o['ingredients'])
                })
            print(f"Generated orders (with ingredients): {self.orders}")