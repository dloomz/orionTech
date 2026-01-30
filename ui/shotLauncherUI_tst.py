import sys
import os
import subprocess
import json

import shutil

import re
import uuid

from datetime import datetime, timedelta
import time

import argparse

# ORION TECH INTEGRATION
current_ui_dir = os.path.dirname(os.path.abspath(__file__))
orion_package_root = os.path.dirname(current_ui_dir)

if orion_package_root not in sys.path:
    sys.path.append(orion_package_root)

try:
    from core.orionUtils import OrionUtils
except ImportError:
    try:
        from orionTech.core.orionUtils import OrionUtils
    except ImportError as e:
        print(f"CRITICAL ERROR: Could not import OrionUtils.\nChecked path: {orion_package_root}\nError: {e}")
        sys.exit()
        
try:
    from core.prefsUtils import PrefsUtils
except ImportError:
    try:
        from orionTech.core.prefsUtils import PrefsUtils
    except ImportError as e:
        print(f"CRITICAL ERROR: Could not import PrefUtils.\nChecked path: {orion_package_root}\nError: {e}")
        sys.exit()
        
try:
    from core.systemUtils import SystemUtils
except ImportError:
    try:
        from orionTech.core.systemUtils import SystemUtils
    except ImportError as e:
        print(f"CRITICAL ERROR: Could not import SystemUtils.\nChecked path: {orion_package_root}\nError: {e}")
        sys.exit()

orion_utils = OrionUtils(check_schema=False)
pref_utils = PrefsUtils(orion_utils)
system_utils = SystemUtils(orion_utils, pref_utils)

#IMPORT CUSTOM LAUNCHERS
try:

    from dcc.maya.maya_launcher import launch_maya
except ImportError as e:
    print(f"Warning: Could not import maya_launcher: {e}")
    launch_maya = None
    
try:

    from dcc.nuke.nuke_launcher import launch_nuke
except ImportError as e:
    print(f"Warning: Could not import nuke_launcher: {e}")
    launch_nuke = None
    
try:

    from dcc.houdini.houdini_launcher import launch_houdini
except ImportError as e:
    print(f"Warning: Could not import houdini_launcher: {e}")
    launch_houdini = None
    
try:

    from dcc.mari.mari_launcher import launch_mari
except ImportError as e:
    print(f"Warning: Could not import mari_launcher: {e}")
    launch_mari = None

#success flag
import_success = False

#loop 3 times
for attempt in range(3):
    try:
        #try to import module
        from PyQt5.QtWidgets import (
            QApplication, QWidget, QLabel, QPushButton,
            QVBoxLayout, QHBoxLayout, QFrame, QGridLayout,
            QSizePolicy, QScrollArea, QSplitter, QInputDialog,
            QMessageBox, QLineEdit, QSpinBox, QTextEdit,
            QFormLayout, QFileDialog, QMenu, QAction, QComboBox, 
            QAbstractButton, QStackedWidget, QCheckBox, QSlider
        )
        from PyQt5.QtCore import Qt, pyqtSignal, QSize, QRect, QTimer
        from PyQt5.QtGui import QPixmap, QPainter
        
        #if we get here imports worked
        import_success = True
        break 

    except ImportError as e:
        #print error for debugging
        print(f"Attempt {attempt} failed: {e}")

        #handle logic based on which attempt just failed
        if attempt == 0:
            #native python failed, add work path for next try
            print("Adding Work Path...")
            if orion_utils.libs_path not in sys.path:
                sys.path.insert(0, orion_utils.libs_path)

        elif attempt == 1:
            #work path failed, add home path for next try
            print("Adding Home Path...")
            home_path = os.path.join(orion_utils.libs_path, "home_vers")
            #check if folder exists first
            if os.path.exists(home_path):
                if home_path not in sys.path:
                    sys.path.insert(0, home_path)
            else:
                print(f"Home path not found at: {home_path}")

        elif attempt == 2:
            #all attempts failed
            print("CRITICAL ERROR: Could not import PyQt5 from any location.")
            break

#final check
if not import_success:
    sys.exit()
    
#dictionary to cache loaded thumbnails
THUMB_CACHE = {}

# STYLE NOTES:
# ORION ORANGE = #FF6000

# HELPERS 
def get_scrollbar_style(bg_color):
    """Returns the CSS string for a consistent scrollbar style."""
    return f"""
        QScrollArea {{ background: transparent; border: none; }}
        QScrollBar:vertical {{ border: none; background: {bg_color}; width: 10px; margin: 0; }}
        QScrollBar::handle:vertical {{ background: #555; min-height: 20px; border-radius: 5px; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
    """

def get_cached_pixmap(path, target_size):
    """
    Loads, scales, and caches pixmaps for fast reuse.
    """
    if not path or not os.path.exists(path):
        return None

    #id to store path and size
    key = (path, target_size.width(), target_size.height())
    #check if in dictionary, return already present entry
    if key in THUMB_CACHE:
        return THUMB_CACHE[key]

    pixmap = QPixmap(path)
    if pixmap.isNull():
        return None
    #scale to fit target size
    pixmap = pixmap.scaled(
        target_size,
        Qt.KeepAspectRatio,
        Qt.SmoothTransformation
    )

    #store in cache
    THUMB_CACHE[key] = pixmap
    return pixmap

def get_path_variants(path):
    r"""
    Returns a dictionary with 'work' and 'home' keys containing the path
    remapped to P:\ (Work) and O:\ (Home) roots respectively.
    """
    if not path:
        return {}
    
    path = os.path.normpath(path)
    work_root = r"P:\all_work\studentGroups\ORION_CORPORATION"
    home_root = "O:\\"
    
    rel_path = None
    
    #check if currently in Work Root
    if path.lower().startswith(work_root.lower()):
        rel_path = path[len(work_root):].lstrip(os.sep)
        
    #check if currently in Home Root
    elif path.lower().startswith("o:"):
        #strip "O:\" or "O:"
        if len(path) > 3:
            rel_path = path[3:]
        elif len(path) == 3: # O:\
            rel_path = ""
        
    #Fallback: Try to find "ORION_CORPORATION"
    if rel_path is None and "ORION_CORPORATION" in path:
        parts = path.split("ORION_CORPORATION")
        if len(parts) > 1:
            rel_path = parts[1].lstrip(os.sep)
            
    if rel_path is not None:
        return {
            "work": os.path.join(work_root, rel_path),
            "home": os.path.join(home_root, rel_path)
        }
    
    #if path cannot be resolved, return original for both as fallback
    return {"work": path, "home": path}


# CUSTOM WIDGETS 
class ExportItemWidget(QFrame):
    """
    Widget for displaying Export files.
    """
    
    #create signal for actions, like publish/unpublish
    action_triggered = pyqtSignal(str, object) # action, self

    def __init__(self, filename, full_path, is_published=False):
        super().__init__()
        self.filename = filename
        self.full_path = full_path 
        self.is_published = is_published
        
        self.setFixedHeight(60)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 5, 10, 5)
        self.layout.setSpacing(10)
        
        # ICON / IMAGE BLOCK 
        self.icon_block = QLabel()
        self.icon_block.setFixedSize(40, 40)
        self.icon_block.setAlignment(Qt.AlignCenter)
        
        #If  an image file, show image. Else show color block.
        image_loaded = False
        valid_img_exts = ['.jpg', '.jpeg', '.png', '.tga', '.tiff', '.tif', '.bmp', '.exr']
        file_ext = os.path.splitext(filename)[1].lower()
        
        if file_ext in valid_img_exts and os.path.exists(full_path):
            clean_path = full_path.replace("\\", "/")

            self.icon_block.setStyleSheet(f"""
                border-image: url('{clean_path}') 0 0 0 0 stretch stretch;
                border-radius: 4px;
                background-color: transparent;
            """)
            image_loaded = True
        
        if not image_loaded:

            bg_col = "#00ff00" if is_published else "#e65c00"
            self.icon_block.setStyleSheet(f"background-color: {bg_col}; border-radius: 4px;")
            
        self.layout.addWidget(self.icon_block)
        
        # Info Layout
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        info_layout.setAlignment(Qt.AlignVCenter)
        
        self.lbl_name = QLabel(filename)
        self.lbl_name.setStyleSheet("color: white; font-weight: bold; font-size: 11px; border: none;")
        info_layout.addWidget(self.lbl_name)
        
        if self.is_published:
            self.lbl_status = QLabel("PUBLISHED")
            self.lbl_status.setStyleSheet("color: #00ff00; font-size: 9px; font-weight: bold; border: none;")
            info_layout.addWidget(self.lbl_status)
        
        self.layout.addLayout(info_layout)
        self.update_style()

    def update_style(self):
        base_style = "ExportItemWidget { background-color: #2b2b2b; border-radius: 6px; }"
        if self.is_published:
            #green border for published
            self.setStyleSheet(base_style + "ExportItemWidget { border: 2px solid #00ff00; }")
        else:
            self.setStyleSheet(base_style + "ExportItemWidget { border: 1px solid #444; } ExportItemWidget:hover { border: 1px solid #666; background-color: #333; }")

    #add context menu on right click and also do mousePressEvent as normal
    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.show_context_menu(event.pos())
        super().mousePressEvent(event)

    def show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #333; color: white; border: 1px solid #555; } QMenu::item:selected { background-color: #555; }")
        
        #file actions
        action_open = QAction("Open File Location", self)
        action_open.triggered.connect(self.open_file_location)
        menu.addAction(action_open)

        #path varientss
        variants = get_path_variants(self.full_path)
        
        action_copy_local = QAction("Copy Path (Local)", self)
        action_copy_local.triggered.connect(self.copy_path)
        menu.addAction(action_copy_local)

        if variants:
            action_copy_work = QAction("Copy Work Path (P:)", self)
            action_copy_work.triggered.connect(lambda: self.copy_specific_path(variants.get("work")))
            menu.addAction(action_copy_work)

            action_copy_home = QAction("Copy Home Path (O:)", self)
            action_copy_home.triggered.connect(lambda: self.copy_specific_path(variants.get("home")))
            menu.addAction(action_copy_home)
        
        menu.addSeparator()
        
        #Publish Actions
        if self.is_published:
            action_pub = QAction("Unpublish (Move to BIN)", self)
            action_pub.triggered.connect(lambda: self.action_triggered.emit("unpublish", self))
        else:
            action_pub = QAction("Publish", self)
            action_pub.triggered.connect(lambda: self.action_triggered.emit("publish", self))
        menu.addAction(action_pub)

        menu.addSeparator()
            
        menu.exec_(self.mapToGlobal(pos))

    def open_file_location(self):
        #Open the file selected in explorer
        if not self.full_path:
            return
        path = os.path.normpath(self.full_path)
        if os.path.exists(path):
            subprocess.Popen(r'explorer /select,"' + path + '"')
    
    def copy_path(self):
        #copy full path to clipboard
        QApplication.clipboard().setText(self.full_path)

    def copy_specific_path(self, path):
        if path:
            QApplication.clipboard().setText(path)

    def set_published(self, state):
        self.is_published = state
        self.update_style()

#Represents Shot / Asset with thumbnail
class ShotButton(QPushButton):
    def __init__(self, text, color, full_data=None):
        super().__init__()
        self.setMinimumHeight(100)
        self.text_label = text
        self.full_data = full_data or {}
        self.is_active = False
        self.default_color = color

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)

        self.lbl = QLabel(text)
        self.box = QLabel()
        self.box.setFixedSize(142, 80)
        self.box.setAlignment(Qt.AlignCenter)
        self.box.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        layout.addWidget(self.lbl)
        layout.addStretch()
        layout.addWidget(self.box)
        self.update_style()

    def set_active(self, active):
        self.is_active = active
        self.update_style()

    def update_style(self):
        if self.is_active:
            btn_style = "QPushButton { background-color: white; border-radius: 8px; border: none; text-align: left; }"
            txt_color = "#222"
        else:
            btn_style = "QPushButton { background-color: #3c3c3c; border-radius: 8px; border: none; text-align: left; } QPushButton:hover { background-color: #4d4d4d; }"
            txt_color = "white"

        self.setStyleSheet(btn_style)
        self.lbl.setStyleSheet(f"color: {txt_color}; font-weight: bold; font-size: 14px; border: none; background: transparent;")

        self.box.setStyleSheet("border: 1px solid #555; border-radius: 4px;")
        
        # Load thumbnail 
        thumb_path = self.full_data.get("thumbnail_path")
        if thumb_path and isinstance(thumb_path, str) and thumb_path.strip():
            clean_path = thumb_path.strip().replace("\\", "/")
            self.box.setStyleSheet(f"""
                border-image: url('{clean_path}') 0 0 0 0 stretch stretch;
                border-radius: 4px;
                border: 1px solid #555;
            """)
            self.box.setText("") 
        else:
            self.box.setStyleSheet(f"background-color: {self.default_color}; border-radius: 4px;")

class SpecButton(QPushButton):
    def __init__(self, text, color):
        super().__init__()
        self.setMinimumHeight(45)
        self.text_label = text
        self.is_active = False
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 5, 10, 5)
        self.lbl = QLabel(text)
        self.box = QLabel()
        self.box.setFixedSize(35, 20)
        self.box.setStyleSheet(f"background-color: {color}; border-radius: 3px;")
        layout.addWidget(self.lbl)
        layout.addStretch()
        layout.addWidget(self.box)
        self.update_style()

    def set_active(self, active):
        self.is_active = active
        self.update_style()

    def update_style(self):
        if self.is_active:
            style = "QPushButton { background-color: #555555; border-radius: 6px; border: none; text-align: left; }"
            txt_color = "white"
        else:
            style = "QPushButton { background-color: #333333; border-radius: 6px; border: none; text-align: left; } QPushButton:hover { background-color: #444444; }"
            txt_color = "#888"
        self.setStyleSheet(style)
        self.lbl.setStyleSheet(f"color: {txt_color}; font-weight: bold; font-size: 11px; border: none; background: transparent;")

class TaskButton(QPushButton):
    def __init__(self, text, color, full_path=None):
        super().__init__()
        self.setMinimumHeight(35) 
        self.text_label = text
        self.full_path = full_path
        self.is_active = False
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 2, 10, 2)
        self.bullet = QLabel("•")
        self.bullet.setStyleSheet("color: #666; font-size: 16px; margin-right: 5px; background: transparent; border: none;")
        layout.addWidget(self.bullet)

        self.lbl = QLabel(text)
        self.box = QLabel()
        self.box.setFixedSize(25, 15)
        self.box.setStyleSheet(f"background-color: {color}; border-radius: 2px;")
        layout.addWidget(self.lbl)
        layout.addStretch()
        layout.addWidget(self.box)
        self.update_style()

    def set_active(self, active):
        self.is_active = active
        self.update_style()

    def update_style(self):
        if self.is_active:
            style = "QPushButton { background-color: #eee; border-radius: 4px; border: none; text-align: left; }"
            txt_color = "#222"
            bullet_color = "#222"
        else:
            style = "QPushButton { background-color: #2b2b2b; border-radius: 4px; border: none; text-align: left; } QPushButton:hover { background-color: #383838; }"
            txt_color = "#bbb"
            bullet_color = "#666"
        self.setStyleSheet(style)
        self.lbl.setStyleSheet(f"color: {txt_color}; font-size: 11px; border: none; background: transparent;")
        self.bullet.setStyleSheet(f"color: {bullet_color}; font-size: 16px; margin-right: 5px; background: transparent; border: none;")
        
    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.show_context_menu(event.pos())
        super().mousePressEvent(event)

    def show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #333; color: white; border: 1px solid #555; } QMenu::item:selected { background-color: #555; }")        

        # New File Actions
        action_open = QAction("Open File Location", self)
        action_open.triggered.connect(self.open_file_location)
        menu.addAction(action_open)

        # Path Variants
        variants = get_path_variants(self.full_path)
        
        action_copy_local = QAction("Copy Path (Local)", self)
        action_copy_local.triggered.connect(self.copy_path)
        menu.addAction(action_copy_local)

        if variants:
            action_copy_work = QAction("Copy Work Path (P:)", self)
            action_copy_work.triggered.connect(lambda: self.copy_specific_path(variants.get("work")))
            menu.addAction(action_copy_work)

            action_copy_home = QAction("Copy Home Path (O:)", self)
            action_copy_home.triggered.connect(lambda: self.copy_specific_path(variants.get("home")))
            menu.addAction(action_copy_home)
            
        menu.exec_(self.mapToGlobal(pos))

    def open_file_location(self):
        # Opens Explorer with the file selected
        path = os.path.normpath(self.full_path)
        if os.path.exists(path):
            subprocess.Popen(r'explorer /select,"' + path + '"')
    
    def copy_path(self):
        QApplication.clipboard().setText(self.full_path)

    def copy_specific_path(self, path):
        if path:
            QApplication.clipboard().setText(path)

class SpecialismGroup(QWidget):
    def __init__(self, spec_name, full_path, parent_ui):
        super().__init__()
        self.spec_name = spec_name
        self.full_path = full_path
        self.parent_ui = parent_ui
        self.is_expanded = False
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(2)
        
        color = "#009966"
        
        self.header_btn = SpecButton(spec_name, color)
        self.header_btn.clicked.connect(self.toggle_expand)
        self.layout.addWidget(self.header_btn)
        
        self.task_container = QWidget()
        self.task_layout = QVBoxLayout(self.task_container)
        self.task_layout.setContentsMargins(30, 10, 0, 10) 
        self.task_layout.setSpacing(2)
        
        self.layout.addWidget(self.task_container)
        self.task_container.setVisible(False)
        self.tasks_loaded = False

    def toggle_expand(self):
        self.is_expanded = not self.is_expanded
        self.task_container.setVisible(self.is_expanded)
        self.header_btn.set_active(self.is_expanded)
        if self.is_expanded and not self.tasks_loaded:
            self.populate_tasks()
            self.tasks_loaded = True

    def populate_tasks(self):
        while self.task_layout.count():
            child = self.task_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()

        if os.path.exists(self.full_path):
            items = sorted([d for d in os.listdir(self.full_path) if os.path.isdir(os.path.join(self.full_path, d))])
            ignore = ["__pycache__"]
            items = [i for i in items if i not in ignore and not i.startswith(".")]

            for task in items:
                color = "#ff33cc" 
                if task == "PUBLISH": color = "#ff0033"
                if task == "WORK": color = "#ff6666"
                full_task_path = os.path.join(self.full_path, task)
                btn = TaskButton(task, color, full_task_path)
                btn.clicked.connect(lambda checked, b=btn, p=full_task_path: self.parent_ui.on_task_select(b, p))
                self.task_layout.addWidget(btn)

            add_btn = QPushButton("+ New Task")
            add_btn.setStyleSheet("""
                QPushButton { background-color: transparent; color: #555; border: 1px dashed #444; border-radius: 4px; height: 25px; text-align: left; padding-left: 18px; }
                QPushButton:hover { background-color: #2a2a2a; color: #888; border-color: #666; }
            """)
            add_btn.clicked.connect(self.create_new_task)
            self.task_layout.addWidget(add_btn)

    def create_new_task(self):
        text, ok = QInputDialog.getText(self, "New Task Folder", f"Create new folder inside {self.spec_name}:")
        if ok and text:
            new_path = os.path.join(self.full_path, text)
            try:
                os.makedirs(new_path, exist_ok=True)

                export_path = os.path.join(new_path, "EXPORT")
                published_path = os.path.join(export_path, "PUBLISHED")
                
                os.makedirs(export_path, exist_ok=True)
                os.makedirs(published_path, exist_ok=True)

                self.populate_tasks() 
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

class MenuSwitch(QFrame):
    
    mode_changed = pyqtSignal(str) 
    
    def __init__(self):
        super().__init__()
        
        self.setFixedSize(750, 34)
        self.setStyleSheet("background-color: #333; border-radius: 17px;")
        
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.setLayout(self.layout)
        
        self.btn_prod = QPushButton("Production")
        self.btn_apps = QPushButton("Apps")
        self.btn_renders = QPushButton("Renders")
        self.btn_vault = QPushButton("Vault")
        self.btn_settings = QPushButton("Settings")
        
        self.btn_list = [self.btn_prod, self.btn_apps, self.btn_renders, self.btn_vault, self.btn_settings]
        
        for btn in self.btn_list:
            btn.setCheckable(True)
            btn.setFixedSize(150, 34) 
            btn.clicked.connect(self.toggle_mode)
            self.layout.addWidget(btn)
            
        self.current_menu = "Production"
        self.update_style()

    def toggle_mode(self):
        
        sender = self.sender()
        
        for btn in self.btn_list:
            if sender == btn: 
                self.current_menu = btn.text()
            
        self.update_style()
        self.mode_changed.emit(self.current_menu)

    def update_style(self):
        active = "QPushButton { background-color: #FF6000; color: white; border-radius: 17px; font-weight: bold; border: none; }"
        inactive = "QPushButton { background-color: transparent; color: #888; border-radius: 17px; font-weight: bold; border: none; } QPushButton:hover { color: white; }"
        
        for btn in self.btn_list:
            name = btn.text()
            if self.current_menu == name:
                btn.setStyleSheet(active)
            else:
                btn.setStyleSheet(inactive)

class ContextSwitch(QFrame):
    
    mode_changed = pyqtSignal(str) 
    
    def __init__(self):
        super().__init__()
        
        self.setFixedSize(140, 34)
        self.setStyleSheet("background-color: #333; border-radius: 17px;")
        
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        self.setLayout(self.layout)
        
        self.btn_assets = QPushButton("assets")
        self.btn_shots = QPushButton("shots")
        
        for btn in [self.btn_assets, self.btn_shots]:
            btn.setCheckable(True)
            btn.setFixedSize(70, 34) 
            btn.clicked.connect(self.toggle_mode)
            self.layout.addWidget(btn)
            
        self.current_context = "Shots"
        self.update_style()

    def toggle_mode(self):
        
        sender = self.sender()
        
        if sender == self.btn_assets: self.current_context = "Assets"
        else: self.current_context = "Shots"
        
        self.update_style()
        self.mode_changed.emit(self.current_context)

    def update_style(self):
        
        active = "QPushButton { background-color: #FF6000; color: white; border-radius: 17px; font-weight: bold; border: none; }"
        inactive = "QPushButton { background-color: transparent; color: #888; border-radius: 17px; font-weight: bold; border: none; } QPushButton:hover { color: white; }"
        
        if self.current_context == "Assets":
            self.btn_assets.setStyleSheet(active)
            self.btn_shots.setStyleSheet(inactive)
            
        else:
            self.btn_assets.setStyleSheet(inactive)
            self.btn_shots.setStyleSheet(active)

class ThumbnailCard(QFrame):
    clicked = pyqtSignal(object)
    double_clicked = pyqtSignal(object)
    action_triggered = pyqtSignal(str, object)

    def __init__(self, filename, full_path, fallback_color, file_type="standard"):
        super().__init__()

        self.filename = filename
        self.full_path = full_path
        self.file_type = file_type

        self.is_selected = False
        self.is_published = False
        self.pixmap_loaded = False

        self.setFixedHeight(250)
        self.setFixedWidth(300)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setObjectName("ThumbnailCard")

        # Resolve thumbnail path
        self.thumb_path = self._resolve_thumbnail_path()

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Image area
        self.image_area = QLabel()
        self.image_area.setFixedHeight(180)
        self.image_area.setFixedWidth(280)
        self.image_area.setAlignment(Qt.AlignCenter)
        #clicks pass through
        self.image_area.setAttribute(Qt.WA_TransparentForMouseEvents) 
        self.image_area.setStyleSheet(
            f"background-color: {fallback_color}; border-radius: 6px;"
        )

        layout.addWidget(self.image_area)

        # Filename
        self.name_lbl = QLabel(filename)
        self.name_lbl.setWordWrap(True)
        self.name_lbl.setAttribute(Qt.WA_TransparentForMouseEvents) 
        self.name_lbl.setStyleSheet(
            "color: white; font-weight: bold; font-size: 12px;"
        )
        layout.addWidget(self.name_lbl)

        # Published label
        self.status_lbl = QLabel("PUBLISHED ✓")
        self.status_lbl.setAttribute(Qt.WA_TransparentForMouseEvents) 
        self.status_lbl.setStyleSheet(
            "color: #00ff00; font-size: 11px; font-weight: bold;"
        )
        self.status_lbl.hide()
        layout.addWidget(self.status_lbl)

        self.update_border()


    # Thumbnail resolution
    def _resolve_thumbnail_path(self):
        """
        Determines the best thumbnail path to use.
        """
        base_dir = os.path.dirname(self.full_path)
        base_name, ext = os.path.splitext(self.filename)
        ext = ext.lower()

        valid_img_exts = {'.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.exr'}

        #already an image, prefer it
        if ext in valid_img_exts:
            return self.full_path

        # Look for generated thumbnails
        thumb = os.path.join(base_dir, "thumbnails", base_name + ".jpg")
        if os.path.exists(thumb):
            return thumb

        # Fallback: same folder jpg
        thumb = os.path.join(base_dir, base_name + ".jpg")
        if os.path.exists(thumb):
            return thumb

        return None

    # Lazy loading
    def showEvent(self, event):
        """
        Lazy-load the pixmap only when widget becomes visible.
        """
        super().showEvent(event)
        if not self.pixmap_loaded:
            self.load_thumbnail()

    def load_thumbnail(self):
        """
        Loads thumbnail pixmap using cache.
        """
        if not self.thumb_path:
            return

        pixmap = get_cached_pixmap(self.thumb_path, self.image_area.size())
        if pixmap:
            self.image_area.setPixmap(pixmap)
            self.image_area.setStyleSheet(
                "background-color: transparent; border-radius: 6px;"
            )
            self.pixmap_loaded = True

    # Interaction
    def mousePressEvent(self, event):
        #left click for selection
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self)
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        #right click menu
        self.show_context_menu(event.globalPos())

    def mouseDoubleClickEvent(self, event):
        if self.full_path:
            self.double_clicked.emit(self)
        super().mouseDoubleClickEvent(event)

    def show_context_menu(self, global_pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #333; color: white; border: 1px solid #555; }
            QMenu::item:selected { background-color: #555; }
        """)

        #Publish Action
        if self.file_type == "export":
            action_text = "Unpublish" if self.is_published else "Publish"
            action_pub = QAction(action_text, self)
            action_pub.triggered.connect(
                lambda: self.action_triggered.emit(
                    "unpublish" if self.is_published else "publish", self
                )
            )
            menu.addAction(action_pub)
            menu.addSeparator()

        #File Actions
        action_open = QAction("Open File Location", self)
        action_open.triggered.connect(self.open_file_location)
        menu.addAction(action_open)

        #Path Variants
        variants = get_path_variants(self.full_path)
        
        action_copy_local = QAction("Copy Path (Local)", self)
        action_copy_local.triggered.connect(self.copy_path)
        menu.addAction(action_copy_local)

        if variants:
            action_copy_work = QAction("Copy Work Path (P:)", self)
            action_copy_work.triggered.connect(lambda: self.copy_specific_path(variants.get("work")))
            menu.addAction(action_copy_work)

            action_copy_home = QAction("Copy Home Path (O:)", self)
            action_copy_home.triggered.connect(lambda: self.copy_specific_path(variants.get("home")))
            menu.addAction(action_copy_home)

        menu.exec_(global_pos)

    def open_file_location(self):
        path = os.path.normpath(self.full_path)
        if os.path.exists(path):
            subprocess.Popen(f'explorer /select,"{path}"')
    
    def copy_path(self):
        QApplication.clipboard().setText(self.full_path)

    def copy_specific_path(self, path):
        if path:
            QApplication.clipboard().setText(path)

    #State updates
    def set_selected(self, selected):
        self.is_selected = selected
        self.update_border()

    def mark_published(self, published=True):
        self.is_published = published
        self.status_lbl.setVisible(published)
        self.update_border()

    def update_border(self):
        base_bg = "#1e1e1e"
        hover_bg = "#333333"

        if self.is_selected:
            css = (
                "ThumbnailCard {"
                f"background-color: {base_bg};"
                "border: 3px solid #FF6000;"
                "border-radius: 10px;"
                "}"
            )
        elif self.is_published:
            css = (
                "ThumbnailCard {"
                f"background-color: {base_bg};"
                "border: 3px solid #00ff00;"
                "border-radius: 10px;"
                "}"
            )
        else:
            css = (
                "ThumbnailCard {"
                f"background-color: {base_bg};"
                "border-radius: 10px;"
                "}"
                f"ThumbnailCard:hover {{ background-color: {hover_bg}; }}"
            )

        self.setStyleSheet(css)

class ShotInfoPanel(QFrame):
    def __init__(self):
        super().__init__()
        self.setVisible(False)
        self.setStyleSheet("background-color: #1a1a1a; border-bottom: 2px solid #333; border-radius: 0px;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(5)
        header_layout = QHBoxLayout()
        self.lbl_shot_code = QLabel("CODE")
        self.lbl_shot_code.setStyleSheet("color: #33ccff; font-size: 20px; font-weight: bold; background: transparent; border: none;")
        
        self.lbl_range = QLabel("Range: -")
        self.lbl_range.setStyleSheet("color: #FF6000; font-size: 14px; font-weight: bold; background: transparent; border: none;")
        self.lbl_range.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        header_layout.addWidget(self.lbl_shot_code)
        header_layout.addStretch()
        header_layout.addWidget(self.lbl_range)
        
        self.lbl_desc = QLabel("Description...")
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setStyleSheet("color: #aaa; font-size: 12px; font-style: italic; margin-top: 5px; background: transparent; border: none;")
        layout.addLayout(header_layout)
        layout.addWidget(self.lbl_desc)
    
    def update_info(self, code, start=None, end=None, description=""):
        self.lbl_shot_code.setText(code)
        if start is not None and end is not None:
            self.lbl_range.setText(f"Range: {start} - {int(end) + 20}")
            self.lbl_range.show()
        else:
            self.lbl_range.hide()
        self.lbl_desc.setText(description if description else "No description available.")
        self.setVisible(True)

# EDITORS 
class ShotEditor(QFrame):
    saved = pyqtSignal(dict)
    cancelled = pyqtSignal()
    
    def __init__(self, mode="create", existing_data=None):
        super().__init__()
        self.mode = mode
        self.existing_data = existing_data or {}
        self.setStyleSheet("""
            QFrame { background-color: #222; border-radius: 8px; }
            QLabel { color: #aaa; font-size: 12px; border: none; }
            QLineEdit, QSpinBox, QTextEdit { background-color: #333; color: white; border: 1px solid #444; border-radius: 4px; padding: 5px; }
            QPushButton { padding: 8px; font-weight: bold; border-radius: 4px; border: none; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        title = "Create New Shot" if mode == "create" else f"Edit {existing_data.get('code', 'Shot')}"
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: white; font-size: 16px; font-weight: bold; border: none;")
        layout.addWidget(lbl_title)
        layout.addSpacing(10)
        
        form = QFormLayout()
        form.setSpacing(10)
        
        self.inp_code = QLineEdit()
        self.inp_code.setText(existing_data.get('code', ''))
        
        form.addRow("Shot Code:", self.inp_code)
        range_layout = QHBoxLayout()
        
        self.inp_start = QSpinBox()
        self.inp_start.setRange(0, 999999)
        self.inp_start.setValue(existing_data.get('frame_start', 1001))
        self.inp_end = QSpinBox()
        self.inp_end.setRange(0, 999999)
        self.inp_end.setValue(existing_data.get('frame_end', 1100))
        
        range_layout.addWidget(self.inp_start)
        range_layout.addWidget(QLabel("-"))
        range_layout.addWidget(self.inp_end)
        
        form.addRow("Frame Range:", range_layout)
        
        self.inp_discord = QLineEdit()
        self.inp_discord.setPlaceholderText("Optional Discord Thread ID")
        self.inp_discord.setText(str(existing_data.get('discord_thread_id', '')))
        
        form.addRow("Discord ID:", self.inp_discord)
        
        layout.addLayout(form)
        self.thumbnail_path = existing_data.get('thumbnail_path', '')
        thumb_layout = QHBoxLayout()
        
        self.btn_browse_thumb = QPushButton("Browse")
        self.btn_browse_thumb.setFixedSize(70, 30)
        self.btn_browse_thumb.setStyleSheet("background-color: #3498db; color: white;")
        self.btn_browse_thumb.clicked.connect(self.browse_thumbnail)
        self.lbl_thumb_preview = QLabel()
        self.lbl_thumb_preview.setFixedSize(50, 30)
        self.lbl_thumb_preview.setStyleSheet("background-color: #444; border-radius: 4px;")
        
        if self.thumbnail_path: self.update_thumb_preview()
        
        thumb_layout.addWidget(QLabel("Thumbnail:"))
        thumb_layout.addWidget(self.btn_browse_thumb)
        thumb_layout.addWidget(self.lbl_thumb_preview)
        thumb_layout.addStretch()
        
        layout.addLayout(thumb_layout)
        layout.addWidget(QLabel("Description:"))
        
        self.inp_desc = QTextEdit()
        self.inp_desc.setPlaceholderText("Enter shot description...")
        self.inp_desc.setMaximumHeight(80)
        
        desc_val = existing_data.get('description')
        if desc_val is None: desc_val = ""
        self.inp_desc.setText(str(desc_val))
        
        layout.addWidget(self.inp_desc)
        layout.addStretch()
        
        btn_layout = QHBoxLayout()
        
        btn_save = QPushButton("Save Shot")
        btn_save.setStyleSheet("background-color: #27ae60; color: white;")
        btn_save.clicked.connect(self.on_save)
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet("background-color: #7f8c8d; color: white;")
        btn_cancel.clicked.connect(self.cancelled.emit)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        
        layout.addLayout(btn_layout)
        
    def browse_thumbnail(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Thumbnail", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if path:
            self.thumbnail_path = path
            self.update_thumb_preview()
            
    def update_thumb_preview(self):
        if self.thumbnail_path and os.path.exists(self.thumbnail_path):
             clean = self.thumbnail_path.replace("\\", "/")
             self.lbl_thumb_preview.setStyleSheet(f"border-image: url('{clean}') 0 0 0 0 stretch stretch; border-radius: 4px;")
        else:
             self.lbl_thumb_preview.setStyleSheet("background-color: #444; border-radius: 4px;")
             
    def on_save(self):
        code = self.inp_code.text().strip()
        if not code: return 
        data = {
            "code": code,
            "frame_start": self.inp_start.value(),
            "frame_end": self.inp_end.value(),
            "discord_thread_id": self.inp_discord.text().strip(),
            "description": self.inp_desc.toPlainText(),
            "thumbnail_path": self.thumbnail_path,
            "original_code": self.existing_data.get("code")
        }
        self.saved.emit(data)

class AssetEditor(QFrame):
    saved = pyqtSignal(dict)
    cancelled = pyqtSignal()
    def __init__(self, mode="create", existing_data=None):
        super().__init__()
        self.mode = mode
        # FIX: Ensure existing_data is a dictionary immediately
        existing_data = existing_data or {}
        self.existing_data = existing_data

        self.setStyleSheet("""
            QFrame { background-color: #222; border-radius: 8px; }
            QLabel { color: #aaa; font-size: 12px; border: none; }
            QLineEdit, QComboBox, QTextEdit { background-color: #333; color: white; border: 1px solid #444; border-radius: 4px; padding: 5px; }
            QPushButton { padding: 8px; font-weight: bold; border-radius: 4px; border: none; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Safe to use .get() now because existing_data is guaranteed to be a dict
        title = "Create New Asset" if mode == "create" else f"Edit {existing_data.get('name', 'Asset')}"
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: white; font-size: 16px; font-weight: bold; border: none;")
        layout.addWidget(lbl_title)
        layout.addSpacing(10)
        
        form = QFormLayout()
        form.setSpacing(10)
        self.inp_name = QLineEdit()
        self.inp_name.setText(existing_data.get('name', ''))
        form.addRow("Asset Name:", self.inp_name)
        
        self.inp_type = QComboBox()
        self.inp_type.addItems(["Character", "Prop", "Environment", "Vehicle", "MattePaint"])
        current_type = existing_data.get('type', 'Prop')
        index = self.inp_type.findText(current_type)
        if index >= 0: self.inp_type.setCurrentIndex(index)
        form.addRow("Asset Type:", self.inp_type)
        layout.addLayout(form)
        
        self.thumbnail_path = existing_data.get('thumbnail_path', '')
        thumb_layout = QHBoxLayout()
        
        self.btn_browse_thumb = QPushButton("Browse")
        self.btn_browse_thumb.setFixedSize(70, 30)
        self.btn_browse_thumb.setStyleSheet("background-color: #3498db; color: white;")
        self.btn_browse_thumb.clicked.connect(self.browse_thumbnail)
        self.lbl_thumb_preview = QLabel()
        self.lbl_thumb_preview.setFixedSize(50, 30)
        
        if self.thumbnail_path: self.update_thumb_preview()
        thumb_layout.addWidget(QLabel("Thumbnail:"))
        thumb_layout.addWidget(self.btn_browse_thumb)
        thumb_layout.addWidget(self.lbl_thumb_preview)
        thumb_layout.addStretch()
        layout.addLayout(thumb_layout)
        
        layout.addWidget(QLabel("Description:"))
        self.inp_desc = QTextEdit()
        self.inp_desc.setPlaceholderText("Enter asset description...")
        self.inp_desc.setMaximumHeight(80)
        self.inp_desc.setText(str(existing_data.get('description', '')))
        layout.addWidget(self.inp_desc)
        
        layout.addStretch()
        
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Save Asset")
        btn_save.setStyleSheet("background-color: #27ae60; color: white;")
        btn_save.clicked.connect(self.on_save)
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet("background-color: #7f8c8d; color: white;")
        btn_cancel.clicked.connect(self.cancelled.emit)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)
        
    def browse_thumbnail(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Thumbnail", "", "Images (*.png *.jpg *.jpeg)")
        if path:
            self.thumbnail_path = path
            self.update_thumb_preview()
            
    def update_thumb_preview(self):
        if self.thumbnail_path and os.path.exists(self.thumbnail_path):
             clean = self.thumbnail_path.replace("\\", "/")
             self.lbl_thumb_preview.setStyleSheet(f"border-image: url('{clean}') 0 0 0 0 stretch stretch; border-radius: 4px;")
             
    def on_save(self):
        name = self.inp_name.text().strip()
        if not name: return 
        data = {
            "name": name,
            "type": self.inp_type.currentText(),
            "description": self.inp_desc.toPlainText(),
            "thumbnail_path": self.thumbnail_path,
            "original_name": self.existing_data.get("name") # Pass original name for rename detection
        }
        self.saved.emit(data)

#ORION LOGO BUTTON

class OrionButton(QAbstractButton):
    def __init__(self, pixmap, pixmap_hover, pixmap_pressed, parent=None):
        super(OrionButton, self).__init__(parent)
        
        self.pixmap = QPixmap(pixmap)
        self.pixmap_hover = QPixmap(pixmap_hover)
        self.pixmap_pressed = QPixmap(pixmap_pressed)

        self.pressed.connect(self.update)
        self.released.connect(self.update)

    def paintEvent(self, event):
        pix = self.pixmap_hover if self.underMouse() else self.pixmap
        if self.isDown():
            pix = self.pixmap_pressed

        painter = QPainter(self)
        painter.drawPixmap(event.rect(), pix)

    def enterEvent(self, event):
        self.update()

    def leaveEvent(self, event):
        self.update()

    def sizeHint(self):
        return QSize(200, 200)

# SEQUENCE PLAYER WIDGET
class SequencePlayer(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(10)

        # IMAGE DISPLAY 
        self.view_container = QLabel()
        self.view_container.setAlignment(Qt.AlignCenter)
        self.view_container.setStyleSheet("background-color: #000; border-radius: 8px; border: 2px solid #444;")
        self.view_container.setMinimumSize(500, 300) 
        self.view_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.layout.addWidget(self.view_container)

        # SCRUBBER & CONTROLS
        # Scrubber Row
        scrubber_layout = QHBoxLayout()
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal { border: 1px solid #444; height: 6px; background: #222; margin: 2px 0; border-radius: 3px; }
            QSlider::handle:horizontal { background: #FF6000; border: 1px solid #FF6000; width: 12px; height: 12px; margin: -3px 0; border-radius: 6px; }
        """)
        # Connect slider 
        self.slider.valueChanged.connect(self.change_frame)
        self.slider.sliderPressed.connect(self.pause_playback) # Pause when dragging
        
        self.lbl_frame = QLabel("0000")
        self.lbl_frame.setStyleSheet("color: #888; font-weight: bold; background: #222; padding: 2px 6px; border-radius: 4px;")
        
        scrubber_layout.addWidget(self.slider)
        scrubber_layout.addWidget(self.lbl_frame)
        self.layout.addLayout(scrubber_layout)

        # Buttons Row (Centered)
        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignCenter)
        btn_layout.setSpacing(20)

        btn_style = """
            QPushButton { background-color: transparent; color: #888; font-size: 18px; border: none; }
            QPushButton:hover { color: #FF6000; }
        """
        
        self.btn_start = QPushButton("|<")
        self.btn_play = QPushButton("▶")
        self.btn_end = QPushButton(">|")
        
        # Connect Buttons
        self.btn_start.clicked.connect(self.go_to_start)
        self.btn_play.clicked.connect(self.toggle_playback)
        self.btn_end.clicked.connect(self.go_to_end)
        
        for btn in [self.btn_start, self.btn_play, self.btn_end]:
            btn.setStyleSheet(btn_style)
            btn_layout.addWidget(btn)

        self.layout.addLayout(btn_layout)

        # METADATA SECTION
        meta_container = QWidget()
        meta_layout = QGridLayout(meta_container)
        meta_layout.setContentsMargins(0, 10, 0, 0)
        meta_layout.setSpacing(15)

        def create_meta_field(label_text):
            lbl = QLabel(label_text)
            lbl.setStyleSheet("color: white; font-weight: bold; font-size: 11px; border-bottom: 2px solid #FF6000; padding-bottom: 2px;")
            val = QLabel("")
            val.setStyleSheet("background-color: #111; color: #aaa; padding: 5px; border-radius: 4px; min-height: 20px;")
            return lbl, val

        self.lbl_author_header, self.lbl_author_val = create_meta_field("author")
        meta_layout.addWidget(self.lbl_author_header, 0, 0)
        meta_layout.addWidget(self.lbl_author_val, 1, 0)

        self.lbl_date_header, self.lbl_date_val = create_meta_field("date-time")
        meta_layout.addWidget(self.lbl_date_header, 0, 1)
        meta_layout.addWidget(self.lbl_date_val, 1, 1)

        self.lbl_notes_header, self.lbl_notes_val = create_meta_field("notes")
        self.lbl_notes_val.setWordWrap(True)
        self.lbl_notes_val.setMinimumHeight(40)
        self.lbl_notes_val.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        meta_layout.addWidget(self.lbl_notes_header, 2, 0, 1, 2)
        meta_layout.addWidget(self.lbl_notes_val, 3, 0, 1, 2)

        self.layout.addWidget(meta_container)

        # LOGIC & VARS
        self.current_sequence = []
        self.cache = {}
        self.is_playing = False
        
        # Playback Timer
        self.timer = QTimer()
        self.timer.setInterval(42) # Approx 24 fps (1000ms / 24)
        self.timer.timeout.connect(self.advance_frame)

    # METADATA 
    def set_metadata(self, author="--", date="--", notes=""):
        self.lbl_author_val.setText(author)
        self.lbl_date_val.setText(date)
        self.lbl_notes_val.setText(notes if notes else "No notes available.")

    # LOADING 
    def load_sequence(self, folder_path):
        self.pause_playback() # Stop if playing
        self.current_sequence = []
        self.cache = {}
        
        # Guard Clause
        if not folder_path or not os.path.exists(folder_path):
            self.view_container.setText("No Sequence Loaded")
            self.view_container.setPixmap(QPixmap())
            self.lbl_frame.setText("0000")
            self.slider.setRange(0, 0)
            self.set_metadata()
            return

        valid_ext = ['.jpg', '.jpeg', '.png']
        
        files = sorted(os.listdir(folder_path))
        
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in valid_ext:
                self.current_sequence.append(os.path.join(folder_path, f))
        
        if self.current_sequence:
            self.slider.blockSignals(True) 
            self.slider.setRange(0, len(self.current_sequence) - 1)
            self.slider.setValue(0)
            self.slider.blockSignals(False)
            
            self.change_frame(0)
        else:
            self.view_container.setText("No Images Found\n(EXR ignored)")
            self.view_container.setPixmap(QPixmap())

    # PLAYBACK CONTROLS 
    def toggle_playback(self):
        if self.is_playing:
            self.pause_playback()
        else:
            self.start_playback()

    def start_playback(self):
        if not self.current_sequence: return
        self.is_playing = True
        self.btn_play.setText("||") 
        self.timer.start()

    def pause_playback(self):
        self.is_playing = False
        self.btn_play.setText("▶")
        self.timer.stop()

    def go_to_start(self):
        self.slider.setValue(0)

    def go_to_end(self):
        self.slider.setValue(self.slider.maximum())

    def advance_frame(self):
        current = self.slider.value()
        next_frame = current + 1
        if next_frame > self.slider.maximum():
            next_frame = 0 # Loop
        self.slider.setValue(next_frame)

    # DISPLAY LOGIC 
    def change_frame(self, index):
        if not self.current_sequence or index >= len(self.current_sequence): return
        
        path = self.current_sequence[index]
        
        # Frame Number Display
        match = re.search(r'(\d+)\.', os.path.basename(path))
        frame_num = match.group(1) if match else str(index)
        self.lbl_frame.setText(str(int(frame_num) + 1000))
        
        # Image Display
        if path in self.cache:
            self.view_container.setPixmap(self.cache[path])
        else:
            pix = QPixmap(path)
            
            if pix.isNull():
                self.view_container.setText("Invalid Image")
                return

            # SAFETY: Ensure don't scale to 0 if widget isn't visible yet
            w = self.view_container.width()
            h = self.view_container.height()
            if w <= 0: w = 600
            if h <= 0: h = 350

            scaled = pix.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.cache[path] = scaled
            self.view_container.setPixmap(scaled)
    
    # Handle window resizing to rescale images
    def resizeEvent(self, event):
        # When player resizes, refresh current frame to fit new size
        if self.current_sequence:
            self.cache = {} # Clear cache so we redraw at new resolution
            self.change_frame(self.slider.value())
        super().resizeEvent(event)

#RENDER LIST ITEM WIDGET

class RenderTaskButton(QPushButton):
    """
    Styled button for the 'renders' list (COMP, SLAPCOMP, etc.)
    """
    def __init__(self, text, full_path):
        super().__init__()
        self.full_path = full_path
        self.setMinimumHeight(45)
        self.setCheckable(True)
        self.text_label = text
        
        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 15, 0)
        
        self.lbl_text = QLabel(text)
        self.lbl_text.setStyleSheet("font-weight: bold; font-size: 11px; color: #888; border: none; background: transparent;")
        
        # The 'light' indicator on the right
        self.indicator = QLabel()
        self.indicator.setFixedSize(30, 18)
        self.indicator.setStyleSheet("background-color: #333; border-radius: 4px;")
        
        layout.addWidget(self.lbl_text)
        layout.addStretch()
        layout.addWidget(self.indicator)
        
        self.update_style(False)
        self.toggled.connect(self.update_style)

    def update_style(self, checked):
        if checked:
            self.setStyleSheet("QPushButton { background-color: #2b2b2b; border: none; border-radius: 4px; }")
            self.lbl_text.setStyleSheet("font-weight: bold; font-size: 11px; color: white; border: none; background: transparent;")
            self.indicator.setStyleSheet("background-color: #00CC66; border-radius: 4px;") # Bright Green
        else:
            self.setStyleSheet("QPushButton { background-color: transparent; border: none; border-radius: 4px; } QPushButton:hover { background-color: #222; }")
            self.lbl_text.setStyleSheet("font-weight: bold; font-size: 11px; color: #888; border: none; background: transparent;")
            self.indicator.setStyleSheet("background-color: #333; border-radius: 4px;") # Dark Grey

class VersionCard(QPushButton):
    """
    Styled button for the 'versions' list (v003, v002, etc.)
    """
    def __init__(self, text, full_path):
        super().__init__()
        self.full_path = full_path
        self.setMinimumHeight(60) # Taller, like a card
        self.setCheckable(True)
        self.text_label = text
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        
        self.lbl_text = QLabel(text)
        self.lbl_text.setStyleSheet("font-weight: bold; font-size: 12px; color: #888; border: none; background: transparent;")
        
        # Larger indicator box
        self.indicator = QLabel()
        self.indicator.setFixedSize(50, 35)
        self.indicator.setStyleSheet("background-color: #333; border-radius: 4px;")
        
        layout.addWidget(self.lbl_text)
        layout.addStretch()
        layout.addWidget(self.indicator)
        
        self.update_style(False)
        self.toggled.connect(self.update_style)

    def update_style(self, checked):
        if checked:
            self.setStyleSheet("QPushButton { background-color: #2b2b2b; border: 1px solid #00CC66; border-radius: 6px; }")
            self.lbl_text.setStyleSheet("font-weight: bold; font-size: 12px; color: white; border: none; background: transparent;")
            self.indicator.setStyleSheet("background-color: #00CC66; border-radius: 4px;")
        else:
            self.setStyleSheet("QPushButton { background-color: #222; border: 1px solid #333; border-radius: 6px; } QPushButton:hover { background-color: #2a2a2a; }")
            self.lbl_text.setStyleSheet("font-weight: bold; font-size: 12px; color: #888; border: none; background: transparent;")
            self.indicator.setStyleSheet("background-color: #333; border-radius: 4px;")

class RenderItemWidget(QPushButton):
    def __init__(self, text, subtext="", is_active=False):
        super().__init__()
        self.setFixedHeight(50)
        self.setCheckable(True)
        self.setChecked(is_active)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 5, 15, 5)
        
        lbl_main = QLabel(text)
        lbl_main.setStyleSheet("font-weight: bold; font-size: 12px; color: white; background: transparent; border: none;")
        
        layout.addWidget(lbl_main)
        
        if subtext:
            lbl_sub = QLabel(subtext)
            lbl_sub.setStyleSheet("color: #888; font-size: 10px; background: transparent; border: none;")
            layout.addStretch()
            layout.addWidget(lbl_sub)
            
        self.update_style()
        self.toggled.connect(self.update_style)

    def update_style(self):
        if self.isChecked():
            #green style like the image
            self.setStyleSheet("""
                QPushButton { background-color: #333; border: 1px solid #00ff00; border-radius: 6px; }
            """)
        else:
            self.setStyleSheet("""
                QPushButton { background-color: #2b2b2b; border: 1px solid #444; border-radius: 6px; }
                QPushButton:hover { background-color: #383838; }
            """)

#RENDER UI MANAGER
class RenderManagerWidget(QWidget):
    def __init__(self, parent_ui):
        super().__init__()
        self.parent_ui = parent_ui #ref to main window for paths
        self.project_root = parent_ui.project_root
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(20)

        #COLUMN 1: SELECTION (Renders + Versions)
        col1_layout = QVBoxLayout()
        
        #renders header
        col1_layout.addWidget(QLabel("RENDERS"))
        self.render_list = QVBoxLayout()
        col1_layout.addLayout(self.render_list)
        col1_layout.addSpacing(20)
        
        #versions header
        col1_layout.addWidget(QLabel("VERSIONS"))
        self.version_list = QVBoxLayout()
        col1_layout.addLayout(self.version_list)
        col1_layout.addStretch()
        
        #COLUMN 2: PLAYER
        self.player = SequencePlayer()
        
        #COLUMN 3: AOVS
        col3_layout = QVBoxLayout()
        col3_layout.addWidget(QLabel("AOV / PASSES"))
        self.aov_list = QVBoxLayout()
        col3_layout.addLayout(self.aov_list)
        col3_layout.addStretch()

        #add to main layout
        #container widgets for columns to control width
        w1 = QWidget(); w1.setLayout(col1_layout); w1.setFixedWidth(250)
        w3 = QWidget(); w3.setLayout(col3_layout); w3.setFixedWidth(250)
        
        self.layout.addWidget(w1)
        self.layout.addWidget(self.player, 1) #stretch factor 1
        self.layout.addWidget(w3)
        
        self.current_render_path = None
        self.current_version_path = None

    def refresh(self, shot_code):
        #clear all lists
        self.clear_layout(self.render_list)
        self.clear_layout(self.version_list)
        self.clear_layout(self.aov_list)
        self.player.view.clear()
        
        if not shot_code: return

        #structure: 40_shots/code/3D_RENDERS
        base = os.path.join(self.project_root, "40_shots", shot_code, "3D_RENDERS")
        
        if not os.path.exists(base):
            self.render_list.addWidget(QLabel("No 3D_RENDER folder"))
            return

        #find DEPT > TASK
        #we assume folders in 3D_RENDER are DEPTS
        depts = [d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))]
        
        found_any = False
        
        for dept in depts:
            dept_path = os.path.join(base, dept)
            tasks = [t for t in os.listdir(dept_path) if os.path.isdir(os.path.join(dept_path, t))]
            
            for task in tasks:
                task_path = os.path.join(dept_path, task)
                #create button
                btn = RenderItemWidget(task, dept)
                btn.clicked.connect(lambda c, p=task_path, b=btn: self.on_render_selected(p, b))
                self.render_list.addWidget(btn)
                found_any = True
                
        if not found_any:
            self.render_list.addWidget(QLabel("No Tasks Found"))
        else:
            self.render_list.addStretch()

    def on_render_selected(self, path, btn):
        self.current_render_path = path
        
        #toggle logic (radio button behavior)
        for i in range(self.render_list.count()):
            w = self.render_list.itemAt(i).widget()
            if isinstance(w, RenderItemWidget) and w != btn:
                w.setChecked(False)
        
        #populate versions
        self.clear_layout(self.version_list)
        
        if os.path.exists(path):
            vers = sorted([v for v in os.listdir(path) if v.startswith("v") and os.path.isdir(os.path.join(path, v))], reverse=True)
            
            for v in vers:
                v_path = os.path.join(path, v)
                v_btn = RenderItemWidget(v)
                v_btn.clicked.connect(lambda c, p=v_path, b=v_btn: self.on_version_selected(p, b))
                self.version_list.addWidget(v_btn)
                
            self.version_list.addStretch()
            
            #auto select latest
            if self.version_list.count() > 1: #remember stretch is an item
                first = self.version_list.itemAt(0).widget()
                if first: first.click()

    def on_version_selected(self, path, btn):
        self.current_version_path = path
        
        #toggle logic
        for i in range(self.version_list.count()):
            w = self.version_list.itemAt(i).widget()
            if isinstance(w, RenderItemWidget) and w != btn:
                w.setChecked(False)
                
        #populate passes/AOVs
        self.clear_layout(self.aov_list)
        
        if os.path.exists(path):
            passes = sorted([p for p in os.listdir(path) if os.path.isdir(os.path.join(path, p))])
            
            for p in passes:
                p_path = os.path.join(path, p)
                p_btn = RenderItemWidget(p)
                #clicking a pass loads it into player
                p_btn.clicked.connect(lambda c, p=p_path, b=p_btn: self.on_pass_selected(p, b))
                self.aov_list.addWidget(p_btn)
                
            self.aov_list.addStretch()
            
            #auto select first pass (often beauty)
            if self.aov_list.count() > 1:
                first = self.aov_list.itemAt(0).widget()
                if first: first.click()

    def on_pass_selected(self, path, btn):
        #toggle logic
        for i in range(self.aov_list.count()):
            w = self.aov_list.itemAt(i).widget()
            if isinstance(w, RenderItemWidget) and w != btn:
                w.setChecked(False)
                
        #load into player
        self.player.load_sequence(path)

    def clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()

#MAIN APP
class OrionLauncherUI(QWidget):
    
    def __init__(self):
        super().__init__()
        
        self.orion = OrionUtils(check_schema=True)
        self.prefs_utils = PrefsUtils(self.orion)
        self.settings = self.prefs_utils.load_settings()
        self.system_utils = SystemUtils(self.orion, self.prefs_utils)
            
        self.project_root = self.orion.get_root_dir()
        self.current_context = "Shots" # Assets vs Shots
        self.current_menu = "Production" # Top menu tab
        self.current_shot_code = None
        self.current_task_path = None
        
        self.active_buttons = {"col1": None, "task": None} 
        self.selected_card = None 
        
        self.init_ui()

    def init_ui(self):
        
        self.setWindowTitle(f'OrionTech')
        self.resize(1570, 900)
        self.setStyleSheet("background-color: #121212; color: #ffffff; font-family: Segoe UI, sans-serif;")

        # MAIN LAYOUT
        # Holds the Left Sidebar and the Right Content Area
        main_layout = QHBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)

        # LEFT SIDEBAR (Previously col1)
        # Logo, Asset/Shot Switcher, and the List of Items
        self.sidebar_frame, self.sidebar_layout, self.sidebar_scroll, self.sidebar_content = self.create_column_structure(
            "#1e1e1e", 320, "border-right: 1px solid #2a2a2a;"
        )
        
        # sidebar header (Logo + Context Switch)
        sidebar_header = QHBoxLayout()
        sidebar_header.setContentsMargins(5, 0, 5, 10)
        sidebar_header.setSpacing(15)
        
        # logo setup
        logo_dir = os.path.join(self.project_root, "20_pre", "branding", "logos")
        btn_path = os.path.join(logo_dir, "orion_colour.png")
        btn_hover_path = os.path.join(logo_dir, "orion_white.png")
        btn_clicked_path = os.path.join(logo_dir, "orion_orange.png")
        
        self.orion_btn = OrionButton(btn_path, btn_hover_path, btn_clicked_path)
        self.orion_btn.setFixedSize(108, 34)
        sidebar_header.addWidget(self.orion_btn)
        
        # context switch (Assets vs Shots)
        self.context_switch = ContextSwitch()
        self.context_switch.mode_changed.connect(self.switch_context)
        sidebar_header.addWidget(self.context_switch)
        sidebar_header.addStretch()
        
        self.sidebar_layout.addLayout(sidebar_header)
        self.sidebar_layout.addWidget(self.sidebar_scroll)
        
        # action bar (Create/Edit/Delete buttons)
        self.action_bar = QWidget()
        self.action_layout = QVBoxLayout(self.action_bar)
        self.action_layout.setContentsMargins(0, 0, 0, 0)
        
        create_btn = QPushButton("create")
        create_btn.setStyleSheet("background-color: #66cc66; color: #222; font-weight: bold; border-radius: 5px; height: 30px; border: none;")
        create_btn.clicked.connect(self.enter_create_mode)
        self.action_layout.addWidget(create_btn)
        
        sub_action_layout = QHBoxLayout()
        edit_btn = QPushButton("edit")
        edit_btn.setStyleSheet("background-color: #FF6000; color: #222; font-weight: bold; border-radius: 5px; height: 30px; border: none;")
        edit_btn.clicked.connect(self.enter_edit_mode)
        del_btn = QPushButton("delete")
        del_btn.setStyleSheet("background-color: #ff0033; color: white; font-weight: bold; border-radius: 5px; height: 30px; border: none;")
        del_btn.clicked.connect(self.delete_current_shot)
        
        sub_action_layout.addWidget(edit_btn)
        sub_action_layout.addWidget(del_btn)
        self.action_layout.addLayout(sub_action_layout)
        self.sidebar_layout.addWidget(self.action_bar)

        # RIGHT CONTENT AREA
        # Holds: Top Menu and the Stacked Pages (Production, Apps, etc)
        self.right_content_widget = QWidget()
        self.right_content_layout = QVBoxLayout(self.right_content_widget)
        self.right_content_layout.setContentsMargins(0, 0, 0, 0) # No margins
        self.right_content_layout.setSpacing(0)

        # Top Navigation Bar (The MenuSwitch)
        nav_container = QHBoxLayout()
        nav_container.setContentsMargins(5, 0, 5, 10)
        nav_container.setSpacing(15)
        
        self.top_menu_bar = MenuSwitch()
        self.top_menu_bar.mode_changed.connect(self.switch_menu_page) 
        nav_container.addWidget(self.top_menu_bar)
        
        self.right_content_layout.addLayout(nav_container)

        # The Stack 
        self.page_stack = QStackedWidget()
        
        # Page 0: PRODUCTION VIEW 
        self.production_view_widget = QWidget()
        self.setup_production_view() 
        self.page_stack.addWidget(self.production_view_widget)
        
        # Page 1: APPS VIEW 
        self.apps_view_widget = QWidget()
        self.setup_apps_view()
        self.page_stack.addWidget(self.apps_view_widget)

        # Page 2: RENDERS VIEW 
        self.renders_view_widget = QWidget()
        self.setup_renders_view()
        # self.renders_view_widget = QLabel("RENDER UI UNDER CONSTRUCTION")
        # self.renders_view_widget.setAlignment(Qt.AlignCenter)
        self.page_stack.addWidget(self.renders_view_widget)

        # Page 3: VAULT VIEW (Placeholder)
        self.vault_view_widget = QLabel("VAULT UI UNDER CONSTRUCTION")
        self.vault_view_widget.setAlignment(Qt.AlignCenter)
        self.page_stack.addWidget(self.vault_view_widget)

        # Page 4: SETTINGS VIEW 
        self.settings_view_widget = QWidget()
        self.setup_settings_view() 
        self.page_stack.addWidget(self.settings_view_widget)
        
        # Add stack to right layout
        self.right_content_layout.addWidget(self.page_stack)

        # MAIN SPLITTER (Combines Left Sidebar + Right Content)
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setHandleWidth(2)
        self.main_splitter.setStyleSheet("QSplitter::handle { background-color: #121212; }")
        
        self.main_splitter.addWidget(self.sidebar_frame)
        self.main_splitter.addWidget(self.right_content_widget)
        self.main_splitter.setStretchFactor(1, 2)
        
        main_layout.addWidget(self.main_splitter)

        # Initial Load
        self.populate_sidebar()

    def setup_production_view(self):
        layout = QVBoxLayout(self.production_view_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # 1. TASK PANEL (Previously col2)
        self.task_panel_frame = QFrame()
        self.task_panel_frame.setMinimumWidth(280)
        self.task_panel_frame.setStyleSheet("background-color: #252525; border-right: 1px solid #2a2a2a;")
        task_main_layout = QVBoxLayout(self.task_panel_frame)
        task_main_layout.setContentsMargins(0,0,0,0)
        
        self.task_splitter = QSplitter(Qt.Vertical)
        self.task_splitter.setHandleWidth(2)
        self.task_splitter.setStyleSheet("QSplitter::handle { background-color: #121212; }")

        # Top: Specialisms List
        self.task_top_widget = QWidget()
        task_top_layout = QVBoxLayout(self.task_top_widget)
        task_top_layout.setContentsMargins(15, 20, 15, 20)
        self.add_header(task_top_layout, "specialism / task")
        
        self.task_scroll = QScrollArea()
        self.task_scroll.setWidgetResizable(True)
        self.task_scroll.setFrameShape(QFrame.NoFrame)
        self.task_scroll.setStyleSheet(get_scrollbar_style("#252525"))
        
        self.task_content_container = QWidget()
        self.task_content_container.setStyleSheet("background: transparent;")
        self.task_content = QVBoxLayout(self.task_content_container)
        self.task_content.setAlignment(Qt.AlignTop)
        self.task_scroll.setWidget(self.task_content_container)
        task_top_layout.addWidget(self.task_scroll)

        # Bottom: Exports List
        self.task_bottom_widget = QWidget()
        task_bot_layout = QVBoxLayout(self.task_bottom_widget)
        task_bot_layout.setContentsMargins(15, 10, 15, 20)
        self.add_header(task_bot_layout, "exports")
        
        self.export_scroll = QScrollArea()
        self.export_scroll.setWidgetResizable(True)
        self.export_scroll.setFrameShape(QFrame.NoFrame)
        self.export_scroll.setStyleSheet(get_scrollbar_style("#252525"))
        
        self.export_container = QWidget()
        self.export_container.setStyleSheet("background: transparent;")
        self.export_layout = QVBoxLayout(self.export_container)
        self.export_layout.setAlignment(Qt.AlignTop)
        self.export_layout.setSpacing(5)
        self.export_scroll.setWidget(self.export_container)
        task_bot_layout.addWidget(self.export_scroll)

        self.task_splitter.addWidget(self.task_top_widget)
        self.task_splitter.addWidget(self.task_bottom_widget)
        self.task_splitter.setStretchFactor(0, 1)
        self.task_splitter.setStretchFactor(1, 1)
        self.task_splitter.setSizes([1000, 1000])
        
        task_main_layout.addWidget(self.task_splitter)

        # 2. GALLERY PANEL (Previously right_panel)
        self.gallery_frame = QWidget()
        gallery_layout = self.create_right_panel() # Uses your existing helper
        self.gallery_frame.setLayout(gallery_layout)
        
        # 3. Combine Task Panel and Gallery Panel
        self.production_splitter = QSplitter(Qt.Horizontal)
        self.production_splitter.setHandleWidth(2)
        self.production_splitter.addWidget(self.task_panel_frame)
        self.production_splitter.addWidget(self.gallery_frame)
        self.production_splitter.setStretchFactor(1, 2)
        
        layout.addWidget(self.production_splitter)

    def setup_apps_view(self):
        # Apply layout to apps view
        self.apps_layout = QVBoxLayout(self.apps_view_widget)
        self.apps_layout.setContentsMargins(60, 60, 60, 60) # Added padding for a cleaner look
        self.apps_layout.setSpacing(20)

        # Maya Launcher 
        self.btn_launch_maya = QPushButton("Launch Maya")
        self.btn_launch_maya.setMinimumHeight(60)
        self.btn_launch_maya.setCursor(Qt.PointingHandCursor)
        self.btn_launch_maya.setStyleSheet("""
            QPushButton { background-color: #63B2BF; color: white; font-weight: bold; font-size: 16px; border-radius: 8px; }
            QPushButton:hover { background-color: #87C8D4; }
        """)
        
        # Nuke Launcher
        self.btn_launch_nuke = QPushButton("Launch Nuke")
        self.btn_launch_nuke.setMinimumHeight(60)
        self.btn_launch_nuke.setCursor(Qt.PointingHandCursor)
        self.btn_launch_nuke.setStyleSheet("""
            QPushButton { background-color: #F2DC61; color: black; font-weight: bold; font-size: 16px; border-radius: 8px; }
            QPushButton:hover { background-color: #FFEF9E; }
        """)
        
        # Houdini Launcher 
        self.btn_launch_houdini = QPushButton("Launch Houdini")
        self.btn_launch_houdini.setMinimumHeight(60)
        self.btn_launch_houdini.setCursor(Qt.PointingHandCursor)
        self.btn_launch_houdini.setStyleSheet("""
            QPushButton { background-color: #FC9749; color: white; font-weight: bold; font-size: 16px; border-radius: 8px; }
            QPushButton:hover { background-color: #FFB37D; }
        """)
        
        # Mari Launcher
        self.btn_launch_mari = QPushButton("Launch Mari")
        self.btn_launch_mari.setMinimumHeight(60)
        self.btn_launch_mari.setCursor(Qt.PointingHandCursor)
        self.btn_launch_mari.setStyleSheet("""
            QPushButton { background-color: black; color: #F2DC61; font-weight: bold; font-size: 16px; border-radius: 8px; }
            QPushButton:hover { background-color: #404040; }
        """)
        
        # Connect Buttons to Handlers
        self.btn_launch_maya.clicked.connect(self.handle_launch_maya)
        self.btn_launch_nuke.clicked.connect(self.handle_launch_nuke)
        self.btn_launch_houdini.clicked.connect(self.handle_launch_houdini)
        self.btn_launch_mari.clicked.connect(self.handle_launch_mari)
        
        # Add to Layout
        self.apps_layout.addWidget(self.btn_launch_maya)
        self.apps_layout.addWidget(self.btn_launch_nuke)
        self.apps_layout.addWidget(self.btn_launch_houdini)
        self.apps_layout.addWidget(self.btn_launch_mari)
        
        self.apps_layout.addStretch()

    def setup_renders_view(self):
        # Master Layout for this page
        layout = QHBoxLayout(self.renders_view_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- COLUMN 2: RENDER & VERSION LISTS ---
        # Styling matched to Production View (#252525)
        self.render_panel_frame = QFrame()
        self.render_panel_frame.setMinimumWidth(280)
        self.render_panel_frame.setMaximumWidth(320)
        self.render_panel_frame.setStyleSheet("background-color: #252525; border-right: 1px solid #2a2a2a;")
        
        panel_layout = QVBoxLayout(self.render_panel_frame)
        panel_layout.setContentsMargins(0, 0, 0, 0)

        # Vertical Splitter
        self.render_splitter = QSplitter(Qt.Vertical)
        self.render_splitter.setHandleWidth(2)
        self.render_splitter.setStyleSheet("QSplitter::handle { background-color: #121212; }")

        # 1. TOP LIST: RENDERS (Tasks)
        self.render_list_widget = QWidget()
        render_list_layout = QVBoxLayout(self.render_list_widget)
        render_list_layout.setContentsMargins(15, 20, 15, 20)
        self.add_header(render_list_layout, "renders")

        self.render_scroll = QScrollArea()
        self.render_scroll.setWidgetResizable(True)
        self.render_scroll.setFrameShape(QFrame.NoFrame)
        self.render_scroll.setStyleSheet(get_scrollbar_style("#252525"))
        
        self.render_container = QWidget()
        self.render_container.setStyleSheet("background: transparent;")
        self.render_layout = QVBoxLayout(self.render_container)
        self.render_layout.setAlignment(Qt.AlignTop)
        self.render_layout.setSpacing(2)
        
        self.render_scroll.setWidget(self.render_container)
        render_list_layout.addWidget(self.render_scroll)

        # 2. BOTTOM LIST: VERSIONS
        self.version_list_widget = QWidget()
        version_list_layout = QVBoxLayout(self.version_list_widget)
        version_list_layout.setContentsMargins(15, 10, 15, 20)
        self.add_header(version_list_layout, "versions")

        self.version_scroll = QScrollArea()
        self.version_scroll.setWidgetResizable(True)
        self.version_scroll.setFrameShape(QFrame.NoFrame)
        self.version_scroll.setStyleSheet(get_scrollbar_style("#252525"))

        self.version_container = QWidget()
        self.version_container.setStyleSheet("background: transparent;")
        self.version_layout = QVBoxLayout(self.version_container)
        self.version_layout.setAlignment(Qt.AlignTop)
        self.version_layout.setSpacing(5)

        self.version_scroll.setWidget(self.version_container)
        version_list_layout.addWidget(self.version_scroll)

        self.render_splitter.addWidget(self.render_list_widget)
        self.render_splitter.addWidget(self.version_list_widget)
        self.render_splitter.setStretchFactor(0, 1)
        self.render_splitter.setStretchFactor(1, 1)

        panel_layout.addWidget(self.render_splitter)
        layout.addWidget(self.render_panel_frame)

        # --- COLUMN 3: MAIN CONTENT (Header + Player + AOVs) ---
        self.main_content_widget = QWidget()
        main_content_layout = QVBoxLayout(self.main_content_widget)
        main_content_layout.setContentsMargins(0, 0, 0, 0)
        main_content_layout.setSpacing(0)

        # A. Header (Shot Info) - Reusing ShotInfoPanel class
        self.render_info_panel = ShotInfoPanel()
        main_content_layout.addWidget(self.render_info_panel)

        # B. Content Area (Player Left, AOV Right)
        content_area = QWidget()
        content_row = QHBoxLayout(content_area)
        content_row.setContentsMargins(30, 20, 30, 30)
        content_row.setSpacing(30)

        # Player
        self.player = SequencePlayer()
        content_row.addWidget(self.player, stretch=3)

        # AOV List (Right Side)
        aov_group = QWidget()
        aov_group.setFixedWidth(220)
        aov_layout = QVBoxLayout(aov_group)
        aov_layout.setContentsMargins(0, 0, 0, 0)
        
        self.add_header(aov_layout, "AOV")
        
        self.aov_scroll = QScrollArea()
        self.aov_scroll.setWidgetResizable(True)
        self.aov_scroll.setFrameShape(QFrame.NoFrame)
        self.aov_scroll.setStyleSheet(get_scrollbar_style("#121212"))
        
        self.aov_inner_container = QWidget()
        self.aov_inner_container.setStyleSheet("background: transparent;")
        self.aov_item_layout = QVBoxLayout(self.aov_inner_container)
        self.aov_item_layout.setAlignment(Qt.AlignTop)
        self.aov_item_layout.setSpacing(5)
        
        self.aov_scroll.setWidget(self.aov_inner_container)
        aov_layout.addWidget(self.aov_scroll)
        
        content_row.addWidget(aov_group, stretch=1)

        main_content_layout.addWidget(content_area)
        layout.addWidget(self.main_content_widget)


    def setup_settings_view(self):

        # Apply layout to settings view
        self.settings_layout = QVBoxLayout(self.settings_view_widget)
        self.settings_layout.setContentsMargins(60, 60, 60, 60) # Added padding for a cleaner look
        self.settings_layout.setSpacing(20)
        
        self.dark_mode_checkbox = QCheckBox('Enable Windows Dark Mode')
        self.discord_checkbox = QCheckBox('Open Discord on Startup')
        self.wacom_checkbox = QCheckBox('Wacom Fix')
        
        self.settings_layout.addWidget(self.dark_mode_checkbox)
        self.settings_layout.addWidget(self.discord_checkbox)
        self.settings_layout.addWidget(self.wacom_checkbox)
        self.settings_layout.addStretch()

        # Connections
        self.dark_mode_checkbox.stateChanged.connect(self.toggle_dark_mode)
        self.discord_checkbox.stateChanged.connect(self.toggle_discord_startup)
        self.wacom_checkbox.stateChanged.connect(self.toggle_wacom_fix)
        
        # Set Defaults
        self.dark_mode_checkbox.setChecked(self.settings.get('dark_mode', False))
        self.discord_checkbox.setChecked(self.settings.get('discord_on_startup', False))
        self.wacom_checkbox.setChecked(self.settings.get('wacom_fix', False))

    # RENDER CONTEXT LOGIC
    
    def populate_render_list(self):
        self.clear_layout(self.task_content)
        if not self.current_shot_code: return

        if self.current_context == "Assets":
            base_folder = "30_assets"
            item_path = os.path.join(self.project_root, base_folder, self.current_shot_code, "RENDERS")
        else:
            base_folder = "40_shots"
            item_path = os.path.join(self.project_root, base_folder, self.current_shot_code, "3D_RENDERS")
        
        if os.path.exists(item_path):
            items = sorted([d for d in os.listdir(item_path) if os.path.isdir(os.path.join(item_path, d))])
            ignore = ["__pycache__", ".git"]
            items = [i for i in items if i not in ignore and not i.startswith(".")]

            for spec in items:
                spec_full_path = os.path.join(item_path, spec)
                group = SpecialismGroup(spec, spec_full_path, self)
                self.task_content.addWidget(group)
        else:
             self.task_content.addWidget(QLabel("Folder not found on disk."))

        self.task_content.addStretch()


    # RENDER TAB LOGIC 

    def refresh_renders_tab(self):
        """Called when switching to Renders tab or selecting a shot while in Renders tab."""
        self.clear_layout(self.render_layout)
        self.clear_layout(self.version_layout)
        self.clear_layout(self.aov_item_layout)
        self.player.load_sequence(None) # Clear player

        if not self.current_shot_code: 
            return

        shot_data = None
        if self.current_context == "Shots":
            shot_row = self.orion.get_shot(self.current_shot_code)
            if shot_row: shot_data = dict(shot_row)
        else:
            asset_row = self.orion.get_asset(self.current_shot_code)
            if asset_row: shot_data = dict(asset_row)

        if shot_data:
            s = shot_data.get('frame_start')
            e = shot_data.get('frame_end')
            d = shot_data.get('description', "")
            # Update the specific panel for this view
            self.render_info_panel.update_info(self.current_shot_code, s, e, d)

        # Path: 40_shots/shot_code/3D_RENDER
        render_root = os.path.join(self.project_root, "40_shots", self.current_shot_code, "3D_RENDERS")
        
        if not os.path.exists(render_root):
            lbl = QLabel("No 3D_RENDER folder found")
            lbl.setStyleSheet("color: #666; margin: 10px;")
            self.render_layout.addWidget(lbl)
            return

        # Find all folders inside all Departments
        # Assuming structure: 3D_RENDER > DEPT > TASK
        depts = [d for d in os.listdir(render_root) if os.path.isdir(os.path.join(render_root, d))]
        
        tasks_found = []
        for dept in depts:
            dept_path = os.path.join(render_root, dept)
            tasks = [t for t in os.listdir(dept_path) if os.path.isdir(os.path.join(dept_path, t))]
            for t in tasks:
                full_path = os.path.join(dept_path, t)
                tasks_found.append((t, full_path))
        
        # Create buttons for the "renders" list (Col 2 Top)
        for name, path in tasks_found:
            btn = RenderTaskButton(name, path)
            btn.clicked.connect(lambda c, b=btn: self.on_render_task_clicked(b))
            self.render_layout.addWidget(btn)

    def on_render_task_clicked(self, active_btn):
        # 1. Visual Toggle Logic
        for i in range(self.render_layout.count()):
            widget = self.render_layout.itemAt(i).widget()
            if isinstance(widget, RenderTaskButton):
                widget.setChecked(widget == active_btn)
        
        # 2. Populate Versions (Col 2 Bottom)
        self.clear_layout(self.version_layout)
        self.clear_layout(self.aov_item_layout)
        
        task_path = active_btn.full_path
        if not os.path.exists(task_path): return

        # Find versions (v001, v002...)
        versions = sorted([v for v in os.listdir(task_path) if v.startswith('v') and os.path.isdir(os.path.join(task_path, v))], reverse=True)

        for v in versions:
            v_path = os.path.join(task_path, v)
            # Check if published
            is_published = os.path.exists(os.path.join(v_path, "PUBLISHED")) # Example check
            
            btn = VersionCard(v, v_path)
            if is_published:
                # Add a "PUBLISHED" label inside the card if needed, or just change color
                pass 
                
            btn.clicked.connect(lambda c, b=btn: self.on_version_clicked(b))
            self.version_layout.addWidget(btn)
            
        # Auto-click latest version if exists
        if self.version_layout.count() > 0:
            first_ver = self.version_layout.itemAt(0).widget()
            first_ver.click()

    def on_version_clicked(self, active_btn):
        # 1. Visual Toggle Logic
        for i in range(self.version_layout.count()):
            widget = self.version_layout.itemAt(i).widget()
            if isinstance(widget, VersionCard):
                widget.setChecked(widget == active_btn)

        # 2. Populate AOVs and Load Player
        self.clear_layout(self.aov_item_layout)
        version_path = active_btn.full_path
        
        # Find AOVs (subfolders inside the version folder)
        # e.g. v001/beauty, v001/diffuse
        aovs = sorted([d for d in os.listdir(version_path) if os.path.isdir(os.path.join(version_path, d))])
        
        first_aov_path = None
        
        for aov in aovs:
            aov_path = os.path.join(version_path, aov)
            
            # Simple button for AOV
            btn = QPushButton(aov)
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton { text-align: left; padding: 10px; background-color: #2b2b2b; border: none; border-radius: 4px; color: #888; font-weight: bold;}
                QPushButton:checked { background-color: #333; color: white; border-left: 3px solid #00CC66; }
                QPushButton:hover { background-color: #333; }
            """)
            btn.clicked.connect(lambda c, p=aov_path, b=btn: self.on_aov_clicked(p, b))
            self.aov_item_layout.addWidget(btn)
            
            if first_aov_path is None: first_aov_path = aov_path

        self.aov_item_layout.addStretch()

        # 3. Load the first AOV into the player automatically
        if first_aov_path:
            # Manually trigger the first AOV button to look active and load
            first_btn = self.aov_item_layout.itemAt(0).widget()
            first_btn.setChecked(True)
            self.player.load_sequence(first_aov_path)
    
    def on_aov_clicked(self, path, active_btn):
        # Toggle logic for AOVs
        for i in range(self.aov_item_layout.count()):
            widget = self.aov_item_layout.itemAt(i).widget()
            if isinstance(widget, QPushButton) and widget != active_btn:
                widget.setChecked(False)
        
        self.player.load_sequence(path)

    #LOGIC
    def populate_sidebar(self):
        
        self.context_switch.show()
        self.action_bar.show()
        self.sidebar_scroll.show()
        self.clear_layout(self.sidebar_content)
        
        if self.current_context == "Assets":
            try:
                assets_data = self.orion.get_all_assets()
                for asset in assets_data:
                    name = asset['name']
                    asset_dict = {key: asset[key] for key in asset.keys()}
                    btn = ShotButton(name, "#ff9966", full_data=asset_dict)
                    btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                    btn.clicked.connect(lambda checked, b=btn: self.on_sidebar_select(b))
                    self.sidebar_content.addWidget(btn)
            except Exception as e:
                print(f"Asset DB Error: {e}")
        else:
            try:
                shots_data = self.orion.get_all_shots()
                for shot in shots_data:
                    code = shot['code']
                    shot_dict = {key: shot[key] for key in shot.keys()}
                    btn = ShotButton(code, "#66ffcc", full_data=shot_dict) 
                    btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                    btn.clicked.connect(lambda checked, b=btn: self.on_sidebar_select(b))
                    self.sidebar_content.addWidget(btn)
            except Exception as e:
                print(f"Shot DB Error: {e}")
        
        self.sidebar_content.addStretch()
        
    def on_sidebar_select(self, btn):
        if self.active_buttons["col1"]:
            try: self.active_buttons["col1"].set_active(False)
            except: pass
        btn.set_active(True)
        self.active_buttons["col1"] = btn

        self.current_shot_code = btn.text_label
        
        if btn.full_data:
            start = btn.full_data.get('frame_start')
            end = btn.full_data.get('frame_end')
            desc = btn.full_data.get('description', "")
            self.info_panel.update_info(self.current_shot_code, start, end, desc)

        self.populate_task_list()
        self.clear_gallery()
        self.clear_layout(self.export_layout)
        
        #RENDER LOGIC
        if self.current_menu == "Renders":
            self.refresh_renders_tab() # UPDATED CALL
            
    def populate_task_list(self):
        self.clear_layout(self.task_content)
        if not self.current_shot_code: return

        if self.current_context == "Assets":
            base_folder = "30_assets"
        else:
            base_folder = "40_shots"

        item_path = os.path.join(self.project_root, base_folder, self.current_shot_code)
        
        if os.path.exists(item_path):
            items = sorted([d for d in os.listdir(item_path) if os.path.isdir(os.path.join(item_path, d))])
            ignore = ["__pycache__", ".git"]
            items = [i for i in items if i not in ignore and not i.startswith(".")]

            for spec in items:
                spec_full_path = os.path.join(item_path, spec)
                group = SpecialismGroup(spec, spec_full_path, self)
                self.task_content.addWidget(group)
        else:
             self.task_content.addWidget(QLabel("Folder not found on disk."))

        self.task_content.addStretch()

    def get_next_available_shot_code(self):
        shots_dir = os.path.join(self.project_root, "40_shots")
        highest = 0
        if os.path.exists(shots_dir):
            for item in os.listdir(shots_dir):
                if os.path.isdir(os.path.join(shots_dir, item)):
                    match = re.search(r'^stc_(\d+)$', item)
                    if match:
                        try:
                            num = int(match.group(1))
                            if num > highest: highest = num
                        except ValueError: pass
        next_num = highest + 10
        if next_num == 10: next_num = 10 
        return f"stc_{next_num:04d}"

    def enter_create_mode(self):
        self.context_switch.hide()
        self.action_bar.hide()
        self.sidebar_scroll.hide()
        
        if self.current_context == "Assets":
            self.editor = AssetEditor(mode="create")
            self.editor.saved.connect(self.save_new_asset)
            self.editor.cancelled.connect(self.exit_edit_mode)
        else:
            next_code = self.get_next_available_shot_code()
            default_data = {"code": next_code, "frame_start": 1001, "frame_end": 1100}
            self.editor = ShotEditor(mode="create", existing_data=default_data)
            self.editor.saved.connect(self.save_new_shot)
            self.editor.cancelled.connect(self.exit_edit_mode)
        
        self.sidebar_layout.insertWidget(2, self.editor) 

    def enter_edit_mode(self):
        
        if not self.current_shot_code:
            QMessageBox.warning(self, "Select Item", "Please select an item to edit.")
            return

        #Hide main widgets
        self.context_switch.hide()
        self.action_bar.hide()
        self.sidebar_scroll.hide()

        try:
            if self.current_context == "Assets":
                #ASSET EDIT MODE
                asset_row = self.orion.get_asset(self.current_shot_code)
                full_data = {}
                
                if asset_row:
                    row_dict = dict(asset_row)

                    full_data["name"] = row_dict.get("name") or self.current_shot_code
                    full_data["type"] = row_dict.get("type") or "Prop"
                    full_data["description"] = row_dict.get("description") or ""
                    full_data["thumbnail_path"] = row_dict.get("thumbnail_path") or ""
                else:
                    full_data["name"] = self.current_shot_code
                    full_data["type"] = "Prop"
                    full_data["description"] = ""
                    full_data["thumbnail_path"] = ""
                
                #load description from meta JSON if DB was empty
                if not full_data["description"]:
                    try:
                        meta_path = os.path.join(self.project_root, "30_assets", self.current_shot_code, "orion_meta.json")
                        if os.path.exists(meta_path):
                            with open(meta_path, 'r') as f:
                                d = json.load(f)
                                full_data["description"] = d.get("description", "")
                    except: pass

                self.editor = AssetEditor(mode="edit", existing_data=full_data)
                self.editor.saved.connect(self.save_edited_asset)
                self.editor.cancelled.connect(self.exit_edit_mode)
                self.sidebar_layout.insertWidget(2, self.editor)

            else:
                #SHOT EDIT MODE 
                full_data = {}
                shot_row = self.orion.get_shot(self.current_shot_code)
                if shot_row:
                    row_dict = dict(shot_row)
                    full_data["code"] = row_dict.get('code') or self.current_shot_code
                    full_data["frame_start"] = row_dict.get('frame_start', 1001)
                    full_data["frame_end"] = row_dict.get('frame_end', 1100)
                    full_data["discord_thread_id"] = row_dict.get('discord_thread_id') or ""
                    full_data["description"] = row_dict.get('description') or ""
                    full_data["thumbnail_path"] = row_dict.get('thumbnail_path') or ""
                    
                    #Fallback for Discord ID if missing in dict
                    if not full_data["discord_thread_id"]:
                        tid = self.orion.get_shot_thread_id(self.current_shot_code)
                        if tid: full_data["discord_thread_id"] = tid

                else:
                    full_data["code"] = self.current_shot_code
                    
                #Load description from meta if missing
                if not full_data.get("description"):
                    try:
                        meta_path = os.path.join(self.project_root, "40_shots", self.current_shot_code, "orion_meta.json")
                        if os.path.exists(meta_path):
                            with open(meta_path, 'r') as f:
                                d = json.load(f)
                                full_data["description"] = d.get("description", "")
                    except: pass
                
                self.editor = ShotEditor(mode="edit", existing_data=full_data)
                self.editor.saved.connect(self.save_edited_shot)
                self.editor.cancelled.connect(self.exit_edit_mode)
                self.sidebar_layout.insertWidget(2, self.editor)

        except Exception as e:
            #If error, restore UI and show message
            print(f"Edit Mode Error: {e}")
            import traceback
            traceback.print_exc()
            
            self.context_switch.show()
            self.action_bar.show()
            self.sidebar_scroll.show()
            QMessageBox.critical(self, "Editor Error", f"Could not load editor:\n{e}")

    def exit_edit_mode(self):
        if hasattr(self, 'editor'):
            self.editor.deleteLater()
            del self.editor
        self.populate_sidebar()

    def update_discord_id_in_db(self, code, discord_id):
        try:
            conn = self.orion.get_db_connection()
            conn.execute("UPDATE shots SET discord_thread_id = ? WHERE code = ?", (discord_id, code))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Failed to update Discord ID: {e}")

    def save_new_shot(self, data):
        code = data["code"]
        start = data["frame_start"]
        end = data["frame_end"]
        desc = data.get("description", "")
        disc_id = data.get("discord_thread_id", "")
        thumb = data.get("thumbnail_path", "")
        try:
            self.orion.create_shot(code, start, end, os.getlogin(), description=desc, thumbnail_path=thumb)
            if disc_id: self.update_discord_id_in_db(code, disc_id)
            QMessageBox.information(self, "Success", f"Shot {code} created.")
            self.exit_edit_mode()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def save_edited_shot(self, data):
        old_code = data["original_code"]
        new_code = data["code"]
        start = data["frame_start"]
        end = data["frame_end"]
        desc = data.get("description", "")
        disc_id = data.get("discord_thread_id", "")
        thumb = data.get("thumbnail_path")
        thumb = str(thumb).strip() if thumb else ""
        try:
            if old_code != new_code:
                shots_root = os.path.join(self.project_root, "40_shots")
                old_path = os.path.join(shots_root, old_code)
                new_path = os.path.join(shots_root, new_code)
                if os.path.exists(new_path): raise Exception(f"Destination {new_code} already exists.")
                os.rename(old_path, new_path)
                self.orion.rename_shot_code_in_db(old_code, new_code)
                self.current_shot_code = new_code 
            
            self.orion.update_shot_frames(new_code, start, end)
            self.update_discord_id_in_db(new_code, disc_id)
            
            shot_row = self.orion.get_shot(new_code)
            shot_id = shot_row['id'] if shot_row else new_code 
            
            conn = self.orion.get_db_connection()
            conn.execute("UPDATE shots SET description = ?, thumbnail_path = ? WHERE code = ?", (desc, thumb, new_code))
            conn.commit()
            conn.close()

            shot_path = os.path.join(self.project_root, "40_shots", new_code)
            self.orion.create_meta_tag(shot_path, new_code, {"description": desc}, shot_id=shot_id)
            
            QMessageBox.information(self, "Success", f"Shot {new_code} updated.")
            self.exit_edit_mode()
        except Exception as e:
            QMessageBox.critical(self, "Update Failed", str(e))

    def save_edited_asset(self, data):
        old_name = data.get("original_name")
        new_name = data["name"]
        atype = data["type"]
        desc = data.get("description", "")
        thumb = data.get("thumbnail_path", "")
        
        try:
            #Handle Rename
            if old_name and old_name != new_name:
                assets_root = os.path.join(self.project_root, "30_assets")
                old_path = os.path.join(assets_root, old_name)
                new_path = os.path.join(assets_root, new_name)
                
                if os.path.exists(new_path):
                    raise Exception(f"Asset '{new_name}' already exists.")
                
                os.rename(old_path, new_path)
                
                #Update DB Name and Path
                conn = self.orion.get_db_connection()
                new_rel_path = self.orion.get_relative_path(new_path)
                conn.execute("UPDATE assets SET name = ?, asset_path = ? WHERE name = ?", 
                             (new_name, new_rel_path, old_name))
                conn.commit()
                conn.close()
                self.current_shot_code = new_name 

            #Update DB Metadata
            #Get ID first
            asset_row = self.orion.get_asset(new_name)
            asset_id = asset_row['id'] if asset_row else str(uuid.uuid4())
            
            conn = self.orion.get_db_connection()
            conn.execute("UPDATE assets SET type = ?, description = ?, thumbnail_path = ? WHERE name = ?", 
                         (atype, desc, thumb, new_name))
            conn.commit()
            conn.close()

            #Update Meta Tag (JSON)
            asset_path = os.path.join(self.project_root, "30_assets", new_name)
            self.orion.create_meta_tag(asset_path, new_name, 
                                       {"type": "asset", "asset_type": atype, "description": desc}, 
                                       shot_id=asset_id)
            
            QMessageBox.information(self, "Success", f"Asset {new_name} updated.")
            self.exit_edit_mode()
            
        except Exception as e:
            QMessageBox.critical(self, "Update Failed", str(e))

    def delete_current_shot(self):
        if not self.current_shot_code: return
        
        item_type = "Asset" if self.current_context == "Assets" else "Shot"
        reply = QMessageBox.question(self, "Confirm Delete", 
                                     f"Are you sure you want to delete {item_type}: {self.current_shot_code}?\n"
                                     "This will remove the folder and DB entry permanently.",
                                     QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                success = False
                if self.current_context == "Assets":
                    success = self.orion.delete_asset(self.current_shot_code)
                else:
                    success = self.orion.delete_shot(self.current_shot_code)
                
                if success:
                    QMessageBox.information(self, "Deleted", f"{item_type} deleted successfully.")
                    # Reset Selection
                    self.current_shot_code = None
                    self.active_buttons["col1"] = None
                    
                    # Clear UI Panes
                    self.clear_layout(self.task_content) 
                    self.clear_layout(self.export_layout) 
                    self.info_panel.setVisible(False)
                    
                    # Refresh List
                    self.populate_sidebar()
                else:
                    QMessageBox.warning(self, "Error", "Failed to delete item. Check console for details.")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def switch_context(self, mode):
        
        self.current_context = mode
        print(self.current_context)
        
        self.active_buttons = {"col1": None, "task": None}
        self.clear_layout(self.task_content)
        self.clear_layout(self.export_layout) 
        self.clear_gallery()
        self.info_panel.setVisible(False) 
        
        self.task_bottom_widget.setVisible(True)
            
        self.populate_sidebar()
        
    def switch_menu_page(self, mode):
        
        self.current_menu = mode
        
        # Logic to actually switch the stack page
        if mode == "Production":
            self.page_stack.setCurrentIndex(0)
        elif mode == "Apps":
            self.page_stack.setCurrentIndex(1)
        elif mode == "Renders":
            self.page_stack.setCurrentIndex(2)
            if self.current_shot_code:
                self.refresh_renders_tab() 
        elif mode == "Vault":
            self.page_stack.setCurrentIndex(3)
        elif mode == "Settings":
            self.page_stack.setCurrentIndex(4)
            
        print(f"Switched to: {mode}")

    def on_task_select(self, btn, full_path):
        if self.active_buttons["task"]:
            try: self.active_buttons["task"].set_active(False)
            except: pass
        btn.set_active(True)
        self.active_buttons["task"] = btn

        self.current_task_path = full_path
        
        self.populate_gallery(full_path, exclude_dirs=["EXPORT", "BIN"])
        self.populate_exports_pane(full_path)

    def populate_exports_pane(self, task_path):
        """Populates the bottom of Column 2 with items from EXPORT and EXPORT/PUBLISHED"""
        self.clear_layout(self.export_layout)
        
        export_path = os.path.join(task_path, "EXPORT")
        publish_path = os.path.join(export_path, "PUBLISHED")
        
        items_to_add = [] 

        # standard exports 
        if os.path.exists(export_path):
            try:
                for f in os.listdir(export_path):
                    if f.startswith('.'): continue
                    full_p = os.path.join(export_path, f)
                    if os.path.isfile(full_p):
                        items_to_add.append((f, full_p, False))
            except Exception as e:
                print(f"[DEBUG] Error reading export path: {e}")

        # published exports
        if os.path.exists(publish_path):
            try:
                for f in os.listdir(publish_path):
                    if f.startswith('.'): continue
                    full_p = os.path.join(publish_path, f)
                    if os.path.isfile(full_p):
                        items_to_add.append((f, full_p, True))
            except Exception as e:
                print(f"[DEBUG] Error reading publish path: {e}")
        
        # Sort alphabetically by filename
        items_to_add.sort(key=lambda x: x[0])

        if not items_to_add:
            lbl = QLabel("No export files found.")
            lbl.setStyleSheet("color: #666; font-style: italic; margin-left: 10px;")
            self.export_layout.addWidget(lbl)
        else:
            for name, path, is_pub in items_to_add:
                item = ExportItemWidget(name, path, is_published=is_pub)
                item.action_triggered.connect(self.handle_export_action)
                self.export_layout.addWidget(item)
                
        self.export_layout.addStretch()

    def handle_export_action(self, action, item):
        if action == "publish":
            self.publish_asset_file(item)
        elif action == "unpublish":
            self.unpublish_asset_file(item)

    def publish_asset_file(self, item):
        src = item.full_path
        dir_name = os.path.dirname(src)
        publish_dir = os.path.join(dir_name, "PUBLISHED")
        if not os.path.exists(publish_dir): os.makedirs(publish_dir)
        
        dst = os.path.join(publish_dir, item.filename)
        try:
            shutil.copy2(src, dst)
            QMessageBox.information(self, "Published", f"Published: {item.filename}")
            # Refresh list
            self.populate_exports_pane(self.current_task_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Publish failed: {e}")

    def unpublish_asset_file(self, item):
        export_dir = os.path.dirname(item.full_path)

        export_root = os.path.dirname(export_dir)
        task_dir = os.path.dirname(export_root) 
        
        bin_dir = os.path.join(task_dir, "BIN")
        if not os.path.exists(bin_dir): os.makedirs(bin_dir)
        
        dst = os.path.join(bin_dir, item.filename)

        if os.path.exists(dst):
            base, ext = os.path.splitext(item.filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dst = os.path.join(bin_dir, f"{base}_{timestamp}{ext}")

        try:
            shutil.move(item.full_path, dst)
            QMessageBox.information(self, "Unpublished", f"Moved to BIN:\n{os.path.basename(dst)}")
            # Refresh list
            self.populate_exports_pane(self.current_task_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Unpublish failed: {e}")

    def create_right_panel(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.info_panel = ShotInfoPanel()
        layout.addWidget(self.info_panel)
        
        # SCROLL AREA FOR GALLERY
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(get_scrollbar_style("#121212"))
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        gallery_container = QWidget()
        gallery_container.setStyleSheet("background: transparent;")
        gallery_layout = QVBoxLayout(gallery_container)
        gallery_layout.setContentsMargins(20, 20, 20, 20)
        
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(20)
        self.grid_layout.setAlignment(Qt.AlignTop) 
        
        self.grid_layout.setColumnStretch(0, 1)
        self.grid_layout.setColumnStretch(1, 1)
        self.grid_layout.setColumnStretch(2, 1)

        gallery_layout.addLayout(self.grid_layout)
        gallery_layout.addStretch()
        
        scroll.setWidget(gallery_container)
        layout.addWidget(scroll)

        bottom_bar_container = QWidget()
        bottom_bar = QHBoxLayout(bottom_bar_container)
        bottom_bar.setContentsMargins(20, 10, 20, 20)
        
        self.pub_btn = QPushButton("publish")
        self.pub_btn.setFixedSize(80, 30)
        self.pub_btn.setStyleSheet("background-color: #66cc66; color: #222; font-weight: bold; border-radius: 5px;")
        self.pub_btn.clicked.connect(self.on_publish_clicked)
        
        self.new_btn = QPushButton("new")
        self.new_btn.setFixedSize(80, 30)
        self.new_btn.setStyleSheet("background-color: #33ccff; color: #222; font-weight: bold; border-radius: 5px;")
        self.new_btn.clicked.connect(self.on_new_file_clicked)
        
        open_btn = QPushButton("open folder")
        open_btn.setFixedSize(80, 30)
        open_btn.setStyleSheet("background-color: #FF6000; color: #222; font-weight: bold; border-radius: 5px;")
        open_btn.clicked.connect(self.on_open_folder_clicked)
        
        bottom_bar.addWidget(self.pub_btn)   
        bottom_bar.addStretch()             
        bottom_bar.addWidget(self.new_btn)   
        bottom_bar.addWidget(open_btn)       
        
        layout.addWidget(bottom_bar_container)
        return layout

    def on_new_file_clicked(self):
        
        if self.current_context == "Shot":
            
            shot_code = self.current_shot_code
            shot_row = self.orion.get_shot(shot_code)
            row_dict = dict(shot_row)
            
            frame_start = row_dict.get('frame_start')
            frame_end = row_dict.get('frame_end')
            discord_thread_id = row_dict.get('discord_thread_id') 
            shot_path = row_dict.get('shot_path')
            
            items = ["Maya", "Nuke", "Houdini", "Mari"]
            choice, ok = QInputDialog.getItem(self, "Launch DCC", "Select Software to Open:", items, 0, False)
            if not ok: return
            launcher_map = {
                "Maya": "dcc/maya/maya_launcher.py",
                "Nuke": "dcc/nuke/nuke_launcher.py",
                "Houdini": "dcc/houdini/houdini_launcher.py",
                "Mari": "dcc/mari/mari_launcher.py"
            }
            launcher_rel_path = launcher_map[choice]
            launcher_abs_path = os.path.join(orion_package_root, launcher_rel_path)
            
            if os.path.exists(launcher_abs_path):
                #FLAGS
                cmd_args = [sys.executable, launcher_abs_path]
                
                if shot_code:
                    cmd_args.extend(["--code", str(shot_code)])
                    cmd_args.extend(["--start", str(frame_start)])
                    cmd_args.extend(["--end", str(frame_end)])
                    cmd_args.extend(["--discord", str(discord_thread_id)])
                    cmd_args.extend(["--shotpath", str(shot_path)])

                subprocess.Popen(cmd_args)
            else:
                QMessageBox.warning(self, "Error", f"Launcher script not found: {launcher_abs_path}")
                
        elif self.current_context == "Assets":
            
            shot_code = self.current_shot_code
            shot_row = self.orion.get_shot(shot_code)
            
            items = ["Maya", "Nuke", "Houdini", "Mari"]
            choice, ok = QInputDialog.getItem(self, "Launch DCC", "Select Software to Open:", items, 0, False)
            if not ok: return
            launcher_map = {
                "Maya": "dcc/maya/maya_launcher.py",
                "Nuke": "dcc/nuke/nuke_launcher.py",
                "Houdini": "dcc/houdini/houdini_launcher.py",
                "Mari": "dcc/mari/mari_launcher.py"
            }
            launcher_rel_path = launcher_map[choice]
            launcher_abs_path = os.path.join(orion_package_root, launcher_rel_path)
            
            if os.path.exists(launcher_abs_path):
                #FLAGS
                cmd_args = [sys.executable, launcher_abs_path]
                
                if shot_code:
                    cmd_args.extend(["--code", str(shot_code)])

                subprocess.Popen(cmd_args)
            else:
                QMessageBox.warning(self, "Error", f"Launcher script not found: {launcher_abs_path}")

    def launch_dcc_file(self, card):
        
        if self.current_context == "Shots":
                
            shot_code = self.current_shot_code
            shot_row = self.orion.get_shot(shot_code)
            row_dict = dict(shot_row)
            
            frame_start = row_dict.get('frame_start')
            frame_end = row_dict.get('frame_end')
            discord_thread_id = row_dict.get('discord_thread_id') 
            shot_path = row_dict.get('shot_path') 
            
            file_path = card.full_path
            ext = os.path.splitext(file_path)[1].lower()
            
            launcher_map = {
                ".ma": "dcc/maya/maya_launcher.py",
                ".mb": "dcc/maya/maya_launcher.py",
                ".nk": "dcc/nuke/nuke_launcher.py",
                ".hip": "dcc/houdini/houdini_launcher.py",
                ".hipnc": "dcc/houdini/houdini_launcher.py",
                ".mari": "dcc/mari/mari_launcher.py"
            }
            
            if ext in launcher_map:
                launcher_rel_path = launcher_map[ext]
                launcher_abs_path = os.path.join(orion_package_root, launcher_rel_path)
                
                if os.path.exists(launcher_abs_path):
                    # BUILD ARGUMENTS WITH FLAGS
                    cmd_args = [sys.executable, launcher_abs_path]
                    
                    # We HAVE a file, so add it
                    cmd_args.extend(["--file", file_path])
                    
                    if shot_code: 
                        cmd_args.extend(["--code", str(shot_code)])
                        cmd_args.extend(["--start", str(frame_start)])
                        cmd_args.extend(["--end", str(frame_end)])
                        cmd_args.extend(["--discord", str(discord_thread_id)])
                        cmd_args.extend(["--shotpath", str(shot_path)])
                        
                    subprocess.Popen(cmd_args)
                    return
                
            try:
                os.startfile(file_path)
            except Exception as e:
                QMessageBox.warning(self, "Launch Error", f"Could not open file: {e}")
                
        elif self.current_context == "Assets":
            
            shot_code = self.current_shot_code
            shot_row = self.orion.get_shot(shot_code)
            
            file_path = card.full_path
            ext = os.path.splitext(file_path)[1].lower()
            
            launcher_map = {
                ".ma": "dcc/maya/maya_launcher.py",
                ".mb": "dcc/maya/maya_launcher.py",
                ".nk": "dcc/nuke/nuke_launcher.py",
                ".hip": "dcc/houdini/houdini_launcher.py",
                ".hipnc": "dcc/houdini/houdini_launcher.py",
                ".mari": "dcc/mari/mari_launcher.py"
            }
            
            if ext in launcher_map:
                launcher_rel_path = launcher_map[ext]
                launcher_abs_path = os.path.join(orion_package_root, launcher_rel_path)
                
                if os.path.exists(launcher_abs_path):
                    # BUILD ARGUMENTS WITH FLAGS
                    cmd_args = [sys.executable, launcher_abs_path]
                    
                    # We HAVE a file, so add it
                    cmd_args.extend(["--file", file_path])
                    
                    if shot_code: 
                        cmd_args.extend(["--code", str(shot_code)])
                        
                    subprocess.Popen(cmd_args)
                    return
                
            try:
                os.startfile(file_path)
            except Exception as e:
                QMessageBox.warning(self, "Launch Error", f"Could not open file: {e}")

    def populate_gallery(self, folder_path, exclude_dirs=None):
        self.clear_gallery()
        if not os.path.exists(folder_path): return
        
        if exclude_dirs is None: exclude_dirs = []

        files = sorted(os.listdir(folder_path))
        files = [f for f in files if f not in exclude_dirs]
        files = [f for f in files if os.path.isfile(os.path.join(folder_path, f))]
        files = [f for f in files if not f.startswith(".")]

        if not files:
            lbl = QLabel("No files found.")
            lbl.setStyleSheet("color: #555; font-size: 14px; font-weight: bold;")
            self.grid_layout.addWidget(lbl, 0, 0)
            return

        row, col = 0, 0
        max_cols = 3
        for i, filename in enumerate(files):
            color = "#33ccff" if i % 2 == 0 else "#e65c00"
            full_path = os.path.join(folder_path, filename)
            card = ThumbnailCard(filename, full_path, color)
            card.clicked.connect(self.on_card_clicked)
            card.double_clicked.connect(self.launch_dcc_file) 
            self.grid_layout.addWidget(card, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def launch_shot_creator(self):
        self.enter_create_mode()

    def on_open_folder_clicked(self):
        if self.current_task_path and os.path.exists(self.current_task_path):
            os.startfile(self.current_task_path)
        elif self.current_shot_code:
             path = os.path.join(self.project_root, "40_shots", self.current_shot_code)
             if os.path.exists(path): os.startfile(path)
    
    def clear_gallery(self):
        while self.grid_layout.count():
            child = self.grid_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
        self.selected_card = None

    def on_card_clicked(self, card_widget):
        if self.selected_card: self.selected_card.set_selected(False)
        self.selected_card = card_widget
        self.selected_card.set_selected(True)

    def on_publish_clicked(self):
        if self.selected_card: self.selected_card.mark_published()

    def add_header(self, layout, text):
        #container to hold text and line 
        header_container = QWidget()
        v_layout = QVBoxLayout(header_container)
        v_layout.setContentsMargins(0, 0, 0, 0)
        
        #space between text and line
        v_layout.setSpacing(4) 

        #text label
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: #ccc; font-weight: bold; font-size: 13px; background: transparent; border: none;")
        v_layout.addWidget(lbl, 0, Qt.AlignCenter)

        #separator line
        line = QFrame()
        line.setFixedSize(30, 2) #30px wide, 2px tall
        line.setStyleSheet("background-color: #FF6000;") #using a subtle grey, change to #FF6000 for orange
        v_layout.addWidget(line, 0, Qt.AlignCenter)

        #add container to main layout
        layout.addWidget(header_container, 0, Qt.AlignCenter)

    def clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
            elif child.layout(): self.clear_layout(child.layout())
            
    def save_new_asset(self, data):
        try:
            self.orion.create_asset(
                name=data['name'], 
                asset_type=data['type'], 
                user=os.getlogin(), 
                description=data.get('description', ""), 
                thumbnail_path=data.get('thumbnail_path', "")
            )
            QMessageBox.information(self, "Success", f"Asset {data['name']} created.")
            self.exit_edit_mode()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
        
    def create_column_structure(self, bg_color, min_width, radius_style=""):
        wrapper = QFrame()
        wrapper.setMinimumWidth(min_width)
        wrapper.setStyleSheet(f"background-color: {bg_color}; {radius_style}")
        root_layout = QVBoxLayout(wrapper)
        root_layout.setContentsMargins(15, 20, 15, 20)
        root_layout.setSpacing(10)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(get_scrollbar_style(bg_color))
        
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(container)
        content_layout.setContentsMargins(0, 0, 5, 0)
        content_layout.setSpacing(10)
        content_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(container)
        return wrapper, root_layout, scroll, content_layout

#LAUNCHER LOGIC

    def _launch_dcc(self, launcher_rel_path):
        """
        Helper method to run external launcher scripts using the current UI context.
        """
        import sys
        import subprocess

        # 1. Locate the launcher script in the pipeline structure
        # self.orion.pipeline_dir resolves to the root folder (e.g. .../orionTech/core/..)
        launcher_path = os.path.join(self.orion.pipeline_dir, launcher_rel_path)
        
        if not os.path.exists(launcher_path):
            QMessageBox.warning(self, "Launcher Missing", f"Could not find launcher script at:\n{launcher_path}")
            return

        # 2. Prepare the command
        # using sys.executable ensures we use the same python interpreter
        cmd = [sys.executable, launcher_path]

        # 3. Inject Context (if a shot or asset is selected)
        if self.current_shot_code:
            cmd.extend(["--code", self.current_shot_code])
            
            # If in "Shots" mode, we likely have frame ranges and discord IDs to pass
            if self.current_context != "Assets":
                shot_data = self.orion.get_shot(self.current_shot_code)
                if shot_data:
                    # Pass frame range
                    cmd.extend(["--start", str(shot_data['frame_start'])])
                    cmd.extend(["--end", str(shot_data['frame_end'])])
                    
                    # Pass Discord ID if it exists
                    if shot_data['discord_thread_id']:
                        cmd.extend(["--discord", str(shot_data['discord_thread_id'])])
                        
                    # Pass Shot Path on Disk
                    if shot_data['shot_path']:
                        cmd.extend(["--shotpath", str(shot_data['shot_path'])])

        # 4. Execute non-blocking
        try:
            print(f"Orion Launching: {' '.join(cmd)}")
            subprocess.Popen(cmd) 
        except Exception as e:
            QMessageBox.critical(self, "Launch Error", f"Failed to launch process:\n{e}")

    def handle_launch_maya(self):
        self._launch_dcc(os.path.join("dcc", "maya", "maya_launcher.py"))

    def handle_launch_nuke(self):
        self._launch_dcc(os.path.join("dcc", "nuke", "nuke_launcher.py"))

    def handle_launch_houdini(self):
        self._launch_dcc(os.path.join("dcc", "houdini", "houdini_launcher.py"))

    def handle_launch_mari(self):
        self._launch_dcc(os.path.join("dcc", "mari", "mari_launcher.py"))

#SETTINGS LOGIC
    def toggle_dark_mode(self, state):
        self.settings['dark_mode'] = (state == Qt.Checked)
        self.prefs_utils.save_settings(self.settings)
        self.system_utils.set_windows_dark_mode(state == Qt.Checked)
        
    def toggle_discord_startup(self, state):
        self.settings['discord_on_startup'] = (state == Qt.Checked)
        self.prefs_utils.save_settings(self.settings)
        
        discord_path = "https://discord.com/login"
        self.system_utils.open_window(discord_path, state == Qt.Checked)
        
    def toggle_wacom_fix(self, state):
        self.settings['wacom_fix'] = (state == Qt.Checked)
        self.prefs_utils.save_settings(self.settings)
        self.system_utils.wacom_fix(state == Qt.Checked)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = OrionLauncherUI()
    window.show()
    sys.exit(app.exec_())