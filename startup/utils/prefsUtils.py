import os
import shutil
import json
import subprocess
from .orionUtils import OrionUtils

class PrefsUtils:

    def __init__(self):
        self.orion = OrionUtils()
        self.root_dir = self.orion.get_root_dir()
        self.json_path = self.orion.get_json_path()
        self.softwares = self.orion.read_config("software")
        self.usernames = self.orion.read_config("usernames")
        self.current_user = os.getlogin()
        
    def is_user_recognized(self):
        #Checks if the current user is in the recognized usernames list
        return self.current_user in self.usernames
    
    def save_prefs(self, software, user = None):

        pref_json = self.json_path + f"\\software\\{software}.json"
        pref_data = self.orion.read_json(pref_json)
    
        src = pref_data["source"]
        dst = pref_data["destination"]
        
        if software == "houdini":

            src_paths = list(src.values())

            dst_config = dst["houdini_config"]
            src_path = src["houdini_pref"]

            dst_format_path = dst_config.format(user=user if user else self.current_user)
            dst = os.path.join(self.root_dir, dst_format_path)

            src_files = os.listdir(src_path)
            for f in src_files:
                src_file_paths = os.path.join(src_path, f)
                root, extension = os.path.splitext(src_file_paths)

                if extension == '.pref':
                    if f != "jump.pref":
                        try:
                            shutil.copy2(src_file_paths, dst)

                        except shutil.SameFileError:
                            print("Source and destination represents the same file.")

                        except PermissionError:
                            print("Permission denied.")

                        except:
                            print("Error occurred while copying file.")

                    else:
                        pass
                else:
                    pass

        elif software == "nuke":
            pass

        else:
            pref_json = self.json_path + f"\\software\\{software}.json"
            pref_data = self.orion.read_json(pref_json)
        
            src = pref_data["source"]
            dst = pref_data["destination"]
            
            src_paths = list(src.values())
            dst_paths = []
            
            for s in src_paths:
                path_sections = s.split("\\")
                pref_configs = path_sections[-1]
                
                dst_path_raw = dst[f"{software}_config"]
                dst_format = dst_path_raw.format(user=user if user else self.current_user)
                dst_path = os.path.join(self.root_dir, dst_format, pref_configs)

                dst_paths.append(dst_path)
                
            transfer_route = zip(src_paths, dst_paths)
            
            for r in transfer_route:
                s_path, d_path = r
                if not os.path.exists(s_path):
                    print(f"Source path does not exist: {s_path}")
                    continue
                
                try:
                    os.makedirs(os.path.dirname(d_path), exist_ok=True)
                    shutil.copytree(s_path, d_path, dirs_exist_ok=True)
                    print(f"Successfully saved prefs from {s_path} to {d_path}")
                except Exception as e:
                    print(f"Error saving prefs from {s_path} to {d_path}: {e}")
        
    def load_prefs(self, software, user=None):
        
        if software == "houdini":
            command = "setx HOUDINI_PACKAGE_DIR \"P:\\all_work\\studentGroups\\ORION_CORPORATION\\60_config\\softwarePrefs\\houdini\\packages\""
            subprocess.run(command, shell=True, check=True)

            config_dir = self.orion.get_config_path()

            houdini_path = "C:\\Docs\\houdini20.5"
            jump_path_src = os.path.join(config_dir, "softwarePrefs","houdini","jump.pref")
            jump_path_dst = os.path.join(houdini_path, "jump.pref")

            try:
                shutil.copyfile(jump_path_src, jump_path_dst)
            except:
                print("an error has occured")

        elif software == "nuke":
            command = "setx NUKE_PATH \"P:\\all_work\\studentGroups\\ORION_CORPORATION\\60_config\\softwarePrefs\\nuke\""
            subprocess.run(command, shell=True, check=True)

        else:
            
            pref_json = self.json_path + f"\\software\\{software}.json"

            if os.path.exists(pref_json):
                pref_data = self.orion.read_json(pref_json)
                
                src = pref_data["destination"]
                dst = pref_data["source"]

                if "env_var" in pref_data:
                    env_var = pref_data["env_var"]
            
                    variables = list(env_var.keys())
                    values = list(env_var.values())

                    for i in range(len(variables)):
                        var = variables[i]
                        val = values[i]
                        command = f'setx {var} "{val}"'

                dst_paths = list(dst.values())
                src_paths = []
                
                for d in dst_paths:
                    path_sections = d.split("\\")
                    pref_configs = path_sections[-1]

                    src_path_raw = src[f"{software}_config"]
                    src_format = src_path_raw.format(user=user if user else self.current_user, config = pref_configs)
                    src_path = os.path.join(self.root_dir, src_format)
                    
                    print(src_path)
                    src_paths.append(src_path)
                    
                transfer_route = zip(src_paths, dst_paths)
                
                for r in transfer_route:
                    s_path, d_path = r
                    if not os.path.exists(s_path):
                        print(f"Source path does not exist: {s_path}")
                        continue
                    
                    try:
                        os.makedirs(os.path.dirname(d_path), exist_ok=True)
                        shutil.copytree(s_path, d_path, dirs_exist_ok=True)
                        print(f"Successfully saved prefs from {s_path} to {d_path}")
                    except Exception as e:
                        print(f"Error saving prefs from {s_path} to {d_path}: {e}")  
                        
            else:
                pass
            
    def get_settings_path(self, user):
        #Gets the path to the user_settings.json file
        settings_path = os.path.join(self.root_dir, f"60_config\\userPrefs\\{user}\\user_settings.json")
        return settings_path

    def load_settings(self):
        #Loads settings from user_settings.json
        settings_path = self.get_settings_path(self.current_user)
        try:
            return self.orion.read_json(settings_path)
        except FileNotFoundError:
            # If the file doesn't exist, create with default values
            default_settings = {
                "dark_mode": False,
                "wacom_fix": False,
                "discord_on_startup": False
            }
            self.save_settings(default_settings)
            return default_settings

    def save_settings(self, data):
        #Saves data to the user_settings.json file
        settings_path = self.get_settings_path(self.current_user)
        os.makedirs(os.path.dirname(settings_path), exist_ok=True) # Ensure directory exists
        with open(settings_path, 'w') as f:
            json.dump(data, f, indent=4)
