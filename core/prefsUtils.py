import os
import shutil
import json
import subprocess

class PrefsUtils:

    def __init__(self, orion_utils_instance):
        self.orion = orion_utils_instance      
        self.root_dir = self.orion.get_root_dir()
        
        #updated paths
        self.config_folder = os.path.join(self.root_dir, "60_config")
        self.software_config_path = os.path.join(self.config_folder, "dcc_configs")
        self.data_folder = os.path.join(self.root_dir, "data")
        
        # Load main config to get lists
        self.softwares = self.orion.software
        self.usernames = self.orion.usernames

        self.current_user = os.getlogin()
        
    def is_user_recognized(self):
        """Checks if the current user is in the recognized usernames list"""
        return self.current_user in self.usernames
    
    def set_pref_env_var(self, env_var, user=None):
        """Sets environment variables using setx"""
        variables = list(env_var.keys())
        raw_values = list(env_var.values())
        user_to_use = user if user else self.current_user

        for i in range(len(variables)):
            var = variables[i]
            raw_val = raw_values[i]

            # Format string with user and resolve paths
            val = raw_val.format(user=user_to_use)

            # If the value looks like a relative path in our pipeline, make it absolute
            if "60_config" in val or "00_pipeline" in val:
                val = os.path.join(self.root_dir, val)

            print(f"Setting ENV: {var} = {val}")
            
            # Use setx for permanent system changes (Windows)
            command = f'setx {var} "{val}"'
            subprocess.run(command, shell=True, check=False)

    def get_software_config_file(self, software):
        """Helper to get path to software json"""
        return os.path.join(self.software_config_path, f"{software}.json")

    def save_prefs(self, software, user=None):
        """Backs up local preferences to the server"""
        pref_json = self.get_software_config_file(software)
        if not os.path.exists(pref_json):
            print(f"Config for {software} not found.")
            return

        pref_data = self.orion.read_json(pref_json)
        src_config = pref_data.get("source", {})
        dst_config = pref_data.get("destination", {})
        
        # Handle Houdini specifically (files)
        if software == "houdini":
            # Define Source (Local) and Destination (Server)
            # Note: You might need to adjust these keys based on your houdini.json content
            src_dir = src_config.get("houdini_pref", "C:\\Docs\\houdini20.5")
            
            dst_fmt = dst_config.get("houdini_config", "60_config\\userPrefs\\{user}\\houdini")
            dst_dir = os.path.join(self.root_dir, dst_fmt.format(user=user if user else self.current_user))

            if os.path.exists(src_dir):
                if not os.path.exists(dst_dir):
                    os.makedirs(dst_dir)

                src_files = os.listdir(src_dir)
                for f in src_files:
                    if f.endswith(".pref") and f != "jump.pref":
                        src_file = os.path.join(src_dir, f)
                        try:
                            shutil.copy2(src_file, dst_dir)
                            print(f"Saved {f}")
                        except Exception as e:
                            print(f"Error copying {f}: {e}")
        
        # Handle Folder-based software (Maya, etc.)
        elif software != "nuke": # Nuke usually handled via env vars only
            src_paths = list(src_config.values())
            
            for s_path in src_paths:
                # Determine folder name
                folder_name = os.path.basename(s_path)
                
                # Destination on server
                dst_key = f"{software}_config" # e.g. maya_config
                if dst_key in dst_config:
                    dst_fmt = dst_config[dst_key]
                    dst_final = os.path.join(self.root_dir, dst_fmt.format(user=user if user else self.current_user), folder_name)
                    
                    if os.path.exists(s_path):
                        try:
                            if os.path.exists(dst_final):
                                shutil.rmtree(dst_final) # Clear old backup to ensure sync
                            shutil.copytree(s_path, dst_final)
                            print(f"Saved folder {s_path} to {dst_final}")
                        except Exception as e:
                            print(f"Error saving {s_path}: {e}")

    def load_prefs(self, software, user=None):
        """Loads preferences from server to local machine"""
        user_to_use = user if user else self.current_user
        pref_json = self.get_software_config_file(software)

        if not os.path.exists(pref_json):
            print(f"Config for {software} not found.")
            return

        pref_data = self.orion.read_json(pref_json)
        
        #copy files
        src_config = pref_data.get("source") 
        dst_path = pref_data.get("destination")      

        if not src_config or not dst_path:
            return

        src_path = os.path.join(self.root_dir, src_config.format(user=user_to_use))

        if os.path.exists(src_path):
                try:
                    shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
                    print(f"Copied prefs from: {src_path} to {dst_path}")
                except Exception as e:
                    print(f"Error copying prefs from: {src_path} to {dst_path}: {e}")

        # if software == "houdini":
        #     jump_src = os.path.join(self.root_dir, "60_config", "softwarePrefs", "houdini", "jump.pref")
        #     jump_dst = os.path.join("C:\\Docs\\houdini20.5", "jump.pref") 
            
        #     if os.path.exists(jump_src):
        #         try:
        #             shutil.copyfile(jump_src, jump_dst)
        #             print("Loaded jump.pref")
        #         except Exception as e:
        #             print(f"Error loading jump.pref: {e}")

        # elif software != "nuke":

        #     server_paths_map = src_config # This holds "maya_config": "path/to/server"
        #     local_paths_map = dst_config  # This holds "maya_pref": "C:/Docs/..."
            
        #     # We need to map specific keys if they exist, or iterate
        #     # Simplified logic assuming keys align somewhat or we just iterate values
            
        #     #retrieve server base path
        #     server_base_key = f"{software}_config"
        #     if server_base_key in server_paths_map:
        #         server_fmt = server_paths_map[server_base_key]
        #         server_root = os.path.join(self.root_dir, server_fmt.format(user=user_to_use))
                
        #         if os.path.exists(server_root):
        #             #iterate over local destinations
        #             for local_path in local_paths_map.values():
        #                 folder_name = os.path.basename(local_path)
        #                 server_source = os.path.join(server_root, folder_name)
                        
        #                 if os.path.exists(server_source):
        #                     try:
        #                         #copytree with dirs_exist_ok=True 
        #                         os.makedirs(os.path.dirname(local_path), exist_ok=True)
        #                         shutil.copytree(server_source, local_path, dirs_exist_ok=True)
        #                         print(f"Loaded prefs from {server_source} to {local_path}")
        #                     except Exception as e:
        #                         print(f"Error loading prefs to {local_path}: {e}")

    # --- SETTINGS HANDLING ---

    def get_settings_path(self, user):
        """Gets path to user settings json. Updated to use 'data' folder."""
        #data/user_prefs/{user}/settings.json
        return os.path.join(self.data_folder, "user_prefs", user, "settings.json")

    def load_settings(self):
        """Loads user settings (Dark Mode, etc.)"""
        settings_path = self.get_settings_path(self.current_user)
        
        if os.path.exists(settings_path):
            return self.orion.read_json(settings_path)
        else:
            #Default Settings
            return {
                "dark_mode": False,
                "wacom_fix": False,
                "discord_on_startup": False
            }

    def save_settings(self, data):
        """Saves user settings to disk"""
        settings_path = self.get_settings_path(self.current_user)
        
        try:
            os.makedirs(os.path.dirname(settings_path), exist_ok=True)
            with open(settings_path, 'w') as f:
                json.dump(data, f, indent=4)
            print("Settings saved.")
        except Exception as e:
            print(f"Failed to save settings: {e}")
            
if __name__ == "__main__":
    
    import orionUtils
    import prefsUtils
    
    orion = orionUtils.OrionUtils()
    prefs = prefsUtils.PrefsUtils(orion)
    
    prefs.load_prefs("maya")