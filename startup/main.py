import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QCheckBox, QTabWidget
from utils.orionUtils import OrionUtils

class OrionTechUI(QWidget):
    def __init__(self):
        super().__init__()
        self.orion_utils = OrionUtils()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('OrionTech Prefs Manager')
        self.setGeometry(100, 100, 400, 300)

        # Main layout
        self.layout = QVBoxLayout()

        # Tabs
        self.tabs = QTabWidget()
        self.prefs_tab = QWidget()
        self.settings_tab = QWidget()

        self.tabs.addTab(self.prefs_tab, 'Prefs')
        self.tabs.addTab(self.settings_tab, 'Settings')

        #Prefs Tab
        self.prefs_layout = QVBoxLayout()
        self.welcome_label = QLabel(f"Welcome, {os.getlogin()}")
        self.load_prefs_button = QPushButton('Load Prefs')
        self.save_prefs_button = QPushButton('Save Prefs')

        self.prefs_layout.addWidget(self.welcome_label)
        self.prefs_layout.addWidget(self.load_prefs_button)
        self.prefs_layout.addWidget(self.save_prefs_button)
        self.prefs_tab.setLayout(self.prefs_layout)

        #Settings Tab
        self.settings_layout = QVBoxLayout()
        self.dark_mode_checkbox = QCheckBox('Enable Dark Mode')
        self.discord_checkbox = QCheckBox('Open Discord on Startup')

        self.settings_layout.addWidget(self.dark_mode_checkbox)
        self.settings_layout.addWidget(self.discord_checkbox)
        self.settings_tab.setLayout(self.settings_layout)

        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = OrionTechUI()
    ex.show()
    sys.exit(app.exec_())