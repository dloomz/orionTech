import sys
from PyQt5.QtWidgets import QApplication
from ui.orionTechUI import OrionTechUI
from utils.systemUtils import SystemUtils

system_utils = SystemUtils()

if __name__ == '__main__':
    
    system_utils.change_wallpaper("graphics\orionBack_001.png")
    
    app = QApplication(sys.argv)
    ex = OrionTechUI()
    ex.show()
    sys.exit(app.exec_())