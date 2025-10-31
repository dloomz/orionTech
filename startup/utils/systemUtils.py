import os
from datetime import datetime
import subprocess
import ctypes
import winreg
from .orionUtils import OrionUtils

class SystemUtils:

    def __init__(self):
        self.orion = OrionUtils()
        self.root = self.orion.get_root_dir()

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

        if enabled == True:
            if os.name != 'nt' or winreg is None:
                print("Dark mode control is only supported on Windows.")
                return

            try:
                # The registry key that controls theme settings
                key_path = r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize'
                
                reg_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
                winreg.SetValueEx(reg_key, "AppsUseLightTheme", 0, winreg.REG_DWORD, 0)
                winreg.SetValueEx(reg_key, "SystemUsesLightTheme", 0, winreg.REG_DWORD, 0)
                winreg.CloseKey(reg_key)

                print(f"Windows dark mode set to: {enabled}")
            
            except FileNotFoundError:
                print("Could not find the reg key for theme.")
            except Exception as e:
                print(f"An error occurred while changing the theme: {e}")

            os.system("taskkill /f /im explorer.exe")
            subprocess.Popen("explorer.exe")
            
        else:

            try:
                # The registry key that controls theme settings
                key_path = r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize'

                reg_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
        
                is_app_light = winreg.QueryValueEx(reg_key, "AppsUseLightTheme")
                is_sys_light = winreg.QueryValueEx(reg_key, "SystemUsesLightTheme")

                if is_app_light and is_sys_light == 0:
                    winreg.SetValueEx(reg_key, "AppsUseLightTheme", 1, winreg.REG_DWORD, 1)
                    winreg.SetValueEx(reg_key, "SystemUsesLightTheme", 1, winreg.REG_DWORD, 1)

                else:
                    pass
            
            except:
                pass



            
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
    
    def env_setup(self):
        
        #set maya env var
        os.environ['MAYA_DISABLE_CLIC_IPM'] = "1"
        os.environ['MAYA_DISABLE_CIP'] = "1"
        os.environ['MAYA_DISABLE_CER'] = "1"
        
        #set orion project path
        os.environ['ORION_PROJECT_PATH'] = self.root + "\\00_pipeline"
        os.environ['ORION_PIPELINE_PATH'] = self.root 

