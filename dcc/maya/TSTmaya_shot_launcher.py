import sys
import os
import re
import maya.cmds as cmds
import maya.mel as mel
import maya.OpenMaya as om
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

#QT
try:
    from PySide2 import QtWidgets, QtCore, QtGui
except ImportError:
    try:
        from PySide6 import QtWidgets, QtCore, QtGui
    except ImportError:
        cmds.error("Could not load PySide2 or PySide6. UI cannot start.")

#PATH SETUP
pipeline_path = os.environ.get("ORI_PIPELINE_PATH")

if not pipeline_path:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    pipeline_path = os.path.dirname(os.path.dirname(current_dir))

if pipeline_path and pipeline_path not in sys.path:
    sys.path.append(pipeline_path)

try:
    from core.orionUtils import OrionUtils
    try: 
        from maya.plugin.timeSliderBookmark.timeSliderBookmark import createBookmark
    except ImportError:
        createBookmark = None
except ImportError:
    print("Warning: Could not import OrionUtils. Check sys.path.")

#UI
class OrionMayaUI(MayaQWidgetDockableMixin, QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(OrionMayaUI, self).__init__(parent=parent)
        
        # Init Core
        if 'OrionUtils' in globals():
            self.orion = OrionUtils()
            self.root_dir = self.orion.get_root_dir()
        else:
            self.orion = None
            self.root_dir = ""

        self.current_shot = None
        
        self.setWindowTitle("Orion Maya Loader")
        self.setObjectName("OrionMayaWindow")
        self.resize(600, 700)
        
        #always on top
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)
        
        self.init_ui()
        
        if self.orion:
            self.populate_shots()
            
            #sync context
            context_shot = os.environ.get("ORI_SHOT_CONTEXT")
            if context_shot:
                index = self.combo_shots.findText(context_shot)
                if index >= 0:
                    self.combo_shots.setCurrentIndex(index)

    def init_ui(self):
        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setAlignment(QtCore.Qt.AlignTop)
        self.setLayout(self.main_layout)
        
        self.setStyleSheet("""
            QWidget { background-color: #2b2b2b; color: #dddddd; font-family: Segoe UI, Arial; }
            QGroupBox { border: 1px solid #444; border-radius: 4px; margin-top: 10px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QPushButton { background-color: #444; border-radius: 3px; padding: 6px; }
            QPushButton:hover { background-color: #555; }
            QComboBox { background-color: #333; border: 1px solid #555; padding: 4px; }
            QListWidget { background-color: #222; border: 1px solid #444; }
            QTreeWidget { background-color: #222; border: 1px solid #444; }
            QTreeWidget::item:selected { background-color: #FF6000; color: white; }
            QSplitter::handle { background-color: #444; }
        """)

        #HEADER
        header_layout = QtWidgets.QHBoxLayout()
        logo_label = QtWidgets.QLabel("ORION<b>MAYA</b>")
        logo_label.setTextFormat(QtCore.Qt.RichText)
        logo_label.setStyleSheet("font-size: 16px; color: #FF6000;")
        header_layout.addWidget(logo_label)
        self.main_layout.addLayout(header_layout)

        #SHOT CONTEXT
        shot_group = QtWidgets.QGroupBox("Shot Context")
        shot_layout = QtWidgets.QVBoxLayout()
        
        self.combo_shots = QtWidgets.QComboBox()
        self.combo_shots.currentIndexChanged.connect(self.on_shot_changed)
        
        self.lbl_shot_info = QtWidgets.QLabel("Select a shot...")
        self.lbl_shot_info.setStyleSheet("color: #888; font-style: italic;")
        
        shot_layout.addWidget(self.combo_shots)
        shot_layout.addWidget(self.lbl_shot_info)
        shot_group.setLayout(shot_layout)
        self.main_layout.addWidget(shot_group)

        #TABS
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setStyleSheet("QTabWidget::pane { border: 0; }")
        
        #scene tab
        self.tab_scene = QtWidgets.QWidget()
        self.build_scene_tab()
        self.tabs.addTab(self.tab_scene, "Scene Setup")
        
        #asset tab
        self.tab_assets = QtWidgets.QWidget()
        self.build_assets_tab()
        self.tabs.addTab(self.tab_assets, "Assets")
        
        #shot tasks tab
        self.tab_shot_tasks = QtWidgets.QWidget()
        self.build_shot_tasks_tab()
        self.tabs.addTab(self.tab_shot_tasks, "Shot Tasks")

        self.main_layout.addWidget(self.tabs)

    def build_scene_tab(self):
        layout = QtWidgets.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignTop)
        
        btn_cam = QtWidgets.QPushButton("Import Shot Camera")
        btn_cam.setStyleSheet("background-color: #336699;")
        btn_cam.clicked.connect(self.import_camera)
        layout.addWidget(btn_cam)
        
        btn_layout = QtWidgets.QPushButton("Import Layout")
        btn_layout.setStyleSheet("background-color: #996633;")
        btn_layout.clicked.connect(self.import_layout)
        layout.addWidget(btn_layout)
        
        self.tab_scene.setLayout(layout)

    def build_assets_tab(self):
        layout = QtWidgets.QVBoxLayout()
        
        #search bar
        self.input_search = QtWidgets.QLineEdit()
        self.input_search.setPlaceholderText("Search Assets...")
        self.input_search.textChanged.connect(self.filter_assets)
        layout.addWidget(self.input_search)
        
        #splitter
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        
        #list
        self.list_assets = QtWidgets.QListWidget()
        self.list_assets.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.list_assets.itemClicked.connect(self.on_asset_clicked) 
        splitter.addWidget(self.list_assets)
        
        #tree
        self.tree_asset_tasks = QtWidgets.QTreeWidget()
        self.tree_asset_tasks.setHeaderLabel("Asset Tasks")
        self.tree_asset_tasks.itemClicked.connect(self.on_asset_task_clicked)
        splitter.addWidget(self.tree_asset_tasks)
        
        #files
        right_widget = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        right_layout.addWidget(QtWidgets.QLabel("Files:"))
        self.list_asset_files = QtWidgets.QListWidget()
        right_layout.addWidget(self.list_asset_files)
        
        self.btn_load_asset = QtWidgets.QPushButton("Reference Asset")
        self.btn_load_asset.setStyleSheet("background-color: #2e7d32; font-weight: bold;")
        self.btn_load_asset.clicked.connect(self.import_selected_asset_file)
        right_layout.addWidget(self.btn_load_asset)
        
        splitter.addWidget(right_widget)
        splitter.setSizes([150, 150, 250])
        
        layout.addWidget(splitter)
        
        if self.orion:
            self.populate_assets()
        self.tab_assets.setLayout(layout)

    def build_shot_tasks_tab(self):
        layout = QtWidgets.QVBoxLayout()
        
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        
        self.tree_shot_tasks = QtWidgets.QTreeWidget()
        self.tree_shot_tasks.setHeaderLabel("Shot Structure")
        self.tree_shot_tasks.itemClicked.connect(self.on_tree_item_clicked)
        splitter.addWidget(self.tree_shot_tasks)
        
        right_widget = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        right_layout.addWidget(QtWidgets.QLabel("Published Files:"))
        self.list_shot_files = QtWidgets.QListWidget()
        right_layout.addWidget(self.list_shot_files)
        
        btn_load = QtWidgets.QPushButton("Reference/Import File")
        btn_load.clicked.connect(self.import_shot_task_file)
        right_layout.addWidget(btn_load)
        
        splitter.addWidget(right_widget)
        splitter.setSizes([150, 300])
        
        layout.addWidget(splitter)
        self.tab_shot_tasks.setLayout(layout)

    #LOGIC 

    def populate_shots(self):
        self.combo_shots.clear()
        shots = self.orion.get_all_shots()
        self.combo_shots.addItem("Select Shot...", None)
        for shot in shots:
            self.combo_shots.addItem(shot['code'], shot)

    def populate_assets(self):
        self.list_assets.clear()
        self.assets_data = self.orion.get_all_assets()
        for asset in self.assets_data:
            item = QtWidgets.QListWidgetItem(f"{asset['name']} ({asset['type']})")
            item.setData(QtCore.Qt.UserRole, asset)
            self.list_assets.addItem(item)

    def filter_assets(self, text):
        for i in range(self.list_assets.count()):
            item = self.list_assets.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def on_asset_clicked(self, item):
        asset = item.data(QtCore.Qt.UserRole)
        name = asset['name']
        path = os.path.join(self.root_dir, "30_assets", name)
        
        self.tree_asset_tasks.clear()
        self.list_asset_files.clear()

        if os.path.exists(path):
            ignore = ["__pycache__", ".git"]
            depts = sorted([d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d)) and d not in ignore])
            
            for dept_name in depts:
                dept_item = QtWidgets.QTreeWidgetItem(self.tree_asset_tasks)
                dept_item.setText(0, dept_name)
                
                dept_full_path = os.path.join(path, dept_name)
                if os.path.exists(dept_full_path):
                    tasks = sorted([t for t in os.listdir(dept_full_path) if os.path.isdir(os.path.join(dept_full_path, t)) and t not in ignore])
                    if tasks:
                        for task_name in tasks:
                            task_item = QtWidgets.QTreeWidgetItem(dept_item)
                            task_item.setText(0, task_name)
                            task_full_path = os.path.join(dept_full_path, task_name)
                            task_item.setData(0, QtCore.Qt.UserRole, task_full_path)
                    else:
                        dept_item.setData(0, QtCore.Qt.UserRole, dept_full_path)

    def on_asset_task_clicked(self, item, column):
        task_path = item.data(0, QtCore.Qt.UserRole)
        if task_path:
            self.refresh_asset_task_files(task_path)
        else:
            self.list_asset_files.clear()
            item.setExpanded(not item.isExpanded())

    def refresh_asset_task_files(self, task_path):
        self.list_asset_files.clear()
        pub_path = os.path.join(task_path, "EXPORT", "PUBLISHED")
        
        found_files = []
        if os.path.exists(pub_path):
            for root, dirs, files in os.walk(pub_path):
                for f in files:
                    if f.endswith((".abc", ".usd", ".usdc", ".obj", ".fbx", ".ma", ".mb")):
                        full_path = os.path.join(root, f)
                        found_files.append((f, full_path))
        
        if not found_files:
            files = [f for f in os.listdir(task_path) if f.endswith((".abc", ".usd", ".usdc", ".obj", ".fbx", ".ma", ".mb"))]
            if files:
                for f in sorted(files):
                    found_files.append((f, os.path.join(task_path, f)))
        
        if not found_files:
            self.list_asset_files.addItem("No files found.")
            return

        for name, path in found_files:
            l_item = QtWidgets.QListWidgetItem(name)
            l_item.setData(QtCore.Qt.UserRole, path)
            self.list_asset_files.addItem(l_item)

    def on_shot_changed(self):
        data = self.combo_shots.currentData()
        if not data:
            self.current_shot = None
            self.lbl_shot_info.setText("Select a shot...")
            return
        
        self.current_shot = data
        shot_code = data['code']
        start_frame = str(data['frame_start'])
        end_frame = str(data['frame_end'])
        shot_path = data['shot_path']
        thread_id = str(data['discord_thread_id']) if data['discord_thread_id'] else ""

        self.lbl_shot_info.setText(f"Shot: {shot_code} ({start_frame}-{end_frame})")

        print(f"Setting Context to: {shot_code}")
        os.environ["ORI_SHOT_CONTEXT"] = shot_code
        os.environ["ORI_DISCORD_THREAD_ID"] = thread_id
        os.environ["ORI_SHOT_PATH"] = shot_path
        os.environ["ORI_SHOT_FRAME_START"] = start_frame
        os.environ["ORI_SHOT_FRAME_END"] = end_frame
        
        self.set_frames_from_shot(end_frame)
        self.populate_shot_tree()

    def set_frames_from_shot(self, end_frame_str):
        if not cmds.pluginInfo("timeSliderBookmark", query=True, loaded=True):
            try: cmds.loadPlugin("timeSliderBookmark")
            except: pass

        if end_frame_str:
            end_bookmark = int(end_frame_str)
        else:
            end_bookmark = 1250
            
        start_bookmark = 1011
        
        start_frame = 1001
        end_frame = end_bookmark + 10
        start_scene = 981
        
        cmds.playbackOptions(min=start_frame, max=end_frame)
        cmds.playbackOptions(animationStartTime=start_scene, animationEndTime=end_frame)
        cmds.currentTime(start_frame)

        bm_name = "MainAction"
        try:
            all_bms = cmds.ls(type="timeSliderBookmark") or []
            for b in all_bms:
                if cmds.getAttr(f"{b}.name") == bm_name:
                    cmds.delete(b)
            
            if createBookmark:
                createBookmark(name=bm_name, start=start_bookmark, stop=end_bookmark, color=(1.0, 0.37, 0.0))
            else:
                cmds.timeSliderBookmark(name=bm_name, start=start_bookmark, end=end_bookmark, color=(1.0, 0.37, 0.0))
        except Exception as e:
            print(f"Error creating bookmark: {e}")

    def populate_shot_tree(self):
        self.tree_shot_tasks.clear()
        self.list_shot_files.clear()
        if not self.current_shot: return

        shot_code = self.current_shot['code']
        shot_path = os.path.join(self.root_dir, "40_shots", shot_code)
        if not os.path.exists(shot_path): return

        ignore = ["__pycache__", ".git", "COMP"]
        depts = sorted([d for d in os.listdir(shot_path) if os.path.isdir(os.path.join(shot_path, d)) and d not in ignore and not d.startswith(".")])

        for dept_name in depts:
            dept_item = QtWidgets.QTreeWidgetItem(self.tree_shot_tasks)
            dept_item.setText(0, dept_name)
            dept_full_path = os.path.join(shot_path, dept_name)
            
            if os.path.exists(dept_full_path):
                tasks = sorted([t for t in os.listdir(dept_full_path) if os.path.isdir(os.path.join(dept_full_path, t)) and t not in ignore])
                if tasks:
                    for task_name in tasks:
                        task_item = QtWidgets.QTreeWidgetItem(dept_item)
                        task_item.setText(0, task_name)
                        task_full_path = os.path.join(dept_full_path, task_name)
                        task_item.setData(0, QtCore.Qt.UserRole, task_full_path)
                else:
                    dept_item.setData(0, QtCore.Qt.UserRole, dept_full_path)

    def on_tree_item_clicked(self, item, column):
        task_path = item.data(0, QtCore.Qt.UserRole)
        if task_path:
            self.refresh_shot_task_files(task_path)
        else:
            self.list_shot_files.clear()
            item.setExpanded(not item.isExpanded())

    def refresh_shot_task_files(self, task_path):
        self.list_shot_files.clear()
        pub_path = os.path.join(task_path, "EXPORT", "PUBLISHED")
        
        found_files = []
        if os.path.exists(pub_path):
            for root, dirs, files in os.walk(pub_path):
                for f in files:
                    if f.endswith((".abc", ".usd", ".usdc", ".bgeo.sc", ".obj", ".fbx", ".ma", ".mb")):
                        full_path = os.path.join(root, f)
                        found_files.append((f, full_path))
        
        if not found_files:
            self.list_shot_files.addItem("No published files found.")
            return

        for name, path in found_files:
            item = QtWidgets.QListWidgetItem(name)
            item.setData(QtCore.Qt.UserRole, path)
            self.list_shot_files.addItem(item)

    #IMPORTERS

    def import_camera(self):
        if not self.current_shot:
            print("Please select a shot first.")
            return

        shot_code = self.current_shot['code']
        cam_path = os.path.join(self.root_dir, "40_shots", shot_code, "CAMERA", "MAYA", "EXPORT", "PUBLISHED")
        plate_root = os.path.join(self.root_dir, "40_shots", shot_code, "CAMERA", "PLATES")
        
        found = None
        if os.path.exists(cam_path):
            candidates = [f for f in os.listdir(cam_path) if f.endswith(".usdc") or f.endswith(".usd")]
            candidates.sort()
            if candidates:
                found = os.path.join(cam_path, candidates[-1])
        
        if found:
            if found.endswith(".usd"):
                if not cmds.pluginInfo("mayaUsdPlugin", q=True, loaded=True):
                    cmds.loadPlugin("mayaUsdPlugin")
            try:

                cmds.mayaUSDImport(
                    file = found,
                    readAnimData = True
                    )
                print(f"Imported Camera: {os.path.basename(found)}")
            except Exception as e:
                print(f"Error importing camera: {e}")       
        else:
            print(f"No camera files found in: {cam_path}")

        ORI_SHOT_CONTEXT = os.getenv('ORI_SHOT_CONTEXT')

        cam_transform = cmds.ls(f'{ORI_SHOT_CONTEXT}_camera', type='transform')
        cam_shapes = cmds.listRelatives(cam_transform, shapes=True, type='camera')
        
        cam = cam_shapes[0]
        cam2 = cam[1]
        
        cam_parent = cmds.listRelatives(cam, parent=True)[0]

        for attr in ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"):
            cmds.setAttr(f"{cam_parent}.{attr}", lock=True, keyable=False, channelBox=False)
            
        cmds.setAttr(f"{cam_parent}.displayGateMask", )
        
        # print(str(cam_transform))  
        # print(str(cam_shapes))  
        # print(str(camera_transform))  
        # print(str(camera))    
        cmds.camera(cam, displayGateMask = True, displayFilmGate = True)
        
        if not os.path.exists(plate_root):
            print("Plate folder not found.")
            return

        found_seq = None
        for item in os.listdir(plate_root):
            if item.lower().endswith((".exr", ".jpg", ".png", ".tif", ".tiff")):
                found_seq = os.path.join(plate_root, item)
                break
            
        if found_seq:

            try:
                image_plane = cmds.imagePlane(camera=cam, fileName=found_seq)[0]
                cmds.setAttr(f"{image_plane}.useFrameExtension", 1)
                print(f"Created Image Plane on {cam}")
            except Exception as e:
                print(f"Error creating image plane: {e}")
        else:
            print("No image sequences found in Source.")

    def import_layout(self):
        
        shot_code = self.current_shot['code']
        layout_path = os.path.join(self.root_dir, "40_shots", shot_code, "CAMERA", "LAYOUT", "EXPORT", "PUBLISHED")
        
        found = None
        if os.path.exists(layout_path):
            candidates = [f for f in os.listdir(layout_path) if f.endswith(".usdc") or f.endswith(".usd")]
            candidates.sort()
            if candidates:
                found = os.path.join(layout_path, candidates[-1])

        if found:
            if found.endswith(".usd"):
                if not cmds.pluginInfo("mayaUsdPlugin", q=True, loaded=True):
                    cmds.loadPlugin("mayaUsdPlugin")
            try:

                cmds.mayaUSDImport(
                    file = found,
                    readAnimData = True
                    )
                print(f"Imported Layout: {os.path.basename(found)}")
            except Exception as e:
                print(f"Error importing layout: {e}")       
        else:
            print(f"No layout files found in: {layout_path}")

    def import_selected_asset_file(self):
        item = self.list_asset_files.currentItem()
        if not item: return
        
        path = item.data(QtCore.Qt.UserRole)
        if not path or not os.path.exists(path): return

        asset_item = self.list_assets.selectedItems()[0]
        asset_name = asset_item.data(QtCore.Qt.UserRole)['name']
        
        try:
            cmds.file(path, reference=True, namespace=asset_name, returnNewNodes=True)
            print(f"Referenced Asset: {asset_name}")
        except Exception as e:
            print(f"Error referencing asset: {e}")

    def import_shot_task_file(self):
        item = self.list_shot_files.currentItem()
        if not item: return
        
        path = item.data(QtCore.Qt.UserRole)
        if not path or not os.path.exists(path): return 
        
        name = item.text().split('.')[0]
        
        try:
            cmds.file(path, reference=True, namespace=name, returnNewNodes=True)
            print(f"Referenced File: {name}")
        except Exception as e:
            print(f"Error loading file: {e}")

#ENTRY POINT
def show_orion_maya():
    workspace_control_name = "OrionMayaWindowWorkspaceControl"
    
    if cmds.workspaceControl(workspace_control_name, exists=True):
        cmds.deleteUI(workspace_control_name, control=True)
    elif cmds.window("OrionMayaWindow", exists=True):
        cmds.deleteUI("OrionMayaWindow", window=True)
    
    global orion_maya_window
    orion_maya_window = OrionMayaUI()
    orion_maya_window.show(dockable=True, floating=True)

#run
show_orion_maya()