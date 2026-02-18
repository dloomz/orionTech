import sys
import os
import subprocess
import traceback
import nuke

# --- CONFIGURATION ---
libs_path = r"P:\all_work\studentGroups\ORION_CORPORATION\60_config\libs"
PIPELINE_ROOT = r"P:\all_work\studentGroups\ORION_CORPORATION\00_pipeline\orionTech"
EVENT_SCRIPT_DIR = os.path.join(PIPELINE_ROOT, "deadline", "nuke")
STARTUP_PATH = os.path.join(PIPELINE_ROOT, "startup")

# --- PATH SETUP ---
if libs_path not in sys.path:
    sys.path.insert(0, libs_path)

if PIPELINE_ROOT not in sys.path:
    sys.path.append(PIPELINE_ROOT)

# --- QT COMPATIBILITY WRAPPER (PySide6 / PySide2) ---
try:
    from PySide6 import QtWidgets, QtCore, QtGui
    QT_VERSION = 6
except ImportError:
    try:
        from PySide2 import QtWidgets, QtCore, QtGui
        QT_VERSION = 2
    except ImportError:
        nuke.message("Could not import PySide6 or PySide2.\nThis script requires Nuke 11+.")
        raise

# --- ORION IMPORTS ---
try:
    from core.orionUtils import OrionUtils
except ImportError:
    print("OrionUtils not found. Shot Context features will be disabled.")
    OrionUtils = None

# --- DEADLINE HELPERS ---
def get_deadline_command():
    forced_path = r"C:\Program Files\Thinkbox\Deadline10\bin\deadlinecommand.exe"
    if os.path.exists(forced_path):
        return forced_path
    return "deadlinecommand"

def call_deadline_command(arguments, hide_window=True):
    deadline_cmd = get_deadline_command()
    startupinfo = None
    if hide_window and os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    try:
        proc = subprocess.Popen([deadline_cmd] + arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo, universal_newlines=True)
        output, errors = proc.communicate()
        return output.strip()
    except Exception as e:
        return f"Error: {e}"

# --- UI CLASS ---
class OrionNukeSubmitter(QtWidgets.QDialog):
    def __init__(self, parent=None):
        if not parent:
            parent = QtWidgets.QApplication.activeWindow()
        super(OrionNukeSubmitter, self).__init__(parent)
        
        self.setWindowTitle("Orion Nuke Submitter")
        self.setMinimumWidth(500)
        
        # Stylesheet (Matches Houdini)
        self.setStyleSheet("""
            QDialog { background-color: #333; color: #ddd; }
            QLabel { color: #ddd; font-weight: bold; }
            QLineEdit, QComboBox, QSpinBox { background-color: #444; color: #fff; border: 1px solid #555; padding: 5px; border-radius: 3px; }
            QPushButton { background-color: #d35400; color: white; font-weight: bold; padding: 8px; border-radius: 4px; }
            QPushButton:hover { background-color: #e67e22; }
            QCheckBox { color: #ddd; }
        """)

        self.orion = OrionUtils() if OrionUtils else None
        self.init_ui()
        self.populate_defaults()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # Job Details
        gb_job = QtWidgets.QGroupBox("Job Details")
        form_job = QtWidgets.QFormLayout(gb_job)
        
        self.le_name = QtWidgets.QLineEdit()
        self.le_comment = QtWidgets.QLineEdit()
        self.le_dept = QtWidgets.QLineEdit("Comp")
        
        form_job.addRow("Job Name:", self.le_name)
        form_job.addRow("Comment:", self.le_comment)
        form_job.addRow("Department:", self.le_dept)
        layout.addWidget(gb_job)

        # Shot Context
        gb_context = QtWidgets.QGroupBox("Shot Context")
        form_context = QtWidgets.QFormLayout(gb_context)
        
        self.cb_shot = QtWidgets.QComboBox()
        self.cb_shot.setToolTip("Overrides the ORI_SHOT_CONTEXT for the render job.")
        
        if self.orion:
            self.load_shots()
        else:
            self.cb_shot.addItem("OrionUtils Not Found")
            self.cb_shot.setEnabled(False)
            
        form_context.addRow("Select Shot:", self.cb_shot)
        layout.addWidget(gb_context)

        # Deadline Settings
        gb_deadline = QtWidgets.QGroupBox("Deadline Settings")
        form_deadline = QtWidgets.QFormLayout(gb_deadline)
        
        self.cb_pool = QtWidgets.QComboBox()
        self.cb_group = QtWidgets.QComboBox()
        self.sb_priority = QtWidgets.QSpinBox()
        self.sb_priority.setRange(0, 100)
        self.sb_priority.setValue(50)
        
        form_deadline.addRow("Pool:", self.cb_pool)
        form_deadline.addRow("Group:", self.cb_group)
        form_deadline.addRow("Priority:", self.sb_priority)
        layout.addWidget(gb_deadline)

        # Render Settings
        gb_render = QtWidgets.QGroupBox("Render Settings")
        form_render = QtWidgets.QFormLayout(gb_render)
        
        self.cb_node = QtWidgets.QComboBox()
        self.refresh_nodes() 
        
        self.le_frames = QtWidgets.QLineEdit()
        self.le_frames.setPlaceholderText("e.g. 1001-1050")
        
        self.sb_chunk = QtWidgets.QSpinBox()
        self.sb_chunk.setValue(5)
        self.sb_chunk.setMinimum(1)
        
        self.chk_nukex = QtWidgets.QCheckBox("Use NukeX License")
        # Fix: nuke.env.get requires string default
        nukex_env = nuke.env.get('nukex', '0')
        self.chk_nukex.setChecked(bool(int(nukex_env)))

        form_render.addRow("Write Node:", self.cb_node)
        form_render.addRow("Frame Range:", self.le_frames)
        form_render.addRow("Frames Per Task:", self.sb_chunk)
        form_render.addRow("", self.chk_nukex)
        layout.addWidget(gb_render)

        # Options
        self.chk_discord = QtWidgets.QCheckBox("Send Discord Notifications")
        self.chk_discord.setChecked(True)
        self.chk_submit_scene = QtWidgets.QCheckBox("Submit Scene File")
        self.chk_submit_scene.setChecked(True)
        
        layout.addWidget(self.chk_discord)
        layout.addWidget(self.chk_submit_scene)

        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        self.btn_submit = QtWidgets.QPushButton("Submit to Deadline")
        self.btn_submit.clicked.connect(self.submit_job)
        self.btn_refresh = QtWidgets.QPushButton("Refresh Nodes")
        self.btn_refresh.clicked.connect(self.refresh_nodes)
        
        btn_layout.addWidget(self.btn_refresh)
        btn_layout.addWidget(self.btn_submit)
        layout.addLayout(btn_layout)

    def load_shots(self):
        try:
            shots = self.orion.get_all_shots()
            self.cb_shot.addItem("Current Context (Do Not Override)", None)
            
            current_code = None
            script_name = os.path.basename(nuke.root().name())
            parts = script_name.split("_")
            if len(parts) > 1 and parts[0] == "stc":
                current_code = f"{parts[0]}_{parts[1]}"

            for shot in shots:
                code = shot['code'] if isinstance(shot, dict) else shot[1] 
                shot_id = shot['id'] if isinstance(shot, dict) else shot[0]
                self.cb_shot.addItem(f"{code}", shot_id)
                
                if current_code and code == current_code:
                    self.cb_shot.setCurrentText(code)
        except Exception as e:
            print(f"Error loading shots: {e}")

    def populate_defaults(self):
        start = int(nuke.root().firstFrame())
        end = int(nuke.root().lastFrame())
        self.le_frames.setText(f"{start}-{end}")
        
        script_name = os.path.basename(nuke.root().name())
        if script_name == "Root": script_name = "Untitled"
        self.le_name.setText(script_name)

        try:
            pools = call_deadline_command(["-pools"]).split('\n')
            groups = call_deadline_command(["-groups"]).split('\n')
            self.cb_pool.addItems([p for p in pools if p])
            self.cb_group.addItems([g for g in groups if g])
            
            if "none" in [self.cb_pool.itemText(i) for i in range(self.cb_pool.count())]:
                self.cb_pool.setCurrentText("none")
            if "none" in [self.cb_group.itemText(i) for i in range(self.cb_group.count())]:
                self.cb_group.setCurrentText("none")
        except:
            pass

    def refresh_nodes(self):
        self.cb_node.clear()
        found_nodes = []
        try:
            writes = nuke.allNodes("Write")
            deep_writes = nuke.allNodes("DeepWrite")
            for node in writes + deep_writes:
                found_nodes.append(node.name())
        except Exception as e:
            pass
        found_nodes.sort()
        self.cb_node.addItems(found_nodes)

    def submit_job(self):
        node_name = self.cb_node.currentText()
        if not node_name:
            nuke.message("Please select a Write Node.")
            return
        
        if nuke.root().name() == "Root":
             nuke.message("Please save the Script before submitting.")
             return
             
        if nuke.root().modified():
            if nuke.ask("Script has modified changes. Save now?"):
                nuke.scriptSave()

        job_name = self.le_name.text()
        comment = self.le_comment.text()
        dept = self.le_dept.text()
        pool = self.cb_pool.currentText()
        group = self.cb_group.currentText()
        priority = self.sb_priority.value()
        frames = self.le_frames.text()
        chunk_size = self.sb_chunk.value()
        submit_scene = self.chk_submit_scene.isChecked()
        use_discord = self.chk_discord.isChecked()
        use_nukex = self.chk_nukex.isChecked()
        
        selected_shot_id = self.cb_shot.currentData()
        selected_shot_code = self.cb_shot.currentText()
        
        orion_ocio = r"\\monster\projects\all_work\studentGroups\ORION_CORPORATION\60_config\colorManagement\aces_1.2\config.ocio"

        tmp_dir = os.path.join(os.getenv("TEMP"), "orion_submission")
        if not os.path.exists(tmp_dir): os.makedirs(tmp_dir)
        
        job_info_path = os.path.join(tmp_dir, "nuke_job_info.job")
        plugin_info_path = os.path.join(tmp_dir, "nuke_plugin_info.job")

        with open(job_info_path, "w") as f:
            f.write(f"Plugin=Nuke\n")
            f.write(f"Name={job_name}\n")
            f.write(f"Comment={comment}\n")
            f.write(f"Department={dept}\n")
            f.write(f"Pool={pool}\n")
            f.write(f"Group={group}\n")
            f.write(f"Priority={priority}\n")
            f.write(f"Frames={frames}\n")
            f.write(f"ChunkSize={chunk_size}\n")
            f.write(f"UserName={os.getenv('USERNAME')}\n")
            
            env_idx = 0
            f.write(f"EnvironmentKeyValue{env_idx}=PYTHONPATH={STARTUP_PATH}\n"); env_idx+=1
            f.write(f"EnvironmentKeyValue{env_idx}=OCIO={orion_ocio}\n"); env_idx+=1
            
            if selected_shot_id:
                f.write(f"EnvironmentKeyValue{env_idx}=SHOT={selected_shot_code}\n"); env_idx+=1
                f.write(f"EnvironmentKeyValue{env_idx}=SHOT_ID={selected_shot_id}\n"); env_idx+=1
                f.write(f"EnvironmentKeyValue{env_idx}=SEQ={selected_shot_code.split('_')[0]}\n"); env_idx+=1

            if use_discord:
                on_job_start = os.path.join(EVENT_SCRIPT_DIR, "orion_nuke_on_job_start.py").replace("\\", "/")
                on_job_finish = os.path.join(EVENT_SCRIPT_DIR, "orion_nuke_on_job_finish.py").replace("\\", "/")
                on_job_fail = os.path.join(EVENT_SCRIPT_DIR, "orion_nuke_on_job_fail.py").replace("\\", "/")
                
                f.write(f"PreJobScript={on_job_start}\n")
                f.write(f"PostJobScript={on_job_finish}\n")
                f.write(f"ExtraInfoKeyValue0=OnJobFailureScript={on_job_fail}\n") 
                f.write(f"ExtraInfoKeyValue1=OrionDiscordNotify=True\n")
            else:
                f.write(f"ExtraInfoKeyValue1=OrionDiscordNotify=False\n")

        with open(plugin_info_path, "w") as f:
            if not submit_scene:
                f.write(f"SceneFile={nuke.root().name()}\n")
            
            f.write(f"WriteNode={node_name}\n")
            
            version = f"{nuke.env['NukeVersionMajor']}.{nuke.env['NukeVersionMinor']}"
            f.write(f"Version={version}\n")
            f.write(f"NukeX={use_nukex}\n")
            f.write("Threads=0\n")

        args = [job_info_path, plugin_info_path]
        if submit_scene:
            args.append(nuke.root().name())
            
        result = call_deadline_command(args, hide_window=False)
        nuke.message("Submission Result:\n\n" + result)

# --- EXECUTION HANDLERS ---
def show_submitter():
    # keep reference to avoid garbage collection
    global orion_nuke_dialog 
    orion_nuke_dialog = OrionNukeSubmitter()
    orion_nuke_dialog.show()

def add_orion_menu():
    """Adds the Orion Submitter to the Nuke Render menu."""
    try:
        mainMenu = nuke.menu("Nuke")
        if mainMenu:
            orionMenu = mainMenu.addMenu("ORION")
            # Changed the callback from 'submit_to_orion_deadline' to 'show_submitter'
            orionMenu.addCommand("Render/Submit to Deadline", show_submitter)
        else:
            # fallback
            mainMenu.addCommand("Orion/Submit Nuke to Deadline", show_submitter)
        print("Orion Nuke Submitter added to Render menu.")
    except Exception as e:
        print(f"Failed to add Orion menu item: {e}")
