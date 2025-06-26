import sqlite3
import os

class RecipeManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(RecipeManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, db_path=None):
        if hasattr(self, '_initialized'):
            return

        if db_path is None:
            base_dir = os.path.dirname(__file__)
            db_path = os.path.join(base_dir, 'recipes.db')

        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database tidak ditemukan di {db_path}")

        self.db_path = db_path
        self._recipes_cache = self._load_recipes_to_cache()
        self._initialized = True
        print("RecipeManager initialized and recipes cached.")

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
        """
        Mengembalikan daftar resep yang jumlah bahannya kurang dari atau sama dengan max_ingredients.
        Jika max_ingredients None, kembalikan semua resep.
        """
        if max_ingredients is None:
            return list(self._cache.values()) # Mengembalikan semua resep

        filtered_recipes = []
        for recipe_data in self._cache.values():
            # recipe_data['ingredients'] adalah frozenset dari nama bahan
            if len(recipe_data['ingredients']) <= max_ingredients:
                filtered_recipes.append(recipe_data)
        return filtered_recipes

# Singleton instance untuk diimpor di seluruh proyek
recipe_manager = RecipeManager()