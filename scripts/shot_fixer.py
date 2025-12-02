import sys
import os
import re
import json
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QLabel, QMessageBox)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt

#import core
current_dir = os.path.dirname(os.path.abspath(__file__))
pipeline_root = os.path.dirname(current_dir)
if pipeline_root not in sys.path:
    sys.path.append(pipeline_root)

from core.orionUtils import OrionUtils

class ShotFixer(QWidget):
    def __init__(self):
        super().__init__()
        self.orion = OrionUtils()
        
        #path 2 scan
        root_attempt = os.path.join(self.orion.get_root_dir(), "40_shots")
        if os.path.exists(root_attempt):
             self.root_path = os.path.abspath(root_attempt)
        else:
             #safe fallback
             self.root_path = r"P:\all_work\studentGroups\ORION_CORPORATION\00_pipeline\40_shots"

        self.setWindowTitle("Orion Shot Fixer & Migrator")
        self.setGeometry(200, 200, 1200, 600)
        self.init_ui()
        self.scan_folders()

    def init_ui(self):
        layout = QVBoxLayout()

        header_layout = QHBoxLayout()
        self.lbl_path = QLabel(f"Scanning: {self.root_path}")
        self.lbl_path.setStyleSheet("font-weight: bold; font-size: 14px; color: #3498db;")
        btn_refresh = QPushButton("Rescan")
        btn_refresh.clicked.connect(self.scan_folders)
        header_layout.addWidget(self.lbl_path)
        header_layout.addWidget(btn_refresh)
        layout.addLayout(header_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(7) 
        self.table.setHorizontalHeaderLabels(["Current Folder", "Target Code", "Health", "DB Status", "ID Status", "Action", "Target Path"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        self.btn_fix_all = QPushButton("Fix All Issues (With Confirmation)")
        self.btn_fix_all.setStyleSheet("background-color: #e67e22; color: white; font-weight: bold; padding: 10px;")
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
        
        #check name
        if folder_name != proposed:
            state["issues"].append("Wrong Name")

        #check db
        in_db_as_proposed = self.orion.check_shot_exists_in_db(proposed)
        in_db_as_current = self.orion.check_shot_exists_in_db(folder_name)

        if in_db_as_proposed:
            state["db_status"] = "Good (Exists)"
            shot_data = self.orion.get_shot(proposed)
            if shot_data:
                shot_id = shot_data['id']
                if len(shot_id) > 20 and shot_id != proposed:
                    state["id_status"] = "Complex ID"
                    state["issues"].append("Simplify ID")
                else:
                    state["id_status"] = "Simple"
                    
        elif in_db_as_current:
            state["db_status"] = "Old Name in DB"
            state["issues"].append("DB needs Update")
        else:
            state["db_status"] = "Missing"
            state["issues"].append("Register in DB")

        #check struc
        missing_subs = False
        for sub in self.orion.SHOT_SUBFOLDERS:
            if not os.path.exists(os.path.join(full_path, sub)):
                missing_subs = True
                break
        if missing_subs:
            state["issues"].append("Missing Folders")

        #check tags n path
        expected_rel_path = self.orion.get_relative_path(full_path)
        
        json_path = os.path.join(full_path, "orion_meta.json")
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r') as f:
                    data = json.load(f)
                    #check if stored path matches expected RELATIVE path
                    if data.get("original_path") != expected_rel_path:
                        state["issues"].append("JSON Path Update")
                    if data.get("code") != proposed:
                         state["issues"].append("JSON Code Update")
            except:
                state["issues"].append("JSON Corrupt")
        else:
            state["issues"].append("Missing JSON")

        if not os.path.exists(os.path.join(full_path, f".id_{proposed}")):
            state["issues"].append("Missing ID Tag")

        if state["issues"]:
            state["action_needed"] = True
            
        return state

    def scan_folders(self):
        self.table.setRowCount(0)
        if not os.path.exists(self.root_path):
            QMessageBox.warning(self, "Error", f"Path not found: {self.root_path}")
            return

        folders = sorted(os.listdir(self.root_path))
        
        row = 0
        for folder in folders:
            full_path = os.path.join(self.root_path, folder)
            if not os.path.isdir(full_path): continue
            if folder.lower() == "old": continue 

            state = self.analyze_folder(folder, full_path)
            proposed = self.get_proposed_name(folder)
            
            #calc relative path
            rel_path = self.orion.get_relative_path(full_path)

            self.table.insertRow(row)
            
            item_name = QTableWidgetItem(folder)
            item_prop = QTableWidgetItem(proposed)
            
            health_str = ", ".join(state["issues"]) if state["issues"] else "Healthy"
            item_health = QTableWidgetItem(health_str)
            
            item_db = QTableWidgetItem(state["db_status"])
            item_id = QTableWidgetItem(state["id_status"])
            item_path = QTableWidgetItem(rel_path)

            #styling
            if not state["action_needed"]:
                item_health.setBackground(QColor("#27ae60")) # Green
                item_health.setForeground(QColor("white"))
            else:
                item_health.setBackground(QColor("#c0392b")) # Red
                item_health.setForeground(QColor("white"))

            if state["db_status"] == "Old Name in DB":
                item_db.setBackground(QColor("#f39c12")) # Orange
            
            if state["id_status"] == "Complex ID":
                item_id.setBackground(QColor("#e74c3c")) # Red
                item_id.setForeground(QColor("white"))

            btn_fix = QPushButton("Fix")
            btn_fix.clicked.connect(lambda ch, r=row: self.fix_row(r))
            if not state["action_needed"]:
                btn_fix.setEnabled(False)

            self.table.setItem(row, 0, item_name)
            self.table.setItem(row, 1, item_prop)
            self.table.setItem(row, 2, item_health)
            self.table.setItem(row, 3, item_db)
            self.table.setItem(row, 4, item_id)
            self.table.setCellWidget(row, 5, btn_fix)
            self.table.setItem(row, 6, item_path)
            
            row += 1

    def fix_row(self, row):
        current_name = self.table.item(row, 0).text()
        proposed_name = self.table.item(row, 1).text()
        health = self.table.item(row, 2).text()
        db_status = self.table.item(row, 3).text()
        id_status = self.table.item(row, 4).text()
        
        current_physical_path = os.path.join(self.root_path, current_name)
        
        #RENAME
        final_physical_path = current_physical_path
        if "Wrong Name" in health:
            reply = QMessageBox.question(self, "Confirm Rename", 
                                       f"Rename folder '{current_name}' to '{proposed_name}'?\n",
                                       QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                new_physical_path = os.path.join(self.root_path, proposed_name)
                try:
                    os.rename(current_physical_path, new_physical_path)
                    final_physical_path = new_physical_path
                    print(f"Renamed {current_name} -> {proposed_name}")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Rename failed: {e}")
                    return
            else:
                return 

        #DB UPDATE
        if db_status == "Old Name in DB":
            reply = QMessageBox.question(self, "Update Database Code", 
                                       f"DB lists '{current_name}'.\nREPLACE with '{proposed_name}'?",
                                       QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.orion.rename_shot_code_in_db(current_name, proposed_name)

        elif db_status == "Missing":
            reply = QMessageBox.question(self, "Register Database", 
                                       f"Register '{proposed_name}' in DB?",
                                       QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.orion.create_shot(proposed_name, 1001, 1100, "Migrated")

        #ID SIMPLIFICATION
        if id_status == "Complex ID" or "Simplify ID" in health:
             reply = QMessageBox.question(self, "Simplify DB ID", 
                                       f"Replace UUID with '{proposed_name}'?",
                                       QMessageBox.Yes | QMessageBox.No)
             if reply == QMessageBox.Yes:
                 self.orion.simplify_shot_id(proposed_name)

        #UPDATE PATH & TAGS (RELATIVE PATHS)
        #get relative path for DB/JSON
        final_rel_path = self.orion.get_relative_path(final_physical_path)
        
        if "Missing" in health or "Mismatch" in health or "Register" in health or "Update" in health or "JSON" in health:
            reply = QMessageBox.question(self, "Finalize", 
                                       f"Create structure, update tags,\n"
                                       f"and set DB/JSON path to RELATIVE path:\n{final_rel_path}?",
                                       QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.orion.create_shot_structure(proposed_name) 
                
                #OrionUtils internally handles relative path conversion
                #call it explicitly to be sure
                self.orion.create_meta_tag(final_physical_path, proposed_name, 
                                         {"type": "shot", "note": "Fixed/Migrated"})
                
                self.orion.register_shot_path(proposed_name, final_physical_path)

        QMessageBox.information(self, "Done", f"Processed {proposed_name}")
        self.scan_folders()

    def fix_all(self):
        rows = self.table.rowCount()
        for r in range(rows):
            if self.table.cellWidget(r, 5).isEnabled():
                self.fix_row(r)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    fixer = ShotFixer()
    fixer.show()
    sys.exit(app.exec_())