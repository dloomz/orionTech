import sys
import os

from core.orionUtils import OrionUtils
from core.systemUtils import SystemUtils
from core.prefsUtils import PrefsUtils

orion_utils = OrionUtils()
libs_path = orion_utils.get_libs_path()

if libs_path not in sys.path:
    sys.path.insert(0, libs_path)

from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QCheckBox, QTabWidget, QMessageBox, QComboBox, QLineEdit
from PyQt5.QtCore import Qt

class OrionTechUI(QWidget):
    def __init__(self, orion_utils_inst, system_utils_inst, prefs_utils_inst):
        super().__init__()

        self.orion_utils = orion_utils_inst
        self.system_utils = system_utils_inst
        self.prefs_utils = prefs_utils_inst

        self.settings = self.prefs_utils.load_settings()
        self.current_user = os.getlogin()

        self.init_ui()
        self.apply_startup_settings()

    def init_ui(self):
        #SETUP MAIN WINDOW & TABS FIRST
        self.setWindowTitle('OrionTech Prefs Manager')
        self.setGeometry(100, 100, 400, 300)

        self.layout = QVBoxLayout()
        self.tabs = QTabWidget() # Initialize tab widget here

        #PRODUCTION TAB
        self.prod_tab = QWidget()
        self.prod_layout = QVBoxLayout()

        #shot Creation Interface
        self.shot_code_input = QLineEdit()
        self.shot_code_input.setPlaceholderText("Shot Code (e.g., sh010)")
        self.frame_start_input = QLineEdit()
        self.frame_start_input.setPlaceholderText("Start Frame")
        self.frame_end_input = QLineEdit()
        self.frame_end_input.setPlaceholderText("End Frame")

        self.create_shot_btn = QPushButton("Create / Update Shot")
        self.create_shot_btn.clicked.connect(self.handle_create_shot)

        self.prod_layout.addWidget(QLabel("Shot Management"))
        self.prod_layout.addWidget(self.shot_code_input)
        self.prod_layout.addWidget(self.frame_start_input)
        self.prod_layout.addWidget(self.frame_end_input)
        self.prod_layout.addWidget(self.create_shot_btn)

        self.prod_tab.setLayout(self.prod_layout)
        
        #PREFS TAB
        self.prefs_tab = QWidget()
        self.prefs_layout = QVBoxLayout()
        
        self.welcome_label = QLabel(f"Welcome, {self.current_user}")

        #dropdown to select the software
        self.software_selector = QComboBox()
        self.software_selector.addItems(self.orion_utils.software)

        self.load_prefs_button = QPushButton('Load Prefs')
        self.save_prefs_button = QPushButton('Save Prefs')

        self.prefs_layout.addWidget(self.welcome_label)
        self.prefs_layout.addWidget(self.software_selector)
        self.prefs_layout.addWidget(self.load_prefs_button)
        self.prefs_layout.addWidget(self.save_prefs_button)
        self.prefs_tab.setLayout(self.prefs_layout)

        #SETTINGS TAB
        self.settings_tab = QWidget()
        self.settings_layout = QVBoxLayout()
        self.dark_mode_checkbox = QCheckBox('Enable Windows Dark Mode')
        self.discord_checkbox = QCheckBox('Open Discord on Startup')
        self.settings_layout.addWidget(self.dark_mode_checkbox)
        self.settings_layout.addWidget(self.discord_checkbox)
        self.settings_tab.setLayout(self.settings_layout)

        #ADD ALL TABS TO MAIN WIDGET
        self.tabs.addTab(self.prod_tab, 'Production')
        self.tabs.addTab(self.prefs_tab, 'Prefs')
        self.tabs.addTab(self.settings_tab, 'Settings')

        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

        #ONNECTIONS & DEFAULTS
        self.load_prefs_button.clicked.connect(self.load_prefs)
        self.save_prefs_button.clicked.connect(self.save_prefs)
        self.dark_mode_checkbox.stateChanged.connect(self.toggle_dark_mode)
        self.discord_checkbox.stateChanged.connect(self.toggle_discord_startup)

        self.dark_mode_checkbox.setChecked(self.settings.get('dark_mode', False))
        self.discord_checkbox.setChecked(self.settings.get('discord_on_startup', False))

    def handle_create_shot(self):
        code = self.shot_code_input.text()
        start = int(self.frame_start_input.text())
        end = int(self.frame_end_input.text())
        
        # Use your upgraded utils to talk to the DB
        self.orion_utils.create_shot(code, start, end, self.current_user)
        QMessageBox.information(self, "Success", f"Shot {code} logged in Database!")

    def apply_startup_settings(self):

        dark_mode_enabled = self.settings.get('dark_mode', False)
        if dark_mode_enabled:
            self.system_utils.set_windows_dark_mode(True)

    #Button Functions
    def load_prefs(self):

        selected_software = self.software_selector.currentText()
        self.prefs_utils.load_prefs(selected_software, self.current_user)
        QMessageBox.information(self, "Success", "Preferences loaded!")

    def save_prefs(self):

        selected_software = self.software_selector.currentText()
        self.prefs_utils.save_prefs(selected_software, self.current_user)
        QMessageBox.information(self, f"Save {selected_software.capitalize()} Prefs", "Preferences saved!")

    def toggle_dark_mode(self, state):

        is_checked = state == Qt.Checked
        self.settings['dark_mode'] = is_checked
        self.prefs_utils.save_settings(self.settings)
        self.system_utils.set_windows_dark_mode(is_checked)


    def toggle_discord_startup(self, state):

        is_checked = state == Qt.Checked
        self.settings['discord_on_startup'] = is_checked
        self.prefs_utils.save_settings(self.settings)