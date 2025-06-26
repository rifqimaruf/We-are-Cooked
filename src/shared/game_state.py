import random
from . import config
from .recipe_manager import RecipeManager 

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
        self.recipe_manager = RecipeManager()
        self.clients_info = {} # Untuk melacak status ready klien
        # self._generate_initial_orders() # Kita akan panggil ini dari server nanti, bukan di init GameState

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
        positions = {} # { (x,y): [player1_obj, player2_obj, ...] }
        for p in self.players.values():
            grid_x, grid_y = int(p.pos[0]), int(p.pos[1])
            positions.setdefault((grid_x, grid_y), []).append(p)

        merged_results = []
        players_to_remove = set() # Menggunakan set untuk menghindari duplikat player_id

        for pos_key, plist in positions.items(): # pos_key adalah (grid_x, grid_y)
            if len(plist) > 1: # Hanya periksa jika lebih dari satu pemain di petak yang sama
                available_players_on_tile = {p.player_id: p for p in plist}
                for order_index, order in enumerate(list(self.orders)): 
                    required_order_ingredients = list(order['ingredients']) # Ambil list bahan yang dibutuhkan order

                    # List untuk melacak player_id yang berpotensi terlibat dalam fusi ini
                    potential_merge_player_ids = []
                    potential_merge_ingredient_names = []

                    # Buat salinan bahan yang tersedia dari pemain di tile untuk percobaan ini
                    # {ingredient_name: [player_id1, player_id2, ...]}
                    temp_available_ingredients = {}
                    for p_id, p_obj in available_players_on_tile.items():
                        temp_available_ingredients.setdefault(p_obj.ingredient, []).append(p_id)

                    all_ingredients_found_for_order = True

                    # Coba penuhi setiap bahan yang dibutuhkan oleh pesanan ini
                    for required_ing in required_order_ingredients:
                        if required_ing in temp_available_ingredients and temp_available_ingredients[required_ing]:
                            # Ambil satu pemain dengan bahan ini
                            p_id_for_this_ing = temp_available_ingredients[required_ing].pop(0)
                            potential_merge_player_ids.append(p_id_for_this_ing)
                            potential_merge_ingredient_names.append(required_ing)
                        else:
                            all_ingredients_found_for_order = False
                            break # Bahan tidak ditemukan untuk pesanan ini

                    # Jika semua bahan untuk pesanan ini ditemukan
                    if all_ingredients_found_for_order and \
                       len(potential_merge_ingredient_names) == len(required_order_ingredients):

                        # Verifikasi ulang fusi menggunakan recipe_manager dengan frozenset
                        # (penting karena check_merge mengambil frozenset)
                        result_recipe = self.recipe_manager.check_merge(frozenset(potential_merge_ingredient_names))

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

                            # Hapus pesanan yang sudah terpenuhi dari daftar pesanan aktif
                            # Gunakan pop(order_index) karena kita iterasi list(self.orders)
                            order['fulfilled'] = True # Hapus dari list original

                            print(f"Order '{order['name']}' fulfilled. Remaining orders: {[o['name'] for o in self.orders]}")

                            # Perbarui available_players_on_tile agar pemain yang sudah berfusi tidak digunakan lagi
                            for p_id in potential_merge_player_ids:
                                if p_id in available_players_on_tile:
                                    del available_players_on_tile[p_id]

                            # Jika semua pesanan terpenuhi, buat pesanan baru
                            if not self.orders:
                                self.generate_orders(len(self.players))
                                print("All orders fulfilled, generating new ones.")

                            break # Keluar dari loop for order in self.orders

        # Hapus pemain yang berfusi dan respawn mereka
        for p_id in players_to_remove:
            if p_id in self.players: # Pastikan pemain belum dihapus
                self.remove_player(p_id)

                # Respawn pemain dengan bahan baru dan posisi acak
                all_ingredients = ['Rice', 'Salmon', 'Tuna', 'Shrimp', 'Egg', 'Seaweed',
                                   'Cucumber', 'Avocado', 'Crab Meat', 'Eel', 'Cream Cheese', 'Fish Roe']
                new_ingredient = random.choice(all_ingredients)

                # Cari posisi kosong untuk respawn
                existing_positions = [p.pos for p in self.players.values()]
                new_pos = None
                attempts = 0
                while new_pos is None and attempts < 100: # Batasi percobaan
                    temp_x = random.randint(0, config.GRID_WIDTH - 1)
                    temp_y = random.randint(0, config.GRID_HEIGHT - 1)
                    # Cek apakah posisi (int,int) kosong
                    if (temp_x, temp_y) not in existing_positions:
                        new_pos = (float(temp_x), float(temp_y)) # Simpan sebagai float
                    attempts += 1

                if new_pos is None: # Jika tidak menemukan posisi kosong setelah banyak percobaan
                     new_pos = (random.randint(0, config.GRID_WIDTH - 1), random.randint(0, config.GRID_HEIGHT - 1)) # Fallback ke posisi acak

                self.add_player(p_id, new_ingredient, new_pos)
                print(f"Player {p_id} respawned as {new_ingredient} at {new_pos}")

        return merged_results if merged_results else None

    def to_dict(self):
        # Pastikan order yang dikirim ke client memiliki semua info yang relevan
        # Termasuk daftar ingredientsnya.
        serializable_orders = []
        for order in self.orders:
            # Asumsi 'order' di self.orders sekarang sudah menyimpan 'ingredients'
            serializable_orders.append({
                "name": order.get("name"),
                "price": order.get("price"),
                "ingredients": order.get("ingredients", []) # Pastikan ingredients ikut dikirim
            })

        return {
            "players": {pid: {"ingredient": p.ingredient, "pos": p.pos, "target_pos": p.target_pos} for pid, p in self.players.items()},
            "orders": serializable_orders,
            "score": self.score,
            "timer": self.timer
        }

    def remove_player(self, player_id):
        if player_id in self.players:
            del self.players[player_id]

    def generate_orders(self, num_active_players): # Menerima argumen
        """
        Menghasilkan pesanan baru berdasarkan jumlah pemain aktif yang diberikan.
        """
        if num_active_players == 0:
            self.orders = []
            return

        # Dapatkan resep yang jumlah bahannya <= jumlah pemain
        possible_recipes = self.recipe_manager.get_recipes_by_ingredient_count(max_ingredients=num_active_players)

        if not possible_recipes:
            print("Warning: No suitable recipes found for current number of players.")
            self.orders = []
            return

        # Pilih beberapa pesanan secara acak dari daftar yang difilter
        # Misalnya, maksimal 3 pesanan
        num_orders_to_generate = min(3, len(possible_recipes))

        # Kita perlu memastikan 'ingredients' juga disimpan di order
        selected_orders = random.sample(possible_recipes, num_orders_to_generate)

        # Format ulang pesanan untuk disimpan di game_state.orders
        self.orders = [{"name": o['name'], "price": o['price'], "ingredients": list(o['ingredients'])} for o in selected_orders]
        print(f"Generated orders (with ingredients): {self.orders}")
        