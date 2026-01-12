import sys
import os
import hou
from PySide2 import QtWidgets, QtCore, QtGui

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
    hou.ui.displayMessage("Could not import OrionUtils. Check sys.path.")

class OrionHoudiniUI(QtWidgets.QWidget):
    def __init__(self):
        super(OrionHoudiniUI, self).__init__()
        
        if 'OrionUtils' in globals():
            self.orion = OrionUtils()
            self.root_dir = self.orion.get_root_dir()
        else:
            self.orion = None
            self.root_dir = ""

        self.current_shot = None
        
        self.init_ui()
        
        if self.orion:
            self.populate_shots()
            
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
            QWidget { background-color: #2b2b2b; color: #dddddd; font-family: Segoe UI; }
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

        header_layout = QtWidgets.QHBoxLayout()
        logo_label = QtWidgets.QLabel("ORION<b>HOUDINI</b>")
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

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setStyleSheet("QTabWidget::pane { border: 0; }")
        
        #TABS 
        self.tab_scene = QtWidgets.QWidget()
        self.build_scene_tab()
        self.tabs.addTab(self.tab_scene, "Scene Setup")
        
        self.tab_assets = QtWidgets.QWidget()
        self.build_assets_tab()
        self.tabs.addTab(self.tab_assets, "Assets")
        
        self.tab_shot_tasks = QtWidgets.QWidget()
        self.build_shot_tasks_tab()
        self.tabs.addTab(self.tab_shot_tasks, "Shot Tasks")

        self.main_layout.addWidget(self.tabs)

    def build_scene_tab(self):
        layout = QtWidgets.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignTop)
        
        btn_cam = QtWidgets.QPushButton("Load Shot Camera (Sublayer)")
        btn_cam.setStyleSheet("background-color: #336699;")
        btn_cam.clicked.connect(self.import_camera)
        layout.addWidget(btn_cam)
        
        btn_plate = QtWidgets.QPushButton("Load Plate (Background Plate)")
        btn_plate.setStyleSheet("background-color: #996633;")
        btn_plate.clicked.connect(self.import_plate)
        layout.addWidget(btn_plate)

        btn_hdri = QtWidgets.QPushButton("Load HDRI (Dome Light)")
        btn_hdri.clicked.connect(self.import_hdri)
        layout.addWidget(btn_hdri)
        
        self.tab_scene.setLayout(layout)

    def build_assets_tab(self):
        layout = QtWidgets.QVBoxLayout()
        
        #search bar
        self.input_search = QtWidgets.QLineEdit()
        self.input_search.setPlaceholderText("Search Assets...")
        self.input_search.textChanged.connect(self.filter_assets)
        layout.addWidget(self.input_search)
        
        #splitter (asset list | task tree | file list)
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        
        #pane 1: asset list
        self.list_assets = QtWidgets.QListWidget()
        self.list_assets.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.list_assets.itemClicked.connect(self.on_asset_clicked) 
        splitter.addWidget(self.list_assets)
        
        #pane 2: task tree
        self.tree_asset_tasks = QtWidgets.QTreeWidget()
        self.tree_asset_tasks.setHeaderLabel("Asset Tasks")
        self.tree_asset_tasks.itemClicked.connect(self.on_asset_task_clicked)
        splitter.addWidget(self.tree_asset_tasks)
        
        #pane 3: file n action
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
        
        btn_load = QtWidgets.QPushButton("Sublayer File")
        btn_load.clicked.connect(self.import_shot_task_file)
        right_layout.addWidget(btn_load)
        
        splitter.addWidget(right_widget)
        splitter.setSizes([150, 300])
        
        layout.addWidget(splitter)
        self.tab_shot_tasks.setLayout(layout)

    #helpers
    
    def get_stage(self):

        stage = hou.node("/stage")
        
        if not stage:
            stage = hou.node("/").createNode("stage", "stage")
        return stage

    def connect_node(self, node):

        selected = hou.selectedNodes()
        if selected and selected[0].parent() == node.parent():
            #connect to the output of the selected node
            node.setInput(0, selected[0])
            #move new node below
            node.moveToGoodPosition()
        else:
            node.moveToGoodPosition()
        
        #select the new node
        node.setSelected(True, clear_all_selected=True)
        node.setDisplayFlag(True)

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
                    if f.endswith((".abc", ".usd", ".usdc", ".bgeo.sc", ".obj", ".fbx")):
                        full_path = os.path.join(root, f)
                        found_files.append((f, full_path))
        
        if not found_files:
            files = [f for f in os.listdir(task_path) if f.endswith((".abc", ".usd", ".usdc", ".bgeo.sc", ".obj"))]
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
        shot_start = int(data['frame_start'])
        shot_end = int(data['frame_end'])
        
        global_start = 981
        global_end = shot_end + 20
        playback_start = shot_start
        playback_end = shot_end + 20
        
        orion_orange = hou.Color((1.0, 0.376, 0.0))
        bm_name = "Orion Range"
        bm_start = 1011
        bm_end = shot_end + 10

        try:
            for b in hou.anim.bookmarks():
                if b.name() == bm_name:
                    try: hou.anim.removeBookmark(b)
                    except: pass
            
            bookmark = hou.anim.newBookmark(bm_name, bm_start, bm_end)
            bookmark.setColor(orion_orange)
            bookmark.setSelected(True)
        except: pass

        self.lbl_shot_info.setText(f"Shot Range: {shot_start} - {shot_end}")
        hou.playbar.setFrameRange(global_start, global_end)
        hou.playbar.setPlaybackRange(playback_start, playback_end)
        hou.setFrame(playback_start)
        
        self.populate_shot_tree()

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
                    if f.endswith((".abc", ".usd", ".usdc", ".bgeo.sc", ".obj", ".fbx")):
                        full_path = os.path.join(root, f)
                        found_files.append((f, full_path))
        
        if not found_files:
            self.list_shot_files.addItem("No published files found.")
            return

        for name, path in found_files:
            item = QtWidgets.QListWidgetItem(name)
            item.setData(QtCore.Qt.UserRole, path)
            self.list_shot_files.addItem(item)

    #LOP IMPORTERS

    def import_camera(self):
        if not self.current_shot:
            hou.ui.displayMessage("Please select a shot first.")
            return

        shot_code = self.current_shot['code']
        cam_path = os.path.join(self.root_dir, "40_shots", shot_code, "CAMERA", "PUBLISHED")
        
        found = None
        if os.path.exists(cam_path):
            candidates = [f for f in os.listdir(cam_path) if f.endswith(".abc") or f.endswith(".usd")]
            candidates.sort()
            if candidates:
                found = os.path.join(cam_path, candidates[-1])
        
        if found:
            stage = self.get_stage()
            #use sublayer for shot camera to bring in the opinion
            lop = stage.createNode("sublayer", node_name=f"cam_{shot_code}")
            lop.parm("filepath1").set(found)
            
            self.connect_node(lop)
            hou.ui.displayMessage(f"Camera Sublayered: {os.path.basename(found)}")
        else:
            hou.ui.displayMessage(f"No camera files found in: {cam_path}")

    def import_plate(self):
        if not self.current_shot: return
        shot_code = self.current_shot['code']
        plate_root = os.path.join(self.root_dir, "40_shots", shot_code, "COMP", "Plates", "Offline")
        
        if not os.path.exists(plate_root):
            hou.ui.displayMessage("Plate folder not found.")
            return

        found_seq = None
        for item in os.listdir(plate_root):

            if item.lower().endswith((".exr", ".jpg", ".png", ".tif", ".tiff")):
                found_seq = os.path.join(plate_root, item)
                break
        
        if found_seq:
            stage = self.get_stage()
            lop = stage.createNode("backgroundplate", node_name=f"plate_{shot_code}")
            
            import re
            match = re.search(r"(\d+)(\.[a-zA-Z]+)$", found_seq)
            if match:
                padding = len(match.group(1))
                path_stub = found_seq[:match.start(1)] + f"$F{padding}" + match.group(2)
                final_path = path_stub
            else:
                final_path = found_seq
            
            #PARAMETER 
            parm = lop.parm("plate")
            if not parm:
                #fallback
                for p_name in ["imagepath", "picture", "file", "texturepath"]:
                    if lop.parm(p_name):
                        parm = lop.parm(p_name)
                        break
            
            if parm:
                parm.set(final_path)
                self.connect_node(lop)
                hou.ui.displayMessage("Plate loaded in /stage.")
            else:
                #debug 
                all_parms = [p.name() for p in lop.parms()]
                print(f"Error: Could not find plate parameter. Available parameters: {all_parms}")
                hou.ui.displayMessage("Error: Could not set plate path. Check console for details.")
                
        else:
            hou.ui.displayMessage("No image sequences found in Source.")

    def import_hdri(self):
        start_path = os.path.join(self.root_dir, "25_footage", "hdri", "HDRI")
        path = hou.ui.selectFile(start_directory=start_path, title="Select HDRI", pattern="*.exr *.hdr")
        if path:
            stage = self.get_stage()
            lop = stage.createNode("domelight", node_name="dome_light")
            lop.parm("texturefile").set(path)
            
            self.connect_node(lop)

    def import_selected_asset_file(self):
        item = self.list_asset_files.currentItem()
        if not item: return
        
        path = item.data(QtCore.Qt.UserRole)
        if not path or not os.path.exists(path): return

        asset_item = self.list_assets.selectedItems()[0]
        asset_name = asset_item.data(QtCore.Qt.UserRole)['name']
        
        #ASSETS = REFERENCE LOP
        stage = self.get_stage()
        lop = stage.createNode("reference", node_name=asset_name)
        lop.parm("filepath1").set(path)
        #default prim path 
        lop.parm("primpath").set(f"/ASSETS/{asset_name}")
        
        self.connect_node(lop)
        hou.ui.displayMessage(f"Asset Referenced: {asset_name}")

    def import_shot_task_file(self):
        item = self.list_shot_files.currentItem()
        if not item: return
        
        path = item.data(QtCore.Qt.UserRole)
        if not path or not os.path.exists(path): return 
        
        name = item.text().split('.')[0]
        
        #SHOT TASKS 
        stage = self.get_stage()
        lop = stage.createNode("sublayer", node_name=name)
        lop.parm("filepath1").set(path)
        
        self.connect_node(lop)
        hou.ui.displayMessage(f"Shot Layer Sublayered: {name}")

def onCreateInterface():
    return OrionHoudiniUI()