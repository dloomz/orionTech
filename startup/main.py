import sys
import os

from ui.orionTechUI import OrionTechUI
from utils.systemUtils import SystemUtils
from utils.orionUtils import OrionUtils

orion_utils = OrionUtils()
system_utils = SystemUtils()

libs_path = orion_utils.get_libs_path()

if libs_path not in sys.path:
    sys.path.insert(0, libs_path)

from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QCheckBox, QTabWidget, QMessageBox, QComboBox
from PyQt5.QtCore import Qt

if __name__ == '__main__':
    
    # print(libs_path)

    system_utils.env_setup()
    
    app = QApplication(sys.argv)
    ex = OrionTechUI()
    ex.show()
    sys.exit(app.exec_())

