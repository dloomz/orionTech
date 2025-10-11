import os
import json

class orionUtil():
    
    def __init__(self):
        
         self.location = self.is_at_home()
         self.root_dir = self.root_dir()
         
         
    def is_at_home(self):
        
        user = os.getlogin()
        
        at_home = None
        if user == "do23aaf":
            at_home = False
        else: 
            at_home = True
    
    def root_dir(self):
         
        if self.location == False:
            root_dir =  "O:\\"
        else:
            root_dir = "P:\\all_work\\studentGroups\\ORION_CORPORATION"       
    
    def get_json_path(self):
        pass
         
    def read_json(self, file):
       
        with open(file) as f:
            data = json.load(f)
            f.close()
        return data
    