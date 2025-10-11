import os
import json

class OrionUtils():
    
    def __init__(self):
        
         self.location = self.is_at_home()
         self.root_dir = self.get_root_dir()
         self.json_path = self.get_json_path()
         
    def is_at_home(self):
        
        user = os.getlogin()
        
        at_home = None
        if user == "do23aaf":
            at_home = False
        else: 
            at_home = True
        return at_home
    
    def get_root_dir(self):
         
        if self.location == False:
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