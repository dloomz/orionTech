import sys
import os
import subprocess
import json
import shutil
import re
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QFrame, QGridLayout,
    QSizePolicy, QScrollArea, QSplitter, QInputDialog,
    QMessageBox, QLineEdit, QSpinBox, QTextEdit,
    QFormLayout, QFileDialog, QMenu, QAction
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QPixmap

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

# HELPERS 

def get_scrollbar_style(bg_color):
    """Returns the CSS string for a consistent scrollbar style matching the column background."""
    return f"""
        QScrollArea {{ background: transparent; border: none; }}
        QScrollBar:vertical {{ border: none; background: {bg_color}; width: 10px; margin: 0; }}
        QScrollBar::handle:vertical {{ background: #555; min-height: 20px; border-radius: 5px; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
    """

# CUSTOM WIDGETS 

class ExportItemWidget(QFrame):
    """
    Compact widget for displaying Export files in the 2nd Column (Asset Mode).
    """
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
            # Green border for published
            self.setStyleSheet(base_style + "ExportItemWidget { border: 2px solid #00ff00; }")
        else:
            self.setStyleSheet(base_style + "ExportItemWidget { border: 1px solid #444; } ExportItemWidget:hover { border: 1px solid #666; background-color: #333; }")

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.show_context_menu(event.pos())
        super().mousePressEvent(event)

    def show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #333; color: white; border: 1px solid #555; } QMenu::item:selected { background-color: #555; }")
        
        if self.is_published:
            action = QAction("Unpublish (Move to .BIN)", self)
            action.triggered.connect(lambda: self.action_triggered.emit("unpublish", self))
        else:
            action = QAction("Publish", self)
            action.triggered.connect(lambda: self.action_triggered.emit("publish", self))
            
        menu.addAction(action)
        menu.exec_(self.mapToGlobal(pos))

    def set_published(self, state):
        self.is_published = state
        self.update_style()


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
        if thumb_path and isinstance(thumb_path, str) and os.path.exists(thumb_path):
            clean_path = thumb_path.strip().replace("\\", "/")
            self.box.setStyleSheet(f"""
                border-image: url('{clean_path}') 0 0 0 0 stretch stretch;
                border-radius: 4px;
                border: 1px solid #555;
            """)
            self.box.setText("") # Clear pixmap if set previously
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
        if spec_name == "COMP": color = "#66ffcc"
        
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
        active = "QPushButton { background-color: #ffaa00; color: white; border-radius: 17px; font-weight: bold; border: none; }"
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
    
    def __init__(self, filename, full_path, color, file_type="standard"):
        super().__init__()
        # Flexible width
        self.setFixedHeight(250) 
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        self.filename = filename
        self.full_path = full_path
        self.is_selected = False
        self.is_published = False
        self.file_type = file_type

        # THUMBNAIL LOGIC
        base_dir = os.path.dirname(full_path)
        base_name, ext = os.path.splitext(filename)
        ext = ext.lower()
        
        valid_img_exts = ['.jpg', '.jpeg', '.png', '.tga', '.tiff', '.tif', '.bmp', '.exr']
        
        if ext in valid_img_exts:
            self.thumb_path = full_path
        else:
            target_thumb = os.path.join(base_dir, ".thumbnails", base_name + ".jpg")
            if not os.path.exists(target_thumb):
                target_thumb = os.path.join(base_dir, base_name + ".jpg")
            self.thumb_path = target_thumb
        
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.setLayout(self.layout)
        
        self.image_area = QLabel()
        self.image_area.setFixedHeight(180) 
        self.image_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.image_area.setAlignment(Qt.AlignCenter)
        
        # DEFAULT STYLE
        self.image_area.setStyleSheet(f"background-color: {color}; border-radius: 6px;")
        
        # Load Image using STYLE SHEET 
        if os.path.exists(self.thumb_path):
            clean_path = self.thumb_path.replace("\\", "/")
            self.image_area.setStyleSheet(f"""
                border-image: url('{clean_path}') 0 0 0 0 stretch stretch;
                border-radius: 6px;
                background-color: transparent; 
            """)

        self.layout.addWidget(self.image_area)
        
        self.name_lbl = QLabel(filename)
        self.name_lbl.setStyleSheet("color: white; font-weight: bold; font-size: 12px; border: none; background: transparent;")
        self.name_lbl.setWordWrap(True)
        self.layout.addWidget(self.name_lbl)
        
        self.status_lbl = QLabel("PUBLISHED ✓")
        self.status_lbl.setStyleSheet("color: #00ff00; font-size: 11px; font-weight: bold; border: none; background: transparent;")
        self.status_lbl.hide()
        self.layout.addWidget(self.status_lbl)
        
        self.update_border()

    def mousePressEvent(self, event):
        # right-click only if export file in asset context
        if event.button() == Qt.RightButton and self.file_type == "export":
            self.show_context_menu(event.pos())
        else:
            self.clicked.emit(self)
        super().mousePressEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        if self.full_path:
            self.double_clicked.emit(self)
        super().mouseDoubleClickEvent(event)

    def show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #333; color: white; border: 1px solid #555; } QMenu::item:selected { background-color: #555; }")
        
        if self.is_published:
            action = QAction("Unpublish", self)
            action.triggered.connect(lambda: self.action_triggered.emit("unpublish", self))
        else:
            action = QAction("Publish", self)
            action.triggered.connect(lambda: self.action_triggered.emit("publish", self))
            
        menu.addAction(action)
        menu.exec_(self.mapToGlobal(pos))

    def set_selected(self, selected):
        self.is_selected = selected
        self.update_border()

    def mark_published(self, published=True):
        self.is_published = published
        if published: self.status_lbl.show()
        else: self.status_lbl.hide()
        self.update_border()

    def update_border(self):
        base_bg = "#1e1e1e"
        hover_bg = "#333333" 
        css = "ThumbnailCard { border-radius: 10px; }"
        if self.is_selected:
            css += f"ThumbnailCard {{ background-color: {base_bg}; border: 3px solid #ffcc00; padding: 2px; }}"
        elif self.is_published:
            css += f"ThumbnailCard {{ background-color: {base_bg}; border: 3px solid #00ff00; }}"
        else:
            css += f"ThumbnailCard {{ background-color: {base_bg}; border: none; }} ThumbnailCard:hover {{ background-color: {hover_bg}; }}"
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
        self.lbl_range.setStyleSheet("color: #ffcc00; font-size: 14px; font-weight: bold; background: transparent; border: none;")
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
        self.existing_data = existing_data or {}
        self.setStyleSheet("""
            QFrame { background-color: #222; border-radius: 8px; }
            QLabel { color: #aaa; font-size: 12px; border: none; }
            QLineEdit, QComboBox, QTextEdit { background-color: #333; color: white; border: 1px solid #444; border-radius: 4px; padding: 5px; }
            QPushButton { padding: 8px; font-weight: bold; border-radius: 4px; border: none; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
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
            "thumbnail_path": self.thumbnail_path
        }
        self.saved.emit(data)

# MAIN APP

class OrionLauncherUI(QWidget):
    def __init__(self):
        super().__init__()
        self.orion = OrionUtils()
        if hasattr(self.orion, 'check_and_update_schema'):
            self.orion.check_and_update_schema()
            
        self.project_root = self.orion.get_root_dir()
        self.current_context = "Shots"
        self.current_shot_code = None
        self.current_task_path = None
        
        self.active_buttons = {"col1": None, "task": None} 
        self.selected_card = None 
        
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f'OrionTech')
        self.resize(1500, 900)
        self.setStyleSheet("background-color: #121212; font-family: Segoe UI, sans-serif;")

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
        
        self.context_switch = ContextSwitch()
        self.context_switch.mode_changed.connect(self.switch_context)
        self.col1_root.insertWidget(0, self.context_switch, 0, Qt.AlignCenter)
        self.col1_root.insertSpacing(1, 10)
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
        edit_btn.setStyleSheet("background-color: #ffaa00; color: #222; font-weight: bold; border-radius: 5px; height: 30px; border: none;")
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
        self.col2_bottom_widget.setVisible(False) 
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
        self.col2_splitter.setStretchFactor(0, 2)
        self.col2_splitter.setStretchFactor(1, 1)
        
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
            QMessageBox.warning(self, "Select Shot", "Please select a shot to edit.")
            return
            
        full_data = {}
        shot_row = self.orion.get_shot(self.current_shot_code)
        if shot_row:
            full_data["code"] = shot_row['code']
            full_data["frame_start"] = shot_row['frame_start']
            full_data["frame_end"] = shot_row['frame_end']
            
            if 'discord_thread_id' in shot_row.keys():
                full_data["discord_thread_id"] = shot_row['discord_thread_id']
            else:
                 tid = self.orion.get_shot_thread_id(self.current_shot_code)
                 full_data["discord_thread_id"] = tid if tid else ""
                 
            if 'description' in shot_row.keys():
                full_data["description"] = shot_row['description']
            if 'thumbnail_path' in shot_row.keys():
                full_data["thumbnail_path"] = shot_row['thumbnail_path']
        else:
            full_data["code"] = self.current_shot_code
            
        try:
            meta_path = os.path.join(self.project_root, "40_shots", self.current_shot_code, "orion_meta.json")
            if os.path.exists(meta_path):
                with open(meta_path, 'r') as f:
                    d = json.load(f)
                    if "description" not in full_data or not full_data["description"]:
                        full_data["description"] = d.get("description", "")
        except: pass

        self.context_switch.hide()
        self.action_bar.hide()
        self.col1_scroll.hide()
        
        self.editor = ShotEditor(mode="edit", existing_data=full_data)
        self.editor.saved.connect(self.save_edited_shot)
        self.editor.cancelled.connect(self.exit_edit_mode)
        
        self.col1_root.insertWidget(2, self.editor)

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
                    self.current_shot_code = None
                    self.active_buttons["col1"] = None
                    self.clear_layout(self.col2_content) 
                    self.clear_layout(self.col2_export_layout) 
                    self.info_panel.setVisible(False)
                    self.populate_column_1()
                    QMessageBox.information(self, "Deleted", f"{item_type} deleted successfully.")
                else:
                    QMessageBox.warning(self, "Error", "Failed to delete item.")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def switch_context(self, mode):
        self.current_context = mode
        self.active_buttons = {"col1": None, "task": None}
        self.clear_layout(self.col2_content)
        self.clear_layout(self.col2_export_layout) 
        self.clear_gallery()
        self.info_panel.setVisible(False) 
        
        # Toggle Asset Layout in Col 2
        if mode == "Assets":
            self.col2_bottom_widget.setVisible(True)
        else:
            self.col2_bottom_widget.setVisible(False)
            
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
        
        if self.current_context == "Assets":
            # Asset Logic:
            # Gallery = Work Files (Excluding .EXPORT, .BIN)
            self.populate_gallery(full_path, exclude_dirs=[".EXPORT", ".BIN"])
            # Col 2 Bottom = Export Files
            self.populate_exports_pane(full_path)
        else:
            # Shot Logic: Standard Gallery
            self.populate_gallery(full_path)

    def populate_exports_pane(self, task_path):
        """Populates the bottom of Column 2 with items from .EXPORT and .EXPORT/.PUBLISHED"""
        self.clear_layout(self.col2_export_layout)
        
        export_path = os.path.join(task_path, ".EXPORT")
        publish_path = os.path.join(export_path, ".PUBLISHED")
        
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
        publish_dir = os.path.join(dir_name, ".PUBLISHED")
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
        
        bin_dir = os.path.join(task_dir, ".BIN")
        if not os.path.exists(bin_dir): os.makedirs(bin_dir)
        
        dst = os.path.join(bin_dir, item.filename)

        if os.path.exists(dst):
            base, ext = os.path.splitext(item.filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dst = os.path.join(bin_dir, f"{base}_{timestamp}{ext}")

        try:
            shutil.move(item.full_path, dst)
            QMessageBox.information(self, "Unpublished", f"Moved to .BIN:\n{os.path.basename(dst)}")
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
        open_btn.setStyleSheet("background-color: #ffaa00; color: #222; font-weight: bold; border-radius: 5px;")
        open_btn.clicked.connect(self.on_open_folder_clicked)
        
        bottom_bar.addWidget(self.pub_btn)   
        bottom_bar.addStretch()             
        bottom_bar.addWidget(self.new_btn)   
        bottom_bar.addWidget(open_btn)       
        
        layout.addWidget(bottom_bar_container)
        return layout

    def on_new_file_clicked(self):
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
            cmd_args = [sys.executable, launcher_abs_path]
            if self.current_shot_code:
                cmd_args.extend(["", self.current_shot_code])
            subprocess.Popen(cmd_args)
        else:
            QMessageBox.warning(self, "Error", f"Launcher script not found: {launcher_abs_path}")

    def launch_dcc_file(self, card):
        file_path = card.full_path
        ext = os.path.splitext(file_path)[1].lower()
        shot_code = self.current_shot_code
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
                cmd_args = [sys.executable, launcher_abs_path, file_path]
                if shot_code: cmd_args.append(shot_code)
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
        header = QLabel(text)
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("color: #aaa; font-weight: bold; background-color: #3e3e3e; border-radius: 10px;")
        header.setFixedSize(140, 25)
        layout.addWidget(header, 0, Qt.AlignCenter)

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