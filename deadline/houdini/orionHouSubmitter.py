import sys
import os
import subprocess
import traceback
import json
import hou
import tempfile
from PySide2 import QtWidgets, QtCore, QtGui

#   CONFIGURATION  
PIPELINE_ROOT = r"P:\all_work\studentGroups\ORION_CORPORATION\00_pipeline\orionTech"
EVENT_SCRIPT_DIR = os.path.join(PIPELINE_ROOT, "deadline", "houdini")
STARTUP_PATH = os.path.join(PIPELINE_ROOT)

if PIPELINE_ROOT not in sys.path:
    sys.path.append(PIPELINE_ROOT)

try:
    from core.orionUtils import OrionUtils
except ImportError:
    print("OrionUtils not found. Shot Context features will be disabled.")
    OrionUtils = None

#   DEADLINE HELPERS  
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

#   UI CLASS  
class OrionHoudiniSubmitter(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(OrionHoudiniSubmitter, self).__init__(parent)
        self.setWindowTitle("Orion Houdini Submitter")
        self.setMinimumWidth(500)
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

        #   Job Details  
        gb_job = QtWidgets.QGroupBox("Job Details")
        form_job = QtWidgets.QFormLayout(gb_job)
        
        self.le_name = QtWidgets.QLineEdit()
        self.le_comment = QtWidgets.QLineEdit()
        self.le_dept = QtWidgets.QLineEdit("3D")
        
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
        
        self.cb_rop = QtWidgets.QComboBox()
        self.refresh_rops() # initial
        
        self.le_frames = QtWidgets.QLineEdit()
        self.le_frames.setPlaceholderText("e.g. 1001-1050")
        
        self.sb_chunk = QtWidgets.QSpinBox()
        self.sb_chunk.setValue(5)
        self.sb_chunk.setMinimum(1)
        
        form_render.addRow("Node:", self.cb_rop)
        form_render.addRow("Frame Range:", self.le_frames)
        form_render.addRow("Frames Per Task:", self.sb_chunk)
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
        self.btn_refresh.clicked.connect(self.refresh_rops)
        
        btn_layout.addWidget(self.btn_refresh)
        btn_layout.addWidget(self.btn_submit)
        layout.addLayout(btn_layout)

    def load_shots(self):
        try:
            shots = self.orion.get_all_shots()
            self.cb_shot.addItem("Current Context (Do Not Override)", None)
            
            current_code = None
            hip_name = hou.hipFile.basename()
            parts = hip_name.split("_")
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
        start = int(hou.playbar.frameRange()[0])
        end = int(hou.playbar.frameRange()[1])
        self.le_frames.setText(f"{start}-{end}")
        self.le_name.setText(os.path.basename(hou.hipFile.path()))

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

    def refresh_rops(self):
        self.cb_rop.clear()
        found_nodes = []
        
        try:
            all_nodes = hou.node("/").allSubChildren()
            
            for node in all_nodes:
                if isinstance(node, hou.RopNode):
                    if node.type().name() != "Deadline": 
                        found_nodes.append(node.path())
                
                elif isinstance(node, hou.LopNode):
                    if node.type().name() in ["karma", "karmacpu", "karmaxpu", "usdrender"]:
                        found_nodes.append(node.path())
                        
        except Exception as e:
            print(f"Error refreshing ROPs: {e}")
            pass

        found_nodes.sort()
        self.cb_rop.addItems(found_nodes)

    def submit_job(self):
        rop_path = self.cb_rop.currentText()
        if not rop_path:
            hou.ui.displayMessage("Please select a Render Node.")
            return
        
        if not hou.hipFile.path() or hou.hipFile.path() == "untitled.hip":
             hou.ui.displayMessage("Please save the Scene before submitting.")
             return
             
        if hou.hipFile.hasUnsavedChanges():
            hou.hipFile.save()

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
        
        selected_shot_id = self.cb_shot.currentData()
        selected_shot_code = self.cb_shot.currentText()

        tmp_dir = os.path.join(os.getenv("TEMP"), "orion_submission")
        if not os.path.exists(tmp_dir): os.makedirs(tmp_dir)
        
        job_info_path = os.path.join(tmp_dir, "houdini_job_info.job")
        plugin_info_path = os.path.join(tmp_dir, "houdini_plugin_info.job")

        with open(job_info_path, "w") as f:
            f.write(f"Plugin=Houdini\n")
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
            
            if selected_shot_id:
                f.write(f"EnvironmentKeyValue{env_idx}=SHOT={selected_shot_code}\n"); env_idx+=1
                f.write(f"EnvironmentKeyValue{env_idx}=SHOT_ID={selected_shot_id}\n"); env_idx+=1
                f.write(f"EnvironmentKeyValue{env_idx}=SEQ={selected_shot_code.split('_')[0]}\n"); env_idx+=1

            if use_discord:
                on_job_start = os.path.join(EVENT_SCRIPT_DIR, "orion_hou_on_job_start.py").replace("\\", "/")
                on_job_finish = os.path.join(EVENT_SCRIPT_DIR, "orion_hou_on_job_finish.py").replace("\\", "/")
                on_job_fail = os.path.join(EVENT_SCRIPT_DIR, "orion_hou_on_job_fail.py").replace("\\", "/")
                
                f.write(f"PreJobScript={on_job_start}\n")
                f.write(f"PostJobScript={on_job_finish}\n")
                f.write(f"ExtraInfoKeyValue0=OnJobFailureScript={on_job_fail}\n") 
                f.write(f"ExtraInfoKeyValue1=OrionDiscordNotify=True\n")
            else:
                f.write(f"ExtraInfoKeyValue1=OrionDiscordNotify=False\n")

        with open(plugin_info_path, "w") as f:
            if not submit_scene:
                f.write(f"SceneFile={hou.hipFile.path()}\n")
            
            f.write(f"OutputDriver={rop_path}\n")
            
            ver = hou.applicationVersion()
            safe_version = f"{ver[0]}.{ver[1]}" # 20.5
            f.write(f"Version={safe_version}\n")

            f.write("IgnoreInputs=True\n")

        args = [job_info_path, plugin_info_path]
        if submit_scene:
            args.append(hou.hipFile.path())
            
        result = call_deadline_command(args, hide_window=False)
        hou.ui.displayMessage("Submission Result:\n\n" + result)

def show_submitter():
    dialog = OrionHoudiniSubmitter(hou.qt.mainWindow())
    dialog.show()
    
