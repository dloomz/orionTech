import os
from datetime import datetime
import webbrowser
import subprocess
import ctypes
import time
import shutil

class SystemUtils:

    def __init__(self, orion_utils_instance, pref_utils_instance):
        self.orion = orion_utils_instance
        self.pref = pref_utils_instance
        self.root = self.orion.get_root_dir()
        self.config_path = self.orion.config_path
        self.current_user = os.getlogin()

    def run_terminal_command(self, command):
        """
        Runs a command in the terminal.

        Args:
            command (str): The command to execute.
        """
        try:
            subprocess.run(command, shell=True, check=True)
            print(f"Successfully executed command: {command}")
        except subprocess.CalledProcessError as e:
            print(f"Error executing command: {e}")

    def change_wallpaper(self, image_path):
        #image_path (str): The full path to the wallpaper image.

        try:
            ctypes.windll.user32.SystemParametersInfoW(20, 0, image_path, 3)
            print(f"Wallpaper changed to {image_path}")
        except Exception as e:
            print(f"Error changing wallpaper: {e}")

            
    def set_windows_dark_mode(self, enabled: bool):

        #enabled (bool): True to enable dark mode, False for light mode.

        #C:\Windows\Resources\Themes\aero.theme
        #C:\Windows\Resources\Themes\dark.theme

        light_path = r"C:\Windows\Resources\Themes\aero.theme"
        dark_path = r"C:\Windows\Resources\Themes\dark.theme"

        if enabled == True:
            
            try:
                os.startfile(dark_path)
                time.sleep(0.45)
                subprocess.run("taskkill /IM SystemSettings.exe /F", shell=True)
                             
            except Exception as e:
                print(f"An error occurred: {e}") 
            
        else:

            try:
                os.startfile(light_path)
                time.sleep(0.45)
                subprocess.run("taskkill /IM SystemSettings.exe /F", shell=True)
            
            except Exception as e:
                print(f"An error occurred: {e}") 
            
    def add_line_to_file(self, file_path, line_to_add):

        #file_path (str): The full path to the file.
        #line_to_add (str): The line of text to add.

        try:
            with open(file_path, 'a') as f:
                f.write(f"\n{line_to_add}")
            print(f"Successfully added line to {file_path}")
        except FileNotFoundError:
            print(f"Error: The file at {file_path} was not found.")
        except Exception as e:
            print(f"An error occurred: {e}")   
            
    def get_modified_files(self, path):

        config_dir = path
        config_files = os.listdir(config_dir)
        current_day = datetime.today().date()

        files_modified = []

        for f in config_files:
            full_path = os.path.join(config_dir, f)
            mtime = os.path.getmtime(full_path)
            file_date = datetime.fromtimestamp(mtime).date()

            if file_date == current_day:
                files_modified.append(f)

        return files_modified

    def open_window(self, site, enabled: bool):
        
        chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        webbrowser.register('chrome', None, 
                        webbrowser.BackgroundBrowser(chrome))
        
        if enabled == True:
            webbrowser.get('chrome').open(site)
            
        else:
            pass

    def wacom_fix(self, enabled: bool):
        
        if enabled == True:
            WACOM_PATH = r"P:\all_work\studentGroups\ORION_CORPORATION\60_config\wacom\ORION.wacomprefs"
            
            CMD = f"powershell -c \"{WACOM_PATH}\""
            subprocess.run(CMD, shell=True)
            
        else:
            pass

    def env_setup(self):

        env_json = os.path.join(self.config_path, "env_var.json")

        if os.path.exists(env_json):

            pref_data = self.orion.read_json(env_json)

            env_var = pref_data.get("env_var") 
            self.pref.set_pref_env_var(env_var)