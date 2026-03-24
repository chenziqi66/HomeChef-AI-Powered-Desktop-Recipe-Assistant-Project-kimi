#!/usr/bin/env python3
import os, sqlite3, json
from typing import List

class Database:
    def __init__(self, path="homechef.db"):
        self.path = path

    def get_conn(self):
        return sqlite3.connect(self.path)

    def init_db(self):
        first = not os.path.exists(self.path)
        conn = self.get_conn()
        cur = conn.cursor()
        # recipes: ingredients and steps stored as JSON text
        cur.execute("""
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT UNIQUE,
            ingredients TEXT,
            steps TEXT,
            time INTEGER,
            difficulty TEXT
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS pantry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS grocery (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
        """)
        conn.commit()
        # seed data if new
        if first:
            seed_path = os.path.join(os.path.dirname(__file__), "seed_recipes.json")
            if os.path.exists(seed_path):
                with open(seed_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for r in data:
                    self.add_recipe(r['title'], r['ingredients'], r['steps'], r.get('time',0), r.get('difficulty','Easy'))
        conn.close()

    def add_recipe(self, title, ingredients: List[str], steps: List[str], time=0, difficulty="Easy"):
        conn = self.get_conn()
        cur = conn.cursor()
        try:
            cur.execute("INSERT OR IGNORE INTO recipes (title, ingredients, steps, time, difficulty) VALUES (?, ?, ?, ?, ?)",
                        (title, json.dumps(ingredients), json.dumps(steps), time, difficulty))
            conn.commit()
        finally:
            conn.close()

    def get_all_recipes(self):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id, title, ingredients, steps, time, difficulty FROM recipes ORDER BY title")
        rows = cur.fetchall()
        conn.close()
        out = []
        for r in rows:
            out.append({
                "id": r[0],
                "title": r[1],
                "ingredients": json.loads(r[2]),
                "steps": json.loads(r[3]),
                "time": r[4],
                "difficulty": r[5]
            })
        return out

    def get_recipe_by_id(self, rid):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id, title, ingredients, steps, time, difficulty FROM recipes WHERE id=?", (rid,))
        r = cur.fetchone()
        conn.close()
        if not r:
            return None
        return {
            "id": r[0],
            "title": r[1],
            "ingredients": json.loads(r[2]),
            "steps": json.loads(r[3]),
            "time": r[4],
            "difficulty": r[5]
        }

    def search_by_ingredients(self, available_ingredients):
        # Simple match: percent of recipe ingredients that are present
        all_recipes = self.get_all_recipes()
        results = []
        for r in all_recipes:
            req = [i.lower() for i in r['ingredients']]
            have = set([i.lower() for i in available_ingredients])
            matched = [x for x in req if any(x in h for h in have)]
            percent = int(len(matched) / max(1, len(req)) * 100)
            if percent > 0:
                rr = r.copy()
                rr['match_percent'] = percent
                results.append(rr)
        # sort by highest match
        results.sort(key=lambda x: x['match_percent'], reverse=True)
        return results

    # Pantry functions
    def add_pantry_item(self, name):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("INSERT OR IGNORE INTO pantry (name) VALUES (?)", (name,))
        conn.commit()
        conn.close()

    def remove_pantry_item(self, name):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM pantry WHERE name=?", (name,))
        conn.commit()
        conn.close()

    def get_pantry_items(self):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT name FROM pantry ORDER BY name")
        rows = [r[0] for r in cur.fetchall()]
        conn.close()
        return rows

    # Grocery functions
    def add_grocery_item(self, name):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("INSERT OR IGNORE INTO grocery (name) VALUES (?)", (name,))
        conn.commit()
        conn.close()

    def remove_grocery_item(self, name):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM grocery WHERE name=?", (name,))
        conn.commit()
        conn.close()

    def get_grocery_items(self):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT name FROM grocery ORDER BY name")
        rows = [r[0] for r in cur.fetchall()]
        conn.close()
        return rows

    def get_missing_ingredients_for_recipe(self, recipe_id):
        r = self.get_recipe_by_id(recipe_id)
        if not r:
            return []
        pantry = [p.lower() for p in self.get_pantry_items()]
        missing = []
        for ing in r['ingredients']:
            # simple contains matching
            low = ing.lower()
            if not any(low in p for p in pantry):
                missing.append(ing)
        return missing

    # ==================== Meal Plan Functions ====================

    def init_meal_plan_tables(self):
        """Initialize meal plan related tables"""
        conn = self.get_conn()
        cur = conn.cursor()
        # Meal plans table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS meal_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            diet_type TEXT DEFAULT 'balanced',
            max_time INTEGER DEFAULT 60,
            preferences TEXT DEFAULT '[]'
        )
        """)
        # Meal plan items (daily meals)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS meal_plan_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER,
            day_of_week INTEGER,
            meal_type TEXT,
            recipe_id INTEGER,
            FOREIGN KEY (plan_id) REFERENCES meal_plans(id) ON DELETE CASCADE,
            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
        )
        """)
        conn.commit()
        conn.close()

    def create_meal_plan(self, name, diet_type='balanced', max_time=60, preferences=None):
        """Create a new meal plan"""
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO meal_plans (name, diet_type, max_time, preferences) VALUES (?, ?, ?, ?)",
            (name, diet_type, max_time, json.dumps(preferences or []))
        )
        plan_id = cur.lastrowid
        conn.commit()
        conn.close()
        return plan_id

    def get_meal_plan(self, plan_id):
        """Get meal plan with all meals"""
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id, name, created_at, diet_type, max_time, preferences FROM meal_plans WHERE id=?", (plan_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return None
        plan = {
            'id': row[0],
            'name': row[1],
            'created_at': row[2],
            'diet_type': row[3],
            'max_time': row[4],
            'preferences': json.loads(row[5]),
            'meals': {}
        }
        # Get all meals for this plan
        cur.execute("""
            SELECT mpi.day_of_week, mpi.meal_type, mpi.recipe_id, r.title, r.ingredients, r.time, r.difficulty
            FROM meal_plan_items mpi
            JOIN recipes r ON mpi.recipe_id = r.id
            WHERE mpi.plan_id=?
        """, (plan_id,))
        for row in cur.fetchall():
            day = row[0]
            meal_type = row[1]
            if day not in plan['meals']:
                plan['meals'][day] = {}
            plan['meals'][day][meal_type] = {
                'recipe_id': row[2],
                'title': row[3],
                'ingredients': json.loads(row[4]),
                'time': row[5],
                'difficulty': row[6]
            }
        conn.close()
        return plan

    def get_all_meal_plans(self):
        """Get all meal plans (summary)"""
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id, name, created_at, diet_type FROM meal_plans ORDER BY created_at DESC")
        plans = []
        for row in cur.fetchall():
            plans.append({
                'id': row[0],
                'name': row[1],
                'created_at': row[2],
                'diet_type': row[3]
            })
        conn.close()
        return plans

    def add_meal_to_plan(self, plan_id, day_of_week, meal_type, recipe_id):
        """Add or update a meal in the plan"""
        conn = self.get_conn()
        cur = conn.cursor()
        # Remove existing meal for this slot
        cur.execute(
            "DELETE FROM meal_plan_items WHERE plan_id=? AND day_of_week=? AND meal_type=?",
            (plan_id, day_of_week, meal_type)
        )
        # Add new meal
        cur.execute(
            "INSERT INTO meal_plan_items (plan_id, day_of_week, meal_type, recipe_id) VALUES (?, ?, ?, ?)",
            (plan_id, day_of_week, meal_type, recipe_id)
        )
        conn.commit()
        conn.close()

    def remove_meal_from_plan(self, plan_id, day_of_week, meal_type):
        """Remove a meal from the plan"""
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM meal_plan_items WHERE plan_id=? AND day_of_week=? AND meal_type=?",
            (plan_id, day_of_week, meal_type)
        )
        conn.commit()
        conn.close()

    def delete_meal_plan(self, plan_id):
        """Delete a meal plan and all its meals"""
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM meal_plans WHERE id=?", (plan_id,))
        conn.commit()
        conn.close()

    def get_meal_plan_ingredients(self, plan_id):
        """Get aggregated ingredients for a meal plan"""
        plan = self.get_meal_plan(plan_id)
        if not plan:
            return []
        ingredient_map = {}
        for day_meals in plan['meals'].values():
            for meal in day_meals.values():
                for ing in meal['ingredients']:
                    ing_lower = ing.lower().strip()
                    if ing_lower not in ingredient_map:
                        ingredient_map[ing_lower] = ing
        return sorted(ingredient_map.values())
