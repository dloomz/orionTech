import mari
import os
import shutil
import sys
import re
from PySide2 import QtWidgets, QtCore, QtGui

try:
    from core.orionUtils import OrionUtils
except ImportError:
    current_dir = os.path.dirname(__file__)
    pipeline_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
    if pipeline_root not in sys.path:
        sys.path.append(pipeline_root)
    from core.orionUtils import OrionUtils

class MariExporter(QtWidgets.QDialog):
    def __init__(self):
        super(MariExporter, self).__init__()
        
        self.orion = OrionUtils()
        
        self.setWindowTitle("Orion Mari Exporter")
        self.resize(350, 450)
        
        # Main Layout
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5) # Small global margin
        layout.setSpacing(5)
        self.setLayout(layout)
        
        # --- CONTEXT SECTION (Top) ---
        # Keeping GroupBox here as it visually separates the inputs well
        context_group = QtWidgets.QGroupBox("Context")
        context_layout = QtWidgets.QFormLayout()
        context_layout.setContentsMargins(5, 5, 5, 5)
        context_layout.setSpacing(5)
        
        self.asset_combo = QtWidgets.QComboBox()
        self.task_combo = QtWidgets.QComboBox()
        self.task_combo.setEditable(True)
        
        context_layout.addRow("Asset:", self.asset_combo)
        context_layout.addRow("Task:", self.task_combo)
        context_group.setLayout(context_layout)
        layout.addWidget(context_group)

        # --- SEPARATOR ---
        line1 = QtWidgets.QFrame()
        line1.setFrameShape(QtWidgets.QFrame.HLine)
        line1.setFrameShadow(QtWidgets.QFrame.Sunken)
        layout.addWidget(line1)

        # --- EXPORT HEADER (Flat Row) ---
        # Putting title and version info on ONE line to save space
        exp_header_layout = QtWidgets.QHBoxLayout()
        exp_header_layout.setContentsMargins(0, 2, 0, 0)
        
        exp_label = QtWidgets.QLabel("EXPORT")
        exp_label.setStyleSheet("font-weight: bold;")
        exp_header_layout.addWidget(exp_label)
        
        exp_header_layout.addStretch()
        
        # Green Text on the right
        self.next_ver_label = QtWidgets.QLabel("Next: ...")
        self.next_ver_label.setStyleSheet("font-weight: bold; color: #4CAF50;") 
        exp_header_layout.addWidget(self.next_ver_label)
        
        layout.addLayout(exp_header_layout)

        # --- CHANNELS LIST ---
        self.channel_list = QtWidgets.QListWidget()
        self.channel_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        # Reduced height since we are compacting
        self.channel_list.setFixedHeight(100)
        layout.addWidget(self.channel_list)
        
        # --- EXPORT BUTTON ---
        self.export_btn = QtWidgets.QPushButton("Export New Version")
        self.export_btn.setStyleSheet("padding: 5px;")
        self.export_btn.clicked.connect(self.run_export)
        layout.addWidget(self.export_btn)
        
        # --- SEPARATOR ---
        line2 = QtWidgets.QFrame()
        line2.setFrameShape(QtWidgets.QFrame.HLine)
        line2.setFrameShadow(QtWidgets.QFrame.Sunken)
        layout.addWidget(line2)

        # --- PUBLISH SECTION (Flat Row) ---
        pub_layout = QtWidgets.QHBoxLayout()
        pub_layout.setContentsMargins(0, 2, 0, 0)
        
        pub_label = QtWidgets.QLabel("PUBLISH")
        pub_label.setStyleSheet("font-weight: bold;")
        pub_layout.addWidget(pub_label)
        
        pub_layout.addStretch()
        
        self.pub_version_combo = QtWidgets.QComboBox()
        self.pub_version_combo.setMinimumWidth(80)
        pub_layout.addWidget(self.pub_version_combo)
        
        self.publish_btn = QtWidgets.QPushButton("Publish")
        self.publish_btn.clicked.connect(self.run_publish)
        pub_layout.addWidget(self.publish_btn)
        
        layout.addLayout(pub_layout)

        # --- FOOTER INFO ---
        layout.addStretch() # Push everything up
        self.info_label = QtWidgets.QLabel("Ready")
        self.info_label.setStyleSheet("color: gray; font-style: italic; font-size: 10px; margin-top: 5px;")
        self.info_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.info_label)

        # --- INITIALIZE ---
        self.populate_assets()
        self.populate_channels()
        
        # --- SIGNALS ---
        self.asset_combo.currentIndexChanged.connect(self.populate_tasks)
        self.task_combo.currentIndexChanged.connect(self.update_ui_state)
        self.task_combo.editTextChanged.connect(self.update_ui_state)
        self.task_combo.lineEdit().textEdited.connect(self.force_caps)

        # Trigger
        self.populate_tasks()

    def force_caps(self, text):
        if not text: return
        upper_text = text.upper()
        if text != upper_text:
            line_edit = self.task_combo.lineEdit()
            pos = line_edit.cursorPosition()
            self.task_combo.blockSignals(True)
            line_edit.setText(upper_text)
            line_edit.setCursorPosition(pos)
            self.task_combo.blockSignals(False)
            self.update_ui_state()

    def populate_assets(self):
        self.asset_combo.clear()
        try:
            assets = self.orion.get_all_assets()
            for asset in assets:
                self.asset_combo.addItem(asset['name'])
        except Exception as e:
            print(f"Error loading assets: {e}")

    def populate_tasks(self):
        current_task = self.task_combo.currentText()
        self.task_combo.blockSignals(True)
        self.task_combo.clear()
        
        defaults = ["MAIN", "VARIANT", "LOOKDEV", "FIX", "WIP"]
        found_tasks = []

        root = self.orion.get_root_dir()
        asset_name = self.asset_combo.currentText()
        
        if asset_name:
            tex_path = os.path.join(root, "30_assets", asset_name, "TEX")
            print(f"[Orion] Scanning tasks: {tex_path}")
            
            if os.path.exists(tex_path):
                try:
                    items = os.listdir(tex_path)
                    for item in items:
                        full_path = os.path.join(tex_path, item)
                        if os.path.isdir(full_path):
                            found_tasks.append(item.upper())
                except Exception as e:
                    print(f"[Orion] Scan error: {e}")

        all_tasks = sorted(list(set(defaults + found_tasks)))
        self.task_combo.addItems(all_tasks)
        
        if current_task and current_task.upper() in all_tasks:
             self.task_combo.setCurrentText(current_task.upper())
        else:
             self.task_combo.setCurrentText("MAIN")
            
        self.task_combo.blockSignals(False)
        self.update_ui_state()

    def populate_channels(self):
        self.channel_list.clear()
        if not mari.projects.current():
            return
        geo = mari.geo.current()
        if not geo:
            return
        for channel in geo.channelList():
            item = QtWidgets.QListWidgetItem(channel.name())
            item.setSelected(True)
            self.channel_list.addItem(item)

    def get_paths(self):
        root = self.orion.get_root_dir()
        asset_name = self.asset_combo.currentText()
        task_name = self.task_combo.currentText().upper()
        if not task_name: task_name = "MAIN"
        
        # 30_assets/ASSET/TEX/TASK
        task_root = os.path.join(root, "30_assets", asset_name, "TEX", task_name)
        
        # DIRECTLY to EXPORT (No intermediate MARI folder)
        export_upper = os.path.join(task_root, "EXPORT")
        export_lower = os.path.join(task_root, "export")
        
        if os.path.exists(export_lower) and not os.path.exists(export_upper):
            final_path = export_lower
        else:
            final_path = export_upper
            
        return final_path, asset_name

    def update_ui_state(self):
        base_path, _ = self.get_paths()
        
        next_ver = self.get_next_export_version(base_path)
        self.next_ver_label.setText(f"Next: v{next_ver:03d}")
        
        current_pub_selection = self.pub_version_combo.currentText()
        
        self.pub_version_combo.blockSignals(True)
        self.pub_version_combo.clear()
        
        existing_versions = []
        if os.path.exists(base_path):
            try:
                for item in os.listdir(base_path):
                    if re.match(r"^v\d{3}$", item):
                        existing_versions.append(item)
            except: pass
            
        existing_versions.sort(reverse=True)
        
        if existing_versions:
            self.pub_version_combo.addItems(existing_versions)
            self.publish_btn.setEnabled(True)
            if current_pub_selection in existing_versions:
                self.pub_version_combo.setCurrentText(current_pub_selection)
        else:
            self.pub_version_combo.addItem("-")
            self.publish_btn.setEnabled(False)
            
        self.pub_version_combo.blockSignals(False)

    def get_next_export_version(self, base_path):
        if not os.path.exists(base_path):
            return 1
        highest_ver = 0
        try:
            for item in os.listdir(base_path):
                if re.match(r"^v\d{3}$", item):
                    try:
                        num = int(item[1:])
                        if num > highest_ver: highest_ver = num
                    except: continue
        except: pass
        return highest_ver + 1

    def run_export(self):
        if not mari.projects.current():
            self.info_label.setText("Error: No project")
            return

        base_path, asset_name = self.get_paths()
        ver_num = self.get_next_export_version(base_path)
        ver_str = f"v{ver_num:03d}"
        output_dir = os.path.join(base_path, ver_str)
        
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception as e:
                 print(f"Error creating dir: {e}")
                 self.info_label.setText(f"Error: {e}")
                 return
            
        selected_items = self.channel_list.selectedItems()
        if not selected_items:
            self.info_label.setText("Error: No channels")
            return
            
        geo = mari.geo.current()
        count = 0
        
        for item in selected_items:
            chan_name = item.text()
            channel = geo.channel(chan_name)
            if channel:
                filename = f"{asset_name}_{chan_name}.$UDIM.exr"
                full_path = os.path.join(output_dir, filename)
                
                self.info_label.setText(f"Exporting {chan_name}...")
                mari.app.processEvents()
                try:
                    channel.exportImagesFlattened(full_path)
                    count += 1
                except Exception as e:
                    print(f"Failed: {e}")

        self.info_label.setText(f"Done: {ver_str}")
        print(f"[Orion] Exported: {output_dir}")
        self.update_ui_state()

    def run_publish(self):
        base_path, _ = self.get_paths()
        
        ver_to_pub = self.pub_version_combo.currentText()
        if not ver_to_pub or ver_to_pub == "-":
            return
            
        src_dir = os.path.join(base_path, ver_to_pub)
        dst_dir = os.path.join(base_path, "PUBLISHED")
        
        if not os.path.exists(src_dir):
            self.info_label.setText(f"Err: {ver_to_pub} missing")
            return

        self.info_label.setText(f"Publishing {ver_to_pub}...")
        mari.app.processEvents()

        try:
            if os.path.exists(dst_dir):
                shutil.rmtree(dst_dir)
            shutil.copytree(src_dir, dst_dir)
            
            self.info_label.setText(f"Published: {ver_to_pub}")
            print(f"[Orion] Published: {src_dir} -> {dst_dir}")
        except Exception as e:
            self.info_label.setText(f"Fail: {str(e)}")

def show_ui():
    global exporter_win
    try:
        exporter_win.close()
    except:
        pass
    exporter_win = MariExporter()
    exporter_win.show()
