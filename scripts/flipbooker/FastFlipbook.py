from PySide2 import QtGui, QtCore, QtWidgets
from PySide2.QtCore import QFile
from PySide2.QtUiTools import *
import os, subprocess, re, tempfile, shutil, requests, json, math

class FastFlipbook(QtWidgets.QDialog):
    def __init__(self):
        # Init UI
        super(FastFlipbook, self).__init__()

        loader = QUiLoader()
        file = QFile(r"P:\all_work\userNames\ka23aaw\Sandbox\Tools\Flippy\Fast_Flipbook_Dialogue_003.ui")
        file.open(QFile.ReadOnly)
        self.ui = loader.load(file)
        file.close()
        
        self.ui.setParent(hou.qt.mainWindow(), self.ui.windowFlags())

        self.ui.show()

        # Initialise Variables
        self.initVariables()
        # Assign UI element default values
        self.initUiValues()
        
        # UI actions
        self.ui.CB_maxViewport.stateChanged.connect(self.toggleMaxViewport)
        self.ui.CB_allViewports.stateChanged.connect(self.toggleAllViewports)
        self.ui.CB_saveVideo.stateChanged.connect(self.toggleSaveVideo)
        self.ui.CB_pushToDiscord.stateChanged.connect(self.togglePushToDiscord)

        self.ui.SB_startFrame.valueChanged.connect(self.updateFrameRange)
        self.ui.SB_endFrame.valueChanged.connect(self.updateFrameRange)

        self.ui.SB_xResolution.valueChanged.connect(self.updateResolution)
        self.ui.SB_yResolution.valueChanged.connect(self.updateResolution)

        self.ui.PB_flipbook.pressed.connect(self.performSequence)

        self.ui.PB_openSelection.pressed.connect(self.openVideo)
        self.ui.PB_compare.pressed.connect(self.compareVideos)

    def initVariables(self):
        self.ffmpeg_path = r"C:\Program Files\Side Effects Software\Houdini 20.5.584\bin\hffmpeg.exe"
        self.hip = hou.expandString('$HIP')
        self.file_name = hou.expandString('$HIPNAME')

        self.viewer = hou.ui.paneTabOfType(hou.paneTabType.SceneViewer)
        self.fb_settings = self.viewer.flipbookSettings()

        self.fb_settings.outputToMPlay(True)

        self.resetMaximize = self.viewer.pane().isMaximized()

    def initUiValues(self):
        s_frame, e_frame = self.fb_settings.frameRange()
        
        self.ui.SB_startFrame.setValue(int(s_frame))
        self.ui.SB_endFrame.setValue(int(e_frame))

        self.ui.CB_allViewports.setChecked(self.fb_settings.renderAllViewports())

        x_res, y_res = self.fb_settings.resolution()

        self.ui.SB_xResolution.setValue(int(x_res))
        self.ui.SB_yResolution.setValue(int(y_res))

        self.findExistingVideos()
        self.findWebhookKeys()

    def findWebhookKeys(self):
        webhooks_folder = r"P:\all_work\userNames\ka23aaw\Sandbox\Tools\Flippy\FastFlipbook_webhooks.json"

        with open(webhooks_folder, 'r') as file:
            self.webhooks = json.load(file)

        keys = self.webhooks.keys()
        
        if len(keys) == 0:
            self.CanExport = 0
            return
        
        self.CanExport = 1
        for key in keys:
            self.ui.DD_chooseDiscord.addItem(key)


    def findExistingVideos(self):
        self.existingVideos = []
        
        self.flipbook_path = os.path.join(self.hip, 'flipbooks')
        if not os.path.exists(self.flipbook_path):
            return
        
        for file in os.scandir(self.flipbook_path):
            is_comparison = os.path.splitext(file)[0].split('_')[-1] == 'comparison'

            if file.is_file() & is_comparison == False:
                self.existingVideos.append(file.name)
                self.ui.LW_videoList.addItem(file.name)

    def toggleSaveVideo(self):
        state = self.ui.CB_saveVideo.isChecked()
        
        self.ui.CB_pushToDiscord.setEnabled(state & self.CanExport)
        self.togglePushToDiscord()

    def toggleMaxViewport(self):
        state = self.ui.CB_maxViewport.isChecked()

        self.viewer.pane().setIsMaximized(state)

    def toggleAllViewports(self):
        state = self.ui.CB_allViewports.isChecked()

        self.fb_settings.renderAllViewports(state)

    def togglePushToDiscord(self):
        state = self.ui.CB_saveVideo.isChecked() & self.ui.CB_pushToDiscord.isChecked()
        
        self.ui.DD_chooseDiscord.setEnabled(state)

    def updateFrameRange(self):
        s_frame = self.ui.SB_startFrame.value()
        e_frame = self.ui.SB_endFrame.value()

        self.fb_settings.frameRange([s_frame, e_frame])

    def updateResolution(self):
        x_res = self.ui.SB_xResolution.value()
        y_res = self.ui.SB_yResolution.value()

    def setSaveSettings(self):
        self.temp_path = tempfile.TemporaryDirectory().name
        os.mkdir(self.temp_path)

        img_output_path = os.path.join(self.temp_path, 'frame.$F4.jpg')

        self.fb_settings = self.fb_settings.stash()

        self.fb_settings.output(img_output_path)

    def flipbook(self):
        self.viewer.flipbook(self.viewer.curViewport(), self.fb_settings)

    def saveVideo(self):
        input_pattern = os.path.join(self.temp_path, 'frame.%04d.jpg')
        self.output_path = f'{self.hip}/flipbooks/{self.file_name}.mp4'

        path_exists = os.path.exists(f'{self.hip}/flipbooks')
        if not path_exists:
            os.makedirs(f'{self.hip}/flipbooks')

        s_frame = self.fb_settings.frameRange()[0]

        cmd = f'{self.ffmpeg_path} -framerate 24 -start_number {s_frame} -i {input_pattern} -vcodec h264_nvenc -pix_fmt yuv420p {self.output_path}'
        subprocess.run(cmd, shell=False)

        shutil.rmtree(self.temp_path)

    def sendToDiscord(self):
        selected_server_index = self.ui.DD_chooseDiscord.currentIndex()

        url = list(self.webhooks.values())[selected_server_index]

        data = {'content': f'New flipbook from {self.file_name}.\n `{self.output_path}`'}
        attachments = {"file": open(self.output_path, 'rb')}

        requests.post(url, data, files=attachments)
        
    def checkSceneSaved(self):
        if hou.hipFile.isNewFile():
            hou.ui.displayMessage('Please save file to export')
            self.ui.close()
            return False
        return True

    def saveSceneVersion(self):
        path = self.hip
        folders = os.listdir(path)

        versions = []
        for file in folders:
            if 'recovered' not in file:
                ext = os.path.splitext(file)[-1]
                if ext.lower() == '.hip' or ext.lower() == '.hipnc':
                    pattern = re.compile(r'\S*(?P<version>\d{3})\.\w+')

                    match = re.fullmatch(pattern, file)
                    num = int(match.group('version'))
                    versions.append(num)

        latest = max(versions)

        no_ext_name, ext = os.path.splitext(hou.hipFile.basename())
        no_ext_name = no_ext_name.rstrip('1234567890')

        incremented_file_basename = f'{no_ext_name}{int(latest)+1:03}{ext}'
        incremented_file_name = os.path.join(self.hip, incremented_file_basename).replace("\\", "/")
        
        hou.hipFile.save(file_name=incremented_file_name)

    def performSequence(self):
        save_video = self.ui.CB_saveVideo.isChecked()

        if save_video:
            if self.checkSceneSaved():
                self.setSaveSettings()
                self.flipbook()
                self.saveVideo()
                self.saveSceneVersion()

                if self.ui.CB_pushToDiscord.isChecked():
                    self.sendToDiscord()

        else:
            self.flipbook()

        self.ui.close()

        self.viewer.pane().setIsMaximized(self.resetMaximize)

    def openVideo(self):
        selection = self.ui.LW_videoList.selectedItems()

        for item in selection:
            index = self.ui.LW_videoList.row(item)

            path = os.path.join(self.flipbook_path, self.existingVideos[index])
            os.startfile(path)

    def compareVideos(self):
        widget_selection = self.ui.LW_videoList.selectedItems()

        paths = []
        filenames = []

        for item in widget_selection:
            index = self.ui.LW_videoList.row(item)

            filenames.append(self.existingVideos[index])
            paths.append(f'{self.hip}/flipbooks/{self.existingVideos[index]}')

        paths.sort()
        num_inputs = len(paths)

        pattern = re.compile(r'(?P<basename>\S*)(?P<version>\d{3})\.\w+')
        output_file_name = ''

        for item in filenames:
            match = re.fullmatch(pattern, item)
            basename = str(match.group('basename'))
            print(basename)
            num = str(match.group('version'))
            if item == filenames[0]:
                output_file_name += basename
            else:
                output_file_name += '_'

            output_file_name += num

            print(output_file_name)

        output_file_name += '_comparison.mp4'

        output_path = os.path.join(self.hip, 'flipbooks', output_file_name).replace(r'\\', r'/')

        # Set Grid Size
        grid_div_width = math.ceil(math.sqrt(num_inputs))
        grid_div_height = (num_inputs // grid_div_width) + min(math.ceil(num_inputs % grid_div_width), 1)

        max_width = math.trunc(1920 / grid_div_width)
        max_height = math.trunc(1080 / grid_div_height)

        # INPUTS
        inputs_expression = []

        for input_path in paths:
            cur_input = f'-i {input_path}'
            inputs_expression.append(cur_input)
        inputs_string = ' '.join(inputs_expression)

        # FILTER COMPLEX
        index_expression = []
        index_list = []

        for path in paths:
            index = paths.index(path)
            basename = os.path.basename(path)

            cur_index_string = f"[{index}:v] setpts=PTS-STARTPTS, scale=w={max_width}:h={max_height}:force_original_aspect_ratio=decrease, drawtext=text='{basename}':fontfile=C\\:/Windows/Fonts/arial.ttf:fontcolor=white:fontsize=16:box=1:boxcolor=black [a{index}]; "
            index_expression.append(cur_index_string)

            index_list.append(f'[a{index}]')

        index_string = ' '.join(index_expression)
        index_list_string = ''.join(index_list)

        # MOSAIC POSITIONS
        pos_expression = []

        for input_index in range(0, num_inputs):
            x_pos = input_index % grid_div_width
            y_pos = input_index // grid_div_width

            # create xpos string
            x_expression = []

            if x_pos != 0:
                for i in range(0, x_pos):
                    x_expression.append(f'w{i}')
            else:
                x_expression.append('0')
            x_string = '+'.join(x_expression)

            # create ypos string
            y_expression = []

            if y_pos != 0:
                for i in range(0, y_pos):
                    y_expression.append(f'h{i}')
            else:
                y_expression.append('0')
            y_string = '+'.join(y_expression)

            cur_pos_string = f'{x_string}_{y_string}'
            pos_expression.append(cur_pos_string)

        layout_string = '|'.join(pos_expression)

        cmd = f'"{self.ffmpeg_path}" {inputs_string} -filter_complex "{index_string} {index_list_string}xstack=inputs={num_inputs}:layout={layout_string}:fill=black[out]" -map "[out]" -c:v h264_nvenc {output_path}'

        print(os.path.exists(output_path))

        if not os.path.exists(output_path):
            subprocess.run(cmd, shell=True)
        os.startfile(f'{output_path}')
            


tool = FastFlipbook()