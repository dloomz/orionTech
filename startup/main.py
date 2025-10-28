import sys
import os

startup_dir = os.path.dirname(os.path.abspath(__file__))
main_dir = os.path.dirname(os.path.abspath(startup_dir))
libs_path = os.path.join(startup_dir, 'libs')

if libs_path not in sys.path:
    sys.path.insert(0, libs_path)

from PyQt5.QtWidgets import QApplication

from ui.orionTechUI import OrionTechUI
from utils.systemUtils import SystemUtils
from utils.orionUtils import OrionUtils

system_utils = SystemUtils()
orion_utils = OrionUtils()

wallpaper_path = os.path.join(main_dir, "graphics\orionBack_001.png")

if __name__ == '__main__':
    
    system_utils.change_wallpaper(wallpaper_path)
    
    app = QApplication(sys.argv)
    ex = OrionTechUI()
    ex.show()
    sys.exit(app.exec_())