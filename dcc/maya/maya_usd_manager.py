import sys
import os
import re
import shutil
import maya.cmds as cmds
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

#QT SETUP
try:
    from PySide2 import QtWidgets, QtCore, QtGui
except ImportError:
    try:
        from PySide6 import QtWidgets, QtCore, QtGui
    except ImportError:
        cmds.error("Could not load PySide2 or PySide6.")

#PATH SETUP
pipeline_path = os.environ.get("ORI_PIPELINE_PATH")
if not pipeline_path:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    pipeline_path = os.path.dirname(os.path.dirname(current_dir))

if pipeline_path and pipeline_path not in sys.path:
    sys.path.append(pipeline_path)

try:
    from core.orionUtils import OrionUtils
except ImportError:
    print("Warning: Could not import OrionUtils.")

class OrionUSDManager(MayaQWidgetDockableMixin, QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(OrionUSDManager, self).__init__(parent=parent)
        
        if 'OrionUtils' in globals():
            self.orion = OrionUtils()
        else:
            self.orion = None

        self.setWindowTitle("Orion USD Manager")
        self.setObjectName("OrionUSDManagerWindow")
        self.resize(480, 680)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)
        
        #data
        self.ctx = {
            'code': 'Unknown',
            'type': 'Unknown',
            'dept': 'Unknown',
            'task': 'Unknown',
            'path': '',
            'start': 1001,
            'end': 1100
        }
        
        self.init_ui()
        self.refresh_context()

    def init_ui(self):
        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setAlignment(QtCore.Qt.AlignTop)
        self.setLayout(self.main_layout)
        
        self.setStyleSheet("""
            QWidget { background-color: #2b2b2b; color: #dddddd; font-family: Segoe UI, Arial; }
            QGroupBox { border: 1px solid #444; border-radius: 4px; margin-top: 12px; font-weight: bold; padding: 12px 4px 4px 4px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #FF6000; }
            QPushButton { background-color: #444; border-radius: 3px; padding: 8px; font-weight: bold; }
            QPushButton:hover { background-color: #555; }
            QPushButton:disabled { background-color: #333; color: #555; }
            QPushButton#PublishBtn { background-color: #2e7d32; }
            QPushButton#ExportCam { background-color: #336699; }
            QPushButton#ExportAnim { background-color: #996633; }
            QLineEdit { background-color: #333; border: 1px solid #555; padding: 4px; border-radius: 2px;}
            QComboBox { background-color: #333; border: 1px solid #555; padding: 4px; border-radius: 2px; }
            QComboBox QAbstractItemView { background-color: #333; selection-background-color: #FF6000; }
            QSpinBox { background-color: #333; border: 1px solid #555; padding: 4px; border-radius: 2px; }
            QLabel#ContextLabel { font-weight: bold; color: #fff; }
            QLabel#PathLabel { color: #888; font-size: 10px; }
            QListWidget { background-color: #222; border: 1px solid #444; }
            QListWidget::item:selected { background-color: #FF6000; color: white; }
            QTabWidget::pane { border: 0; }
            QTabBar::tab { background: #333; padding: 8px 20px; margin-right: 2px; }
            QTabBar::tab:selected { background: #FF6000; color: white; }
        """)

        #HEADER
        header = QtWidgets.QLabel("ORION<b>USD</b> MANAGER")
        header.setTextFormat(QtCore.Qt.RichText)
        header.setAlignment(QtCore.Qt.AlignCenter)
        header.setStyleSheet("font-size: 16px; margin-bottom: 5px;")
        self.main_layout.addWidget(header)

        #CONTEXT AREA
        ctx_group = QtWidgets.QGroupBox("Current Context")
        ctx_layout = QtWidgets.QGridLayout()
        
        self.lbl_context = QtWidgets.QLabel("Context: -")
        self.lbl_context.setObjectName("ContextLabel")
        self.lbl_task = QtWidgets.QLabel("Task: -")
        self.lbl_task.setObjectName("ContextLabel")
        
        self.lbl_path = QtWidgets.QLabel("Path: -")
        self.lbl_path.setObjectName("PathLabel")
        self.lbl_path.setWordWrap(True)

        ctx_layout.addWidget(self.lbl_context, 0, 0)
        ctx_layout.addWidget(self.lbl_task, 0, 1)
        ctx_layout.addWidget(self.lbl_path, 1, 0, 1, 2)
        
        ctx_group.setLayout(ctx_layout)
        self.main_layout.addWidget(ctx_group)

        #TABS 
        self.tabs = QtWidgets.QTabWidget()
        
        self.tab_export = QtWidgets.QWidget()
        self.build_export_tab()
        self.tabs.addTab(self.tab_export, "Export")
        
        self.tab_publish = QtWidgets.QWidget()
        self.build_publish_tab()
        self.tabs.addTab(self.tab_publish, "Publish")
        
        self.main_layout.addWidget(self.tabs)
        
        #refresh btn
        btn_refresh = QtWidgets.QPushButton("Refresh Context")
        btn_refresh.clicked.connect(self.refresh_context)
        btn_refresh.setStyleSheet("margin-top: 5px; background-color: #333;")
        self.main_layout.addWidget(btn_refresh)

    def build_export_tab(self):
        layout = QtWidgets.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignTop)
        
        #FRAME RANGE
        fr_group = QtWidgets.QGroupBox("Frame Range")
        fr_layout = QtWidgets.QVBoxLayout()
        
        self.chk_use_shot_range = QtWidgets.QCheckBox("Use Shot Range (Database)")
        self.chk_use_shot_range.setChecked(True)
        self.chk_use_shot_range.toggled.connect(self.toggle_frame_inputs)
        fr_layout.addWidget(self.chk_use_shot_range)
        
        input_layout = QtWidgets.QHBoxLayout()
        input_layout.addWidget(QtWidgets.QLabel("Start:"))
        self.spin_start = QtWidgets.QSpinBox()
        self.spin_start.setRange(-9999, 99999)
        self.spin_start.setEnabled(False) 
        input_layout.addWidget(self.spin_start)
        
        input_layout.addWidget(QtWidgets.QLabel("End:"))
        self.spin_end = QtWidgets.QSpinBox()
        self.spin_end.setRange(-9999, 99999)
        self.spin_end.setEnabled(False)
        input_layout.addWidget(self.spin_end)
        
        fr_layout.addLayout(input_layout)
        fr_group.setLayout(fr_layout)
        layout.addWidget(fr_group)

        #CAMERA EXPORT 
        cam_group = QtWidgets.QGroupBox("Camera")
        cam_layout = QtWidgets.QVBoxLayout()
        cam_layout.addWidget(QtWidgets.QLabel("Anim Only (No Geo/Mats, Xform Root).", styleSheet="color:#888"))
        
        self.btn_cam = QtWidgets.QPushButton("Export Camera (vXXX)")
        self.btn_cam.setObjectName("ExportCam")
        self.btn_cam.clicked.connect(self.export_camera)
        cam_layout.addWidget(self.btn_cam)
        cam_group.setLayout(cam_layout)
        layout.addWidget(cam_group)

        #ANIMATION EXPORT 
        anim_group = QtWidgets.QGroupBox("Animation / Cache")
        anim_layout = QtWidgets.QVBoxLayout()
        anim_layout.addWidget(QtWidgets.QLabel("Geo Cache (Meshes, UVs, No Mats).", styleSheet="color:#888"))
        
        #ASSET SELECTION DROPDOWN
        anim_layout.addWidget(QtWidgets.QLabel("Select Character/Asset:"))
        self.combo_assets = QtWidgets.QComboBox()
        self.populate_asset_combo() #fill with DB assets
        anim_layout.addWidget(self.combo_assets)

        self.btn_anim = QtWidgets.QPushButton("Export Animation (vXXX)")
        self.btn_anim.setObjectName("ExportAnim")
        self.btn_anim.clicked.connect(self.export_animation)
        anim_layout.addWidget(self.btn_anim)
        anim_group.setLayout(anim_layout)
        layout.addWidget(anim_group)

        self.tab_export.setLayout(layout)

    def populate_asset_combo(self):
        self.combo_assets.clear()
        
        if not self.orion:
            self.combo_assets.addItem("Error: DB Not Connected")
            return

        try:
            #fetch all assets
            assets = self.orion.get_all_assets()
            
            if not assets:
                self.combo_assets.addItem("No Assets Found")
                return

            for asset in assets:
                #display: "char_hero (Character)"
                display_name = f"{asset['name']} ({asset['type']})"
                #data
                self.combo_assets.addItem(display_name, asset['name'])
                
        except Exception as e:
            print(f"Error populating assets: {e}")
            self.combo_assets.addItem("Error Fetching Assets")

    def build_publish_tab(self):
        layout = QtWidgets.QVBoxLayout()
        
        layout.addWidget(QtWidgets.QLabel("Select an exported file to Publish:"))
        
        #file list
        self.list_files = QtWidgets.QListWidget()
        layout.addWidget(self.list_files)
        
        #info
        self.lbl_pub_status = QtWidgets.QLabel("Ready")
        self.lbl_pub_status.setStyleSheet("color: #888; font-style: italic;")
        self.lbl_pub_status.setWordWrap(True)
        layout.addWidget(self.lbl_pub_status)
        
        #publish btn
        self.btn_pub = QtWidgets.QPushButton("PUBLISH (Make Master)")
        self.btn_pub.setObjectName("PublishBtn")
        self.btn_pub.clicked.connect(self.publish_selected)
        layout.addWidget(self.btn_pub)
        
        self.tab_publish.setLayout(layout)

    #LOGIC

    def refresh_context(self):
        #READ ENV VARS 
        raw_code = os.environ.get("ORI_SHOT_CONTEXT", "Unknown")
        raw_path = os.environ.get("ORI_SHOT_PATH", "")
        
        self.ctx['code'] = raw_code if raw_code != "None" else "Unknown"
        self.ctx['path'] = raw_path if raw_path != "None" else ""
        
        try:
            self.ctx['start'] = int(os.environ.get("ORI_SHOT_FRAME_START", 1001))
            self.ctx['end'] = int(os.environ.get("ORI_SHOT_FRAME_END", 1100))
        except:
            self.ctx['start'] = 1001
            self.ctx['end'] = 1100
        
        #OVERRIDE WITH SCENE PATH 
        scene_name = cmds.file(q=True, sn=True)
        
        self.ctx['dept'] = "Unknown"
        self.ctx['task'] = "Unknown"

        if scene_name:
            scene_norm = scene_name.replace("\\", "/")
            
            #SHOT DETECTION
            if "/40_shots/" in scene_norm:
                self.ctx['type'] = "Shot"
                parts = scene_norm.split("/40_shots/")
                if len(parts) > 1:
                    structure = parts[1].split("/")
                    if len(structure) >= 3:
                        self.ctx['code'] = structure[0]
                        self.ctx['dept'] = structure[1]
                        self.ctx['task'] = structure[2]
                        self.ctx['path'] = os.path.join(parts[0], "40_shots", structure[0])

            #ASSET DETECTION
            elif "/30_assets/" in scene_norm:
                self.ctx['type'] = "Asset"
                parts = scene_norm.split("/30_assets/")
                if len(parts) > 1:
                    structure = parts[1].split("/")
                    if len(structure) >= 3:
                        self.ctx['code'] = structure[0]
                        self.ctx['dept'] = structure[1]
                        self.ctx['task'] = structure[2]
                        self.ctx['path'] = os.path.join(parts[0], "30_assets", structure[0])

        #UPDATE UI
        self.lbl_context.setText(f"{self.ctx['type']}: {self.ctx['code']} / {self.ctx['dept']}")
        self.lbl_task.setText(f"Task: {self.ctx['task']}")
        self.lbl_path.setText(self.ctx['path'] if self.ctx['path'] else "INVALID PATH (Save scene in pipeline)")
        
        #ENABLE/DISABLE
        valid_path = os.path.exists(self.ctx['path']) if self.ctx['path'] else False
        valid_context = valid_path and self.ctx['dept'] != "Unknown"
        
        self.btn_cam.setEnabled(valid_context)
        self.btn_anim.setEnabled(valid_context)
        self.btn_pub.setEnabled(valid_context)
        
        if not valid_context:
            self.lbl_path.setStyleSheet("color: #F44336; font-weight: bold;")
        else:
            self.lbl_path.setStyleSheet("color: #888;")

        self.spin_start.setValue(self.ctx['start'])
        self.spin_end.setValue(self.ctx['end'])
        
        self.refresh_file_list()

    def toggle_frame_inputs(self, checked):
        self.spin_start.setEnabled(not checked)
        self.spin_end.setEnabled(not checked)
        if checked:
            self.spin_start.setValue(self.ctx.get('start', 1001))
            self.spin_end.setValue(self.ctx.get('end', 1100))
        else:
            self.spin_start.setValue(int(cmds.playbackOptions(q=True, min=True)))
            self.spin_end.setValue(int(cmds.playbackOptions(q=True, max=True)))

    def get_paths(self):
        """Calculates Absolute Export and Publish folders."""
        shot_path = self.ctx.get('path')
        dept = self.ctx.get('dept')
        task = self.ctx.get('task')
        
        if not shot_path or dept == "Unknown" or task == "Unknown":
            return None, None
            
        export_dir = os.path.normpath(os.path.join(shot_path, dept, task, "EXPORT"))
        publish_dir = os.path.join(export_dir, "PUBLISHED")
        
        if not os.path.exists(export_dir):
            try: os.makedirs(export_dir)
            except: pass
            
        return export_dir, publish_dir

    def get_versioned_filename(self, folder, base_name):
        version = 1
        if os.path.exists(folder):
            existing = [f for f in os.listdir(folder) if f.startswith(base_name) and f.endswith(".usdc")]
            for f in existing:
                match = re.search(r"_v(\d{3})\.usdc", f)
                if match:
                    v = int(match.group(1))
                    if v >= version: version = v + 1
        return f"{base_name}_v{version:03d}.usdc"

    #EXPORT

    def perform_usd_export(self, path, sel, start, end, export_args):
        path = path.replace("\\", "/")
        try:
            args = {
                "file": path,
                "selection": True,
                "frameRange": (start, end),
                "frameStride": 1.0,
                "shadingMode": "none", 
                "stripNamespaces": True,
                "verbose": True
            }
            args.update(export_args)
            
            print(f"Exporting to: {path}")
            cmds.mayaUSDExport(**args)
            
            cmds.inViewMessage(amg=f"Saved: {os.path.basename(path)}", pos='midCenter', fade=True)
            self.refresh_file_list()
            return True
        except Exception as e:
            cmds.confirmDialog(title="Export Failed", message=str(e), icon="critical")
            return False

    def export_camera(self):
        export_dir, _ = self.get_paths()
        if not export_dir:
            cmds.warning("Invalid context paths. Save file in pipeline structure.")
            return
            
        sel = cmds.ls(sl=True)
        if not sel:
            cmds.warning("Select a camera.")
            return

        base_name = f"{self.ctx['code']}_cam"
        filename = self.get_versioned_filename(export_dir, base_name)
        out_path = os.path.join(export_dir, filename)
        
        root_prim = f"{self.ctx['code']}_camera"
        
        args = {
            "rootPrim": root_prim,
            "rootPrimType": "xform",
            "defaultPrim": root_prim,
        }
        
        self.perform_usd_export(out_path, sel, self.spin_start.value(), self.spin_end.value(), args)

    def export_animation(self):
        export_dir, _ = self.get_paths()
        if not export_dir: return
        
        sel = cmds.ls(sl=True)
        if not sel:
            cmds.warning("Select objects.")
            return

        #name frm dropdown
        asset_name = self.combo_assets.currentData()
        
        if not asset_name:
            cmds.warning("Please select an Asset from the list!")
            return

        #fiel naming
        base_name = f"{self.ctx['code']}_{asset_name}"
        filename = self.get_versioned_filename(export_dir, base_name)
        out_path = os.path.join(export_dir, filename)
        
        #name 2 match asset root prim
        root_prim = asset_name
        
        args = {
            "rootPrim": root_prim,
            "rootPrimType": "xform",
            "defaultPrim": root_prim,
            "exportSkels": "auto",
            "exportSkin": "auto",
            "exportBlendShapes": True,
            "exportUVs": True,
            "exportColorSets": True
        }
        
        self.perform_usd_export(out_path, sel, self.spin_start.value(), self.spin_end.value(), args)

    #PUBLISH

    def refresh_file_list(self):
        self.list_files.clear()
        export_dir, _ = self.get_paths()
        
        if not export_dir or not os.path.exists(export_dir):
            return

        files = [f for f in os.listdir(export_dir) if f.endswith(".usdc") and os.path.isfile(os.path.join(export_dir, f))]
        files.sort(reverse=True) 
        
        for f in files:
            item = QtWidgets.QListWidgetItem(f)
            item.setData(QtCore.Qt.UserRole, os.path.join(export_dir, f))
            self.list_files.addItem(item)

    def publish_selected(self):
        items = self.list_files.selectedItems()
        if not items: return
        
        src_path = items[0].data(QtCore.Qt.UserRole)
        filename = items[0].text()
        
        _, publish_dir = self.get_paths()
        if not os.path.exists(publish_dir):
            os.makedirs(publish_dir)
            
        clean_name = re.sub(r"[._]v\d{3,}", "", filename)
        dst_path = os.path.join(publish_dir, clean_name).replace("\\", "/")
        
        msg = f"Source: {filename}\n\nPublish To:\n{clean_name}\n\n(This overwrites the previous Master file)"
        res = cmds.confirmDialog(title="Confirm Publish", message=msg, button=["Publish", "Cancel"], defaultButton="Publish", cancelButton="Cancel", dismissString="Cancel")
        
        if res == "Publish":
            try:
                shutil.copy2(src_path, dst_path)
                self.lbl_pub_status.setText(f"Successfully published: {clean_name}")
                self.lbl_pub_status.setStyleSheet("color: #4CAF50;") # Green
            except Exception as e:
                self.lbl_pub_status.setText(f"Error: {e}")
                self.lbl_pub_status.setStyleSheet("color: #F44336;") # Red

#LAUNCHER
def show_orion_manager():
    ctl = "OrionUSDManagerWindowWorkspaceControl"
    if cmds.workspaceControl(ctl, exists=True):
        cmds.deleteUI(ctl, control=True)
    elif cmds.window("OrionUSDManagerWindow", exists=True):
        cmds.deleteUI("OrionUSDManagerWindow", window=True)
    
    global orion_usd_manager
    orion_usd_manager = OrionUSDManager()
    orion_usd_manager.show(dockable=True, floating=True)

show_orion_manager()