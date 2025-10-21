import sys
from PyQt5.QtWidgets import QApplication
from ui.orionTechUI import OrionTechUI

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = OrionTechUI()
    ex.show()
    sys.exit(app.exec_())