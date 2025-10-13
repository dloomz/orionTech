import os
import json

class OrionUtils():
    
    def __init__(self):
        
         self.location = self.is_at_home()
         self.root_dir = self.get_root_dir()
         self.json_path = self.get_json_path()
         self.usernames = self.read_config("usernames")
         self.software = self.read_config("software")
         
    def is_at_home(self):
        
        return os.getlogin() != "do23aaf"
    
    def get_root_dir(self):
         
        if self.location == True:
            root_dir =  "O:\\"
        else:
            root_dir = "P:\\all_work\\studentGroups\\ORION_CORPORATION"  
        return root_dir     
    
    def get_json_path(self):
        
        json_path = os.path.join(self.root_dir, "00_pipeline\\orionTech\\json")
        
        return json_path
         
    def read_json(self, file):
       
        with open(file) as f:
            
            data = json.load(f)
            f.close()
            
        return data
    
    def read_config(self, key):
        
        config_path = os.path.join(self.json_path, "config.json")
        config_data = self.read_json(config_path)
        
        return config_data.get(key, None)
        
