import os
import sys
import glob
import subprocess
import json
import maya.cmds as cmds
import maya.mel as mel
from datetime import datetime

#qt
try:
    from PySide2 import QtWidgets, QtCore, QtGui
except ImportError:
    try:
        from PySide6 import QtWidgets, QtCore, QtGui
    except ImportError:
        cmds.error("Could not load PySide QT modules.")

#import util
try:
    from core.orionUtils import OrionUtils
except ImportError:
    pipeline_path = os.environ.get("ORI_PIPELINE_PATH")
    if pipeline_path and pipeline_path not in sys.path:
        sys.path.append(pipeline_path)
    try:
        from core.orionUtils import OrionUtils
    except ImportError:
        print("OrionUtils not found. Discord notifications will be disabled.")
        OrionUtils = None

class OrionPlayblaster(QtWidgets.QWidget):

    WEBHOOK_URL = "https://discord.com/api/webhooks/1430360190037004518/HO2P_UE5CQ3f4PluRjv7W5neC5S08I-bPah8VOP1TgYhdUxisTCzbv337RPgWkO5jAS3"

    def __init__(self, parent=None):
        super(OrionPlayblaster, self).__init__(parent=parent, f=QtCore.Qt.WindowStaysOnTopHint)
        
        self.setWindowTitle("Orion Playblaster")
        self.resize(400, 560)
        
        #styling
        self.setStyleSheet("""
            QWidget { background-color: #2b2b2b; color: #dddddd; font-family: Segoe UI, Arial; font-size: 10pt; }
            
            QGroupBox { border: 1px solid #444; border-radius: 4px; margin-top: 10px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #eeeeee; }
            
            QPushButton { background-color: #444; border-radius: 3px; padding: 8px; font-weight: bold; }
            QPushButton:hover { background-color: #555; }
            QPushButton:pressed { background-color: #333; }
            QPushButton:disabled { background-color: #2a2a2a; color: #555; }
            
            /* Action Button Accent */
            QPushButton#ActionButton { background-color: #FF6000; color: #121212; }
            QPushButton#ActionButton:hover { background-color: #ff8533; color: white; }

            /* --- IMPROVED COMBO BOX STYLING --- */
            QComboBox { 
                background-color: #333; 
                border: 1px solid #555; 
                border-radius: 3px; 
                padding: 4px; 
                padding-right: 25px; /* Make room for arrow */
                color: #eee;
            }
            
            /* The Dropdown Button Area */
            QComboBox::drop-down { 
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 25px;
                border-left-width: 1px;
                border-left-color: #555;
                border-left-style: solid;
                border-top-right-radius: 3px; 
                border-bottom-right-radius: 3px;
                background-color: #404040; /* Slightly lighter to look like a button */
            }
            
            /* The Arrow (CSS Triangle) */
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #FF6000; /* Orion Orange Arrow */
                width: 0;
                height: 0;
                margin-right: 2px;
            }

            QComboBox QAbstractItemView { 
                background-color: #333; 
                color: #dddddd; 
                selection-background-color: #FF6000; 
                selection-color: #121212;
                border: 1px solid #555;
            }

            QLineEdit { background-color: #333; border: 1px solid #555; border-radius: 3px; padding: 4px; color: #eee; }
            
            QLabel { color: #ccc; }
            QLabel#Status { color: #FF6000; font-style: italic; font-size: 9pt; }
            
            QRadioButton { color: #ddd; spacing: 5px; }
            QRadioButton::indicator { width: 12px; height: 12px; }
            QRadioButton::indicator:checked { background-color: #FF6000; border: 2px solid #555; border-radius: 6px; }
            QRadioButton::indicator:unchecked { background-color: #444; border: 2px solid #555; border-radius: 6px; }
            
            QCheckBox { spacing: 5px; }
            QCheckBox::indicator { width: 14px; height: 14px; background-color: #333; border: 1px solid #555; border-radius: 3px; }
            QCheckBox::indicator:checked { background-color: #FF6000; border: 1px solid #FF6000; image: url(:/qt-project.org/styles/commonstyle/images/standardbutton-yes-16.png); }
            QCheckBox:disabled { color: #666; }
        """)

        #util
        self.orion = OrionUtils() if OrionUtils else None
        
        #context
        self.shot_context = os.environ.get("ORI_SHOT_CONTEXT", "No Shot Context")
        raw_shot_path = os.environ.get("ORI_SHOT_PATH", "")
        self.thread_id = os.environ.get("ORI_DISCORD_THREAD_ID", "")
        
        #path setup
        self.render_root = ""
        self.shot_path = ""
        self.ffmpeg_path = "ffmpeg" 

        if self.orion:
            project_root = self.orion.get_root_dir()
            if raw_shot_path:
                if not os.path.isabs(raw_shot_path):
                    self.shot_path = os.path.join(project_root, raw_shot_path)
                else:
                    self.shot_path = raw_shot_path
            
            shared_ffmpeg = os.path.join(project_root, "60_config", "libs", "ffmpeg.exe")
            if os.path.exists(shared_ffmpeg):
                self.ffmpeg_path = shared_ffmpeg
        else:
            self.shot_path = raw_shot_path

        if self.shot_path:
            self.render_root = os.path.join(self.shot_path, "3D_RENDERS", "ANIM")
        
        self.init_ui()
        self.populate_data()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setAlignment(QtCore.Qt.AlignTop)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        self.setLayout(main_layout)

        #header
        header_layout = QtWidgets.QHBoxLayout()
        logo_label = QtWidgets.QLabel("ORION<b>PLAYBLASTER</b>")
        logo_label.setTextFormat(QtCore.Qt.RichText)
        logo_label.setStyleSheet("font-size: 16px; color: #FF6000;")
        header_layout.addWidget(logo_label)
        
        lbl_shot = QtWidgets.QLabel(f" |  {self.shot_context}")
        lbl_shot.setStyleSheet("font-size: 14px; color: #888; font-weight: bold;")
        header_layout.addWidget(lbl_shot)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        #settings
        grp_settings = QtWidgets.QGroupBox("Publish Settings")
        form_layout = QtWidgets.QFormLayout()
        form_layout.setSpacing(10)
        form_layout.setContentsMargins(15, 20, 15, 15)

        #artist
        self.combo_artist = QtWidgets.QComboBox()
        self.combo_artist.setEditable(False)
        form_layout.addRow("Artist:", self.combo_artist)

        #task
        self.combo_task = QtWidgets.QComboBox()
        self.combo_task.setEditable(True) 
        self.combo_task.setPlaceholderText("Select or Type Task...")
        self.combo_task.currentIndexChanged.connect(self.update_version_label)
        self.combo_task.editTextChanged.connect(self.update_version_label)
        form_layout.addRow("Task:", self.combo_task)

        #version
        self.lbl_version = QtWidgets.QLabel("v001")
        self.lbl_version.setStyleSheet("color: #FF6000; font-weight: bold; font-size: 11pt;")
        form_layout.addRow("Next Version:", self.lbl_version)
        
        #selection
        scope_layout = QtWidgets.QHBoxLayout()
        self.radio_sel = QtWidgets.QRadioButton("Selected Only")
        self.radio_sel.setChecked(True)
        self.radio_sel.toggled.connect(self.toggle_slap_option)
        
        self.radio_all = QtWidgets.QRadioButton("All Objects")
        self.radio_all.toggled.connect(self.toggle_slap_option)
        
        scope_layout.addWidget(self.radio_sel)
        scope_layout.addWidget(self.radio_all)
        form_layout.addRow("Scope:", scope_layout)

        #slap comp
        self.chk_slap = QtWidgets.QCheckBox("Slap Comp (Overlay on Plate)")
        self.chk_slap.setStyleSheet("font-weight: bold; color: #ccc;")
        self.chk_slap.setToolTip("Finds plate in CAMERA/PLATES and composites playblast on top.")
        form_layout.addRow("", self.chk_slap)

        #msg input
        self.txt_message = QtWidgets.QLineEdit()
        self.txt_message.setPlaceholderText("Add a note (e.g. Fixed timing...)")
        form_layout.addRow("Note:", self.txt_message)

        grp_settings.setLayout(form_layout)
        main_layout.addWidget(grp_settings)

        main_layout.addSpacing(10)

        #button
        self.btn_blast = QtWidgets.QPushButton("PLAYBLAST")
        self.btn_blast.setObjectName("ActionButton")
        self.btn_blast.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_blast.clicked.connect(self.run_playblast)
        self.btn_blast.setMinimumHeight(45)
        main_layout.addWidget(self.btn_blast)

        #status
        self.lbl_status = QtWidgets.QLabel("Ready")
        self.lbl_status.setObjectName("Status")
        self.lbl_status.setAlignment(QtCore.Qt.AlignCenter)
        main_layout.addWidget(self.lbl_status)

        #checking for shot context
        if not self.shot_context or self.shot_context == "No Shot Context":
            self.btn_blast.setEnabled(False)
            self.btn_blast.setText("No Shot Context Found")
            self.set_status("Error: Environment variables missing")
        
        self.toggle_slap_option()

    def set_status(self, text):
        self.lbl_status.setText(text)
        QtWidgets.QApplication.processEvents()

    def toggle_slap_option(self):
        is_selected_mode = self.radio_sel.isChecked()
        self.chk_slap.setEnabled(is_selected_mode)
        if not is_selected_mode:
            self.chk_slap.setChecked(False)

    def populate_data(self):
        if self.orion:
            users = self.orion.get_usernames()
            if not users: users = ["Artist"]
            self.combo_artist.addItems(sorted(users))
            current_sys_user = os.environ.get("USERNAME", "").lower()
            index = -1
            for i in range(self.combo_artist.count()):
                if current_sys_user in self.combo_artist.itemText(i).lower():
                    index = i
                    break
            if index != -1: self.combo_artist.setCurrentIndex(index)
        else:
            self.combo_artist.addItem(os.environ.get("USERNAME", "Artist"))

        tasks = []
        if self.render_root and os.path.exists(self.render_root):
            try:
                for item in os.listdir(self.render_root):
                    if os.path.isdir(os.path.join(self.render_root, item)):
                        tasks.append(item)
            except Exception as e:
                print(f"Error reading tasks: {e}")
        
        if not tasks: tasks = ["BLOCKING", "LAYOUT", "POLISH"]
        self.combo_task.clear()
        self.combo_task.addItems(sorted(tasks))
        
        index = self.combo_task.findText("BLOCKING")
        if index != -1: self.combo_task.setCurrentIndex(index)
        else: self.combo_task.setCurrentIndex(0)

    def get_task_path(self):
        task_name = self.combo_task.currentText()
        if not task_name: return None, None
        if not os.path.exists(self.render_root):
            try:
                os.makedirs(self.render_root)
            except OSError as e:
                cmds.warning(f"Could not create directory: {self.render_root}. Error: {e}")
                return None, None
        return os.path.join(self.render_root, task_name), task_name

    def get_next_version(self, task_path):
        if not os.path.exists(task_path): return "v001"
        max_ver = 0
        for item in os.listdir(task_path):
            if item.startswith("v") and os.path.isdir(os.path.join(task_path, item)):
                try:
                    num = int(item[1:])
                    if num > max_ver: max_ver = num
                except: pass
        return f"v{max_ver + 1:03d}"

    def update_version_label(self):
        path, _ = self.get_task_path()
        if path:
            ver = self.get_next_version(path)
            self.lbl_version.setText(ver)

    def find_plate_sequence(self):
        if not self.shot_path: return None
        plate_dir = os.path.join(self.shot_path, "CAMERA", "PLATES")
        if not os.path.exists(plate_dir): return None
        
        extensions = ["exr", "png", "jpg", "jpeg", "tif", "tiff"]
        found_file = None
        for item in os.listdir(plate_dir):
            if item.startswith("."): continue
            ext = item.split(".")[-1].lower()
            if ext in extensions:
                found_file = item
                break
        
        if not found_file: return None
        parts = found_file.split(".")
        if len(parts) < 3: return None

        base_name = ".".join(parts[:-2])
        ext = parts[-1]
        if not parts[-2].isdigit(): return None
        padding = len(parts[-2])
        pattern = f"{base_name}.%{0}{padding}d.{ext}"
        return os.path.join(plate_dir, pattern).replace("\\", "/")

    def run_playblast(self):
        #validity
        use_isolation = self.radio_sel.isChecked()
        do_slap_comp = self.chk_slap.isChecked() and use_isolation

        if use_isolation:
            self.set_status("Validating Selection...")
            selection = cmds.ls(sl=True)
            if not selection:
                cmds.warning("Nothing selected!")
                self.set_status("Error: Select objects first")
                return
        
        #path
        task_path, task_name = self.get_task_path()
        if not task_path: return
        
        version = self.get_next_version(task_path)
        output_dir = os.path.join(task_path, version)
        
        if not os.path.exists(output_dir):
            try: os.makedirs(output_dir)
            except OSError: return

        filename = f"{self.shot_context}_{task_name}_{version}"
        img_path = os.path.join(output_dir, filename).replace("\\", "/")
        mp4_path = os.path.join(output_dir, f"{filename}.mp4").replace("\\", "/")

        #VIEWPORT
        self.set_status("Configuring Viewport...")
        panel = cmds.playblast(activeEditor=True)
        
        if use_isolation:
            cmds.isolateSelect(panel, state=1)
            cmds.isolateSelect(panel, addSelected=True)
        
        #CLEANUP VIEWPORT
        cmds.modelEditor(panel, edit=True, 
                         displayAppearance='smoothShaded', 
                         displayTextures=True, 
                         grid=False, headsUpDisplay=False,
                         selectionHiliteDisplay=False,
                         displayLights='default',
                         nurbsCurves=False, nurbsSurfaces=False,
                         imagePlane=False, cameras=False,
                         lights=False, joints=False,
                         locators=False, manipulators=False,
                         deformers=False, dimensions=False,
                         fluids=False, hairSystems=False,
                         follicles=False, dynamicConstraints=False,
                         strokes=False, motionTrails=False,
                         pivots=False, 
                         handles=False,
                         polymeshes=True) 
        
        try:
            self.set_status("Rendering Image Sequence...")
            cmds.playblast(
                filename=img_path, format="image", compression="png",
                quality=100, widthHeight=[1920, 1080], percent=100,
                showOrnaments=False, viewer=False, forceOverwrite=True,
                sequenceTime=0, clearCache=True
            )

            #FFMPEG 
            self.set_status("Encoding MP4...")
            
            fps_map = {"game": 15, "film": 24, "pal": 25, "ntsc": 30, "show": 48, "palf": 50, "ntscf": 60}
            current_fps_unit = cmds.currentUnit(q=True, time=True)
            fps = fps_map.get(current_fps_unit, 24)
            start_frame = int(cmds.playbackOptions(q=True, min=True))
            
            blast_pattern = f"{img_path}.%04d.png"

            if do_slap_comp:
                plate_pattern = self.find_plate_sequence()
                
                if plate_pattern:
                    print(f"Found Plate: {plate_pattern}")
                    #scale2ref filter: scale playblast [1] to match plate [0] 
                    cmd = (
                        f'"{self.ffmpeg_path}" -y '
                        f'-start_number {start_frame} -framerate {fps} -i "{plate_pattern}" '
                        f'-start_number {start_frame} -framerate {fps} -i "{blast_pattern}" '
                        f'-filter_complex "[1:v][0:v]scale2ref[fg][bg];[bg][fg]overlay=format=auto" '
                        f'-c:v libx264 -pix_fmt yuv420p -crf 18 "{mp4_path}"'
                    )
                else:
                    cmds.warning("Slap Comp selected but NO PLATE found. Reverting to normal.")
                    do_slap_comp = False

            if not do_slap_comp:
                cmd = (
                    f'"{self.ffmpeg_path}" -y '
                    f'-start_number {start_frame} -framerate {fps} -i "{blast_pattern}" '
                    f'-c:v libx264 -pix_fmt yuv420p -crf 18 "{mp4_path}"'
                )
            
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            subprocess.run(cmd, shell=True, startupinfo=startupinfo, capture_output=True)
            
            #CLEANUP IMAGE SEQUENCE
            self.set_status("Cleaning up temporary files...")
            temp_images = glob.glob(f"{img_path}.*.png")
            for img in temp_images:
                try:
                    os.remove(img)
                except Exception as e:
                    print(f"Failed to delete {img}: {e}")

            if os.path.exists(mp4_path) and os.path.getsize(mp4_path) > 0:
                msg_suffix = " (Slap Comp)" if do_slap_comp else ""
                self.handle_upload_logic(mp4_path, task_name, version, msg_suffix)
                self.set_status(f"Done! Saved to {version}")
                cmds.inViewMessage(amg=f"<hl>Playblast Complete{msg_suffix}</hl>\nSaved to {version}", pos='midCenter', fade=True)
            else:
                self.set_status("Error: Encoding Failed")
                cmds.warning("MP4 generation failed.")

        except Exception as e:
            print(f"Playblast error: {e}")
            self.set_status(f"Error: {str(e)}")
        
        finally:
            if use_isolation:
                cmds.isolateSelect(panel, state=0)
            
            cmds.modelEditor(panel, edit=True, 
                             grid=True, headsUpDisplay=True, joints=True,
                             cameras=True, lights=True, locators=True,
                             manipulators=True, selectionHiliteDisplay=True,
                             displayLights='default',
                             nurbsCurves=True, imagePlane=True, polymeshes=True, pivots=True)

    def compress_video(self, input_path):
        self.set_status("Compressing (File too big)...")
        dir_name = os.path.dirname(input_path)
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        comp_path = os.path.join(dir_name, f"{base_name}_compressed.mp4").replace("\\", "/")

        cmd = f'"{self.ffmpeg_path}" -y -i "{input_path}" -vcodec libx264 -crf 28 "{comp_path}"'
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
        subprocess.run(cmd, shell=True, startupinfo=startupinfo)
        return comp_path if os.path.exists(comp_path) else None

    def handle_upload_logic(self, file_path, task, ver, suffix=""):
        self.set_status("Preparing Upload...")
        LIMIT_MB = 24.0
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        final_path = file_path
        msg_extra = ""

        if file_size_mb > LIMIT_MB:
            compressed_path = self.compress_video(file_path)
            if compressed_path and (os.path.getsize(compressed_path)/(1024*1024)) < LIMIT_MB:
                final_path = compressed_path
                msg_extra = "\n*(Compressed for Discord)*"
            else:
                final_path = None 

        self.upload_to_discord(final_path, task, ver, original_path=file_path, extra_msg=msg_extra + suffix)

    def upload_to_discord(self, file_to_upload, task, ver, original_path, extra_msg=""):
        try:
            import requests
        except ImportError:
            self.set_status("Error: 'requests' module missing")
            return

        self.set_status("Uploading to Discord...")
        folder_path = os.path.dirname(original_path).replace("\\", "/")
        
        artist_name = self.combo_artist.currentText()
        user_note = self.txt_message.text()

        message_content = f"**Playblast Published**\n"
        message_content += f"**Shot:** {self.shot_context}\n"
        message_content += f"**Task:** {task} | **Ver:** {ver}\n"
        message_content += f"**Artist:** {artist_name}\n"
        if user_note:
            message_content += f"**Note:** {user_note}\n"
        message_content += f"**Folder:** `{folder_path}`"
        message_content += extra_msg

        url = self.WEBHOOK_URL
        if self.thread_id:
            sep = "&" if "?" in url else "?"
            url += f"{sep}thread_id={self.thread_id}"

        if file_to_upload:
            try:
                with open(file_to_upload, 'rb') as f:
                    json_payload = json.dumps({"content": message_content})
                    files = {'file': (os.path.basename(file_to_upload), f, 'video/mp4')}
                    data = {'payload_json': json_payload}
                    
                    response = requests.post(url, data=data, files=files, timeout=120)
                    if response.status_code in [200, 204]:
                        print("Upload successful.")
                    else:
                        self.send_text_only(url, message_content + f"\n**File:** `{original_path}`\n*(Upload failed)*")
            except Exception as e:
                self.send_text_only(url, message_content + f"\n**File:** `{original_path}`")
        else:
            self.send_text_only(url, message_content + f"\n**File:** `{original_path}`\n*(File too large)*")

    def send_text_only(self, url, content):
        try:
            import requests
            requests.post(url, json={"content": content})
        except: pass

def show_ui():
    global orion_playblast_win
    try:
        orion_playblast_win.close()
    except: pass
    orion_playblast_win = OrionPlayblaster()
    orion_playblast_win.show()

if __name__ == "__main__":
    show_ui()