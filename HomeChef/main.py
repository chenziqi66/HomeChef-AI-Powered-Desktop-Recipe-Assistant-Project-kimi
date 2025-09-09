#!/usr/bin/env python3
"""
HomeChef — main PyQt5 application
Simple, beginner-friendly implementation.
"""

import sys, os, json
from PyQt5 import QtWidgets, QtCore
from db import Database
from gpt_client import GPTClient

DB_PATH = os.path.join(os.path.dirname(__file__), "homechef.db")

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HomeChef — AI Recipe Assistant")
        self.resize(1000, 600)

        # Database and GPT client
        self.db = Database(DB_PATH)
        self.db.init_db()  # create tables and seed if needed
        self.gpt = GPTClient()

        # Layouts
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        hbox = QtWidgets.QHBoxLayout(central)

        # Left: Recipe list and controls
        left_v = QtWidgets.QVBoxLayout()
        self.recipe_list = QtWidgets.QListWidget()
        self.recipe_list.itemClicked.connect(self.on_recipe_selected)
        left_v.addWidget(QtWidgets.QLabel("Recipes"))
        left_v.addWidget(self.recipe_list)

        ing_search_h = QtWidgets.QHBoxLayout()
        self.ing_input = QtWidgets.QLineEdit()
        self.ing_input.setPlaceholderText("Enter available ingredients (comma separated)...")
        self.find_btn = QtWidgets.QPushButton("Find Recipes")
        self.find_btn.clicked.connect(self.find_recipes)
        ing_search_h.addWidget(self.ing_input)
        ing_search_h.addWidget(self.find_btn)
        left_v.addLayout(ing_search_h)

        pantry_g_h = QtWidgets.QHBoxLayout()
        self.pantry_btn = QtWidgets.QPushButton("Manage Pantry")
        self.pantry_btn.clicked.connect(self.manage_pantry)
        self.grocery_btn = QtWidgets.QPushButton("Grocery List")
        self.grocery_btn.clicked.connect(self.show_grocery)
        pantry_g_h.addWidget(self.pantry_btn)
        pantry_g_h.addWidget(self.grocery_btn)
        left_v.addLayout(pantry_g_h)

        hbox.addLayout(left_v, 2)

        # Middle: Recipe details and cook controls
        mid_v = QtWidgets.QVBoxLayout()
        mid_v.addWidget(QtWidgets.QLabel("Recipe Details"))
        self.detail = QtWidgets.QTextEdit()
        self.detail.setReadOnly(True)
        mid_v.addWidget(self.detail)
        cook_h = QtWidgets.QHBoxLayout()
        self.cook_btn = QtWidgets.QPushButton("Start Cooking (Step-by-step)")
        self.cook_btn.clicked.connect(self.start_cooking)
        cook_h.addWidget(self.cook_btn)
        mid_v.addLayout(cook_h)
        hbox.addLayout(mid_v, 4)

        # Right: Chatbot
        right_v = QtWidgets.QVBoxLayout()
        right_v.addWidget(QtWidgets.QLabel("AI Cooking Assistant (Chatbot)"))
        self.chat_log = QtWidgets.QTextEdit()
        self.chat_log.setReadOnly(True)
        right_v.addWidget(self.chat_log)
        chat_h = QtWidgets.QHBoxLayout()
        self.chat_input = QtWidgets.QLineEdit()
        self.chat_input.setPlaceholderText("Ask the assistant (e.g., 'How to chop onions?')...")
        self.chat_send = QtWidgets.QPushButton("Send")
        self.chat_send.clicked.connect(self.send_chat)
        chat_h.addWidget(self.chat_input)
        chat_h.addWidget(self.chat_send)
        right_v.addLayout(chat_h)
        hbox.addLayout(right_v, 3)

        # Load recipes
        self.load_recipes()

    def load_recipes(self):
        self.recipe_list.clear()
        self.recipes = self.db.get_all_recipes()
        for r in self.recipes:
            item = QtWidgets.QListWidgetItem(r["title"])
            item.setData(QtCore.Qt.UserRole, r["id"])
            self.recipe_list.addItem(item)

    def on_recipe_selected(self, item):
        rid = item.data(QtCore.Qt.UserRole)
        r = self.db.get_recipe_by_id(rid)
        if not r:
            return
        self.current_recipe = r
        self.show_recipe(r)
        # auto-add missing ingredients to grocery list (ask user confirmation)
        missing = self.db.get_missing_ingredients_for_recipe(rid)
        if missing:
            add = QtWidgets.QMessageBox.question(self, "Add to grocery?",
                                                 f"The following items are missing from your pantry:\n{', '.join(missing)}\n\nAdd them to grocery list?",
                                                 QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            if add == QtWidgets.QMessageBox.Yes:
                for it in missing:
                    self.db.add_grocery_item(it)
                QtWidgets.QMessageBox.information(self, "Grocery", "Missing items added to grocery list.")

    def show_recipe(self, r):
        txt = []
        txt.append(f"Title: {r['title']}")
        txt.append(f"Time: {r.get('time','?')} minutes | Difficulty: {r.get('difficulty','?')}")
        txt.append("\nIngredients:")
        for ing in r['ingredients']:
            txt.append(f" - {ing}")
        txt.append("\nSteps:")
        for i, s in enumerate(r['steps'], 1):
            txt.append(f" {i}. {s}")
        self.detail.setPlainText('\n'.join(txt))

    def find_recipes(self):
        raw = self.ing_input.text().strip()
        if not raw:
            QtWidgets.QMessageBox.information(self, "Input needed", "Please enter ingredients separated by commas.")
            return
        ingredients = [i.strip().lower() for i in raw.split(",") if i.strip()]
        matches = self.db.search_by_ingredients(ingredients)
        if matches:
            self.recipe_list.clear()
            for r in matches:
                item = QtWidgets.QListWidgetItem(f"{r['title']}  (match: {r['match_percent']}%)")
                item.setData(QtCore.Qt.UserRole, r['id'])
                self.recipe_list.addItem(item)
        else:
            # Ask GPT for ideas
            suggestion = self.gpt.suggest_recipes_with_gpt(ingredients, [])
            QtWidgets.QMessageBox.information(self, "No local matches — GPT suggestions", suggestion)

    def manage_pantry(self):
        dlg = PantryDialog(self.db, parent=self)
        dlg.exec_()

    def show_grocery(self):
        dlg = GroceryDialog(self.db, parent=self)
        dlg.exec_()

    def send_chat(self):
        msg = self.chat_input.text().strip()
        if not msg:
            return
        self.chat_log.append(f"You: {msg}\n")
        # include context if a recipe is selected
        context = None
        if hasattr(self, 'current_recipe'):
            context = self.current_recipe
        resp = self.gpt.chat_with_gpt(msg, context=context)
        self.chat_log.append(f"Assistant: {resp}\n")
        self.chat_input.clear()

    def start_cooking(self):
        if not hasattr(self, 'current_recipe'):
            QtWidgets.QMessageBox.information(self, "No recipe selected", "Please select a recipe first.")
            return
        dlg = StepByStepDialog(self.db, self.gpt, self.current_recipe, parent=self)
        dlg.exec_()

# Simple dialogs for pantry and grocery
class PantryDialog(QtWidgets.QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pantry")
        self.db = db
        v = QtWidgets.QVBoxLayout(self)
        self.listw = QtWidgets.QListWidget()
        v.addWidget(self.listw)
        h = QtWidgets.QHBoxLayout()
        self.add_line = QtWidgets.QLineEdit()
        self.add_btn = QtWidgets.QPushButton("Add")
        self.add_btn.clicked.connect(self.add_item)
        self.remove_btn = QtWidgets.QPushButton("Remove Selected")
        self.remove_btn.clicked.connect(self.remove_item)
        h.addWidget(self.add_line)
        h.addWidget(self.add_btn)
        h.addWidget(self.remove_btn)
        v.addLayout(h)
        self.load_items()

    def load_items(self):
        self.listw.clear()
        for it in self.db.get_pantry_items():
            self.listw.addItem(it)

    def add_item(self):
        it = self.add_line.text().strip()
        if not it:
            return
        self.db.add_pantry_item(it)
        self.add_line.clear()
        self.load_items()

    def remove_item(self):
        sel = self.listw.currentItem()
        if not sel:
            return
        name = sel.text()
        self.db.remove_pantry_item(name)
        self.load_items()

class GroceryDialog(QtWidgets.QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Grocery List")
        self.db = db
        v = QtWidgets.QVBoxLayout(self)
        self.listw = QtWidgets.QListWidget()
        v.addWidget(self.listw)
        h = QtWidgets.QHBoxLayout()
        self.add_line = QtWidgets.QLineEdit()
        self.add_btn = QtWidgets.QPushButton("Add")
        self.add_btn.clicked.connect(self.add_item)
        self.remove_btn = QtWidgets.QPushButton("Remove Selected")
        self.remove_btn.clicked.connect(self.remove_item)
        self.export_btn = QtWidgets.QPushButton("Export as text file")
        self.export_btn.clicked.connect(self.export_file)
        h.addWidget(self.add_line)
        h.addWidget(self.add_btn)
        h.addWidget(self.remove_btn)
        h.addWidget(self.export_btn)
        v.addLayout(h)
        self.load_items()

    def load_items(self):
        self.listw.clear()
        for it in self.db.get_grocery_items():
            self.listw.addItem(it)

    def add_item(self):
        it = self.add_line.text().strip()
        if not it:
            return
        self.db.add_grocery_item(it)
        self.add_line.clear()
        self.load_items()

    def remove_item(self):
        sel = self.listw.currentItem()
        if not sel:
            return
        name = sel.text()
        self.db.remove_grocery_item(name)
        self.load_items()

    def export_file(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save grocery list", "grocery_list.txt", "Text files (*.txt)")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            for it in self.db.get_grocery_items():
                f.write(it + "\n")
        QtWidgets.QMessageBox.information(self, "Saved", f"Grocery list saved to {path}")

class StepByStepDialog(QtWidgets.QDialog):
    def __init__(self, db, gpt, recipe, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Cooking: {recipe['title']}")
        self.recipe = recipe
        self.db = db
        self.gpt = gpt
        self.index = 0
        v = QtWidgets.QVBoxLayout(self)
        self.step_label = QtWidgets.QLabel()
        self.step_label.setWordWrap(True)
        v.addWidget(self.step_label)
        h = QtWidgets.QHBoxLayout()
        self.prev_btn = QtWidgets.QPushButton("Previous")
        self.prev_btn.clicked.connect(self.prev_step)
        self.next_btn = QtWidgets.QPushButton("Next")
        self.next_btn.clicked.connect(self.next_step)
        self.tip_btn = QtWidgets.QPushButton("Ask Tip")
        self.tip_btn.clicked.connect(self.ask_tip)
        h.addWidget(self.prev_btn)
        h.addWidget(self.next_btn)
        h.addWidget(self.tip_btn)
        v.addLayout(h)
        self.update_step()

    def update_step(self):
        s = self.recipe['steps'][self.index]
        self.step_label.setText(f"Step {self.index+1} of {len(self.recipe['steps'])}:\n\n{s}")

    def next_step(self):
        if self.index < len(self.recipe['steps']) - 1:
            self.index += 1
            self.update_step()

    def prev_step(self):
        if self.index > 0:
            self.index -= 1
            self.update_step()

    def ask_tip(self):
        step_text = self.recipe['steps'][self.index]
        prompt = f"I am on this recipe step: '{step_text}'. Give me a short, practical tip related to this step."
        resp = self.gpt.chat_with_gpt(prompt, context=self.recipe)
        QtWidgets.QMessageBox.information(self, "Tip", resp)

def main():
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
