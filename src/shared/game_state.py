# src/shared/game_state.py
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

        self.fusion_stations = []
        self.enter_station = None

        self.doorprize_station = None
        self.doorprize_spawn_time = 0
        self.next_doorprize_spawn_delay = random.uniform(config.DOORPRIZE_SPAWN_INTERVAL_MIN, config.DOORPRIZE_SPAWN_INTERVAL_MAX)
        self.players_collected_doorprize = set()

        # --- PERBAIKAN UNTUK ORDER SPAWN ---
        self.last_order_spawn_time = time.time()
        self.next_order_spawn_delay = random.uniform(config.ORDER_SPAWN_INTERVAL_MIN, config.ORDER_SPAWN_INTERVAL_MAX) # Penting: Inisialisasi ini juga
        # --- AKHIR PERBAIKAN ---
        
        self.all_possible_ingredients = ['Rice', 'Salmon', 'Tuna', 'Shrimp', 'Egg', 'Seaweed', 
                                       'Cucumber', 'Avocado', 'Crab Meat', 'Eel', 'Cream Cheese', 'Fish Roe']
        
        self.game_started = False
        self.game_outcome = None

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

    def _is_player_on_station(self, player_pos, station_top_left):
        px, py = int(player_pos[0]), int(player_pos[1])
        sx, sy = station_top_left
        return sx <= px < sx + config.STATION_SIZE and sy <= py < sy + config.STATION_SIZE

    def _get_random_station_pos(self, existing_positions, station_size=config.STATION_SIZE):
        while True:
            x = random.randint(0, config.GRID_WIDTH - station_size)
            y = random.randint(0, config.GRID_HEIGHT - station_size)
            new_pos = (x, y)
            is_overlapping = False
            for ex_x, ex_y, ex_size in existing_positions:
                if not (x + station_size <= ex_x or x >= ex_x + ex_size or \
                        y + station_size <= ex_y or y >= ex_y + ex_size):
                    is_overlapping = True
                    break
            if not is_overlapping:
                return new_pos

    def initialize_stations(self):
        with self._lock:
            self.fusion_stations = []
            existing_station_positions = []

            for _ in range(2):
                pos = self._get_random_station_pos(existing_station_positions, config.STATION_SIZE)
                self.fusion_stations.append(pos)
                existing_station_positions.append((*pos, config.STATION_SIZE))

            pos = self._get_random_station_pos(existing_station_positions, config.STATION_SIZE)
            self.enter_station = pos
            existing_station_positions.append((*pos, config.STATION_SIZE))

            self.doorprize_station = None
            self.doorprize_spawn_time = time.time() 
            self.next_doorprize_spawn_delay = random.uniform(config.DOORPRIZE_SPAWN_INTERVAL_MIN, config.DOORPRIZE_SPAWN_INTERVAL_MAX)
            self.players_collected_doorprize.clear()

            print(f"Stations initialized: Fusion={self.fusion_stations}, Enter={self.enter_station}")

    def can_player_change_ingredient(self, player_id):
        with self._lock:
            p = self.players.get(player_id)
            if not p or not self.enter_station:
                return False
            return self._is_player_on_station(p.pos, self.enter_station)

    def spawn_doorprize_station(self, current_time):
        with self._lock:
            if self.doorprize_station is None:
                existing_station_positions = [(*fs, config.STATION_SIZE) for fs in self.fusion_stations]
                if self.enter_station:
                    existing_station_positions.append((*self.enter_station, config.STATION_SIZE))

                pos = self._get_random_station_pos(existing_station_positions, config.STATION_SIZE)
                self.doorprize_station = pos
                self.doorprize_spawn_time = current_time
                self.players_collected_doorprize.clear()
                self._visual_events.append({"type": "doorprize_spawn", "data": {"pos": pos}})
                print(f"Doorprize station spawned at {pos} at time {current_time:.2f}")
  
    def check_doorprize_interaction(self):
        with self._lock:
            if not self.doorprize_station:
                return

            current_time = time.time()
            if current_time - self.doorprize_spawn_time > config.DOORPRIZE_DURATION:
                print(f"Doorprize station at {self.doorprize_station} expired.")
                self._visual_events.append({"type": "doorprize_expire", "data": {"pos": self.doorprize_station}})
                self.doorprize_station = None
                self.doorprize_spawn_time = current_time
                self.next_doorprize_spawn_delay = random.uniform(config.DOORPRIZE_SPAWN_INTERVAL_MIN, config.DOORPRIZE_SPAWN_INTERVAL_MAX)
                self.players_collected_doorprize.clear()
                return

            for player_id, player in self.players.items():
                if player_id not in self.players_collected_doorprize and \
                   self._is_player_on_station(player.pos, self.doorprize_station):
                    
                    score_gain = random.randint(config.DOORPRIZE_SCORE_MIN, config.DOORPRIZE_SCORE_MAX)
                    self.score += score_gain
                    self.players_collected_doorprize.add(player_id)
                    self._visual_events.append({"type": "doorprize_collect", "data": {"player_id": player_id, "score": score_gain, "pos": self.doorprize_station}})
                    print(f"Player {player_id} collected {score_gain} from doorprize at {self.doorprize_station}. Total score: {self.score}")


    def check_for_merge(self):
        with self._lock:
            positions_on_grid = {}
            for p in self.players.values():
                grid_x, grid_y = int(p.pos[0]), int(p.pos[1])
                positions_on_grid.setdefault((grid_x, grid_y), []).append(p)
            temp_players_processed_in_merge_cycle = set() 
            
            if not self.fusion_stations:
                return False 

            for pos_key, plist in positions_on_grid.items():
                is_on_fusion_station = False
                for station_pos in self.fusion_stations:
                    if self._is_player_on_station(pos_key, station_pos):
                        is_on_fusion_station = True
                        break
                
                if not is_on_fusion_station:
                    continue

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
            
            for event in events_to_process:
                recipe = event['recipe']
                pos = event['pos']
                players_involved = event['players_involved']
                order_name_fulfilled = event['order_name_fulfilled']
                self.score += recipe["price"]
                print(f"Processing Fusion: {recipe['name']} served! +{recipe['price']} cuan at {pos}")
                
                for player_id in players_involved:
                    self._relocate_and_change_ingredient(player_id)
                
                for order_obj in self.orders:
                    if order_obj['name'] == order_name_fulfilled:
                        order_obj['fulfilled'] = True
                        break
                print(f"Order '{order_name_fulfilled}' fulfilled.")
                self._visual_events.append({"type": "recipe_fusion", "data": {"pos": pos, "recipe_name": recipe['name']}})

            self.orders = [order for order in self.orders if not order.get('fulfilled', False)]
            
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
                        "ingredients": order.get("ingredients", [])
                    })
            score_copy = self.score
            timer_copy = self.timer
            
            visual_events_copy = list(self._visual_events)
            self._visual_events.clear()
            
            fusion_stations_copy = list(self.fusion_stations)
            enter_station_copy = self.enter_station
            
            doorprize_station_copy = None
            doorprize_remaining_time = 0
            if self.doorprize_station:
                doorprize_station_copy = self.doorprize_station
                doorprize_remaining_time = max(0, config.DOORPRIZE_DURATION - (time.time() - self.doorprize_spawn_time))

        return {
            "players": players_copy,
            "orders": serializable_orders_copy,
            "score": score_copy,
            "timer": timer_copy,
            "visual_events": visual_events_copy,
            "fusion_stations": fusion_stations_copy,
            "enter_station": enter_station_copy,
            "doorprize_station": doorprize_station_copy,
            "doorprize_remaining_time": doorprize_remaining_time,
            "game_started": self.game_started, # Pastikan ini ada
            "game_outcome": self.game_outcome, # Pastikan ini ada
            "clients_info": self.clients_info # Pastikan ini juga ada
        }

    def generate_orders(self, num_active_players):
        with self._lock:
            print(f"DEBUG: generate_orders called with num_active_players={num_active_players}")
            if num_active_players == 0:
                print("DEBUG: No active players, cannot generate orders.")
                return
            
            # Pastikan recipe_manager sudah terinisialisasi dan memiliki resep
            if not hasattr(self, 'recipe_manager') or not self.recipe_manager:
                print("ERROR: RecipeManager is not initialized in GameState.")
                return

            possible_recipes = self.recipe_manager.get_recipes_by_ingredient_count(max_ingredients=num_active_players)
            
            if not possible_recipes:
                print(f"DEBUG: No recipes found suitable for {num_active_players} players. Falling back to all recipes.")
                possible_recipes = self.recipe_manager.get_all_recipes()

            if not possible_recipes:
                print("DEBUG: Warning: No recipes available in the database at all. Cannot generate orders.")
                return

            selected_recipe = random.choice(possible_recipes)
            
            ingredients_list = selected_recipe.get('ingredients', []) 
            if not isinstance(ingredients_list, list): 
                ingredients_list = list(ingredients_list)
            
            self.orders.append({
                "name": selected_recipe['name'],
                "price": selected_recipe['price'],
                "ingredients": ingredients_list,
                "fulfilled": False
            })
            print(f"DEBUG: Added 1 new order: {selected_recipe['name']}. Total orders: {len(self.orders)}")

    def _get_safe_spawn_position(self):
        max_attempts = 50
        for _ in range(max_attempts):
            x = random.randint(1, config.GRID_WIDTH - 2)
            y = random.randint(1, config.GRID_HEIGHT - 2)

            is_safe = True
            
            # Cek fusion stations
            for station_pos in self.fusion_stations:
                sx, sy = station_pos
                if (sx <= x < sx + config.STATION_SIZE and 
                    sy <= y < sy + config.STATION_SIZE):
                    is_safe = False
                    break
            
            # Cek enter station
            if is_safe and self.enter_station:
                sx, sy = self.enter_station
                if (sx <= x < sx + config.STATION_SIZE and 
                    sy <= y < sy + config.STATION_SIZE):
                    is_safe = False
            
            # Cek doorprize station
            if is_safe and self.doorprize_station:
                sx, sy = self.doorprize_station
                if (sx <= x < sx + config.STATION_SIZE and 
                    sy <= y < sy + config.STATION_SIZE):
                    is_safe = False
            
            if is_safe:
                return (float(x), float(y))
        
        # Fallback jika tidak menemukan posisi aman
        return (1.0, 1.0)

    def _relocate_and_change_ingredient(self, player_id):
        try:
            player = self.players.get(player_id)
            if not player:
                print(f"WARNING: Player {player_id} not found for relocation")
                return
            
            old_ingredient = player.ingredient
            old_pos = player.pos
            print(f"Starting relocation for player {player_id} from {old_pos} with ingredient {old_ingredient}")
            
            if config.POST_FUSION_RELOCATION:
                new_pos = self._get_safe_spawn_position()
                player.pos = new_pos
                player.target_pos = new_pos
                print(f"Player {player_id} relocated to {new_pos}")
            else:
                new_pos = old_pos
                print(f"Player {player_id} staying at {old_pos} (relocation disabled)")
            
            if config.POST_FUSION_INGREDIENT_CHANGE:
                available_ingredients = [ing for ing in self.all_possible_ingredients if ing != old_ingredient]
                
                needed_ingredients = []
                for order in self.orders:
                    if not order.get('fulfilled', False):
                        needed_ingredients.extend(order.get('ingredients', []))
                
                # Pilih ingredient berdasarkan prioritas dari config
                if needed_ingredients and random.random() < config.FUSION_NEEDED_INGREDIENT_PRIORITY:
                    filtered_needed = [ing for ing in needed_ingredients if ing != old_ingredient and ing in available_ingredients]
                    if filtered_needed:
                        new_ingredient = random.choice(filtered_needed)
                    else:
                        new_ingredient = random.choice(available_ingredients)
                else:
                    new_ingredient = random.choice(available_ingredients)
                
                player.ingredient = new_ingredient
                print(f"Player {player_id} ingredient changed from {old_ingredient} to {new_ingredient}")
            else:
                new_ingredient = old_ingredient
                print(f"Player {player_id} keeping ingredient {old_ingredient} (ingredient change disabled)")
            
            # Tambahkan visual event untuk relocation
            self._visual_events.append({
                "type": "player_relocate", 
                "data": {
                    "player_id": player_id, 
                    "old_pos": old_pos,
                    "new_pos": new_pos,
                    "old_ingredient": old_ingredient,
                    "new_ingredient": new_ingredient
                }
            })
            
            print(f"Successfully completed relocation for player {player_id}")
        except Exception as e:
            print(f"ERROR in _relocate_and_change_ingredient for player {player_id}: {e}")
            import traceback
            traceback.print_exc()