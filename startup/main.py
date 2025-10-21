import sys
import os
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QCheckBox, QTabWidget, QMessageBox, QComboBox
from PyQt5.QtCore import Qt

from utils.orionUtils import OrionUtils
from utils.systemUtils import SystemUtils
from utils.prefsUtils import PrefsUtils 

class OrionTechUI(QWidget):
    def __init__(self):
        super().__init__()

        self.orion_utils = OrionUtils()
        self.system_utils = SystemUtils()
        self.prefs_utils = PrefsUtils() 
        
        self.settings = self.prefs_utils.load_settings()
        self.current_user = os.getlogin()

        self.init_ui()
        self.apply_startup_settings()

    def init_ui(self):
        self.setWindowTitle('OrionTech Prefs Manager')
        self.setGeometry(100, 100, 400, 300)

        self.layout = QVBoxLayout()
        self.tabs = QTabWidget()
        self.prefs_tab = QWidget()
        self.settings_tab = QWidget()
        self.tabs.addTab(self.prefs_tab, 'Prefs')
        self.tabs.addTab(self.settings_tab, 'Settings')

        # Prefs Tab
        self.prefs_layout = QVBoxLayout()
        self.welcome_label = QLabel(f"Welcome, {self.current_user}")
        
        # Add a dropdown to select the software
        self.software_selector = QComboBox()
        self.software_selector.addItems(self.orion_utils.software)
        
        self.load_prefs_button = QPushButton('Load Prefs')
        self.save_prefs_button = QPushButton('Save Prefs')
        
        self.prefs_layout.addWidget(self.welcome_label)
        self.prefs_layout.addWidget(self.software_selector) 
        self.prefs_layout.addWidget(self.load_prefs_button)
        self.prefs_layout.addWidget(self.save_prefs_button)
        self.prefs_tab.setLayout(self.prefs_layout)

        # Settings Tab
        self.settings_layout = QVBoxLayout()
        self.dark_mode_checkbox = QCheckBox('Enable Windows Dark Mode')
        self.discord_checkbox = QCheckBox('Open Discord on Startup')
        self.settings_layout.addWidget(self.dark_mode_checkbox)
        self.settings_layout.addWidget(self.discord_checkbox)
        self.settings_tab.setLayout(self.settings_layout)

        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

        self.load_prefs_button.clicked.connect(self.load_prefs)
        self.save_prefs_button.clicked.connect(self.save_prefs)
        self.dark_mode_checkbox.stateChanged.connect(self.toggle_dark_mode)
        self.discord_checkbox.stateChanged.connect(self.toggle_discord_startup)
        
        self.dark_mode_checkbox.setChecked(self.settings.get('dark_mode', False))
        self.discord_checkbox.setChecked(self.settings.get('discord_on_startup', False))

    def apply_startup_settings(self):

        dark_mode_enabled = self.settings.get('dark_mode', False)
        self.system_utils.set_windows_dark_mode(dark_mode_enabled)

    #Button Functions
    def load_prefs(self):

        selected_software = self.software_selector.currentText()
        result = self.prefs_utils.load_prefs(selected_software, self.current_user)
        QMessageBox.information(self, f"Load {selected_software.capitalize()} Prefs", result)

    def save_prefs(self):

        selected_software = self.software_selector.currentText()
        result = self.prefs_utils.save_prefs(selected_software, self.current_user)
        QMessageBox.information(self, f"Save {selected_software.capitalize()} Prefs", result)

    def toggle_dark_mode(self, state):

        is_checked = state == Qt.Checked
        self.settings['dark_mode'] = is_checked
        self.orion_utils.save_settings(self.settings)
        self.system_utils.set_windows_dark_mode(is_checked)


    def toggle_discord_startup(self, state):
        
        is_checked = state == Qt.Checked
        self.settings['discord_on_startup'] = is_checked
        self.orion_utils.save_settings(self.settings)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = OrionTechUI()
    ex.show()
    sys.exit(app.exec_())