import sys
import os

from utils.orionUtils import OrionUtils
from utils.systemUtils import SystemUtils
from utils.prefsUtils import PrefsUtils
from ui.orionTechUI import OrionTechUI

orion_utils = OrionUtils()

libs_path = orion_utils.get_libs_path()
if libs_path not in sys.path:
    sys.path.insert(0, libs_path)

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

system_utils = SystemUtils(orion_utils) 
prefs_utils = PrefsUtils(orion_utils)   

if __name__ == '__main__':
    
    system_utils.env_setup()
    
    app = QApplication(sys.argv)
    
    # 5. Pass all the utilities into your UI class
    ex = OrionTechUI(orion_utils, system_utils, prefs_utils)
    
    ex.show()
    sys.exit(app.exec_())