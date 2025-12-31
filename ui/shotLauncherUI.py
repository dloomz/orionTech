import sys
import os
import subprocess
import json
import shutil
import re
import uuid
from datetime import datetime
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

orion_utils = OrionUtils(check_schema=False)

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
            QFormLayout, QFileDialog, QMenu, QAction, QComboBox, QAbstractButton
        )
        from PyQt5.QtCore import Qt, pyqtSignal, QSize, QRect
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
            #Green border for published
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
        
        #File Actions
        action_open = QAction("Open File Location", self) # pyright: ignore[reportPossiblyUnboundVariable]
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
        self.current_mode = "Shots"
        self.update_style()

    def toggle_mode(self):
        sender = self.sender()
        if sender == self.btn_assets: self.current_mode = "Assets"
        else: self.current_mode = "Shots"
        self.update_style()
        self.mode_changed.emit(self.current_mode)

    def update_style(self):
        active = "QPushButton { background-color: #FF6000; color: white; border-radius: 17px; font-weight: bold; border: none; }"
        inactive = "QPushButton { background-color: transparent; color: #888; border-radius: 17px; font-weight: bold; border: none; } QPushButton:hover { color: white; }"
        if self.current_mode == "Assets":
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
        self.setFixedWidth(290)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setObjectName("ThumbnailCard")

        # Resolve thumbnail path
        self.thumb_path = self._resolve_thumbnail_path()

        # ---------- Layout ----------
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Image area
        self.image_area = QLabel()
        self.image_area.setFixedHeight(180)
        self.image_area.setFixedWidth(280)
        self.image_area.setAlignment(Qt.AlignCenter)
        self.image_area.setAttribute(Qt.WA_TransparentForMouseEvents) # FIX: Allow clicks to pass through
        self.image_area.setStyleSheet(
            f"background-color: {fallback_color}; border-radius: 6px;"
        )

        layout.addWidget(self.image_area)

        # Filename
        self.name_lbl = QLabel(filename)
        self.name_lbl.setWordWrap(True)
        self.name_lbl.setAttribute(Qt.WA_TransparentForMouseEvents) # FIX: Allow clicks to pass through
        self.name_lbl.setStyleSheet(
            "color: white; font-weight: bold; font-size: 12px;"
        )
        layout.addWidget(self.name_lbl)

        # Published label
        self.status_lbl = QLabel("PUBLISHED ✓")
        self.status_lbl.setAttribute(Qt.WA_TransparentForMouseEvents) # FIX: Allow clicks to pass through
        self.status_lbl.setStyleSheet(
            "color: #00ff00; font-size: 11px; font-weight: bold;"
        )
        self.status_lbl.hide()
        layout.addWidget(self.status_lbl)

        self.update_border()

    # ------------------------------------------------------------------
    # Thumbnail resolution
    # ------------------------------------------------------------------

    def _resolve_thumbnail_path(self):
        """
        Determines the best thumbnail path to use.
        """
        base_dir = os.path.dirname(self.full_path)
        base_name, ext = os.path.splitext(self.filename)
        ext = ext.lower()

        valid_img_exts = {'.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.exr'}

        # If it's already an image, prefer it
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

    # ------------------------------------------------------------------
    # Lazy loading
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Interaction
    # ------------------------------------------------------------------

    def mousePressEvent(self, event):
        # Handle left click for selection
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self)
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        # Standard way to handle right click menus
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

        # 1. Publish Actions (Only if this card represents an export)
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

        # 2. File Actions (Always Available)
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

    # ------------------------------------------------------------------
    # State updates
    # ------------------------------------------------------------------

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
            self.lbl_range.setText(f"Range: {start} - {end}")
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

# MAIN APP

class OrionLauncherUI(QWidget):
    def __init__(self):
        super().__init__()
        self.orion = OrionUtils(check_schema=True)
            
        self.project_root = self.orion.get_root_dir()
        self.current_context = "Shots"
        self.current_shot_code = None
        self.current_task_path = None
        
        self.active_buttons = {"col1": None, "task": None} 
        self.selected_card = None 
        
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f'OrionTech')
        self.resize(1550, 900)
        self.setStyleSheet("background-color: #121212; color: #ffffff; font-family: Segoe UI, sans-serif;")

        main_layout = QHBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)

        # Helper for basic columns
        def create_column_structure(bg_color, min_width, radius_style=""):
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

        #  COL 1: SHOTS 
        self.col1_frame, self.col1_root, self.col1_scroll, self.col1_content = create_column_structure("#1e1e1e", 320, "border-right: 1px solid #2a2a2a;")
        
        # --- HEADER ROW (Logo + Switcher) ---
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(5, 0, 5, 10) # Margins + Bottom spacing
        header_layout.setSpacing(15) # Space between Logo and Switcher
        
        # 1. Logo (FIX: Use dynamic project_root instead of hardcoded P:)
        logo_dir = os.path.join(self.project_root, "20_pre", "branding", "logos")
        btn_path = os.path.join(logo_dir, "orion_colour.png")
        btn_hover_path = os.path.join(logo_dir, "orion_white.png")
        btn_clicked_path = os.path.join(logo_dir, "orion_orange.png")
        
        self.orion_btn = OrionButton(btn_path, btn_hover_path, btn_clicked_path)
        self.orion_btn.setFixedSize(108, 34)
        header_layout.addWidget(self.orion_btn)
        
        # 2. Context Switcher
        self.context_switch = ContextSwitch()
        self.context_switch.mode_changed.connect(self.switch_context)
        header_layout.addWidget(self.context_switch)
        
        # 3. Spacer (Pushes everything to the left)
        header_layout.addStretch()
        
        self.col1_root.addLayout(header_layout)
        # -------------------------------------
        
        self.col1_root.addWidget(self.col1_scroll)
        
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
        self.col1_root.addWidget(self.action_bar)

        #  COL 2: SPLIT LAYOUT 
        self.col2_frame = QFrame()
        self.col2_frame.setMinimumWidth(280)
        self.col2_frame.setStyleSheet("background-color: #252525; border-right: 1px solid #2a2a2a;")
        col2_main_layout = QVBoxLayout(self.col2_frame)
        col2_main_layout.setContentsMargins(0,0,0,0)
        
        self.col2_splitter = QSplitter(Qt.Vertical)
        self.col2_splitter.setHandleWidth(2)
        self.col2_splitter.setStyleSheet("QSplitter::handle { background-color: #121212; }")

        # Top: Tasks
        self.col2_top_widget = QWidget()
        col2_top_layout = QVBoxLayout(self.col2_top_widget)
        col2_top_layout.setContentsMargins(15, 20, 15, 20)
        self.add_header(col2_top_layout, "specialism / task")
        
        self.col2_scroll = QScrollArea()
        self.col2_scroll.setWidgetResizable(True)
        self.col2_scroll.setFrameShape(QFrame.NoFrame)
        self.col2_scroll.setStyleSheet(get_scrollbar_style("#252525"))
        
        self.col2_content_container = QWidget()
        self.col2_content_container.setStyleSheet("background: transparent;")
        self.col2_content = QVBoxLayout(self.col2_content_container)
        self.col2_content.setAlignment(Qt.AlignTop)
        self.col2_scroll.setWidget(self.col2_content_container)
        col2_top_layout.addWidget(self.col2_scroll)

        # Bottom: Exports (Hidden by default)
        self.col2_bottom_widget = QWidget()
        self.col2_bottom_widget.setVisible(True) 
        col2_bot_layout = QVBoxLayout(self.col2_bottom_widget)
        col2_bot_layout.setContentsMargins(15, 10, 15, 20)
        self.add_header(col2_bot_layout, "exports")
        
        self.col2_export_scroll = QScrollArea()
        self.col2_export_scroll.setWidgetResizable(True)
        self.col2_export_scroll.setFrameShape(QFrame.NoFrame)
        self.col2_export_scroll.setStyleSheet(get_scrollbar_style("#252525"))
        
        self.col2_export_container = QWidget()
        self.col2_export_container.setStyleSheet("background: transparent;")
        self.col2_export_layout = QVBoxLayout(self.col2_export_container)
        self.col2_export_layout.setAlignment(Qt.AlignTop)
        self.col2_export_layout.setSpacing(5)
        self.col2_export_scroll.setWidget(self.col2_export_container)
        col2_bot_layout.addWidget(self.col2_export_scroll)

        self.col2_splitter.addWidget(self.col2_top_widget)
        self.col2_splitter.addWidget(self.col2_bottom_widget)
        self.col2_splitter.setStretchFactor(0, 1)
        self.col2_splitter.setStretchFactor(1, 1)
        
        self.col2_splitter.setSizes([1000, 1000])
        col2_main_layout.addWidget(self.col2_splitter)

        # COL 3: GALLERY
        self.right_panel_widget = QWidget()
        right_layout = self.create_right_panel()
        self.right_panel_widget.setLayout(right_layout)

        # SPLITTER 
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(2)
        self.splitter.setStyleSheet("QSplitter::handle { background-color: #121212; }")
        self.splitter.addWidget(self.col1_frame)
        self.splitter.addWidget(self.col2_frame)
        self.splitter.addWidget(self.right_panel_widget)
        self.splitter.setStretchFactor(2, 1)
        main_layout.addWidget(self.splitter)

        self.populate_column_1()

    # LOGIC

    def populate_column_1(self):
        self.context_switch.show()
        self.action_bar.show()
        self.col1_scroll.show()
        self.clear_layout(self.col1_content)
        
        if self.current_context == "Assets":
            try:
                assets_data = self.orion.get_all_assets()
                for asset in assets_data:
                    name = asset['name']
                    asset_dict = {key: asset[key] for key in asset.keys()}
                    btn = ShotButton(name, "#ff9966", full_data=asset_dict)
                    btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                    btn.clicked.connect(lambda checked, b=btn: self.on_col1_select(b))
                    self.col1_content.addWidget(btn)
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
                    btn.clicked.connect(lambda checked, b=btn: self.on_col1_select(b))
                    self.col1_content.addWidget(btn)
            except Exception as e:
                print(f"Shot DB Error: {e}")
        
        self.col1_content.addStretch()

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
        self.col1_scroll.hide()
        
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
        
        self.col1_root.insertWidget(2, self.editor) 

    def enter_edit_mode(self):
        if not self.current_shot_code:
            QMessageBox.warning(self, "Select Item", "Please select an item to edit.")
            return

        # Hide main widgets
        self.context_switch.hide()
        self.action_bar.hide()
        self.col1_scroll.hide()

        try:
            if self.current_context == "Assets":
                # --- ASSET EDIT MODE ---
                asset_row = self.orion.get_asset(self.current_shot_code)
                full_data = {}
                
                if asset_row:
                    row_dict = dict(asset_row)
                    # Use 'or' to safely handle None (NULL) values from DB
                    full_data["name"] = row_dict.get("name") or self.current_shot_code
                    full_data["type"] = row_dict.get("type") or "Prop"
                    full_data["description"] = row_dict.get("description") or ""
                    full_data["thumbnail_path"] = row_dict.get("thumbnail_path") or ""
                else:
                    full_data["name"] = self.current_shot_code
                    full_data["type"] = "Prop"
                    full_data["description"] = ""
                    full_data["thumbnail_path"] = ""
                
                # Attempt to load description from meta JSON if DB was empty
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
                self.col1_root.insertWidget(2, self.editor)

            else:
                # --- SHOT EDIT MODE ---
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
                    
                    # Fallback for Discord ID if missing in dict
                    if not full_data["discord_thread_id"]:
                        tid = self.orion.get_shot_thread_id(self.current_shot_code)
                        if tid: full_data["discord_thread_id"] = tid

                else:
                    full_data["code"] = self.current_shot_code
                    
                # Load description from meta if missing
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
                self.col1_root.insertWidget(2, self.editor)

        except Exception as e:
            # If error, restore UI and show message
            print(f"Edit Mode Error: {e}")
            import traceback
            traceback.print_exc()
            
            self.context_switch.show()
            self.action_bar.show()
            self.col1_scroll.show()
            QMessageBox.critical(self, "Editor Error", f"Could not load editor:\n{e}")

    def exit_edit_mode(self):
        if hasattr(self, 'editor'):
            self.editor.deleteLater()
            del self.editor
        self.populate_column_1()

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
            # 1. Handle Rename
            if old_name and old_name != new_name:
                assets_root = os.path.join(self.project_root, "30_assets")
                old_path = os.path.join(assets_root, old_name)
                new_path = os.path.join(assets_root, new_name)
                
                if os.path.exists(new_path):
                    raise Exception(f"Asset '{new_name}' already exists.")
                
                os.rename(old_path, new_path)
                
                # Update DB Name and Path
                conn = self.orion.get_db_connection()
                new_rel_path = self.orion.get_relative_path(new_path)
                conn.execute("UPDATE assets SET name = ?, asset_path = ? WHERE name = ?", 
                             (new_name, new_rel_path, old_name))
                conn.commit()
                conn.close()
                self.current_shot_code = new_name 

            # 2. Update DB Metadata
            # Get ID first
            asset_row = self.orion.get_asset(new_name)
            asset_id = asset_row['id'] if asset_row else str(uuid.uuid4())
            
            conn = self.orion.get_db_connection()
            conn.execute("UPDATE assets SET type = ?, description = ?, thumbnail_path = ? WHERE name = ?", 
                         (atype, desc, thumb, new_name))
            conn.commit()
            conn.close()

            # 3. Update Meta Tag (JSON)
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
                    self.clear_layout(self.col2_content) 
                    self.clear_layout(self.col2_export_layout) 
                    self.info_panel.setVisible(False)
                    
                    # Refresh List
                    self.populate_column_1()
                else:
                    QMessageBox.warning(self, "Error", "Failed to delete item. Check console for details.")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def switch_context(self, mode):
        self.current_context = mode
        self.active_buttons = {"col1": None, "task": None}
        self.clear_layout(self.col2_content)
        self.clear_layout(self.col2_export_layout) 
        self.clear_gallery()
        self.info_panel.setVisible(False) 
        
        self.col2_bottom_widget.setVisible(True)
            
        self.populate_column_1()

    def on_col1_select(self, btn):
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
        
        self.populate_merged_column_2()
        self.clear_gallery()
        self.clear_layout(self.col2_export_layout) 

    def populate_merged_column_2(self):
        self.clear_layout(self.col2_content)
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
                self.col2_content.addWidget(group)
        else:
             self.col2_content.addWidget(QLabel("Folder not found on disk."))

        self.col2_content.addStretch()

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
        self.clear_layout(self.col2_export_layout)
        
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
            self.col2_export_layout.addWidget(lbl)
        else:
            for name, path, is_pub in items_to_add:
                item = ExportItemWidget(name, path, is_published=is_pub)
                item.action_triggered.connect(self.handle_export_action)
                self.col2_export_layout.addWidget(item)
                
        self.col2_export_layout.addStretch()

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

    def launch_dcc_file(self, card):
        
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

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = OrionLauncherUI()
    window.show()
    sys.exit(app.exec_())