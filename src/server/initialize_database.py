# src/server/initialize_database.py
import sqlite3
import os

db_dir = os.path.join(os.path.dirname(__file__), '..', 'shared')
db_path = os.path.join(db_dir, 'recipes.db')

os.makedirs(db_dir, exist_ok=True)

ingredients_data = [
    (1, 'Rice'), (2, 'Salmon'), (3, 'Tuna'), (4, 'Shrimp'), (5, 'Egg'),
    (6, 'Seaweed'), (7, 'Cucumber'), (8, 'Avocado'), (9, 'Crab Meat'),
    (10, 'Eel'), (11, 'Cream Cheese'), (12, 'Fish Roe')
]

recipes_data = [
    {'name': 'Sashimi Salmon', 'price': 10000, 'level': 1, 'ingredients': ['Salmon']},
    {'name': 'Sashimi Tuna', 'price': 12000, 'level': 1, 'ingredients': ['Tuna']},
    {'name': 'Kani Stick', 'price': 9000, 'level': 1, 'ingredients': ['Crab Meat']},
    {'name': 'Unagi Slice', 'price': 8000, 'level': 1, 'ingredients': ['Eel']}, 
    {'name': 'Boiled Shrimp', 'price': 13000, 'level': 1, 'ingredients': ['Shrimp']},
    {'name': 'Salmon Nigiri', 'price': 25000, 'level': 2, 'ingredients': ['Salmon', 'Rice']},
    {'name': 'Tuna Nigiri', 'price': 28000, 'level': 2, 'ingredients': ['Tuna', 'Rice']},
    {'name': 'Ebi Nigiri', 'price': 30000, 'level': 2, 'ingredients': ['Shrimp', 'Rice']},
    {'name': 'Kani Nigiri', 'price': 22000, 'level': 2, 'ingredients': ['Crab Meat', 'Rice']},
    {'name': 'Unagi Nigiri', 'price': 32000, 'level': 2, 'ingredients': ['Eel', 'Rice']},
    {'name': 'Onigiri', 'price': 18000, 'level': 2, 'ingredients': ['Rice', 'Seaweed']},
    {'name': 'Kappa Maki', 'price': 40000, 'level': 3, 'ingredients': ['Rice', 'Seaweed', 'Cucumber']},
    {'name': 'Tekka Maki', 'price': 50000, 'level': 3, 'ingredients': ['Rice', 'Seaweed', 'Tuna']},
    {'name': 'California Roll', 'price': 46000, 'level': 3, 'ingredients': ['Rice', 'Crab Meat', 'Avocado']},
    {'name': 'Dragon Roll', 'price': 75000, 'level': 4, 'ingredients': ['Rice', 'Seaweed', 'Shrimp', 'Avocado']},
    {'name': 'Rainbow Roll', 'price': 80000, 'level': 4, 'ingredients': ['Rice', 'Cucumber', 'Salmon', 'Tuna']}, 
]

def initialize_db():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('DROP TABLE IF EXISTS recipe_ingredients')
    cursor.execute('DROP TABLE IF EXISTS recipes')
    cursor.execute('DROP TABLE IF EXISTS ingredients')
    cursor.execute('CREATE TABLE ingredients (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE)')
    cursor.execute('CREATE TABLE recipes (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, price INTEGER NOT NULL, level INTEGER NOT NULL)')
    cursor.execute('CREATE TABLE recipe_ingredients (recipe_id INTEGER, ingredient_id INTEGER, FOREIGN KEY (recipe_id) REFERENCES recipes(id), FOREIGN KEY (ingredient_id) REFERENCES ingredients(id), PRIMARY KEY (recipe_id, ingredient_id))')
    cursor.executemany('INSERT INTO ingredients VALUES (?, ?)', ingredients_data)
    ingredient_map = {name: id for id, name in ingredients_data}
    for recipe in recipes_data:
        cursor.execute('INSERT INTO recipes (name, price, level) VALUES (?, ?, ?)', (recipe['name'], recipe['price'], recipe['level']))
        recipe_id = cursor.lastrowid
        for ingredient_name in recipe['ingredients']:
            ingredient_id = ingredient_map[ingredient_name]
            cursor.execute('INSERT INTO recipe_ingredients VALUES (?, ?)', (recipe_id, ingredient_id))
    conn.commit()
    conn.close()
    print(f"Database '{db_path}' berhasil dibuat dan diisi data.")

if __name__ == '__main__':
    initialize_db()