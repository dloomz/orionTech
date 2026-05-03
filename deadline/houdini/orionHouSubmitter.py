import sys
import os
import subprocess
import traceback
import json
import hou
import tempfile
from PySide2 import QtWidgets, QtCore, QtGui

#CONFIGURATION
PIPELINE_ROOT = r"P:\all_work\studentGroups\ORION_CORPORATION\00_pipeline\orionTech"
EVENT_SCRIPT_DIR = os.path.join(PIPELINE_ROOT, "deadline", "houdini")
STARTUP_PATH = os.path.join(PIPELINE_ROOT)
ORI_SHOT_CONTEXT = os.getenv("ORI_SHOT_CONTEXT")

if PIPELINE_ROOT not in sys.path:
    sys.path.append(PIPELINE_ROOT)

try:
    from core.orionUtils import OrionUtils
except ImportError:
    print("OrionUtils not found. Shot Context features will be disabled.")
    OrionUtils = None

#DEADLINE HELPERS
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

#UI CLASS
class OrionHoudiniSubmitter(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(OrionHoudiniSubmitter, self).__init__(parent)
        self.setWindowTitle("Orion Houdini Submitter")
        self.setMinimumWidth(600)
        self.setMinimumHeight(700)
        self.setStyleSheet("""
            QDialog { background-color: #333; color: #ddd; font-family: Segoe UI; }
            QGroupBox { border: 1px solid #555; border-radius: 5px; margin-top: 10px; font-weight: bold; padding-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #FF6000; }
            QLabel { color: #ddd; }
            QLineEdit, QComboBox, QSpinBox { background-color: #444; color: #fff; border: 1px solid #555; padding: 5px; border-radius: 3px; }
            QListWidget { background-color: #222; border: 1px solid #555; color: #fff; }
            QListWidget::item:selected { background-color: #FF6000; color: white; }
            QPushButton { background-color: #444; color: white; border-radius: 4px; padding: 6px; }
            QPushButton:hover { background-color: #555; }
            QCheckBox { color: #ddd; }
        """)

        self.orion = OrionUtils() if OrionUtils else None
        
        #Original context 
        self.original_context = os.getenv("ORI_SHOT_CONTEXT")
        
        self.init_ui()
        self.populate_defaults()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        #Job Details
        gb_job = QtWidgets.QGroupBox("Job Details")
        form_job = QtWidgets.QFormLayout(gb_job)
        
        self.le_name = QtWidgets.QLineEdit()
        self.le_comment = QtWidgets.QLineEdit()
        self.le_dept = QtWidgets.QLineEdit()
        
        form_job.addRow("Job Name:", self.le_name)
        form_job.addRow("Comment:", self.le_comment)
        form_job.addRow("Department:", self.le_dept)
        layout.addWidget(gb_job)

        #Shot Context
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
        
        #Trigger update_local_context whenever the dropdown changes
        self.cb_shot.currentIndexChanged.connect(self.update_local_context)

        #Deadline Settings
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

        #Render Nodes
        gb_rops = QtWidgets.QGroupBox("Render Nodes")
        rop_layout = QtWidgets.QVBoxLayout(gb_rops)

        self.list_rops = QtWidgets.QListWidget()
        self.list_rops.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.list_rops.setAlternatingRowColors(True)
        rop_layout.addWidget(self.list_rops)

        btn_rop_actions = QtWidgets.QHBoxLayout()
        self.btn_sel_scene = QtWidgets.QPushButton("Select from Scene Selection")
        self.btn_sel_scene.clicked.connect(self.select_rops_from_scene)
        self.btn_refresh = QtWidgets.QPushButton("Refresh ROPs")
        self.btn_refresh.clicked.connect(self.refresh_rops)
        
        btn_rop_actions.addWidget(self.btn_sel_scene)
        btn_rop_actions.addWidget(self.btn_refresh)
        rop_layout.addLayout(btn_rop_actions)
        
        layout.addWidget(gb_rops)

        #FrameRange
        gb_frames = QtWidgets.QGroupBox("Frame Range")
        frame_layout = QtWidgets.QHBoxLayout(gb_frames)
        
        self.sb_start = QtWidgets.QSpinBox()
        self.sb_start.setRange(-100000, 100000)
        self.sb_start.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        
        self.sb_end = QtWidgets.QSpinBox()
        self.sb_end.setRange(-100000, 100000)
        self.sb_end.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        
        self.sb_step = QtWidgets.QSpinBox()
        self.sb_step.setRange(1, 1000)
        self.sb_step.setValue(1)

        frame_layout.addWidget(QtWidgets.QLabel("Start:"))
        frame_layout.addWidget(self.sb_start)
        frame_layout.addWidget(QtWidgets.QLabel("End:"))
        frame_layout.addWidget(self.sb_end)
        frame_layout.addWidget(QtWidgets.QLabel("Step:"))
        frame_layout.addWidget(self.sb_step)
        
        layout.addWidget(gb_frames)
        
        #Chunk Size
        chunk_layout = QtWidgets.QHBoxLayout()
        chunk_layout.addWidget(QtWidgets.QLabel("Frames Per Task (Chunk Size):"))
        self.sb_chunk = QtWidgets.QSpinBox()
        self.sb_chunk.setRange(1, 1000)
        self.sb_chunk.setValue(1)
        chunk_layout.addWidget(self.sb_chunk)
        chunk_layout.addStretch()
        layout.addLayout(chunk_layout)

        #Options
        self.chk_discord = QtWidgets.QCheckBox("Send Discord Notifications")
        self.chk_discord.setChecked(True)
        self.chk_submit_scene = QtWidgets.QCheckBox("Submit Scene File")
        self.chk_submit_scene.setChecked(False)
        self.chk_batch = QtWidgets.QCheckBox("Group Jobs in Deadline (Batch Name)")
        self.chk_batch.setChecked(True)
        
        layout.addWidget(self.chk_discord)
        layout.addWidget(self.chk_submit_scene)
        layout.addWidget(self.chk_batch)

        #Submit Button
        self.btn_submit = QtWidgets.QPushButton("SUBMIT TO DEADLINE")
        self.btn_submit.setStyleSheet("background-color: #d35400; font-weight: bold; font-size: 14px; padding: 10px;")
        self.btn_submit.clicked.connect(self.submit_job)
        layout.addWidget(self.btn_submit)
        
        #Initial Population
        self.refresh_rops()

    def get_next_version(self, task_path):
        #Return v001 if the base directory doesnt exist yet
        if not os.path.exists(task_path): 
            return "v001"

        max_ver = 0

        #Scan directory for existing folders that start with v
        for item in os.listdir(task_path):
            full_path = os.path.join(task_path, item)
            if item.startswith("v") and os.path.isdir(full_path):
                try:
                    #Slice off the v and convert the rest to an integer
                    num = int(item[1:])
                    if num > max_ver: 
                        max_ver = num
                except ValueError:
                    #Skip folders like vTest where conversion to int fails
                    pass

        #Format the highest number + 1 with leading zeros
        return f"v{max_ver + 1:03d}"

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
        #Frame Range
        start = int(hou.playbar.playbackRange()[0])
        end = int(hou.playbar.frameRange()[1])
        self.sb_start.setValue(start)
        self.sb_end.setValue(end)
        
        #Job Name
        raw_name = hou.hipFile.basename()
        clean_name = os.path.splitext(raw_name)[0]
        self.le_name.setText(clean_name)

        #Pools and Groups
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
        
    def update_local_context(self, index):
        #Data and text from the currently selected item
        selected_shot_id = self.cb_shot.itemData(index)
        selected_shot_code = self.cb_shot.itemText(index)
        
        #If specific shot was selected
        if selected_shot_id:
            new_context = selected_shot_code
        else:
            #If no ID Current Context item was selected so revert
            new_context = self.original_context
            
        if new_context:
            #Update the Python environment variable
            os.environ["ORI_SHOT_CONTEXT"] = new_context
            
            #Update Houdinis internal variable so nodes evaluate it properly
            hou.putenv("ORI_SHOT_CONTEXT", new_context)
            
            print(f"Updated local Houdini Context to: {new_context}")

    def refresh_rops(self):
        self.list_rops.clear()
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

        found_nodes.sort()
        self.list_rops.addItems(found_nodes)

    def select_rops_from_scene(self):
        selected = hou.selectedNodes()
        if not selected: return
        
        #Deselect all first
        for i in range(self.list_rops.count()):
            self.list_rops.item(i).setSelected(False)
            
        found_any = False
        for node in selected:
            path = node.path()
            #Find item in list
            items = self.list_rops.findItems(path, QtCore.Qt.MatchExactly)
            if items:
                items[0].setSelected(True)
                found_any = True
        
        if not found_any:
            hou.ui.displayMessage("No supported ROPs found in current selection.")

    def submit_job(self):
        selected_items = self.list_rops.selectedItems()
        if not selected_items:
            hou.ui.displayMessage("Please select at least one Render Node from the list.")
            return
        
        if not hou.hipFile.path() or hou.hipFile.path() == "untitled.hip":
             hou.ui.displayMessage("Please save the Scene before submitting.")
             return
             
        if hou.hipFile.hasUnsavedChanges():
            hou.hipFile.save()

        #Gather Common Data
        base_job_name = self.le_name.text()
        comment = self.le_comment.text()
        dept = self.le_dept.text()
        pool = self.cb_pool.currentText()
        group = self.cb_group.currentText()
        priority = self.sb_priority.value()
        
        start = self.sb_start.value()
        end = self.sb_end.value()
        step = self.sb_step.value()
        frames_str = f"{start}-{end}"
        if step > 1:
            frames_str += f"x{step}"

        chunk_size = self.sb_chunk.value()
        submit_scene = self.chk_submit_scene.isChecked()
        use_discord = self.chk_discord.isChecked()
        use_batch = self.chk_batch.isChecked()
        
        #Shot Context Logic
        active_context = os.getenv("ORI_SHOT_CONTEXT")
        selected_shot_id = self.cb_shot.currentData()
        selected_shot_code = self.cb_shot.currentText()
        
        if selected_shot_id:
            active_context = selected_shot_code

       #SUBMISSION LOOP
        submission_results = []
        
        for item in selected_items:
            rop_path = item.text()
            rop_node_name = rop_path.split("/")[-1]
            
            #Unique name 
            current_job_name = f"{base_job_name} - {rop_node_name}" if len(selected_items) > 1 else base_job_name

            #ctive_context python variable  into the path string
            raw_base_dir = f"P:/all_work/studentGroups/ORION_CORPORATION/40_shots/{active_context}/3D_RENDERS/CG/{rop_node_name}"
            
            #hou.text.expandString 
            expanded_base_dir = hou.text.expandString(raw_base_dir)
            
            #Calculate the next version for specific ROP
            next_version = self.get_next_version(expanded_base_dir)

            tmp_dir = os.path.join(os.getenv("TEMP"), "orion_submission")
            if not os.path.exists(tmp_dir): os.makedirs(tmp_dir)
            
            #Use unique filenames 
            safe_rop_name = rop_node_name.replace(" ", "_")
            job_info_path = os.path.join(tmp_dir, f"hou_job_{safe_rop_name}.job")
            plugin_info_path = os.path.join(tmp_dir, f"hou_plugin_{safe_rop_name}.job")

            #Write Job Info
            with open(job_info_path, "w") as f:
                f.write(f"Plugin=Houdini\n")
                f.write(f"Name={current_job_name}\n")
                if use_batch:
                    f.write(f"BatchName={base_job_name}\n")
                f.write(f"Comment={comment}\n")
                f.write(f"Department={dept}\n")
                f.write(f"Pool={pool}\n")
                f.write(f"Group={group}\n")
                f.write(f"Priority={priority}\n")
                f.write(f"Frames={frames_str}\n")
                f.write(f"ChunkSize={chunk_size}\n")
                f.write(f"UserName={os.getenv('USERNAME')}\n")
                
                env_idx = 0
                f.write(f"EnvironmentKeyValue{env_idx}=PYTHONPATH={STARTUP_PATH}\n"); env_idx+=1
                f.write(f"EnvironmentKeyValue{env_idx}=ORI_SHOT_CONTEXT={active_context}\n"); env_idx+=1
                
                
                f.write(f"EnvironmentKeyValue{env_idx}=ORI_RENDER_VERSION={next_version}\n"); env_idx+=1
                
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

            #Write Plugin Info
            with open(plugin_info_path, "w") as f:
                if not submit_scene:
                    f.write(f"SceneFile={hou.hipFile.path()}\n")
                
                f.write(f"OutputDriver={rop_path}\n")
                
                ver = hou.applicationVersion()
                safe_version = f"{ver[0]}.{ver[1]}"
                f.write(f"Version={safe_version}\n")
                f.write("IgnoreInputs=True\n")

            #Arguments
            args = [job_info_path, plugin_info_path]
            if submit_scene:
                args.append(hou.hipFile.path())
                
            #Submit
            result = call_deadline_command(args, hide_window=False)
            submission_results.append(f"<b>{rop_node_name} ({next_version}):</b><br>{result}<br>")

        #Report
        final_msg = "<br>".join(submission_results)
        hou.ui.displayMessage(f"Submission Complete for {len(selected_items)} Jobs.", details=final_msg)

def show_submitter():
    dialog = OrionHoudiniSubmitter(hou.qt.mainWindow())
    dialog.show()