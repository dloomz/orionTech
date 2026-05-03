import os
import sys
import glob
import subprocess
import json
import re
import math
import tempfile
import shutil
from datetime import datetime

import hou

#qt
try:
    from PySide2 import QtWidgets, QtCore, QtGui
except ImportError:
    try:
        from PySide6 import QtWidgets, QtCore, QtGui
    except ImportError:
        pass

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

class OrionHouPlayblaster(QtWidgets.QWidget):
    
    #your original json path
    WEBHOOKS_FILE = r"P:\all_work\studentGroups\ORION_CORPORATION\00_pipeline\orionTech\data\FastFlipbook_webhooks.json"

    def __init__(self, parent=None):
        if parent is None:
            parent = hou.qt.mainWindow()
        super(OrionHouPlayblaster, self).__init__(parent=parent, f=QtCore.Qt.Window)
        
        self.setWindowTitle("Orion Playblaster (Houdini)")
        self.resize(450, 680)
        
        #styling
        self.setStyleSheet("""
            QWidget { background-color: #2b2b2b; color: #dddddd; font-family: Segoe UI, Arial; font-size: 10pt; }
            
            QGroupBox { border: 1px solid #444; border-radius: 4px; margin-top: 10px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #eeeeee; }
            
            QPushButton { background-color: #444; border-radius: 3px; padding: 8px; font-weight: bold; }
            QPushButton:hover { background-color: #555; }
            QPushButton:pressed { background-color: #333; }
            QPushButton:disabled { background-color: #2a2a2a; color: #555; }
            
            QPushButton#ActionButton { background-color: #FF6000; color: #121212; }
            QPushButton#ActionButton:hover { background-color: #ff8533; color: white; }

            QComboBox { background-color: #333; border: 1px solid #555; border-radius: 3px; padding: 4px; padding-right: 25px; color: #eee; }
            QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 25px; border-left-width: 1px; border-left-color: #555; border-left-style: solid; border-top-right-radius: 3px; border-bottom-right-radius: 3px; background-color: #404040; }
            QComboBox::down-arrow { image: none; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 6px solid #FF6000; width: 0; height: 0; margin-right: 2px; }
            QComboBox QAbstractItemView { background-color: #333; color: #dddddd; selection-background-color: #FF6000; selection-color: #121212; border: 1px solid #555; }
            QComboBox:disabled { background-color: #2a2a2a; color: #777; border: 1px solid #444; }

            QLineEdit, QSpinBox { background-color: #333; border: 1px solid #555; border-radius: 3px; padding: 4px; color: #eee; }
            QSpinBox::up-button, QSpinBox::down-button { width: 0px; } 
            
            QLabel { color: #ccc; }
            QLabel#Status { color: #FF6000; font-style: italic; font-size: 9pt; }
            
            QCheckBox { spacing: 5px; }
            QCheckBox::indicator { width: 14px; height: 14px; background-color: #333; border: 1px solid #555; border-radius: 3px; }
            QCheckBox::indicator:checked { background-color: #FF6000; border: 1px solid #FF6000; }
            QCheckBox:disabled { color: #666; }
            
            QTabWidget::pane { border: 1px solid #444; border-radius: 3px; }
            QTabBar::tab { background: #333; border: 1px solid #444; padding: 6px 15px; margin-right: 2px; border-top-left-radius: 3px; border-top-right-radius: 3px; }
            QTabBar::tab:selected { background: #444; border-bottom-color: #444; color: #FF6000; font-weight: bold; }
        """)

        #util
        self.orion = OrionUtils() if OrionUtils else None
        
        #context
        self.shot_context = os.environ.get("ORI_SHOT_CONTEXT", "No Shot Context")
        raw_shot_path = os.environ.get("ORI_SHOT_PATH", "")
        self.thread_id = os.environ.get("ORI_DISCORD_THREAD_ID", "")
        
        #houdini specific env
        self.hip = hou.expandString('$HIP')
        self.file_name = hou.expandString('$HIPNAME')
        self.viewer = hou.ui.paneTabOfType(hou.paneTabType.SceneViewer)
        
        #path setup
        self.render_root = ""
        self.shot_path = raw_shot_path
        
        #ffmpeg setup
        hfs = hou.expandString("$HFS")
        self.ffmpeg_path = os.path.join(hfs, "bin", "hffmpeg.exe").replace("\\", "/")
        
        #webhook dict
        self.webhooks = {}

        if self.orion:
            project_root = self.orion.get_root_dir()
            if raw_shot_path and not os.path.isabs(raw_shot_path):
                self.shot_path = os.path.join(project_root, raw_shot_path)
            
            shared_ffmpeg = os.path.join(project_root, "60_config", "libs", "ffmpeg.exe")
            if os.path.exists(shared_ffmpeg):
                self.ffmpeg_path = shared_ffmpeg

        #if shot path exists use standard pipeline, else fallback to $HIP/flipbooks
        if self.shot_path:
            self.render_root = os.path.join(self.shot_path, "3D_RENDERS", "CFX")
        else:
            self.render_root = os.path.join(self.hip, "flipbooks")

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

        #tabs
        self.tabs = QtWidgets.QTabWidget()
        self.tab_publish = QtWidgets.QWidget()
        self.tab_compare = QtWidgets.QWidget()
        self.tabs.addTab(self.tab_publish, "Publish")
        self.tabs.addTab(self.tab_compare, "Compare Videos")
        main_layout.addWidget(self.tabs)

        self.setup_publish_tab()
        self.setup_compare_tab()

        #button
        self.btn_blast = QtWidgets.QPushButton("FLIPBOOK & PUBLISH")
        self.btn_blast.setObjectName("ActionButton")
        self.btn_blast.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_blast.clicked.connect(self.run_flipbook)
        self.btn_blast.setMinimumHeight(45)
        main_layout.addWidget(self.btn_blast)

        #status
        self.lbl_status = QtWidgets.QLabel("Ready")
        self.lbl_status.setObjectName("Status")
        self.lbl_status.setAlignment(QtCore.Qt.AlignCenter)
        main_layout.addWidget(self.lbl_status)

    def setup_publish_tab(self):
        layout = QtWidgets.QVBoxLayout(self.tab_publish)
        
        #publish settings
        grp_pub = QtWidgets.QGroupBox("Publish Settings")
        form_pub = QtWidgets.QFormLayout(grp_pub)
        
        self.combo_artist = QtWidgets.QComboBox()
        form_pub.addRow("Artist:", self.combo_artist)

        self.combo_task = QtWidgets.QComboBox()
        self.combo_task.setEditable(True)
        self.combo_task.currentIndexChanged.connect(self.update_version_label)
        self.combo_task.editTextChanged.connect(self.update_version_label)
        form_pub.addRow("Task:", self.combo_task)

        self.lbl_version = QtWidgets.QLabel("v001")
        self.lbl_version.setStyleSheet("color: #FF6000; font-weight: bold; font-size: 11pt;")
        form_pub.addRow("Next Version:", self.lbl_version)
        
        #discord server dropdown
        self.combo_discord = QtWidgets.QComboBox()
        form_pub.addRow("Discord Server:", self.combo_discord)

        self.txt_message = QtWidgets.QLineEdit()
        self.txt_message.setPlaceholderText("Add a note (e.g. Fixed sim...)")
        form_pub.addRow("Note:", self.txt_message)
        
        layout.addWidget(grp_pub)

        #houdini settings
        grp_hou = QtWidgets.QGroupBox("Houdini Options")
        form_hou = QtWidgets.QFormLayout(grp_hou)
        
        frame_layout = QtWidgets.QHBoxLayout()
        self.spin_start = QtWidgets.QSpinBox()
        self.spin_start.setRange(-9999, 99999)
        self.spin_end = QtWidgets.QSpinBox()
        self.spin_end.setRange(-9999, 99999)
        frame_layout.addWidget(self.spin_start)
        frame_layout.addWidget(QtWidgets.QLabel("-"))
        frame_layout.addWidget(self.spin_end)
        form_hou.addRow("Frames:", frame_layout)

        res_layout = QtWidgets.QHBoxLayout()
        self.spin_x = QtWidgets.QSpinBox()
        self.spin_x.setRange(1, 8192)
        self.spin_y = QtWidgets.QSpinBox()
        self.spin_y.setRange(1, 8192)
        res_layout.addWidget(self.spin_x)
        res_layout.addWidget(QtWidgets.QLabel("x"))
        res_layout.addWidget(self.spin_y)
        form_hou.addRow("Resolution:", res_layout)

        self.chk_max = QtWidgets.QCheckBox("Maximize Viewport on Flipbook")
        self.chk_all = QtWidgets.QCheckBox("Render All Viewports")
        self.chk_save_scene = QtWidgets.QCheckBox("Version Up Hip File After")
        self.chk_save_scene.setChecked(True)
        
        form_hou.addRow("", self.chk_max)
        form_hou.addRow("", self.chk_all)
        form_hou.addRow("", self.chk_save_scene)
        
        layout.addWidget(grp_hou)
        layout.addStretch()

    def setup_compare_tab(self):
        layout = QtWidgets.QVBoxLayout(self.tab_compare)
        
        self.list_videos = QtWidgets.QListWidget()
        self.list_videos.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.list_videos.setStyleSheet("background-color: #222; border: 1px solid #555; padding: 5px;")
        layout.addWidget(self.list_videos)
        
        #add the publish checkbox for comparisons
        self.chk_publish_comp = QtWidgets.QCheckBox("Publish to Discord after generating")
        self.chk_publish_comp.setChecked(True)
        layout.addWidget(self.chk_publish_comp)
        
        btn_layout = QtWidgets.QHBoxLayout()
        btn_open = QtWidgets.QPushButton("Open Selected")
        btn_open.clicked.connect(self.open_selected_video)
        
        btn_compare = QtWidgets.QPushButton("Generate Mosaic Comparison")
        btn_compare.clicked.connect(self.compare_videos)
        btn_compare.setStyleSheet("background-color: #005c99; color: white;")
        
        btn_layout.addWidget(btn_open)
        btn_layout.addWidget(btn_compare)
        layout.addLayout(btn_layout)

    def set_status(self, text):
        self.lbl_status.setText(text)
        QtWidgets.QApplication.processEvents()

    def populate_data(self):
        #artists
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

        #tasks
        tasks = []
        if self.render_root and os.path.exists(self.render_root):
            try:
                for item in os.listdir(self.render_root):
                    if os.path.isdir(os.path.join(self.render_root, item)):
                        tasks.append(item)
            except Exception as e:
                print(f"Error reading tasks: {e}")
        
        if not tasks: tasks = ["SIMULATION", "PLAYBLAST"]
        self.combo_task.clear()
        self.combo_task.addItems(sorted(tasks))
        
        #load discord webhooks strictly from json file
        self.combo_discord.clear()
        if os.path.exists(self.WEBHOOKS_FILE):
            try:
                with open(self.WEBHOOKS_FILE, 'r') as file:
                    self.webhooks = json.load(file)
                
                keys = list(self.webhooks.keys())
                if keys:
                    self.combo_discord.addItems(keys)
                    self.combo_discord.setEnabled(True)
                else:
                    self.combo_discord.addItem("No webhooks found")
                    self.combo_discord.setEnabled(False)
            except Exception as e:
                print(f"Failed to read webhooks JSON: {e}")
                self.combo_discord.addItem("Error loading JSON")
                self.combo_discord.setEnabled(False)
        else:
            self.combo_discord.addItem("JSON not found")
            self.combo_discord.setEnabled(False)

        #houdini defaults
        if self.viewer:
            fb_settings = self.viewer.flipbookSettings()
            s_frame, e_frame = fb_settings.frameRange()
            self.spin_start.setValue(int(s_frame))
            self.spin_end.setValue(int(e_frame))
            
            x_res, y_res = fb_settings.resolution()
            self.spin_x.setValue(int(x_res))
            self.spin_y.setValue(int(y_res))
            
            self.chk_all.setChecked(fb_settings.renderAllViewports())

        self.refresh_video_list()

    def get_task_path(self):
        task_name = self.combo_task.currentText()
        if not task_name: return None, None
        if not os.path.exists(self.render_root):
            try: os.makedirs(self.render_root)
            except OSError: return None, None
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

    def run_flipbook(self):
        if hou.hipFile.isNewFile():
            hou.ui.displayMessage('Please save the Houdini file first.')
            return

        task_path, task_name = self.get_task_path()
        if not task_path: return
        
        version = self.get_next_version(task_path)
        output_dir = os.path.join(task_path, version)
        
        if not os.path.exists(output_dir):
            try: os.makedirs(output_dir)
            except OSError: return

        base_filename = f"{self.shot_context}_{task_name}_{version}"
        if self.shot_context == "No Shot Context":
            base_filename = f"{self.file_name}_{version}"

        mp4_path = os.path.join(output_dir, f"{base_filename}.mp4").replace("\\", "/")

        #temp directory for sequence
        temp_dir = tempfile.mkdtemp()
        img_pattern = os.path.join(temp_dir, 'frame.$F4.jpg').replace("\\", "/")
        ffmpeg_input = os.path.join(temp_dir, 'frame.%04d.jpg').replace("\\", "/")

        self.set_status("Rendering Flipbook...")
        
        #stash original settings
        original_max_state = self.viewer.pane().isMaximized()
        if self.chk_max.isChecked():
            self.viewer.pane().setIsMaximized(True)

        fb_settings = self.viewer.flipbookSettings().stash()
        fb_settings.output(img_pattern)
        fb_settings.outputToMPlay(False)
        fb_settings.frameRange([self.spin_start.value(), self.spin_end.value()])
        fb_settings.resolution([self.spin_x.value(), self.spin_y.value()])
        fb_settings.renderAllViewports(self.chk_all.isChecked())

        try:
            #run flipbook blocking
            self.viewer.flipbook(self.viewer.curViewport(), fb_settings)

            #encode mp4
            self.set_status("Encoding MP4...")
            s_frame = int(self.spin_start.value())
            fps = hou.fps()
            
            cmd = (
                f'"{self.ffmpeg_path}" -y -framerate {fps} -start_number {s_frame} '
                f'-i "{ffmpeg_input}" -vcodec libx264 -pix_fmt yuv420p -crf 18 "{mp4_path}"'
            )
            
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            subprocess.run(cmd, shell=True, startupinfo=startupinfo)

            #upload & finish
            if os.path.exists(mp4_path) and os.path.getsize(mp4_path) > 0:
                self.handle_upload_logic(mp4_path, task_name, version)
                
                if self.chk_save_scene.isChecked():
                    self.save_scene_version()
            else:
                self.set_status("Error: Encoding Failed")

        except Exception as e:
            self.set_status(f"Error: {str(e)}")
            print(f"Playblast error: {e}")
        
        finally:
            self.viewer.pane().setIsMaximized(original_max_state)
            #cleanup temp sequence
            self.set_status("Cleaning temp files...")
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"Failed to clear temp directory: {e}")
            
            self.refresh_video_list()

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

    def handle_upload_logic(self, file_path, task, ver):
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

        self.upload_to_discord(final_path, task, ver, original_path=file_path, extra_msg=msg_extra)

    def upload_to_discord(self, file_to_upload, task, ver, original_path, extra_msg=""):
        #grab the selected server and look up the url
        selected_server = self.combo_discord.currentText()
        url = self.webhooks.get(selected_server)

        #if there's no url in the dict (json was missing/empty), skip the upload
        if not url:
            self.set_status(f"Saved locally to {ver} (Skipped Discord Upload)")
            return

        try:
            import requests
        except ImportError:
            self.set_status(f"Saved to {ver} (Skipped Upload: 'requests' missing)")
            return

        self.set_status("Uploading to Discord...")
        folder_path = os.path.dirname(original_path).replace("\\", "/")
        artist_name = self.combo_artist.currentText()
        user_note = self.txt_message.text()
        
        message_content = f"**Houdini Flipbook Published**\n"
        message_content += f"**Shot:** {self.shot_context}\n"
        message_content += f"**Task:** {task} | **Ver:** {ver}\n"
        message_content += f"**Artist:** {artist_name}\n"
        if user_note:
            message_content += f"**Note:** {user_note}\n"
        message_content += f"**Folder:** `{folder_path}`"
        message_content += extra_msg

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
                    if response.status_code not in [200, 204]:
                        self.send_text_only(url, message_content + f"\n**File:** `{original_path}`\n*(Upload failed)*")
            except:
                self.send_text_only(url, message_content + f"\n**File:** `{original_path}`")
        else:
            self.send_text_only(url, message_content + f"\n**File:** `{original_path}`\n*(File too large)*")
            
        self.set_status(f"Done! Saved & Uploaded to {ver}")

    def send_text_only(self, url, content):
        try:
            import requests
            requests.post(url, json={"content": content})
        except: pass

    def save_scene_version(self):
        try:
            path = self.hip
            folders = os.listdir(path)
            versions = []
            
            for file in folders:
                if 'recovered' not in file:
                    ext = os.path.splitext(file)[-1]
                    if ext.lower() in ['.hip', '.hipnc']:
                        pattern = re.compile(r'\S*(?P<version>\d{3})\.\w+')
                        match = re.fullmatch(pattern, file)
                        if match:
                            versions.append(int(match.group('version')))

            latest = max(versions) if versions else 0
            no_ext_name, ext = os.path.splitext(hou.hipFile.basename())
            no_ext_name = no_ext_name.rstrip('0123456789')

            incremented_file_name = os.path.join(self.hip, f"{no_ext_name}{latest+1:03d}{ext}").replace("\\", "/")
            hou.hipFile.save(file_name=incremented_file_name)
        except Exception as e:
            print(f"Could not version up scene automatically: {e}")

    #compare tab features
    def refresh_video_list(self):
        self.list_videos.clear()
        self.existing_videos = {}
        
        #find all mp4s in all version folders under tasks
        if not os.path.exists(self.render_root): return
        
        for task_dir in os.listdir(self.render_root):
            task_path = os.path.join(self.render_root, task_dir)
            if not os.path.isdir(task_path): continue
            
            for ver_dir in os.listdir(task_path):
                ver_path = os.path.join(task_path, ver_dir)
                if not os.path.isdir(ver_path): continue
                
                for file in os.listdir(ver_path):
                    if file.endswith(".mp4") and "comparison" not in file:
                        display_name = f"{task_dir} / {ver_dir} / {file}"
                        full_path = os.path.join(ver_path, file).replace("\\", "/")
                        self.list_videos.addItem(display_name)
                        self.existing_videos[display_name] = full_path

    def open_selected_video(self):
        for item in self.list_videos.selectedItems():
            path = self.existing_videos.get(item.text())
            if path and os.path.exists(path):
                os.startfile(path)

    def compare_videos(self):
        selection = self.list_videos.selectedItems()
        if len(selection) < 2:
            self.set_status("Select at least 2 videos to compare.")
            return

        paths = sorted([self.existing_videos[item.text()] for item in selection])
        num_inputs = len(paths)
        
        output_dir = os.path.join(self.render_root, "COMPARISONS")
        if not os.path.exists(output_dir): os.makedirs(output_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(output_dir, f"{self.shot_context}_comparison_{timestamp}.mp4").replace("\\", "/")

        #grid calc
        grid_div_width = math.ceil(math.sqrt(num_inputs))
        grid_div_height = (num_inputs // grid_div_width) + min(math.ceil(num_inputs % grid_div_width), 1)

        #force even dimensions for the x264 codec
        max_width = int(math.trunc(1920 / grid_div_width))
        if max_width % 2 != 0: max_width -= 1
        
        max_height = int(math.trunc(1080 / grid_div_height))
        if max_height % 2 != 0: max_height -= 1

        inputs_expression = [f'-i "{p}"' for p in paths]
        inputs_string = ' '.join(inputs_expression)

        index_expression = []
        index_list = []

        for i, path in enumerate(paths):
            basename = os.path.basename(path)
            #escape for ffmpeg drawtext
            safe_text = basename.replace("'", "").replace(":", "\\:")
            font_path = "C\\:/Windows/Fonts/arial.ttf" 
            
            #scale, pad to uniform size, set standard pixel format, and draw text
            cur_index_string = (
                f"[{i}:v] setpts=PTS-STARTPTS, "
                f"scale={max_width}:{max_height}:force_original_aspect_ratio=decrease, "
                f"pad={max_width}:{max_height}:(ow-iw)/2:(oh-ih)/2:color=black, "
                f"format=yuv420p, "
                f"drawtext=text='{safe_text}':fontfile='{font_path}':fontcolor=white:fontsize=24:box=1:boxcolor=black@0.7 "
                f"[a{i}];"
            )
            index_expression.append(cur_index_string)
            index_list.append(f'[a{i}]')

        index_string = ' '.join(index_expression)
        index_list_string = ''.join(index_list)

        pos_expression = []
        for i in range(num_inputs):
            x_pos = i % grid_div_width
            y_pos = i // grid_div_width

            x_str = '+'.join([f'w{j}' for j in range(x_pos)]) if x_pos > 0 else '0'
            y_str = '+'.join([f'h{j}' for j in range(y_pos)]) if y_pos > 0 else '0'
            pos_expression.append(f'{x_str}_{y_str}')

        layout_string = '|'.join(pos_expression)

        cmd = (f'"{self.ffmpeg_path}" {inputs_string} -filter_complex '
               f'"{index_string} {index_list_string}xstack=inputs={num_inputs}:layout={layout_string}:fill=black[out]" '
               f'-map "[out]" -c:v libx264 -crf 18 "{output_path}"')

        self.set_status("Generating Mosaic Comparison...")
        
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
        #capture output to see errors
        result = subprocess.run(cmd, shell=True, startupinfo=startupinfo, capture_output=True, text=True)
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            os.startfile(output_path)
            
            #trigger the discord upload if the checkbox is ticked
            if self.chk_publish_comp.isChecked():
                self.handle_upload_logic(output_path, task="COMPARISON", ver=timestamp)
            else:
                self.set_status("Comparison complete.")
        else:
            self.set_status("Error generating comparison. Check console.")
            print("FFMPEG COMPARISON ERROR")
            print("Command Executed:", cmd)
            print("FFMPEG Output:", result.stderr)


def show_ui():
    global orion_hou_pb_win
    try:
        orion_hou_pb_win.close()
    except: pass
    orion_hou_pb_win = OrionHouPlayblaster()
    orion_hou_pb_win.show()

if __name__ == "__main__":
    show_ui()