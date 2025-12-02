# orionTech/scripts/opener.py
import sys
import os
import subprocess

sys.path.append(r"P:\all_work\studentGroups\ORION_CORPORATION\00_pipeline\orionTech")
from core.orionUtils import OrionUtils

def open_by_code(code):
    orion = OrionUtils()
    
    #fast db lookup
    table = "shots" if "stc" in code else "assets" # Simple logic to guess table
    path = orion.get_path_from_code(code, table)
    
    #fallback to disk search
    if not path:
        print("Path not in DB or broken. Searching disk (this may take a moment)...")
        # Search the whole project root
        path = orion.find_code_on_disk(code, orion.get_root_dir())
        
    if path:
        print(f"Opening: {path}")
        os.startfile(path)
    else:
        print(f"Could not find any folder with code: {code}")

if __name__ == "__main__":
    user_input = input("Enter Code (e.g. stc_0010): ")
    open_by_code(user_input)