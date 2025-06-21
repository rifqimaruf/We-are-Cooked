import sqlite3
import os

class RecipeManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(RecipeManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, db_path='src/shared/recipes.db'):
        if hasattr(self, '_initialized'):
            return
        
        if not os.path.exists(db_path):
            alt_path = os.path.join('..', 'shared', 'recipes.db')
            if os.path.exists(alt_path):
                db_path = alt_path
            else:
                 raise FileNotFoundError(f"Database tidak ditemukan di {db_path} atau {alt_path}")

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

# Singleton instance untuk diimpor di seluruh proyek
recipe_manager = RecipeManager()