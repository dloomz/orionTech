import sys
import os
import re
import json
import uuid
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QLabel, QMessageBox, QTabWidget, QInputDialog)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt

# ORION PIPELINE SETUP
current_dir = os.path.dirname(os.path.abspath(__file__))
pipeline_root = os.path.dirname(current_dir)
if pipeline_root not in sys.path:
    sys.path.append(pipeline_root)

from core.orionUtils import OrionUtils

# --- SHOT TAB (Refactored Existing Logic) ---
class ShotFixerTab(QWidget):
    def __init__(self, orion_inst, root_path):
        super().__init__()
        self.orion = orion_inst
        self.root_path = root_path
        self.init_ui()
        self.scan_folders()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Info Header
        header_layout = QHBoxLayout()
        self.lbl_path = QLabel(f"Scanning Shots: {self.root_path}")
        self.lbl_path.setStyleSheet("font-weight: bold; color: #3498db;")
        btn_refresh = QPushButton("Rescan Shots")
        btn_refresh.clicked.connect(self.scan_folders)
        header_layout.addWidget(self.lbl_path)
        header_layout.addWidget(btn_refresh)
        layout.addLayout(header_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7) 
        self.table.setHorizontalHeaderLabels(["Folder Name", "Proposed Code", "Health", "DB Status", "ID Status", "Action", "Rel Path"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        # Footer Actions
        btn_layout = QHBoxLayout()
        self.btn_fix_all = QPushButton("Fix All Shots")
        self.btn_fix_all.setStyleSheet("background-color: #e67e22; color: white; font-weight: bold; padding: 8px;")
        self.btn_fix_all.clicked.connect(self.fix_all)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_fix_all)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def get_proposed_name(self, folder_name):
        match = re.search(r'(\d+)$', folder_name)
        if match:
            number = int(match.group(1))
            return f"stc_{number:04d}"
        return folder_name

    def analyze_folder(self, folder_name, full_path):
        state = {
            "issues": [],
            "db_status": "Unknown",
            "id_status": "Unknown",
            "action_needed": False
        }
        
        proposed = self.get_proposed_name(folder_name)
        
        # 1. Name Check
        if folder_name != proposed:
            state["issues"].append("Wrong Name")

        # 2. DB Check
        in_db_as_proposed = self.orion.check_shot_exists_in_db(proposed)
        in_db_as_current = self.orion.check_shot_exists_in_db(folder_name)

        if in_db_as_proposed:
            state["db_status"] = "Good"
            shot_data = self.orion.get_shot(proposed)
            if shot_data:
                shot_id = shot_data['id']
                # Check for complex/UUID IDs vs Simple IDs if strict mode wanted, 
                # but broadly we just ensure ID exists.
                if len(shot_id) > 20 and shot_id != proposed:
                    state["id_status"] = "UUID"
                else:
                    state["id_status"] = "Simple"
        elif in_db_as_current:
            state["db_status"] = "Old Name in DB"
            state["issues"].append("DB needs Update")
        else:
            state["db_status"] = "Missing"
            state["issues"].append("Register in DB")

        # 3. Structure Check
        missing_subs = False
        for sub in self.orion.SHOT_SUBFOLDERS:
            if not os.path.exists(os.path.join(full_path, sub)):
                missing_subs = True
                break
        if missing_subs:
            state["issues"].append("Missing Folders")

        # 4. Meta & Path Check
        expected_rel_path = self.orion.get_relative_path(full_path)
        json_path = os.path.join(full_path, "orion_meta.json")
        
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r') as f:
                    data = json.load(f)
                    if data.get("original_path") != expected_rel_path:
                        state["issues"].append("JSON Path Update")
                    if data.get("code") != proposed:
                         state["issues"].append("JSON Code Update")
            except:
                state["issues"].append("JSON Corrupt")
        else:
            state["issues"].append("Missing JSON")

        if not os.path.exists(os.path.join(full_path, f".id_{proposed}")) and \
           not any(f.startswith(".id_") for f in os.listdir(full_path)):
            state["issues"].append("Missing ID Tag")

        if state["issues"]:
            state["action_needed"] = True
            
        return state

    def scan_folders(self):
        self.table.setRowCount(0)
        if not os.path.exists(self.root_path):
            return

        folders = sorted(os.listdir(self.root_path))
        row = 0
        for folder in folders:
            full_path = os.path.join(self.root_path, folder)
            if not os.path.isdir(full_path) or folder.lower() == "old": 
                continue 

            state = self.analyze_folder(folder, full_path)
            proposed = self.get_proposed_name(folder)
            rel_path = self.orion.get_relative_path(full_path)

            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(folder))
            self.table.setItem(row, 1, QTableWidgetItem(proposed))
            
            item_health = QTableWidgetItem(", ".join(state["issues"]) if state["issues"] else "Healthy")
            if state["action_needed"]:
                item_health.setBackground(QColor("#c0392b"))
                item_health.setForeground(QColor("white"))
            else:
                item_health.setBackground(QColor("#27ae60"))
                item_health.setForeground(QColor("white"))
            self.table.setItem(row, 2, item_health)

            self.table.setItem(row, 3, QTableWidgetItem(state["db_status"]))
            self.table.setItem(row, 4, QTableWidgetItem(state["id_status"]))
            
            btn_fix = QPushButton("Fix")
            btn_fix.clicked.connect(lambda ch, r=row: self.fix_row(r))
            if not state["action_needed"]:
                btn_fix.setEnabled(False)
            self.table.setCellWidget(row, 5, btn_fix)
            
            self.table.setItem(row, 6, QTableWidgetItem(rel_path))
            row += 1

    def fix_row(self, row):
        current_name = self.table.item(row, 0).text()
        proposed_name = self.table.item(row, 1).text()
        health = self.table.item(row, 2).text()
        db_status = self.table.item(row, 3).text()
        
        current_physical_path = os.path.join(self.root_path, current_name)
        final_physical_path = current_physical_path

        # 1. Rename
        if "Wrong Name" in health:
            if QMessageBox.question(self, "Rename", f"Rename {current_name} -> {proposed_name}?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
                new_path = os.path.join(self.root_path, proposed_name)
                try:
                    os.rename(current_physical_path, new_path)
                    final_physical_path = new_path
                except Exception as e:
                    QMessageBox.critical(self, "Error", str(e))
                    return

        # 2. DB Updates
        if db_status == "Old Name in DB":
            self.orion.rename_shot_code_in_db(current_name, proposed_name)
        elif db_status == "Missing":
            self.orion.create_shot(proposed_name, 1001, 1100, "Migrated")

        # 3. Structure & Tags
        if "Missing" in health or "JSON" in health or "Update" in health:
            self.orion.create_shot_structure(proposed_name) # Ensure folders exist
            
            # Fetch ID to ensure tag consistency
            shot_data = self.orion.get_shot(proposed_name)
            shot_id = shot_data['id'] if shot_data else proposed_name
            
            self.orion.create_meta_tag(final_physical_path, proposed_name, shot_id=shot_id)
            self.orion.register_shot_path(proposed_name, final_physical_path)

        self.scan_folders()

    def fix_all(self):
        for r in range(self.table.rowCount()):
            if self.table.cellWidget(r, 5).isEnabled():
                self.fix_row(r)

# --- ASSET TAB (New Functionality) ---
class AssetFixerTab(QWidget):
    def __init__(self, orion_inst):
        super().__init__()
        self.orion = orion_inst
        self.root_path = os.path.join(self.orion.get_root_dir(), "30_assets")
        self.init_ui()
        self.scan_assets()

    def init_ui(self):
        layout = QVBoxLayout()
        
        header = QHBoxLayout()
        self.lbl_path = QLabel(f"Scanning Assets: {self.root_path}")
        self.lbl_path.setStyleSheet("font-weight: bold; color: #e67e22;")
        btn_refresh = QPushButton("Rescan Assets")
        btn_refresh.clicked.connect(self.scan_assets)
        header.addWidget(self.lbl_path)
        header.addWidget(btn_refresh)
        layout.addLayout(header)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Asset Name", "Health", "DB Status", "Path Status", "Action", "Relative Path"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        self.btn_fix_all = QPushButton("Fix All Assets")
        self.btn_fix_all.setStyleSheet("background-color: #3498db; color: white; font-weight: bold; padding: 8px;")
        self.btn_fix_all.clicked.connect(self.fix_all)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_fix_all)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)

    def analyze_asset(self, name, full_path):
        state = {
            "issues": [],
            "action_needed": False,
            "db_status": "Unknown",
            "path_status": "Unknown"
        }

        # 1. DB Check
        asset_record = self.orion.get_asset(name)
        if not asset_record:
            state["db_status"] = "Missing"
            state["issues"].append("Register in DB")
        else:
            state["db_status"] = "Exists"

        # 2. Path Check
        real_rel_path = self.orion.get_relative_path(full_path)
        if asset_record:
            db_path = asset_record['path']
            if db_path != real_rel_path:
                state["path_status"] = "Mismatch"
                state["issues"].append("Update DB Path")
            else:
                state["path_status"] = "Synced"
        else:
            state["path_status"] = "N/A"

        # 3. Meta Files Check
        meta_json = os.path.join(full_path, "orion_meta.json")
        has_id_marker = any(f.startswith(".id_") for f in os.listdir(full_path))
        
        if not os.path.exists(meta_json):
            state["issues"].append("Missing Meta JSON")
        if not has_id_marker:
            state["issues"].append("Missing ID Tag")

        if state["issues"]:
            state["action_needed"] = True

        return state

    def scan_assets(self):
        self.table.setRowCount(0)
        if not os.path.exists(self.root_path):
            return

        items = sorted(os.listdir(self.root_path))
        row = 0
        for item in items:
            full_path = os.path.join(self.root_path, item)
            if not os.path.isdir(full_path) or item.startswith("."):
                continue

            state = self.analyze_asset(item, full_path)
            rel_path = self.orion.get_relative_path(full_path)

            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(item))

            # Health
            health_str = ", ".join(state["issues"]) if state["issues"] else "Healthy"
            item_health = QTableWidgetItem(health_str)
            if state["action_needed"]:
                item_health.setBackground(QColor("#c0392b"))
                item_health.setForeground(QColor("white"))
            else:
                item_health.setBackground(QColor("#27ae60"))
                item_health.setForeground(QColor("white"))
            self.table.setItem(row, 1, item_health)

            self.table.setItem(row, 2, QTableWidgetItem(state["db_status"]))
            self.table.setItem(row, 3, QTableWidgetItem(state["path_status"]))

            btn_fix = QPushButton("Fix")
            btn_fix.clicked.connect(lambda ch, r=row: self.fix_row(r))
            if not state["action_needed"]: btn_fix.setEnabled(False)
            self.table.setCellWidget(row, 4, btn_fix)

            self.table.setItem(row, 5, QTableWidgetItem(rel_path))
            row += 1

    def fix_row(self, row):
        name = self.table.item(row, 0).text()
        full_path = os.path.join(self.root_path, name)
        
        # 1. Determine ID and Type (Try to read existing meta first)
        asset_id = None
        asset_type = "Prop" # Default
        meta_json = os.path.join(full_path, "orion_meta.json")
        
        if os.path.exists(meta_json):
            try:
                with open(meta_json, 'r') as f:
                    d = json.load(f)
                    asset_id = d.get("id")
                    asset_type = d.get("asset_type", "Prop")
            except: pass
        
        # If no ID found in meta, check .id_ marker
        if not asset_id:
            for f in os.listdir(full_path):
                if f.startswith(".id_"):
                    asset_id = f.replace(".id_", "")
                    break
        
        # If still no ID, generate one
        if not asset_id:
            asset_id = str(uuid.uuid4())

        # 2. Fix DB
        conn = self.orion.get_db_connection()
        try:
            rel_path = self.orion.get_relative_path(full_path)
            
            # Check if exists to decide INSERT or UPDATE
            exists = conn.execute("SELECT 1 FROM assets WHERE name = ?", (name,)).fetchone()
            
            if not exists:
                # Register new
                conn.execute(
                    "INSERT INTO assets (id, name, type, path, description, thumbnail_path) VALUES (?, ?, ?, ?, ?, ?)",
                    (asset_id, name, asset_type, rel_path, "", "")
                )
                print(f"Registered asset: {name}")
            else:
                # Update Path
                conn.execute("UPDATE assets SET path = ?, id = ? WHERE name = ?", (rel_path, asset_id, name))
                print(f"Updated asset path: {name}")
            
            conn.commit()
        except Exception as e:
            QMessageBox.critical(self, "DB Error", str(e))
            return
        finally:
            conn.close()

        # 3. Fix Meta & Structure
        # Ensure standard folders exist
        for task_group, subfolders in self.orion.ASSET_TASKS.items():
            group_path = os.path.join(full_path, task_group)
            os.makedirs(group_path, exist_ok=True)
            for sub in subfolders:
                os.makedirs(os.path.join(group_path, sub), exist_ok=True)
                
        # Write Meta Tag
        self.orion.asset_create_meta_tag(full_path, name, {"type": "asset", "asset_type": asset_type}, asset_id=asset_id)
        
        # Ensure .id_ marker
        marker = os.path.join(full_path, f".id_{asset_id}")
        if not os.path.exists(marker):
            with open(marker, 'w') as f: f.write(name)
            if os.name == 'nt':
                import subprocess
                subprocess.run(["attrib", "+h", marker], check=False, shell=True)

        self.scan_assets()

    def fix_all(self):
        for r in range(self.table.rowCount()):
            if self.table.cellWidget(r, 4).isEnabled():
                self.fix_row(r)

# --- MAIN WINDOW ---
class OrionFixerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.orion = OrionUtils()
        self.setWindowTitle("Orion Pipeline Fixer & Migrator")
        self.resize(1200, 700)
        
        layout = QVBoxLayout(self)
        
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # TAB 1: SHOTS
        shots_root = os.path.join(self.orion.get_root_dir(), "40_shots")
        if not os.path.exists(shots_root):
             # Fallback hardcoded for safety if env not set
             shots_root = r"P:\all_work\studentGroups\ORION_CORPORATION\00_pipeline\40_shots"
        
        self.shot_tab = ShotFixerTab(self.orion, shots_root)
        self.tabs.addTab(self.shot_tab, "Shot Fixer")
        
        # TAB 2: ASSETS
        self.asset_tab = AssetFixerTab(self.orion)
        self.tabs.addTab(self.asset_tab, "Asset Fixer")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Dark Mode Style
    app.setStyle("Fusion")
    palette = app.palette()
    palette.setColor(palette.Window, QColor(53, 53, 53))
    palette.setColor(palette.WindowText, Qt.white)
    palette.setColor(palette.Base, QColor(25, 25, 25))
    palette.setColor(palette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(palette.ToolTipBase, Qt.white)
    palette.setColor(palette.ToolTipText, Qt.white)
    palette.setColor(palette.Text, Qt.white)
    palette.setColor(palette.Button, QColor(53, 53, 53))
    palette.setColor(palette.ButtonText, Qt.white)
    palette.setColor(palette.BrightText, Qt.red)
    palette.setColor(palette.Link, QColor(42, 130, 218))
    palette.setColor(palette.Highlight, QColor(42, 130, 218))
    palette.setColor(palette.HighlightedText, Qt.black)
    app.setPalette(palette)

    win = OrionFixerWindow()
    win.show()
    sys.exit(app.exec_())