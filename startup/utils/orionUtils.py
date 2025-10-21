import os
import json

class OrionUtils():
    
    def __init__(self):
        #define all the possible paths and variables
        logged_in_user = os.getlogin()
        home_root = "O:\\"
        work_root = "P:\\all_work\\studentGroups\\ORION_CORPORATION"
        json_relative_path = "00_pipeline\\orionTech\\json"
        config_filename = "config.json"

        # absolute paths to the config file for both at-home and at-work 
        work_config_path = os.path.join(work_root, json_relative_path, config_filename)
        home_config_path = os.path.join(home_root, json_relative_path, config_filename)
        
        # check which config file exists on system
        config_data = None
        if os.path.exists(work_config_path):
            self.root_dir = work_root
            config_data = self.read_json(work_config_path)
        elif os.path.exists(home_config_path):
            self.root_dir = home_root
            config_data = self.read_json(home_config_path)
        else:
            raise FileNotFoundError(f"Configuration file not found. Checked in {work_config_path} and {home_config_path}")

        #assign the usernames and software lists
        self.usernames = config_data.get("usernames", [])
        self.software = config_data.get("software", [])
        
        #user is at home based on whether username is in list
        # If the user is in the list, they are at work
        if logged_in_user in self.usernames:
            self.home_status = False  # At work
            self.root_dir = work_root 
        else:
            self.home_status = True   # At home
            self.root_dir = home_root  
        
        #set the definite path for the JSON directory.
        self.json_path = os.path.join(self.root_dir, json_relative_path)

    def is_at_home(self):
        #Returns True if the user is 'at home', False otherwise
        return self.home_status
    
    def get_root_dir(self):
        #Returns the determined root directory path
        return self.root_dir     
    
    def get_json_path(self):
        #Returns the full path to the json directory
        return self.json_path
         
    def read_json(self, file_path):
        #Reads a JSON file from given absolute path
        with open(file_path) as f:
            data = json.load(f)
        return data
    
    def read_config(self, key):
        #Reads a specific key from the config.json file
        config_path = os.path.join(self.json_path, "config.json")
        config_data = self.read_json(config_path)
        return config_data.get(key, None)
