import sys
import json
import os
import glob
import tempfile
import base64
from datetime import datetime
from pathlib import Path

#try to import pyside based on houdini version
try:
    from PySide2 import QtWidgets, QtCore, QtGui
except ImportError:
    from PySide6 import QtWidgets, QtCore, QtGui

#import houdini module
try:
    import hou
except ImportError:
    hou = None

#MAIL ITEM WIDGET
class MailItem(QtWidgets.QWidget):
    clicked = QtCore.Signal(object) 

    def __init__(self, filename, data):
        super(MailItem, self).__init__()
        
        self.filename = filename
        self.data = data
        
        #extract data for UI
        self.sender = data.get("sender", "Unknown")
        self.recipient = data.get("recipient", "Unknown")
        self.timestamp = data.get("time", "")
        self.note = data.get("note", "")
        self.node_payload = data.get("copied_node", "")

        #styles
        self.default_style = """
            QWidget { 
                background-color: #3a3a3a; 
                border-radius: 4px; 
                border: 1px solid #555; 
            }
            QLabel { color: #ddd; border: none; background-color: transparent; }
        """
        self.selected_style = """
            QWidget { 
                background-color: #444; 
                border-radius: 4px; 
                border: 2px solid #4a90e2; 
            }
            QLabel { color: #fff; border: none; background-color: transparent; }
        """

        self.setStyleSheet(self.default_style)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)

        self.mail_layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.mail_layout)
        self.mail_layout.setContentsMargins(10, 10, 10, 10)

        #header section
        header_widget = QtWidgets.QWidget()
        header_widget.setStyleSheet("border: none; background-color: transparent;")
        header_layout = QtWidgets.QHBoxLayout()
        header_widget.setLayout(header_layout)
        header_layout.setContentsMargins(0, 0, 0, 0)

        info_container = QtWidgets.QWidget()
        info_container.setStyleSheet("border: none; background-color: transparent;")
        info_layout = QtWidgets.QVBoxLayout()
        info_container.setLayout(info_layout)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)

        self.lbl_from = QtWidgets.QLabel("<b>From:</b> " + self.sender)
        info_layout.addWidget(self.lbl_from)

        #format time better 
        try:
            dt = datetime.fromisoformat(self.timestamp)
            pretty_time = dt.strftime("%Y-%m-%d %H:%M")
        except:
            pretty_time = self.timestamp

        self.lbl_time = QtWidgets.QLabel(pretty_time)
        self.lbl_time.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignTop)
        self.lbl_time.setStyleSheet("color: #aaa; font-size: 10px; border: none; background-color: transparent;")

        header_layout.addWidget(info_container)
        header_layout.addStretch() 
        header_layout.addWidget(self.lbl_time)

        #separator line
        self.line = QtWidgets.QFrame()
        self.line.setFrameShape(QtWidgets.QFrame.HLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Plain)
        self.line.setStyleSheet("color: #555;")

        self.lbl_note = QtWidgets.QLabel(self.note)
        self.lbl_note.setWordWrap(True)
        self.lbl_note.setContentsMargins(5, 10, 5, 10)
        self.lbl_note.setStyleSheet("border: none; background-color: transparent;")

        self.mail_layout.addWidget(header_widget)
        self.mail_layout.addWidget(self.line)
        self.mail_layout.addWidget(self.lbl_note)
        
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit(self)
        super(MailItem, self).mousePressEvent(event)

    def set_selected(self, selected):
        if selected:
            self.setStyleSheet(self.selected_style)
        else:
            self.setStyleSheet(self.default_style)

#MAIN WINDOW CLASS
class NodeMailUI(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super(NodeMailUI, self).__init__(parent)

        #setup paths and pipeline vars
        self.pipeline_root = os.environ.get("ORI_PIPELINE_PATH")
        
        #fallback if env var not set
        if not self.pipeline_root:
            self.pipeline_root = tempfile.gettempdir()
            
        utils_path = os.path.join(str(self.pipeline_root), "core", "orionUtils.py")
        
        #pipeline tool loading logic
        self.orion = None
        self.user = os.getenv("USERNAME", os.getenv("USER", "unknown_user"))
        usernames = [self.user, "supervisor", "lead"] 
        
        if os.path.exists(utils_path):
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location("orion_core_utils_direct", utils_path)
                orion_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(orion_module)
                self.orion = orion_module.OrionUtils()
                print("OrionUtils loaded successfully.")
                
                #update users and paths from orion if available
                usernames = self.orion.get_usernames()
                root_path = self.orion.get_root_dir()
                self.nodemail_path = os.path.join(root_path, "60_config", "nodemail", "houdini")
            except Exception as e:
                print("Error loading OrionUtils: " + str(e))
                self.nodemail_path = os.path.join(tempfile.gettempdir(), "nodemail_houdini")
        else:
            #fallback path for standalone testing
            self.nodemail_path = os.path.join(tempfile.gettempdir(), "nodemail_houdini")

        #ensure directory exists
        if not os.path.exists(self.nodemail_path):
            try:
                os.makedirs(self.nodemail_path)
            except:
                pass

        self.setObjectName("NodeMailWindow")
        self.setWindowTitle("NodeMail Houdini - Logged in as: " + self.user)
        self.setMinimumWidth(800)
        self.setMinimumHeight(500)

        self.current_selected_item = None
        
        self.build_ui(usernames)
        
        self.update_selection_display()
        self.refresh_inbox()

    def build_ui(self, usernames):
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QtWidgets.QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        self.tab_widget = QtWidgets.QTabWidget()
        
        #TAB 1 INCOMING
        update_tab = QtWidgets.QWidget()
        update_layout = QtWidgets.QVBoxLayout(update_tab)
        self.tab_widget.addTab(update_tab, "Inbox")
        
        #refresh inbox button
        btn_refresh_inbox = QtWidgets.QPushButton("Refresh Inbox")
        btn_refresh_inbox.clicked.connect(self.refresh_inbox)
        
        self.scroll_window = QtWidgets.QScrollArea()  
        self.scroll_window.setWidgetResizable(True)
        self.scroll_window.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.scroll_window.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        
        #buttons
        self.paste_button = QtWidgets.QPushButton("Paste Nodes to Graph")
        self.paste_button.setMinimumHeight(40)
        self.paste_button.setStyleSheet("background-color: #4a90e2; color: white; font-weight: bold;")
        self.paste_button.clicked.connect(self.paste_mail)
        self.paste_button.setEnabled(False)

        self.delete_button = QtWidgets.QPushButton("Delete Selected")
        self.delete_button.clicked.connect(self.delete_selected_mail)
        self.delete_button.setEnabled(False)
        
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(self.paste_button)
        button_layout.addWidget(self.delete_button)
        
        #container for mail items
        self.inbox_widget = QtWidgets.QWidget()                 
        self.inbox_vbox = QtWidgets.QVBoxLayout()               
        self.inbox_widget.setLayout(self.inbox_vbox)
        self.inbox_vbox.addStretch() 

        self.scroll_window.setWidget(self.inbox_widget)
        
        update_layout.addWidget(btn_refresh_inbox)
        update_layout.addWidget(self.scroll_window)
        update_layout.addLayout(button_layout)
        
        #RIGHT COLUMN (OUTGOING) 
        right_layout = QtWidgets.QVBoxLayout()
        
        #refresh selection button
        refresh_btn = QtWidgets.QPushButton("Get Selected Nodes")
        refresh_btn.setToolTip("Click to update the list based on current Houdini selection")
        refresh_btn.clicked.connect(self.update_selection_display)
        
        #display box
        self.snapshot_label = QtWidgets.QPlainTextEdit()
        self.snapshot_label.setPlaceholderText("No Nodes Selected")
        self.snapshot_label.setReadOnly(True)
        self.snapshot_label.setStyleSheet("background-color: #2b2b2b; border: 1px solid #555; color: #888; font-family: monospace;")
        
        #inputs
        recipient_row = QtWidgets.QHBoxLayout()
        recipient_label = QtWidgets.QLabel("Recipient:")
        self.recipient_dropdown = QtWidgets.QComboBox()
        
        #add usernames to dropdown
        if usernames:
            for u in usernames:
                self.recipient_dropdown.addItem(u)
        else:
            self.recipient_dropdown.addItem("Unknown")
        
        recipient_row.addWidget(recipient_label)
        recipient_row.addWidget(self.recipient_dropdown, 1)

        note_row = QtWidgets.QHBoxLayout()
        note_label = QtWidgets.QLabel("Note:")
        self.note_edit = QtWidgets.QLineEdit()
        self.note_edit.setPlaceholderText("Message...")
        note_row.addWidget(note_label)
        note_row.addWidget(self.note_edit, 1)

        send_button = QtWidgets.QPushButton("Send Mail")
        send_button.setMinimumHeight(40)
        send_button.setStyleSheet("background-color: #e67e22; color: white; font-weight: bold;")
        send_button.clicked.connect(self.send_mail)
        
        #add to right layout
        right_layout.addWidget(QtWidgets.QLabel("<b>Compose</b>"))
        right_layout.addWidget(refresh_btn)
        right_layout.addWidget(self.snapshot_label)
        right_layout.addLayout(recipient_row)
        right_layout.addLayout(note_row)
        right_layout.addWidget(send_button)
        right_layout.addStretch()
        
        #add to main layout
        main_layout.addWidget(self.tab_widget, 3)
        main_layout.addLayout(right_layout, 2)

    #INBOX LOGIC
    def refresh_inbox(self):
        #clear current list 
        while self.inbox_vbox.count() > 1:
            item = self.inbox_vbox.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        #find files
        search_pattern = os.path.join(self.nodemail_path, "*.json")
        files = glob.glob(search_pattern)
        
        #sort by time
        files.sort(key=os.path.getmtime, reverse=True)

        found_count = 0
        for f in files:
            try:
                with open(f, 'r') as json_file:
                    data = json.load(json_file)
                
                #check if this mail is for the current user
                recipient = data.get("recipient", "")
                
                if recipient == self.user:
                    mail_item = MailItem(filename=f, data=data)
                    mail_item.clicked.connect(self.handle_mail_click)
                    #insert at top (index 0)
                    self.inbox_vbox.insertWidget(found_count, mail_item)
                    found_count += 1
            except Exception as e:
                print("Error reading mail file " + f + ": " + str(e))

    def handle_mail_click(self, clicked_item):
        #deselect old
        if self.current_selected_item:
            self.current_selected_item.set_selected(False)
        
        #select new
        self.current_selected_item = clicked_item
        clicked_item.set_selected(True)
        
        #enable buttons
        self.paste_button.setEnabled(True)
        self.delete_button.setEnabled(True)

    def delete_selected_mail(self):
        if self.current_selected_item:
            #delete file
            try:
                os.remove(self.current_selected_item.filename)
            except OSError as e:
                print("Could not delete file: " + str(e))
            
            #remove from ui
            self.inbox_vbox.removeWidget(self.current_selected_item)
            self.current_selected_item.deleteLater()
            self.current_selected_item = None
            
            #disable buttons
            self.paste_button.setEnabled(False)
            self.delete_button.setEnabled(False)

    def paste_mail(self):
        #paste mail nodes into houdini
        if not self.current_selected_item:
            return
            
        b64_data = self.current_selected_item.node_payload
        if not b64_data:
            if hou: hou.ui.displayMessage("Error: Email contains no node data.")
            return

        if hou:
            try:
                #convert b64 string back to binary
                binary_data = base64.b64decode(b64_data)

                #write binary to temp .cpio file
                fd, temp_cpio_path = tempfile.mkstemp(suffix=".cpio")
                os.close(fd)
                
                with open(temp_cpio_path, "wb") as f:
                    f.write(binary_data)
                
                #find current network editor context
                pane = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
                if not pane:
                    hou.ui.displayMessage("Please open a Network View to paste.")
                    return
                
                current_context = pane.pwd()
                
                #load items
                current_context.loadItemsFromFile(temp_cpio_path)
                
                #cleanup
                os.remove(temp_cpio_path)
                print("Nodes pasted successfully.")
                
            except Exception as e:
                hou.ui.displayMessage("Error pasting nodes: " + str(e))
        else:
            print("Houdini not detected. Cannot paste nodes.")

    #OUTGOING
    def update_selection_display(self):
        #queries houdini for selected nodes
        if hou:
            try:
                selected_nodes = hou.selectedNodes()
                if not selected_nodes:
                    self.snapshot_label.setPlainText("No nodes currently selected in Houdini.")
                    return

                #get names
                names = [n.name() for n in selected_nodes]
                names.sort()
                
                #format list
                display_text = "Selected (" + str(len(names)) + " Nodes):\n----------------\n"
                display_text += "\n".join(names)
                
                self.snapshot_label.setPlainText(display_text)
                
            except Exception as e:
                self.snapshot_label.setPlainText("Error reading selection: " + str(e))
        else:
            self.snapshot_label.setPlainText("Houdini module not found")

    def send_mail(self):
        recipient = self.recipient_dropdown.currentText()
        note = self.note_edit.text()
        
        if hou and not hou.selectedNodes():
            hou.ui.displayMessage("Please select nodes first.")
            return

        b64_node_data = ""
        
        if hou:
            #create temp cpio file
            fd, temp_cpio_path = tempfile.mkstemp(suffix=".cpio")
            os.close(fd) 

            try:
                sel = hou.selectedNodes()
                #save items to binary cpio
                sel[0].parent().saveItemsToFile(sel, temp_cpio_path)

                #read binary and convert to b64 string
                with open(temp_cpio_path, "rb") as f:
                    binary_content = f.read()
                    b64_node_data = base64.b64encode(binary_content).decode('utf-8')

            except Exception as e:
                print("Error copying nodes: " + str(e))
                return
            finally:
                if os.path.exists(temp_cpio_path):
                    os.remove(temp_cpio_path)
        else:
            b64_node_data = "dummy_data_for_testing"

        #generate unique filename
        timestamp = datetime.now()
        time_str_iso = timestamp.isoformat()
        time_str_file = timestamp.strftime("%Y%m%d_%H%M%S")
        
        filename = "{}_{}_{}.json".format(recipient, self.user, time_str_file)
        save_path = os.path.join(self.nodemail_path, filename)

        mail_packet = {
            "sender": self.user,
            "recipient": recipient,
            "time": time_str_iso,
            "note": note,
            "copied_node": b64_node_data
        }

        try:
            with open(save_path, "w") as f:
                json.dump(mail_packet, f, indent=4)
            
            print("Successfully sent mail to: " + save_path)
            if hou: hou.ui.displayMessage("Sent to " + recipient + "!")
            self.note_edit.clear()
            
        except Exception as e:
            if hou: hou.ui.displayMessage("Could not write file: " + str(e))
            print(e)

#MAIN EXECUTION
def start():
    app = QtWidgets.QApplication.instance()
    if not app:
        app = QtWidgets.QApplication(sys.argv)
        app.setStyle("Fusion")
    
    #glob win var
    global custom_nodemail_window_hou

    try:
        if custom_nodemail_window_hou:
            custom_nodemail_window_hou.close()
    except (NameError, RuntimeError):
        pass

    #show win
    custom_nodemail_window_hou = NodeMailUI()
    custom_nodemail_window_hou.show()

    #standalone and nuke open
    if not hou: 
        sys.exit(app.exec())
    # #setup app
    # if QtWidgets.QApplication.instance():
    #     app = QtWidgets.QApplication.instance()
    # else:
    #     app = QtWidgets.QApplication(sys.argv)

    # #keep reference so gc doesnt kill it
    # global custom_nodemail_window_hou

    # try:
    #     if custom_nodemail_window_hou:
    #         custom_nodemail_window_hou.close()
    #         custom_nodemail_window_hou.deleteLater()
    # except:
    #     pass

    # #parent to houdini main window
    # parent_win = None
    # if hou:
    #     parent_win = hou.ui.mainQtWindow()

    # custom_nodemail_window_hou = NodeMailUI(parent_win)
    # custom_nodemail_window_hou.show()
    
if __name__ == "__main__":
    start()
#TO RUN IN HOUDINI USE:
# import sys
# path = r"P:\all_work\studentGroups\ORION_CORPORATION\00_pipeline\orionTech\scripts\nodemail"
# if path not in sys.path:
#     sys.path.append(path)

# import orion_nodemail_hou
# orion_nodemail_hou.start() 