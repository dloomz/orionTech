import os
import json
import sys

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
        self.webhook_url = config_data.get("discord_webhook_url", "")
        
        #user is at home based on whether username is in list
        # If the user is in the list, they are at work
        if logged_in_user in self.usernames:
            self.home_status = False  # At work
            self.root_dir = work_root 
        else:
            self.home_status = True   # At home
            self.root_dir = home_root  
        
        #set the definite path for the config directory.
        self.config_path = os.path.join(self.root_dir, "60_config")

        #set the definite path for the graphics directory.
        self.graphic_path = os.path.join(self.config_path, "graphics")

        #set the definite path for the JSON directory.
        self.json_path = os.path.join(self.root_dir, json_relative_path)

        libs_path = self.get_libs_path()

        if libs_path not in sys.path:
            sys.path.insert(0, libs_path)

        import requests


    def is_at_home(self):
        #Returns True if the user is 'at home', False otherwise
        return self.home_status
    
    def get_root_dir(self):
        #Returns the determined root directory path
        return self.root_dir     
    
    def get_json_path(self):
        #Returns the full path to the json directory
        return self.json_path
    
    def get_config_path(self):
        #Returns the full path to config
        return self.config_path
         
    def get_graphic_path(self):
        #Returns the full path to config
        return self.graphic_path

    def get_libs_path(self):
        
        config_path = self.get_config_path()
        self.libs_path = os.path.join(config_path, 'libs')

        return self.libs_path

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

    def send_discord_notification(self, message):
        """Sends a message directly to the Discord webhook URL using the requests library."""

        if not self.webhook_url:
            print("Discord webhook URL not found in config.json. Skipping notification.")
            return

        # Structure the data as required by Discord webhooks
        data = {"content": message} 
        headers = {"Content-Type": "application/json"} # Standard header

        try:
            # Use requests.post - it handles JSON conversion automatically with the 'json' argument
            result = requests.post(self.webhook_url, json=data, headers=headers, timeout=10) # Added timeout

            # Check for HTTP errors (like 403, 404, 500 etc.)
            result.raise_for_status() 

            print(f"Successfully sent Discord notification via requests (Code: {result.status_code}).")

        except requests.exceptions.RequestException as e: 
            # Catch errors specifically from the requests library (network issues, timeouts, bad status codes)
            print(f"Failed to send Discord notification via requests: {e}")
            # If there's a response body with the error, print it
            if e.response is not None:
                print(f"Response Status Code: {e.response.status_code}")
                print(f"Response Content: {e.response.text}")
        except Exception as e:
            # Catch any other unexpected Python errors during the process
             print(f"An unexpected Python error occurred sending Discord notification: {e}")
             print(traceback.format_exc())
