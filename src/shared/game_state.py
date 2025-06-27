import random
from . import config
from .recipe_manager import RecipeManager
import threading

class PlayerState:
    def __init__(self, player_id, ingredient, pos):
        self.player_id = player_id
        self.ingredient = ingredient
        self.pos = pos # Posisi aktual pemain (bisa float)
        self.target_pos = pos # Posisi tujuan pemain (jika sedang bergerak)

class GameState:
    def __init__(self):
        self.players = {}
        self.orders = []
        self.score = 0
        self.timer = config.GAME_TIMER_SECONDS
        self.recipe_manager = RecipeManager() # Inisialisasi RecipeManager di sini
        self.clients_info = {} # Untuk melacak status ready klien
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

            # Cek batas maksimum grid
            final_x = max(0.0, min(new_x, float(config.GRID_WIDTH - 1)))
            final_y = max(0.0, min(new_y, float(config.GRID_HEIGHT - 1)))

            # Perbarui nilai posisi pemain (tetap float)
            p.pos = (final_x, final_y)
            p.target_pos = (final_x, final_y) # Update target_pos juga

    def check_for_merge(self):
        with self._lock:
            # Mengelompokkan pemain berdasarkan posisi petak integer mereka
            positions_on_grid = {} # { (grid_x,grid_y): [player1_obj, player2_obj, ...] }
            for p in self.players.values():
                grid_x, grid_y = int(p.pos[0]), int(p.pos[1])
                positions_on_grid.setdefault((grid_x, grid_y), []).append(p)

            merged_results = []
            players_to_remove = set() # player_id dari pemain yang akan dihapus

            # Buat daftar pesanan yang akan diperiksa.
            # Kita akan menggunakan list ini untuk iterasi, dan menandai 'fulfilled' di dalamnya.
            # Setelah loop selesai, kita akan membangun ulang self.orders.
            orders_to_process = list(self.orders) 

            # Iterasi setiap posisi di mana ada setidaknya dua pemain
            for pos_key, plist in positions_on_grid.items():
                if len(plist) > 1: # Hanya periksa jika lebih dari satu pemain di petak yang sama

                    # Buat salinan pemain yang tersedia di petak ini yang bisa berfusi.
                    # Ini akan berkurang jika pemain terlibat dalam fusi di petak yang sama.
                    available_players_on_tile = {p.player_id: p for p in plist}

                    # Coba penuhi pesanan yang aktif terlebih dahulu
                    # Iterasi pada orders_to_process, bukan langsung self.orders
                    for order_index, order in enumerate(orders_to_process): 
                        # Lewati pesanan yang sudah ditandai fulfilled dari iterasi ini
                        if order.get('fulfilled', False): 
                            continue

                        required_order_ingredients = list(order['ingredients']) 

                        potential_merge_player_ids = []
                        potential_merge_ingredient_names = []

                        # Buat peta sementara bahan yang tersedia dari pemain di tile untuk percobaan fusi ini
                        # {ingredient_name: [player_id1, player_id2, ...]}
                        temp_available_ingredients_map = {}
                        for p_id, p_obj in available_players_on_tile.items():
                            temp_available_ingredients_map.setdefault(p_obj.ingredient, []).append(p_id)

                        all_ingredients_found_for_order = True

                        # Coba penuhi setiap bahan yang dibutuhkan oleh pesanan ini
                        for required_ing in required_order_ingredients:
                            if required_ing in temp_available_ingredients_map and \
                            temp_available_ingredients_map[required_ing]:

                                p_id_for_this_ing = temp_available_ingredients_map[required_ing].pop(0)
                                potential_merge_player_ids.append(p_id_for_this_ing)
                                potential_merge_ingredient_names.append(required_ing)
                            else:
                                all_ingredients_found_for_order = False
                                break # Bahan tidak ditemukan untuk pesanan ini

                        # Jika semua bahan untuk pesanan ini ditemukan dan jumlahnya cocok
                        if all_ingredients_found_for_order and \
                        len(potential_merge_ingredient_names) == len(required_order_ingredients):

                            # Verifikasi ulang fusi menggunakan recipe_manager dengan frozenset
                            result_recipe = self.recipe_manager.check_merge(frozenset(potential_merge_ingredient_names))

                            # Pastikan resep yang terbentuk cocok dengan nama pesanan yang sedang diproses
                            if result_recipe and result_recipe['name'] == order['name']:
                                self.score += result_recipe["price"]
                                merged_results.append({
                                    "fusion": result_recipe,
                                    "pos": pos_key,
                                    "players_involved": potential_merge_player_ids
                                })
                                print(f"Fusion at {pos_key}: {result_recipe['name']} served! +{result_recipe['price']} cuan")

                                # Tambahkan pemain yang terlibat ke set untuk dihapus nanti
                                players_to_remove.update(potential_merge_player_ids)

                                # Tandai pesanan ini sebagai terpenuhi di list sementara orders_to_process
                                order['fulfilled'] = True 

                                print(f"Order '{order['name']}' fulfilled.")

                                # Perbarui available_players_on_tile agar pemain yang sudah berfusi tidak digunakan lagi
                                for p_id in potential_merge_player_ids:
                                    if p_id in available_players_on_tile:
                                        del available_players_on_tile[p_id]

                                # Keluar dari loop pesanan setelah satu pesanan terpenuhi di petak ini
                                break 

            # --- Bagian PENTING: Penghapusan pesanan yang terpenuhi dan generasi pesanan baru ---
            # Setelah semua potensi fusi di semua posisi diperiksa,
            # bangun ulang self.orders hanya dengan pesanan yang belum terpenuhi
            self.orders = [order for order in orders_to_process if not order.get('fulfilled', False)]

            # Jika semua pesanan terpenuhi setelah membersihkan, dan masih ada pemain aktif, buat pesanan baru
            if not self.orders and len(self.players) > 0: 
                self.generate_orders(len(self.players)) # Generate order berdasarkan jumlah pemain aktif saat ini
                print("All orders fulfilled, generating new ones.")

            # --- Akhir Bagian PENTING ---

            # Hapus pemain yang berfusi dan respawn mereka
            # Hapus pemain yang berfusi dan respawn mereka
            # Kita perlu mengumpulkan data respawn dulu, baru memprosesnya
            players_to_respawn_data = [] # List of (player_id, new_ingredient, new_pos)

            for p_id in list(players_to_remove): # Iterasi salinan set untuk aman menghapus dari self.players
                if p_id in self.players:
                    self.remove_player(p_id) # Hapus pemain dari game_state

                    # Data untuk respawn
                    all_ingredients = ['Rice', 'Salmon', 'Tuna', 'Shrimp', 'Egg', 'Seaweed',
                                    'Cucumber', 'Avocado', 'Crab Meat', 'Eel', 'Cream Cheese', 'Fish Roe']
                    new_ingredient = random.choice(all_ingredients)

                    # Cari posisi kosong untuk respawn
                    new_pos = None
                    attempts = 0

                    # Ambil snapshot posisi petak yang sudah terisi dalam bentuk set untuk pencarian cepat
                    # Ini sudah dilakukan di awal loop players_to_remove, pastikan itu benar-benar snapshot.
                    # Jika tidak, pindahkan inisialisasi ini ke luar loop players_to_remove
                    current_player_grid_positions = { (int(p.pos[0]), int(p.pos[1])) for p in self.players.values() }

                    while new_pos is None and attempts < 100:
                        temp_x = random.randint(0, config.GRID_WIDTH - 1)
                        temp_y = random.randint(0, config.GRID_HEIGHT - 1)

                        # Cek apakah posisi (int,int) kosong menggunakan set lookup
                        if (temp_x, temp_y) not in current_player_grid_positions:
                            new_pos = (float(temp_x), float(temp_y))
                        attempts += 1

                    if new_pos is None: # Fallback jika tidak menemukan posisi kosong setelah banyak percobaan
                        new_pos = (float(random.randint(0, config.GRID_WIDTH - 1)), float(random.randint(0, config.GRID_HEIGHT - 1)))
                        
                    players_to_respawn_data.append((p_id, new_ingredient, new_pos))
                    print(f"Prepared to respawn Player {p_id} as {new_ingredient} at {new_pos}")

            # Sekarang, tambahkan kembali pemain yang di-respawn setelah semua penghapusan selesai
            for p_id, new_ingredient, new_pos in players_to_respawn_data:
                self.add_player(p_id, new_ingredient, new_pos)
                print(f"Player {p_id} respawned as {new_ingredient} at {new_pos}")

            return merged_results if merged_results else None

    def to_dict(self):
        with self._lock:
            # Pastikan order yang dikirim ke client memiliki semua info yang relevan
            serializable_orders = []
            for order in self.orders:
                # Hanya sertakan pesanan yang belum terpenuhi saat mengirim ke klien
                if not order.get('fulfilled', False): 
                    serializable_orders.append({
                        "name": order.get("name"),
                        "price": order.get("price"),
                        "ingredients": order.get("ingredients", [])
                    })

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
                print("No active players, cannot generate orders.")
                return

            possible_recipes = self.recipe_manager.get_recipes_by_ingredient_count(max_ingredients=num_active_players)

            if not possible_recipes:
                print("Warning: No suitable recipes found for current number of players.")
                self.orders = []
                return

            num_orders_to_generate = min(3, len(possible_recipes))
            selected_orders = random.sample(possible_recipes, num_orders_to_generate)

            self.orders = [] # KOSONGKAN LIST ORDERS SEBELUM MENGISI YANG BARU
            for o in selected_orders:
                # Pastikan 'ingredients' yang disimpan di order adalah list, bukan frozenset
                # dan tidak ada flag 'fulfilled' saat awal
                self.orders.append({
                    "name": o['name'],
                    "price": o['price'],
                    "ingredients": list(o['ingredients']) # Pastikan ini list
                })
            print(f"Generated orders (with ingredients): {self.orders}")