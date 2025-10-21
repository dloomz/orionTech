import sys
import os
from PyQt5.QtWidgets import QApplication
from ui.orionTechUI import OrionTechUI
from utils.systemUtils import SystemUtils
from utils.orionUtils import OrionUtils

system_utils = SystemUtils()
orion_utils = OrionUtils()

x = __file__

split = x.split("\\")
path_list = split[:-2]

sep = "\\"
project_path = sep.join(path_list)

wallpaper_path = os.path.join(project_path, "graphics\orionBack_001.png")

if __name__ == '__main__':
    
    system_utils.change_wallpaper(wallpaper_path)
    print(project_path)
    
    app = QApplication(sys.argv)
    ex = OrionTechUI()
    ex.show()
    sys.exit(app.exec_())