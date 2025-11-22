import sys
import os
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, 
                             QVBoxLayout, QHBoxLayout, QCheckBox, QTabWidget, 
                             QMessageBox, QComboBox, QLineEdit, QFrame)
from PyQt5.QtCore import Qt

class OrionTechUI(QWidget):
    def __init__(self, orion_utils_inst, system_utils_inst, prefs_utils_inst):
        super().__init__()

        self.orion_utils = orion_utils_inst
        self.system_utils = system_utils_inst
        self.prefs_utils = prefs_utils_inst

        # Load user settings
        self.settings = self.prefs_utils.load_settings()
        self.current_user = os.getlogin()

        self.init_ui()
        self.apply_startup_settings()

    def init_ui(self):
        # WINDOW SETUP
        self.setWindowTitle('OrionTech Pipeline Manager')
        self.setGeometry(100, 100, 500, 600)
        
        self.layout = QVBoxLayout()
        self.tabs = QTabWidget() # Important: Init before adding tabs

        # --------------------------
        # TAB 1: PRODUCTION
        # --------------------------
        self.prod_tab = QWidget()
        self.prod_layout = QVBoxLayout()

        # A. Auto Create
        next_code = self.orion_utils.get_next_shot_code()
        self.lbl_next_shot = QLabel(f"Next Available Shot: <b>{next_code}</b>")
        self.lbl_next_shot.setStyleSheet("font-size: 14px; color: #2ecc71;") 
        
        self.btn_auto_create = QPushButton(f"Auto-Create {next_code}")
        self.btn_auto_create.clicked.connect(self.handle_auto_create)

        self.prod_layout.addWidget(QLabel("<b>Quick Creation</b>"))
        self.prod_layout.addWidget(self.lbl_next_shot)
        self.prod_layout.addWidget(self.btn_auto_create)
        
        self.add_separator(self.prod_layout)

        # B. Manual Create
        self.prod_layout.addWidget(QLabel("<b>Manual Creation</b>"))
        self.shot_code_input = QLineEdit()
        self.shot_code_input.setPlaceholderText("Custom Code (e.g. stc_0099)")
        
        frame_layout = QHBoxLayout()
        self.frame_start_input = QLineEdit()
        self.frame_start_input.setPlaceholderText("Start (1001)")
        self.frame_end_input = QLineEdit()
        self.frame_end_input.setPlaceholderText("End (1100)")
        frame_layout.addWidget(self.frame_start_input)
        frame_layout.addWidget(self.frame_end_input)

        self.create_shot_btn = QPushButton("Create Shot")
        self.create_shot_btn.clicked.connect(self.handle_manual_create)

        self.prod_layout.addWidget(self.shot_code_input)
        self.prod_layout.addLayout(frame_layout)
        self.prod_layout.addWidget(self.create_shot_btn)

        self.add_separator(self.prod_layout)

        # C. Manage Existing
        self.prod_layout.addWidget(QLabel("<b>Manage Shots</b>"))
        
        self.shot_selector = QComboBox()
        self.shot_selector.currentIndexChanged.connect(self.load_selected_shot_data)
        self.prod_layout.addWidget(self.shot_selector)

        edit_layout = QHBoxLayout()
        self.edit_start_input = QLineEdit()
        self.edit_start_input.setPlaceholderText("New Start")
        self.edit_end_input = QLineEdit()
        self.edit_end_input.setPlaceholderText("New End")
        edit_layout.addWidget(self.edit_start_input)
        edit_layout.addWidget(self.edit_end_input)
        self.prod_layout.addLayout(edit_layout)

        btn_layout = QHBoxLayout()
        self.btn_update_shot = QPushButton("Update Frames")
        self.btn_update_shot.clicked.connect(self.handle_update_shot)
        self.btn_delete_shot = QPushButton("Delete Shot")
        self.btn_delete_shot.setStyleSheet("background-color: #e74c3c; color: white;")
        self.btn_delete_shot.clicked.connect(self.handle_delete_shot)
        
        btn_layout.addWidget(self.btn_update_shot)
        btn_layout.addWidget(self.btn_delete_shot)
        self.prod_layout.addLayout(btn_layout)

        self.prod_layout.addStretch()
        self.prod_tab.setLayout(self.prod_layout)

        # --------------------------
        # TAB 2: PREFERENCES
        # --------------------------
        self.prefs_tab = QWidget()
        self.prefs_layout = QVBoxLayout()
        
        self.welcome_label = QLabel(f"User: <b>{self.current_user}</b>")
        self.software_selector = QComboBox()
        self.software_selector.addItems(self.orion_utils.software)

        self.load_prefs_button = QPushButton('Load Prefs')
        self.load_prefs_button.clicked.connect(self.load_prefs)
        
        self.save_prefs_button = QPushButton('Save Prefs')
        self.save_prefs_button.clicked.connect(self.save_prefs)

        self.prefs_layout.addWidget(self.welcome_label)
        self.prefs_layout.addWidget(QLabel("Select Software:"))
        self.prefs_layout.addWidget(self.software_selector)
        self.prefs_layout.addWidget(self.load_prefs_button)
        self.prefs_layout.addWidget(self.save_prefs_button)
        self.prefs_layout.addStretch()
        self.prefs_tab.setLayout(self.prefs_layout)

        # --------------------------
        # TAB 3: SETTINGS
        # --------------------------
        self.settings_tab = QWidget()
        self.settings_layout = QVBoxLayout()
        
        self.dark_mode_checkbox = QCheckBox('Enable Windows Dark Mode')
        self.discord_checkbox = QCheckBox('Open Discord on Startup')
        
        self.settings_layout.addWidget(self.dark_mode_checkbox)
        self.settings_layout.addWidget(self.discord_checkbox)
        self.settings_layout.addStretch()
        self.settings_tab.setLayout(self.settings_layout)

        # Connections
        self.dark_mode_checkbox.stateChanged.connect(self.toggle_dark_mode)
        self.discord_checkbox.stateChanged.connect(self.toggle_discord_startup)
        
        # Set Defaults
        self.dark_mode_checkbox.setChecked(self.settings.get('dark_mode', False))
        self.discord_checkbox.setChecked(self.settings.get('discord_on_startup', False))

        # Add Tabs and Finalize
        self.tabs.addTab(self.prod_tab, 'Production')
        self.tabs.addTab(self.prefs_tab, 'Prefs')
        self.tabs.addTab(self.settings_tab, 'Settings')
        
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

        # Initial Load
        self.refresh_shot_list()

    # --- HELPERS ---
    def add_separator(self, layout):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

    def apply_startup_settings(self):
        if self.settings.get('dark_mode', False):
            self.system_utils.set_windows_dark_mode(True)

    # --- PRODUCTION HANDLERS ---
    def handle_auto_create(self):
        next_code = self.orion_utils.get_next_shot_code()
        try:
            self.orion_utils.create_shot(next_code, 1001, 1100, self.current_user)
            QMessageBox.information(self, "Success", f"Created {next_code}")
            self.refresh_ui_states()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def handle_manual_create(self):
        code = self.shot_code_input.text()
        if not code: return
        try:
            s = int(self.frame_start_input.text())
            e = int(self.frame_end_input.text())
            self.orion_utils.create_shot(code, s, e, self.current_user)
            QMessageBox.information(self, "Success", f"Created {code}")
            self.refresh_ui_states()
        except ValueError:
            QMessageBox.warning(self, "Error", "Frames must be integers.")

    def handle_update_shot(self):
        code = self.shot_selector.currentData()
        if not code: return
        try:
            s = int(self.edit_start_input.text())
            e = int(self.edit_end_input.text())
            if self.orion_utils.update_shot_frames(code, s, e):
                QMessageBox.information(self, "Success", "Shot updated.")
                self.refresh_shot_list()
        except ValueError:
            QMessageBox.warning(self, "Error", "Invalid frames.")

    def handle_delete_shot(self):
        code = self.shot_selector.currentData()
        if not code: return
        confirm = QMessageBox.question(self, "Delete", f"Delete {code} from Database?", QMessageBox.Yes|QMessageBox.No)
        if confirm == QMessageBox.Yes:
            if self.orion_utils.delete_shot(code):
                QMessageBox.information(self, "Deleted", "Shot removed.")
                self.refresh_ui_states()

    def refresh_ui_states(self):
        """Updates label and dropdown"""
        next_code = self.orion_utils.get_next_shot_code()
        self.lbl_next_shot.setText(f"Next Available Shot: <b>{next_code}</b>")
        self.btn_auto_create.setText(f"Auto-Create {next_code}")
        self.refresh_shot_list()

    def refresh_shot_list(self):
        self.shot_selector.blockSignals(True)
        self.shot_selector.clear()
        self.shot_selector.addItem("Select a Shot...", None)
        for shot in self.orion_utils.get_all_shots():
            label = f"{shot['code']} ({shot['frame_start']}-{shot['frame_end']})"
            self.shot_selector.addItem(label, shot['code'])
        self.shot_selector.blockSignals(False)

    def load_selected_shot_data(self):
        code = self.shot_selector.currentData()
        if code:
            shot = self.orion_utils.get_shot(code)
            if shot:
                self.edit_start_input.setText(str(shot['frame_start']))
                self.edit_end_input.setText(str(shot['frame_end']))

    # --- PREFS & SETTINGS HANDLERS ---
    def load_prefs(self):
        self.prefs_utils.load_prefs(self.software_selector.currentText(), self.current_user)
        QMessageBox.information(self, "Success", "Preferences Loaded")

    def save_prefs(self):
        self.prefs_utils.save_prefs(self.software_selector.currentText(), self.current_user)
        QMessageBox.information(self, "Success", "Preferences Saved")

    def toggle_dark_mode(self, state):
        self.settings['dark_mode'] = (state == Qt.Checked)
        self.prefs_utils.save_settings(self.settings)
        self.system_utils.set_windows_dark_mode(state == Qt.Checked)

    def toggle_discord_startup(self, state):
        self.settings['discord_on_startup'] = (state == Qt.Checked)
        self.prefs_utils.save_settings(self.settings)