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
