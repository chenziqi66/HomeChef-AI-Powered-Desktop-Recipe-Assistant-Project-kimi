#!/usr/bin/env python3
"""
HomeChef — main PyQt5 application
Simple, beginner-friendly implementation.
"""

import sys, os, json, random
from datetime import datetime, timedelta
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import Qt, QMimeData
from PyQt5.QtGui import QDrag, QCursor
from db import Database
from gpt_client import GPTClient

DB_PATH = os.path.join(os.path.dirname(__file__), "homechef.db")

DAYS_OF_WEEK = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
MEAL_TYPES = ['breakfast', 'lunch', 'dinner']
MEAL_TYPE_LABELS = {'breakfast': '早餐', 'lunch': '午餐', 'dinner': '晚餐'}

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HomeChef — AI Recipe Assistant")
        self.resize(1000, 600)

        # Database and GPT client
        self.db = Database(DB_PATH)
        self.db.init_db()  # create tables and seed if needed
        self.db.init_meal_plan_tables()  # initialize meal plan tables
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

        # Meal Planner button
        self.meal_plan_btn = QtWidgets.QPushButton("膳食计划")
        self.meal_plan_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.meal_plan_btn.clicked.connect(self.open_meal_planner)
        left_v.addWidget(self.meal_plan_btn)

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

    def open_meal_planner(self):
        dlg = MealPlannerDialog(self.db, self.gpt, parent=self)
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

class DraggableMealLabel(QtWidgets.QLabel):
    """可拖拽的餐食标签"""
    def __init__(self, recipe_id, title, parent=None):
        super().__init__(title, parent)
        self.recipe_id = recipe_id
        self.recipe_title = title
        self.drag_start_position = None
        self.setStyleSheet("""
            QLabel {
                background-color: #e3f2fd;
                border: 1px solid #2196F3;
                border-radius: 4px;
                padding: 4px;
                font-size: 11px;
            }
            QLabel:hover {
                background-color: #bbdefb;
                border: 1px solid #1976D2;
            }
        """)
        self.setCursor(QtGui.QCursor(Qt.OpenHandCursor))
        self.setWordWrap(True)
        self.setMinimumHeight(30)
        self.setAlignment(Qt.AlignCenter)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()
            self.setCursor(QtGui.QCursor(Qt.ClosedHandCursor))
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.setCursor(QtGui.QCursor(Qt.OpenHandCursor))
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if self.drag_start_position is None:
            return
        if (event.pos() - self.drag_start_position).manhattanLength() < QtWidgets.QApplication.startDragDistance():
            return

        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(f"{self.recipe_id}|{self.recipe_title}")
        drag.setMimeData(mime_data)
        
        # Set drag pixmap for visual feedback
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())
        
        drag.exec_(Qt.CopyAction)


class MealSlotWidget(QtWidgets.QFrame):
    """餐食槽位控件 - 可接受拖拽"""
    meal_dropped = QtCore.pyqtSignal(int, str, int, str)  # day, meal_type, recipe_id, recipe_title

    def __init__(self, day_index, meal_type, parent=None):
        super().__init__(parent)
        self.day_index = day_index
        self.meal_type = meal_type
        self.recipe_id = None
        self.recipe_title = None
        self.setAcceptDrops(True)
        self.setMinimumHeight(50)
        self.setFrameStyle(QtWidgets.QFrame.StyledPanel | QtWidgets.QFrame.Sunken)
        self.setStyleSheet("""
            MealSlotWidget {
                background-color: #f5f5f5;
                border: 2px dashed #ccc;
                border-radius: 6px;
            }
            MealSlotWidget[hasMeal="true"] {
                background-color: #e8f5e9;
                border: 2px solid #4CAF50;
            }
        """)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(4, 4, 4, 4)

        self.label = QtWidgets.QLabel("拖放食谱到这里")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("color: #999; font-size: 10px;")
        self.layout.addWidget(self.label)

        self.clear_btn = QtWidgets.QPushButton("×")
        self.clear_btn.setFixedSize(16, 16)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff5252;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 10px;
            }
        """)
        self.clear_btn.hide()
        self.clear_btn.clicked.connect(self.clear_meal)
        self._is_hovered = False

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.setDropAction(Qt.CopyAction)
            event.accept()
            self._is_hovered = True
            self._apply_hover_style()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.setDropAction(Qt.CopyAction)
            event.accept()
            if not self._is_hovered:
                self._is_hovered = True
                self._apply_hover_style()

    def dragLeaveEvent(self, event):
        self._is_hovered = False
        self._apply_normal_style()

    def dropEvent(self, event):
        self._is_hovered = False
        text = event.mimeData().text()
        if "|" in text:
            try:
                recipe_id_str, recipe_title = text.split("|", 1)
                recipe_id = int(recipe_id_str)
                self.set_meal(recipe_id, recipe_title)
                self.meal_dropped.emit(self.day_index, self.meal_type, recipe_id, recipe_title)
                event.acceptProposedAction()
            except (ValueError, IndexError):
                event.ignore()
        else:
            event.ignore()
        self._apply_normal_style()

    def _apply_hover_style(self):
        """应用悬停时的黄色样式"""
        self.setStyleSheet("""
            MealSlotWidget {
                background-color: #fff3e0;
                border: 2px dashed #FF9800;
                border-radius: 6px;
            }
        """)

    def _apply_normal_style(self):
        """应用正常样式（根据是否有餐食）"""
        if self.recipe_id:
            self.setStyleSheet("""
                MealSlotWidget {
                    background-color: #e8f5e9;
                    border: 2px solid #4CAF50;
                    border-radius: 6px;
                }
            """)
        else:
            self.setStyleSheet("""
                MealSlotWidget {
                    background-color: #f5f5f5;
                    border: 2px dashed #ccc;
                    border-radius: 6px;
                }
            """)

    def set_meal(self, recipe_id, recipe_title):
        self.recipe_id = recipe_id
        self.recipe_title = recipe_title
        self.label.setText(recipe_title)
        self.label.setStyleSheet("color: #2e7d32; font-weight: bold; font-size: 11px;")
        self.clear_btn.show()
        # Add clear button to layout if not already there
        if self.clear_btn not in [self.layout.itemAt(i).widget() for i in range(self.layout.count())]:
            self.layout.addWidget(self.clear_btn, alignment=Qt.AlignRight)
        self._apply_normal_style()

    def clear_meal(self):
        self.recipe_id = None
        self.recipe_title = None
        self.label.setText("拖放食谱到这里")
        self.label.setStyleSheet("color: #999; font-size: 10px;")
        self.clear_btn.hide()
        self._apply_normal_style()
        self.meal_dropped.emit(self.day_index, self.meal_type, 0, "")


class MealPlannerDialog(QtWidgets.QDialog):
    """膳食计划主对话框"""
    def __init__(self, db, gpt, parent=None):
        super().__init__(parent)
        self.db = db
        self.gpt = gpt
        self.current_plan_id = None
        self.meal_slots = {}  # {(day, meal_type): MealSlotWidget}

        self.setWindowTitle("每周膳食计划")
        self.resize(1200, 800)

        self.setup_ui()
        self.load_plans()
        self.load_recipes_for_drag()

    def setup_ui(self):
        main_layout = QtWidgets.QHBoxLayout(self)

        # Left panel: Plan list and controls
        left_panel = QtWidgets.QVBoxLayout()

        # Plan selection
        plan_header = QtWidgets.QHBoxLayout()
        plan_header.addWidget(QtWidgets.QLabel("膳食计划:"))
        self.plan_combo = QtWidgets.QComboBox()
        self.plan_combo.currentIndexChanged.connect(self.on_plan_selected)
        plan_header.addWidget(self.plan_combo)
        left_panel.addLayout(plan_header)

        # Plan controls
        plan_btns = QtWidgets.QHBoxLayout()
        self.new_plan_btn = QtWidgets.QPushButton("新建计划")
        self.new_plan_btn.clicked.connect(self.create_new_plan)
        self.delete_plan_btn = QtWidgets.QPushButton("删除")
        self.delete_plan_btn.clicked.connect(self.delete_current_plan)
        plan_btns.addWidget(self.new_plan_btn)
        plan_btns.addWidget(self.delete_plan_btn)
        left_panel.addLayout(plan_btns)

        # Separator
        left_panel.addWidget(QtWidgets.QLabel("─" * 30))

        # Plan settings
        settings_group = QtWidgets.QGroupBox("计划设置")
        settings_layout = QtWidgets.QFormLayout()

        self.diet_type_combo = QtWidgets.QComboBox()
        self.diet_type_combo.addItems(["均衡饮食", "素食", "低碳水", "高蛋白", "低脂"])
        settings_layout.addRow("饮食类型:", self.diet_type_combo)

        self.max_time_spin = QtWidgets.QSpinBox()
        self.max_time_spin.setRange(10, 180)
        self.max_time_spin.setValue(60)
        self.max_time_spin.setSuffix(" 分钟")
        settings_layout.addRow("最大烹饪时间:", self.max_time_spin)

        self.preferences_edit = QtWidgets.QLineEdit()
        self.preferences_edit.setPlaceholderText("如: 不辣, 少油...")
        settings_layout.addRow("口味偏好:", self.preferences_edit)

        settings_group.setLayout(settings_layout)
        left_panel.addWidget(settings_group)

        # Generate button
        self.generate_btn = QtWidgets.QPushButton("一键生成智能计划")
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 12px;
                font-size: 14px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.generate_btn.clicked.connect(self.generate_smart_plan)
        left_panel.addWidget(self.generate_btn)

        left_panel.addSpacing(20)

        # Shopping list button
        self.shopping_btn = QtWidgets.QPushButton("生成采购清单")
        self.shopping_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 6px;
            }
        """)
        self.shopping_btn.clicked.connect(self.show_shopping_list)
        left_panel.addWidget(self.shopping_btn)

        # Nutrition analysis button
        self.nutrition_btn = QtWidgets.QPushButton("营养均衡检测")
        self.nutrition_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 6px;
            }
        """)
        self.nutrition_btn.clicked.connect(self.analyze_nutrition)
        left_panel.addWidget(self.nutrition_btn)

        left_panel.addStretch()

        # Recipe list for drag
        left_panel.addWidget(QtWidgets.QLabel("可拖拽的食谱:"))
        self.recipe_scroll = QtWidgets.QScrollArea()
        self.recipe_scroll.setWidgetResizable(True)
        self.recipe_container = QtWidgets.QWidget()
        self.recipe_layout = QtWidgets.QVBoxLayout(self.recipe_container)
        self.recipe_layout.setSpacing(4)
        self.recipe_scroll.setWidget(self.recipe_container)
        self.recipe_scroll.setMaximumHeight(300)
        left_panel.addWidget(self.recipe_scroll)

        main_layout.addLayout(left_panel, 2)

        # Right panel: 7-day meal plan grid
        right_panel = QtWidgets.QVBoxLayout()

        # Header
        header = QtWidgets.QLabel("7天膳食计划表")
        header.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        header.setAlignment(Qt.AlignCenter)
        right_panel.addWidget(header)

        # Scroll area for meal grid
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_container = QtWidgets.QWidget()
        self.meal_grid = QtWidgets.QGridLayout(scroll_container)
        self.meal_grid.setSpacing(8)

        # Headers
        self.meal_grid.addWidget(QtWidgets.QLabel(""), 0, 0)  # Empty corner
        for col, day in enumerate(DAYS_OF_WEEK, 1):
            label = QtWidgets.QLabel(day)
            label.setStyleSheet("font-weight: bold; font-size: 12px; padding: 5px;")
            label.setAlignment(Qt.AlignCenter)
            self.meal_grid.addWidget(label, 0, col)

        # Meal type rows
        for row, meal_type in enumerate(MEAL_TYPES, 1):
            label = QtWidgets.QLabel(MEAL_TYPE_LABELS[meal_type])
            label.setStyleSheet("font-weight: bold; font-size: 12px; padding: 5px;")
            self.meal_grid.addWidget(label, row, 0)

            for col, day in enumerate(DAYS_OF_WEEK, 1):
                slot = MealSlotWidget(col - 1, meal_type)
                slot.meal_dropped.connect(self.on_meal_dropped)
                self.meal_slots[(col - 1, meal_type)] = slot
                self.meal_grid.addWidget(slot, row, col)

        scroll.setWidget(scroll_container)
        right_panel.addWidget(scroll)

        main_layout.addLayout(right_panel, 5)

    def load_plans(self):
        self.plan_combo.clear()
        plans = self.db.get_all_meal_plans()
        for plan in plans:
            self.plan_combo.addItem(f"{plan['name']} ({plan['created_at'][:10]})", plan['id'])
        if plans:
            self.load_plan_data(plans[0]['id'])

    def load_plan_data(self, plan_id):
        self.current_plan_id = plan_id
        plan = self.db.get_meal_plan(plan_id)
        if not plan:
            return

        # Clear all slots
        for slot in self.meal_slots.values():
            slot.clear_meal()

        # Load meals into slots
        for day, meals in plan['meals'].items():
            for meal_type, meal_data in meals.items():
                key = (day, meal_type)
                if key in self.meal_slots:
                    self.meal_slots[key].set_meal(meal_data['recipe_id'], meal_data['title'])

    def on_plan_selected(self, index):
        if index >= 0:
            plan_id = self.plan_combo.itemData(index)
            self.load_plan_data(plan_id)

    def create_new_plan(self):
        name, ok = QtWidgets.QInputDialog.getText(self, "新建膳食计划", "计划名称:")
        if ok and name:
            plan_id = self.db.create_meal_plan(name)
            self.load_plans()
            # Select the new plan
            for i in range(self.plan_combo.count()):
                if self.plan_combo.itemData(i) == plan_id:
                    self.plan_combo.setCurrentIndex(i)
                    break

    def delete_current_plan(self):
        if self.current_plan_id is None:
            return
        reply = QtWidgets.QMessageBox.question(
            self, "确认删除", "确定要删除当前膳食计划吗?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if reply == QtWidgets.QMessageBox.Yes:
            self.db.delete_meal_plan(self.current_plan_id)
            self.load_plans()

    def on_meal_dropped(self, day, meal_type, recipe_id, recipe_title):
        if self.current_plan_id is None:
            QtWidgets.QMessageBox.warning(self, "错误", "请先创建或选择一个膳食计划")
            return
        if recipe_id == 0:
            # Clear meal
            self.db.remove_meal_from_plan(self.current_plan_id, day, meal_type)
        else:
            self.db.add_meal_to_plan(self.current_plan_id, day, meal_type, recipe_id)

    def generate_smart_plan(self):
        """根据用户偏好智能生成7天膳食计划"""
        if self.current_plan_id is None:
            QtWidgets.QMessageBox.warning(self, "错误", "请先创建一个膳食计划")
            return

        diet_type = self.diet_type_combo.currentText()
        max_time = self.max_time_spin.value()
        preferences = self.preferences_edit.text()

        # Get all recipes
        all_recipes = self.db.get_all_recipes()

        if not all_recipes:
            QtWidgets.QMessageBox.warning(self, "无食谱", "请先添加一些食谱")
            return

        # Filter recipes by time
        suitable_recipes = [r for r in all_recipes if r.get('time', 999) <= max_time]

        # If no recipes match time filter, use all recipes
        if not suitable_recipes:
            suitable_recipes = all_recipes

        # Shuffle for variety
        random.shuffle(suitable_recipes)

        # Generate plan - cycle through recipes if not enough
        recipe_index = 0
        for day in range(7):
            for meal_type in MEAL_TYPES:
                # Cycle through available recipes
                recipe = suitable_recipes[recipe_index % len(suitable_recipes)]
                self.db.add_meal_to_plan(self.current_plan_id, day, meal_type, recipe['id'])
                recipe_index += 1

        # Reload to show generated plan
        self.load_plan_data(self.current_plan_id)
        QtWidgets.QMessageBox.information(
            self, "完成",
            f"智能膳食计划已生成!\n使用了 {len(suitable_recipes)} 个食谱循环填充21个餐位"
        )

    def show_shopping_list(self):
        """显示采购清单"""
        if self.current_plan_id is None:
            QtWidgets.QMessageBox.warning(self, "错误", "请先选择一个膳食计划")
            return

        ingredients = self.db.get_meal_plan_ingredients(self.current_plan_id)
        if not ingredients:
            QtWidgets.QMessageBox.information(self, "提示", "当前计划没有食谱")
            return

        dlg = ShoppingListDialog(ingredients, self)
        dlg.exec_()

    def analyze_nutrition(self):
        """分析营养均衡性"""
        if self.current_plan_id is None:
            QtWidgets.QMessageBox.warning(self, "错误", "请先选择一个膳食计划")
            return

        plan = self.db.get_meal_plan(self.current_plan_id)
        if not plan or not plan['meals']:
            QtWidgets.QMessageBox.information(self, "提示", "当前计划没有食谱")
            return

        # Simple nutrition analysis based on variety
        total_meals = sum(len(day_meals) for day_meals in plan['meals'].values())
        unique_ingredients = set()
        total_cooking_time = 0

        for day_meals in plan['meals'].values():
            for meal in day_meals.values():
                unique_ingredients.update(ing.lower() for ing in meal['ingredients'])
                total_cooking_time += meal.get('time', 0)

        avg_time = total_cooking_time / total_meals if total_meals > 0 else 0

        # Generate analysis report
        report = f"""
膳食计划营养分析报告
═══════════════════════════════

📊 基本统计:
   • 总餐数: {total_meals} 餐
   • 覆盖天数: {len(plan['meals'])} 天
   • 平均烹饪时间: {avg_time:.1f} 分钟/餐
   • 食材种类: {len(unique_ingredients)} 种

🥗 食材多样性评分: {min(len(unique_ingredients) // 3, 10)}/10
   (食材种类越多，营养越均衡)

⏱️ 时间合理性评分: {max(10 - int(avg_time) // 15, 1)}/10
   (平均烹饪时间适中)

💡 建议:
   • 建议每天摄入至少5种不同颜色的蔬菜
   • 蛋白质来源建议多样化(肉/蛋/豆/鱼轮换)
   • 注意主食粗细搭配

*注: 详细营养分析需要更完整的食材营养数据库
        """

        QtWidgets.QMessageBox.information(self, "营养分析报告", report)

    def load_recipes_for_drag(self):
        """加载可拖拽的食谱列表"""
        # Clear existing
        while self.recipe_layout.count():
            item = self.recipe_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        recipes = self.db.get_all_recipes()
        for recipe in recipes:
            label = DraggableMealLabel(recipe['id'], recipe['title'])
            self.recipe_layout.addWidget(label)

        self.recipe_layout.addStretch()


class ShoppingListDialog(QtWidgets.QDialog):
    """采购清单对话框"""
    def __init__(self, ingredients, parent=None):
        super().__init__(parent)
        self.setWindowTitle("采购清单")
        self.resize(400, 600)

        layout = QtWidgets.QVBoxLayout(self)

        # Title
        title = QtWidgets.QLabel("本周采购清单")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Info label
        info = QtWidgets.QLabel(f"共 {len(ingredients)} 种食材 (已去重)")
        info.setStyleSheet("color: #666;")
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)

        # List
        self.list_widget = QtWidgets.QListWidget()
        for ing in ingredients:
            item = QtWidgets.QListWidgetItem(f"☐ {ing}")
            self.list_widget.addItem(item)
        layout.addWidget(self.list_widget)

        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()

        export_btn = QtWidgets.QPushButton("导出为文本文件")
        export_btn.clicked.connect(self.export_list)
        btn_layout.addWidget(export_btn)

        add_grocery_btn = QtWidgets.QPushButton("添加到购物清单")
        add_grocery_btn.clicked.connect(self.add_to_grocery)
        btn_layout.addWidget(add_grocery_btn)

        close_btn = QtWidgets.QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

        self.ingredients = ingredients

    def export_list(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "保存采购清单", "shopping_list.txt", "Text files (*.txt)"
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write("本周膳食计划采购清单\n")
                f.write("=" * 40 + "\n\n")
                for ing in self.ingredients:
                    f.write(f"☐ {ing}\n")
            QtWidgets.QMessageBox.information(self, "已保存", f"采购清单已保存到:\n{path}")

    def add_to_grocery(self):
        # Get parent dialog's db
        parent = self.parent()
        if parent and hasattr(parent, 'db'):
            for ing in self.ingredients:
                parent.db.add_grocery_item(ing)
            QtWidgets.QMessageBox.information(self, "已添加", "食材已添加到购物清单!")


def main():
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
