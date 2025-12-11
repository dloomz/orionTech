import sys
import json
import os
import glob
import tempfile
from datetime import datetime
from pathlib import Path

from PySide6 import QtWidgets, QtCore, QtGui

try:
    import nuke
except ImportError:
    nuke = None

#MAIL ITEM WIDGET
class MailItem(QtWidgets.QWidget):
    clicked = QtCore.Signal(object) 

    def __init__(self, filename, data):
        super().__init__()
        
        self.filename = filename
        self.data = data
        
        #extract data for UI
        self.sender = data.get("sender", "Unknown")
        self.recipient = data.get("recipient", "Unknown")
        self.timestamp = data.get("time", "")
        self.note = data.get("note", "")
        self.node_payload = data.get("copied_node", "") #raw nuke data

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
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)

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

        self.lbl_from = QtWidgets.QLabel(f"<b>From:</b> {self.sender}")
        info_layout.addWidget(self.lbl_from)

        #format time better 
        try:
            dt = datetime.fromisoformat(self.timestamp)
            pretty_time = dt.strftime("%Y-%m-%d %H:%M")
        except:
            pretty_time = self.timestamp

        self.lbl_time = QtWidgets.QLabel(pretty_time)
        self.lbl_time.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignTop)
        self.lbl_time.setStyleSheet("color: #aaa; font-size: 10px; border: none; background-color: transparent;")

        header_layout.addWidget(info_container)
        header_layout.addStretch() 
        header_layout.addWidget(self.lbl_time)

        #separator line
        self.line = QtWidgets.QFrame()
        self.line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Shadow.Plain)
        self.line.setStyleSheet("color: #555;")

        self.lbl_note = QtWidgets.QLabel(self.note)
        self.lbl_note.setWordWrap(True)
        self.lbl_note.setContentsMargins(5, 10, 5, 10)
        self.lbl_note.setStyleSheet("border: none; background-color: transparent;")

        self.mail_layout.addWidget(header_widget)
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

#MAIN WINDOW CLASS
class NodeMailUI(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        #PATH SETUP AND IMPORT FIX 
        # current_script_dir = Path(__file__).resolve().parent
        os.environ.get("ORI_PIPELINE_PATH")
        self.pipeline_root = os.environ.get("ORI_PIPELINE_PATH")
        # self.pipeline_root = current_script_dir.parent.parent
        
        #exact path to orionUtils.py
        utils_path = os.path.join(str(self.pipeline_root), "core", "orionUtils.py")

        if not os.path.exists(utils_path):
            print("---------------------------------------------------")
            print(f"CRITICAL ERROR: orionUtils.py not found.")
            print(f"Expected location: {utils_path}")
            print("---------------------------------------------------")
            return

        try:
            #DIRECT LOAD: Bypass 'sys.path', load the file directly
            import importlib.util
            
            #unique module name 
            spec = importlib.util.spec_from_file_location("orion_core_utils_direct", utils_path)
            orion_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(orion_module)
            
            #init class
            self.orion = orion_module.OrionUtils()
            print(f"OrionUtils loaded successfully from: {utils_path}")

        except Exception as e:
            print("---------------------------------------------------")
            print(f"CRITICAL ERROR: Failed to load OrionUtils.")
            print(f"Error details: {e}")
            import traceback
            traceback.print_exc()
            print("---------------------------------------------------")
            return
        
        root_path = self.orion.get_root_dir()
        self.nodemail_path = os.path.join(root_path, "60_config", "nodemail")
        
        if not os.path.exists(self.nodemail_path):
            try:
                os.makedirs(self.nodemail_path)
            except:
                pass

        usernames = self.orion.get_usernames()
        self.user = os.getenv("USERNAME")

        self.setObjectName("NodeMailWindow")
        self.setWindowTitle(f"NodeMail - Logged in as: {self.user}")
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
        self.scroll_window.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.scroll_window.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        #buttons
        self.paste_button = QtWidgets.QPushButton("Paste Nodes to Graph")
        self.paste_button.setMinimumHeight(40)
        self.paste_button.setStyleSheet("background-color: #4a90e2; color: white; font-weight: bold;")
        self.paste_button.clicked.connect(self.paste_mail)
        self.paste_button.setEnabled(False) #disable until item selected

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
        self.inbox_vbox.addStretch() #push items to top

        self.scroll_window.setWidget(self.inbox_widget)
        
        update_layout.addWidget(btn_refresh_inbox)
        update_layout.addWidget(self.scroll_window)
        update_layout.addLayout(button_layout)
        
        #RIGHT COLUMN (OUTGOING) 
        right_layout = QtWidgets.QVBoxLayout()
        
        #refresh selection button
        refresh_btn = QtWidgets.QPushButton("Get Selected Nodes")
        refresh_btn.setToolTip("Click to update the list based on current Nuke selection")
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
        """Scans the nodemail directory for JSON files matching the current user."""
        
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
                print(f"Error reading mail file {f}: {e}")

        if found_count == 0:
            #TODO: no mail msg (empty mailbox)
            pass

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
                print(f"Could not delete file: {e}")
            
            #remove from ui
            self.inbox_vbox.removeWidget(self.current_selected_item)
            self.current_selected_item.deleteLater()
            self.current_selected_item = None
            
            #disable buttons
            self.paste_button.setEnabled(False)
            self.delete_button.setEnabled(False)

    def paste_mail(self):
        #paste mail nodes into nuke
        if not self.current_selected_item:
            return
            
        raw_data = self.current_selected_item.node_payload
        if not raw_data:
            if nuke: nuke.message("Error: Email contains no node data.")
            return

        if nuke:
            try:
                #write raw data to temp .nk file
                fd, temp_nk_path = tempfile.mkstemp(suffix=".nk")
                os.close(fd)
                
                with open(temp_nk_path, "w") as f:
                    f.write(raw_data)
                
                #paste into nuke
                nuke.nodePaste(temp_nk_path)
                
                #cleanup
                os.remove(temp_nk_path)
                print("Nodes pasted successfully.")
                
            except Exception as e:
                nuke.message(f"Error pasting nodes: {e}")
        else:
            print("Nuke not detected. Cannot paste nodes.")

    #OUTGOING
    def update_selection_display(self):
        """Queries Nuke for selected nodes."""
        if nuke:
            try:
                selected_nodes = nuke.selectedNodes()
                if not selected_nodes:
                    self.snapshot_label.setPlainText("No nodes currently selected in Nuke.")
                    return

                #get names
                names = [n.name() for n in selected_nodes]
                names.sort()
                
                #format list
                display_text = f"Selected ({len(names)} Nodes):\n----------------\n"
                display_text += "\n".join(names)
                
                self.snapshot_label.setPlainText(display_text)
                
            except Exception as e:
                self.snapshot_label.setPlainText(f"Error reading selection: {e}")
        else:
            self.snapshot_label.setPlainText("Nuke module not found (Running standalone?)")

    def send_mail(self):
        recipient = self.recipient_dropdown.currentText()
        note = self.note_edit.text()
        
        if nuke and not nuke.selectedNodes():
            nuke.message("Please select nodes first.")
            return

        raw_node_data = ""
        
        if nuke:
            #create temp file to store copied nodes
            fd, temp_nk_path = tempfile.mkstemp(suffix=".nk")
            os.close(fd) 

            try:
                nuke.nodeCopy(temp_nk_path) 
                with open(temp_nk_path, "r") as f:
                    raw_node_data = f.read() 
            except Exception as e:
                print(f"Error copying nodes: {e}")
                return
            finally:
                if os.path.exists(temp_nk_path):
                    os.remove(temp_nk_path)
        else:
            raw_node_data = "# Dummy data for standalone testing"

        #generate unique filename using timestamp to prevent overwrite
        timestamp = datetime.now()
        time_str_iso = timestamp.isoformat()
        time_str_file = timestamp.strftime("%Y%m%d_%H%M%S")
        
        filename = f"{recipient}_{self.user}_{time_str_file}.json"
        save_path = os.path.join(self.nodemail_path, filename)

        mail_packet = {
            "sender": self.user,
            "recipient": recipient,
            "time": time_str_iso,
            "note": note,
            "copied_node": raw_node_data
        }

        try:
            with open(save_path, "w") as f:
                json.dump(mail_packet, f, indent=4)
            
            print(f"Successfully sent mail to: {save_path}")
            if nuke: nuke.message(f"Sent to {recipient}!")
            self.note_edit.clear()
            
        except Exception as e:
            if nuke: nuke.message(f"Could not write file: {e}")
            print(e)

#MAIN EXECUTION
app = QtWidgets.QApplication.instance()

def start():
    """Starts the NodeMail UI."""
    #get/create QApplication
    app = QtWidgets.QApplication.instance()
    if not app:
        app = QtWidgets.QApplication(sys.argv)
        app.setStyle("Fusion")
    
    #glob win var
    global custom_nodemail_window

    try:
        if custom_nodemail_window:
            custom_nodemail_window.close()
    except (NameError, RuntimeError):
        pass

    #show win
    custom_nodemail_window = NodeMailUI()
    custom_nodemail_window.show()

    #standalone and nuke open
    if not nuke: 
        sys.exit(app.exec())

if __name__ == "__main__":
    start()
    
#TO RUN IN NUKE USE:
# import sys
# path = r"P:\all_work\studentGroups\ORION_CORPORATION\00_pipeline\orionTech\scripts\nodemail"
# if path not in sys.path:
#     sys.path.append(path)

# import orion_nodemail
# orion_nodemail.start() 