import sys
import os

#folder containing this script (the root of the project)
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

#add this root to python path so can import 
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

#IMPORTS
from core.orionUtils import OrionUtils
from core.systemUtils import SystemUtils
from core.prefsUtils import PrefsUtils
from ui.orionTechUI import OrionTechUI

if __name__ == '__main__':
    #initialize core logic
    orion_utils = OrionUtils()
    prefs_utils = PrefsUtils(orion_utils)
    system_utils = SystemUtils(orion_utils, prefs_utils)

    if orion_utils.libs_path not in sys.path:
            sys.path.insert(0, orion_utils.libs_path)

    from PyQt5.QtWidgets import QApplication

    #run env
    # system_utils.env_setup()

    #start UI
    app = QApplication(sys.argv)
    window = OrionTechUI(orion_utils, system_utils, prefs_utils)
    window.show()
    
    sys.exit(app.exec_())