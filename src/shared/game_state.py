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

        self.last_order_spawn_time = time.time()

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
        # Cek apakah pemain berada di dalam area 2x2 stasiun
        return sx <= px < sx + config.STATION_SIZE and sy <= py < sy + config.STATION_SIZE

    def _get_random_station_pos(self, existing_positions):
        """Mencari posisi 2x2 acak yang tidak tumpang tindih."""
        while True:
            # Pastikan stasiun tidak keluar dari batas grid
            x = random.randint(0, config.GRID_WIDTH - config.STATION_SIZE)
            y = random.randint(0, config.GRID_HEIGHT - config.STATION_SIZE)
            new_pos = (x, y)
            is_overlapping = False
            # Cek tumpang tindih dengan stasiun lain
            for ex_x, ex_y in existing_positions:
                # Periksa tumpang tindih area 2x2
                if not (x + config.STATION_SIZE <= ex_x or x >= ex_x + config.STATION_SIZE or \
                        y + config.STATION_SIZE <= ex_y or y >= ex_y + config.STATION_SIZE):
                    is_overlapping = True
                    break
            if not is_overlapping:
                return new_pos

    def initialize_stations(self):
        with self._lock:
            self.fusion_stations = []
            existing_station_positions = []

            # Generate 2 fusion stations
            for _ in range(2):
                pos = self._get_random_station_pos(existing_station_positions)
                self.fusion_stations.append(pos)
                existing_station_positions.append(pos)
            
            # Generate 1 enter station
            pos = self._get_random_station_pos(existing_station_positions)
            self.enter_station = pos
            existing_station_positions.append(pos)
            
            print(f"Stations initialized: Fusion={self.fusion_stations}, Enter={self.enter_station}")

    def can_player_change_ingredient(self, player_id):
        with self._lock:
            p = self.players.get(player_id)
            if not p or not self.enter_station:
                return False
            return self._is_player_on_station(p.pos, self.enter_station)

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
                for order_obj in self.orders:
                    if order_obj['name'] == order_name_fulfilled:
                        order_obj['fulfilled'] = True
                        break
                print(f"Order '{order_name_fulfilled}' fulfilled.")
                self._visual_events.append({"type": "recipe_fusion", "data": {"pos": pos, "recipe_name": recipe['name']}})

            # Filter order yang fulfilled
            self.orders = [order for order in self.orders if not order.get('fulfilled', False)]
            # Tidak ada lagi logika generate order di sini, karena akan dipicu oleh timer
            
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
                        # --- KONFIRMASI KODE DI SINI ---
                        # Pastikan ini sudah benar, karena data order sudah mengandung list ingredients
                        "ingredients": order.get("ingredients", []) 
                        # --- AKHIR KONFIRMASI ---
                    })
            score_copy = self.score
            timer_copy = self.timer
            visual_events_copy = list(self._visual_events)
            self._visual_events.clear()
            
            fusion_stations_copy = list(self.fusion_stations)
            enter_station_copy = self.enter_station

        return {
            "players": players_copy,
            "orders": serializable_orders_copy,
            "score": score_copy,
            "timer": timer_copy,
            "visual_events": visual_events_copy,
            "fusion_stations": fusion_stations_copy,
            "enter_station": enter_station_copy
        }

    def generate_orders(self, num_active_players):
        with self._lock:
            print(f"DEBUG: generate_orders called with num_active_players={num_active_players}")
            if num_active_players == 0:
                print("DEBUG: No active players, cannot generate orders.")
                return
            
            # --- MODIFIKASI KODE UTAMA DI SINI ---
            # 1. Coba dapatkan resep berdasarkan jumlah pemain aktif
            possible_recipes = self.recipe_manager.get_recipes_by_ingredient_count(max_ingredients=num_active_players)
            
            if not possible_recipes:
                print(f"DEBUG: No recipes found suitable for {num_active_players} players. Falling back to all recipes.")
                # 2. Jika tidak ada yang cocok, ambil semua resep
                possible_recipes = self.recipe_manager.get_all_recipes()

            if not possible_recipes:
                print("DEBUG: Warning: No recipes available in the database at all. Cannot generate orders.")
                return

            # 3. Pilih satu resep acak dari daftar resep yang memenuhi syarat (atau semua resep jika fallback)
            selected_recipe = random.choice(possible_recipes)
            # --- AKHIR MODIFIKASI ---
            
            ingredients_list = selected_recipe.get('ingredients', []) 
            if not isinstance(ingredients_list, list): # Jaga-jaga jika masih frozenset dari cache lama
                ingredients_list = list(ingredients_list)
            
            self.orders.append({
                "name": selected_recipe['name'],
                "price": selected_recipe['price'],
                "ingredients": ingredients_list,
                "fulfilled": False
            })
            print(f"DEBUG: Added 1 new order: {selected_recipe['name']}. Total orders: {len(self.orders)}")