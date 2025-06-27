import sqlite3
import os

# src/shared/recipe_manager.py
class RecipeManager:
    _instance = None # Ini harus di luar __init__
    _initialized = False # Tambahkan flag inisialisasi di level kelas

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(RecipeManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, db_path=None):
        # Penting: Hanya inisialisasi jika belum diinisialisasi untuk instance singleton
        if not self._initialized: 
            if db_path is None:
                base_dir = os.path.dirname(__file__)
                db_path = os.path.join(base_dir, 'recipes.db')

            if not os.path.exists(db_path):
                raise FileNotFoundError(f"Database tidak ditemukan di {db_path}")

            self.db_path = db_path
            self._recipes_cache = self._load_recipes_to_cache()
            RecipeManager._initialized = True # Set flag inisialisasi di kelas
            print("RecipeManager initialized and recipes cached.")
        else:
            print("RecipeManager already initialized. Skipping __init__.") # Debugging
            
    def _load_recipes_to_cache(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Query untuk mengambil semua resep beserta bahan-bahannya
        query = """
            SELECT r.id, r.name, r.price, r.level, GROUP_CONCAT(i.name)
            FROM recipes r
            JOIN recipe_ingredients ri ON r.id = ri.recipe_id
            JOIN ingredients i ON ri.ingredient_id = i.id
            GROUP BY r.id
        """
        cursor.execute(query)
        
        cache = {}
        for row in cursor.fetchall():
            recipe_id, name, price, level, ingredients_str = row
            ingredients_set = frozenset(ingredients_str.split(','))
            
            cache[ingredients_set] = {
                'id': recipe_id,
                'name': name,
                'price': price,
                'level': level
            }
            
        conn.close()
        return cache

    def check_merge(self, ingredients_list):
        ingredients_to_check = frozenset(ingredients_list)
        
        return self._recipes_cache.get(ingredients_to_check)

    def get_random_order(self, level=1):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name, price FROM recipes WHERE level = ? ORDER BY RANDOM() LIMIT 1", (level,))
        result = cursor.fetchone()
        
        conn.close()
        return {"name": result[0], "price": result[1]} if result else None
    
    def get_recipes_by_ingredient_count(self, max_ingredients=None):
        if max_ingredients is None:
            return list(self._recipes_cache.values())

        filtered_recipes = []
        # _recipes_cache berisi {frozenset_bahan: {id, name, price, level}}
        # Jadi kita perlu mengakses kembali frozenset_bahan untuk mendapatkan length
        for ingredients_set, recipe_data in self._recipes_cache.items(): # <--- SUDAH DIUBAH
            if len(ingredients_set) <= max_ingredients: # <--- MENGGUNAKAN ingredients_set
                # Tambahkan 'ingredients' ke recipe_data agar bisa digunakan di GameState
                recipe_data_with_ingredients = recipe_data.copy()
                recipe_data_with_ingredients['ingredients'] = ingredients_set
                filtered_recipes.append(recipe_data_with_ingredients)
        return filtered_recipes

# Singleton instance untuk diimpor di seluruh proyek
recipe_manager = RecipeManager()