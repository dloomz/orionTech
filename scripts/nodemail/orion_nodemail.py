import base64
import sys
import json
import os
import glob
import tempfile
from datetime import datetime
from pathlib import Path
import importlib.util

try:
    from PySide2 import QtWidgets, QtCore, QtGui
except ImportError:
    from PySide6 import QtWidgets, QtCore, QtGui


#software detection
try:
    import nuke
except ImportError:
    nuke = None

try:
    import hou
except ImportError:
    hou = None

#HOST BRIDGE
class DCCSwitcher:
    def __init__(self):
        self.app_name = "standalone"
        if nuke:
            self.app_name = "nuke"
        elif hou:
            self.app_name = "houdini"

    def get_main_window(self):
        if self.app_name == "nuke":
            return QtWidgets.QApplication.activeWindow()
        elif self.app_name == "houdini":
            return hou.qt.mainWindow()
        return None

    def message(self, text):
        if self.app_name == "nuke":
            nuke.message(text)
        elif self.app_name == "houdini":
            hou.ui.displayMessage(text)
        else:
            print(text)

    def get_selection_names(self):
        names = []
        if self.app_name == "nuke":
            try:
                nodes = nuke.selectedNodes()
                names = [n.name() for n in nodes]
            except:
                pass
        elif self.app_name == "houdini":
            try:
                nodes = hou.selectedNodes()
                names = [n.name() for n in nodes]
            except:
                pass
        
        names.sort()
        return names

    def copy_nodes(self):
        if self.app_name == "nuke":
            if not nuke.selectedNodes():
                return None
            
            fd, path = tempfile.mkstemp(suffix=".nk")
            os.close(fd)
            try:
                nuke.nodeCopy(path)
                with open(path, "r") as f:
                    return f.read()
            except Exception as e:
                print(f"Copy Error: {e}")
                return None
            finally:
                if os.path.exists(path):
                    os.remove(path)

        elif self.app_name == "houdini":
            if not hou.selectedNodes():
                return None
            
            fd, path = tempfile.mkstemp(suffix=".cpio")
            os.close(fd)
            try:
                sel = hou.selectedNodes()
                sel[0].parent().saveItemsToFile(sel, path)
                
                with open(path, "rb") as f:
                    binary_content = f.read()
                    return base64.b64encode(binary_content).decode('utf-8')
            except Exception as e:
                print(f"Copy Error: {e}")
                return None
            finally:
                if os.path.exists(path):
                    os.remove(path)
        
        return "TEST_DATA"

    def paste_nodes(self, data):
        if not data:
            return False

        if self.app_name == "nuke":
            fd, path = tempfile.mkstemp(suffix=".nk")
            os.close(fd)
            try:
                with open(path, "w") as f:
                    f.write(data)
                nuke.nodePaste(path)
                return True
            except Exception as e:
                print(f"Paste Error: {e}")
                return False
            finally:
                if os.path.exists(path):
                    os.remove(path)

        elif self.app_name == "houdini":
            try:
                binary_data = base64.b64decode(data)
                fd, path = tempfile.mkstemp(suffix=".cpio")
                os.close(fd)
                with open(path, "wb") as f:
                    f.write(binary_data)
                
                pane = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
                if not pane:
                    self.message("Please click inside a Network View first.")
                    return False
                
                pane.pwd().loadItemsFromFile(path)
                return True
            except Exception as e:
                print(f"Paste Error: {e}")
                return False
            finally:
                if os.path.exists(path):
                    os.remove(path)
        
        return False

BRIDGE = DCCSwitcher()

#MAIL ITEM WIDGET
class MailItem(QtWidgets.QWidget):
    clicked = QtCore.Signal(object) 

    def __init__(self, filename, data, parent=None):
        super().__init__(parent)
        
        self.filename = filename
        self.data = data
        self.sender = data.get("sender", "Unknown")
        self.timestamp = data.get("time", "")
        self.note = data.get("note", "")
        self.node_payload = data.get("copied_node", "")

        self.default_style = """
            QWidget { 
                background-color: #3a3a3a; 
                border-radius: 4px; 
                border: 1px solid #555; 
            }
        """
        self.selected_style = """
            QWidget { 
                background-color: #444; 
                border-radius: 4px; 
                border: 2px solid #4a90e2; 
            }
        """

        self.setStyleSheet(self.default_style)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)

        self.mail_layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.mail_layout)
        self.mail_layout.setContentsMargins(10, 10, 10, 10)

        header_layout = QtWidgets.QHBoxLayout()
        info_layout = QtWidgets.QVBoxLayout()
        info_layout.setSpacing(2)

        self.lbl_from = QtWidgets.QLabel(f"<b>From:</b> {self.sender}")
        self.lbl_from.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.lbl_from.setStyleSheet("border: none; background-color: transparent; color: #ddd;")
        
        info_layout.addWidget(self.lbl_from)

        try:
            dt = datetime.fromisoformat(self.timestamp)
            pretty_time = dt.strftime("%Y-%m-%d %H:%M")
        except:
            pretty_time = self.timestamp

        self.lbl_time = QtWidgets.QLabel(pretty_time)
        self.lbl_time.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.lbl_time.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignTop)
        self.lbl_time.setStyleSheet("color: #aaa; font-size: 10px; border: none; background-color: transparent;")

        header_layout.addLayout(info_layout)
        header_layout.addStretch() 
        header_layout.addWidget(self.lbl_time)

        self.line = QtWidgets.QFrame()
        self.line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Shadow.Plain)
        self.line.setStyleSheet("color: #555;")
        self.line.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self.lbl_note = QtWidgets.QLabel(self.note)
        self.lbl_note.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.lbl_note.setWordWrap(True)
        self.lbl_note.setContentsMargins(5, 10, 5, 10)
        self.lbl_note.setStyleSheet("border: none; background-color: transparent; color: #ddd;")

        self.mail_layout.addLayout(header_layout)
        self.mail_layout.addWidget(self.line)
        self.mail_layout.addWidget(self.lbl_note)
        
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.clicked.emit(self)
        super().mousePressEvent(event)

    def set_selected(self, selected):
        if selected:
            self.setStyleSheet(self.selected_style)
        else:
            self.setStyleSheet(self.default_style)


class NodeMailUI(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        if not parent:
            parent = BRIDGE.get_main_window()
        super().__init__(parent)

        self.pipeline_root = os.environ.get("ORI_PIPELINE_PATH")
        self.orion = self.load_orion_utils()
        
        if not self.orion:
            return

        root_path = self.orion.get_root_dir()
        subdir = "nuke" if BRIDGE.app_name == "nuke" else "houdini"
        if BRIDGE.app_name == "standalone": subdir = "common"
            
        self.nodemail_path = os.path.join(root_path, "60_config", "nodemail", subdir)

        if not os.path.exists(self.nodemail_path):
            try:
                os.makedirs(self.nodemail_path)
            except:
                pass

        usernames = self.orion.get_usernames()
        self.user = os.getenv("USERNAME", "user")

        self.setObjectName("NodeMailWindow")
        self.setWindowTitle(f"NodeMail ({subdir}) - {self.user}")
        self.setMinimumWidth(800)
        self.setMinimumHeight(500)

        self.current_selected_item = None
        
        self.build_ui(usernames)
        self.update_selection_display()
        self.refresh_inbox()

    def load_orion_utils(self):
        if not self.pipeline_root:
            print("ORI_PIPELINE_PATH env var not set.")
            return None

        utils_path = os.path.join(str(self.pipeline_root), "core", "orionUtils.py")
        if not os.path.exists(utils_path):
            print(f"orionUtils not found at {utils_path}")
            return None

        try:
            spec = importlib.util.spec_from_file_location("orion_core_utils_direct", utils_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.OrionUtils()
        except Exception as e:
            print(f"Failed to load OrionUtils: {e}")
            return None

    def build_ui(self, usernames):
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QtWidgets.QHBoxLayout(central_widget)
        
        #LEFT
        left_layout = QtWidgets.QVBoxLayout()
        lbl_inbox = QtWidgets.QLabel("<b>Inbox</b>")
        btn_refresh = QtWidgets.QPushButton("Refresh Inbox")
        btn_refresh.clicked.connect(self.refresh_inbox)
        
        self.scroll_area = QtWidgets.QScrollArea()  
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        
        self.inbox_container = QtWidgets.QWidget()                 
        self.inbox_vbox = QtWidgets.QVBoxLayout(self.inbox_container)
        self.inbox_vbox.setSpacing(5)
        self.inbox_vbox.setContentsMargins(5,5,5,5)
        self.inbox_vbox.addStretch() 
        self.scroll_area.setWidget(self.inbox_container)

        self.btn_paste = QtWidgets.QPushButton("Paste to Graph")
        self.btn_paste.setMinimumHeight(40)
        self.btn_paste.setStyleSheet("background-color: #4a90e2; color: white; font-weight: bold;")
        self.btn_paste.clicked.connect(self.paste_mail)
        self.btn_paste.setEnabled(False)

        self.btn_delete = QtWidgets.QPushButton("Delete Selected")
        self.btn_delete.setMinimumHeight(40)
        self.btn_delete.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold;")
        self.btn_delete.clicked.connect(self.delete_mail)
        self.btn_delete.setEnabled(False)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addWidget(self.btn_paste)
        btn_row.addWidget(self.btn_delete)

        left_layout.addWidget(lbl_inbox)
        left_layout.addWidget(btn_refresh)
        left_layout.addWidget(self.scroll_area)
        left_layout.addLayout(btn_row)

        #RIGHT
        right_layout = QtWidgets.QVBoxLayout()
        lbl_compose = QtWidgets.QLabel("<b>Compose</b>")
        btn_get_sel = QtWidgets.QPushButton("Get Selected Nodes")
        btn_get_sel.clicked.connect(self.update_selection_display)

        self.txt_snapshot = QtWidgets.QPlainTextEdit()
        self.txt_snapshot.setPlaceholderText("No Nodes Selected")
        self.txt_snapshot.setReadOnly(True)
        self.txt_snapshot.setStyleSheet("background-color: #2b2b2b; color: #888; font-family: monospace;")

        form_layout = QtWidgets.QFormLayout()
        self.combo_recipient = QtWidgets.QComboBox()
        if usernames:
            self.combo_recipient.addItems(usernames)
        else:
            self.combo_recipient.addItem("Unknown")

        self.input_note = QtWidgets.QLineEdit()
        self.input_note.setPlaceholderText("Message...")

        form_layout.addRow("Recipient:", self.combo_recipient)
        form_layout.addRow("Note:", self.input_note)

        btn_send = QtWidgets.QPushButton("Send Mail")
        btn_send.setMinimumHeight(40)
        btn_send.setStyleSheet("background-color: #e67e22; color: white; font-weight: bold;")
        btn_send.clicked.connect(self.send_mail)

        right_layout.addWidget(lbl_compose)
        right_layout.addWidget(btn_get_sel)
        right_layout.addWidget(self.txt_snapshot)
        right_layout.addLayout(form_layout)
        right_layout.addWidget(btn_send)
        right_layout.addStretch()

        main_layout.addLayout(left_layout, 3)
        main_layout.addLayout(right_layout, 2)

    def refresh_inbox(self):
        # FIX START: Reset selection to avoid "stale pointer" crash
        self.current_selected_item = None
        self.btn_paste.setEnabled(False)
        self.btn_delete.setEnabled(False)
        
        self.inbox_container.setVisible(False)
        
        while self.inbox_vbox.count():
            item = self.inbox_vbox.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # FIX START: Force Nuke to process the deletion immediately
        QtWidgets.QApplication.processEvents()
        
        pattern = os.path.join(self.nodemail_path, "*.json")
        files = glob.glob(pattern)
        files.sort(key=os.path.getmtime, reverse=True)

        found = 0
        for f in files:
            try:
                with open(f, 'r') as jf:
                    data = json.load(jf)
                
                if data.get("recipient") == self.user:
                    item = MailItem(f, data, parent=self.inbox_container)
                    item.clicked.connect(self.on_item_clicked)
                    self.inbox_vbox.addWidget(item)
                    found += 1
            except Exception as e:
                print(f"Read Error {f}: {e}")
        
        self.inbox_vbox.addStretch()
        self.inbox_container.setVisible(True)

    def on_item_clicked(self, item):
        # FIX: Check if current_selected_item still exists and is valid
        if self.current_selected_item:
            try:
                self.current_selected_item.set_selected(False)
            except RuntimeError:
                # If the item was deleted but variable wasn't cleared, ignore it
                pass
        
        self.current_selected_item = item
        item.set_selected(True)
        
        self.btn_paste.setEnabled(True)
        self.btn_delete.setEnabled(True)

    def delete_mail(self):
        if not self.current_selected_item:
            return
        
        try:
            os.remove(self.current_selected_item.filename)
            self.inbox_vbox.removeWidget(self.current_selected_item)
            self.current_selected_item.deleteLater()
            
            # FIX: Explicitly clear the selection variable
            self.current_selected_item = None
            self.btn_paste.setEnabled(False)
            self.btn_delete.setEnabled(False)
        except Exception as e:
            print(f"Delete Error: {e}")

    def paste_mail(self):
        if not self.current_selected_item:
            return
        
        data = self.current_selected_item.node_payload
        success = BRIDGE.paste_nodes(data)
        
        if success:
            BRIDGE.message("Nodes pasted successfully!")
        else:
            BRIDGE.message("Failed to paste nodes.")

    def update_selection_display(self):
        names = BRIDGE.get_selection_names()
        if not names:
            self.txt_snapshot.setPlainText("No nodes selected.")
            return

        txt = f"Selected ({len(names)}):\n" + "-"*15 + "\n"
        txt += "\n".join(names)
        self.txt_snapshot.setPlainText(txt)

    def send_mail(self):
        recip = self.combo_recipient.currentText()
        note = self.input_note.text()
        node_data = BRIDGE.copy_nodes()
        
        if not node_data:
            BRIDGE.message("Select nodes first!")
            return

        ts = datetime.now()
        packet = {
            "sender": self.user,
            "recipient": recip,
            "time": ts.isoformat(),
            "note": note,
            "copied_node": node_data
        }

        fname = f"{recip}_{self.user}_{ts.strftime('%Y%m%d_%H%M%S')}.json"
        fpath = os.path.join(self.nodemail_path, fname)

        try:
            with open(fpath, "w") as f:
                json.dump(packet, f, indent=4)
            
            BRIDGE.message(f"Sent to {recip}")
            self.input_note.clear()
        except Exception as e:
            BRIDGE.message(f"Save failed: {e}")

#EXECUTION
global nodemail_window

def start():
    app = QtWidgets.QApplication.instance()
    if not app:
        app = QtWidgets.QApplication(sys.argv)
    
    global nodemail_window
    try:
        if nodemail_window:
            nodemail_window.close()
    except:
        pass

    nodemail_window = NodeMailUI()
    nodemail_window.show()

if __name__ == "__main__":
    start()