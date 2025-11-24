import os
import subprocess
import sys
from pathlib import Path

def launch_nuke():
    
    user = os.getlogin()
    
    #custom paths
    current_script_dir = Path(__file__).resolve().parent
    pipeline_root = current_script_dir.parent.parent
    
    if str(pipeline_root) not in sys.path:
        sys.path.append(str(pipeline_root))

    try:
        from core.orionUtils import OrionUtils
    except ImportError as e:
        print(f"CRITICAL ERROR: Could not import OrionUtils. Checked path: {pipeline_root}")
        print(f"Error details: {e}")
        return
    
    orion = OrionUtils()
    
    ORI_PROJECT_PATH = orion.get_root_dir()
    print(f"Pipeline Root Detected: {ORI_PROJECT_PATH}")

    if not ORI_PROJECT_PATH:
        print("CRITICAL ERROR: ORI_PROJECT_PATH not found. Check your data/.env file.")
        return
    
    #path to maya exe
    NUKE_EXE = r"C:\Program Files\Nuke16.0v2\Nuke16.0.exe"

    ORI_ROOT_PATH = os.environ.get("ORI_ROOT_PATH")
    print("ORI_ROOT_PATH:", ORI_ROOT_PATH)

    if not ORI_ROOT_PATH:
        print("CRITICAL ERROR: ORI_ROOT_PATH is still missing. Check your .env file content.")
        return

    ROOT_PATH = os.path.join(ORI_ROOT_PATH, "60_config", "softwarePrefs", "nuke") 
    USER_PATH = os.path.join(ORI_ROOT_PATH, "60_config", "userPrefs", f"{user}", "nuke")
    OCIO_PATH = r"\\monster\projects\all_work\studentGroups\ORION_CORPORATION\60_config\colorManagement\aces_1.2\config.ocio"

    #ocio = \\monster\projects\all_work\studentGroups\ORION_CORPORATION\60_config\colorManagement\aces_1.2\config.ocio

    BASE_PLUGINS_PATH = os.path.join(ORI_ROOT_PATH, "60_config", "softwarePrefs", "nuke", "plugins")
    NEW_PLUGINS_PATH = [BASE_PLUGINS_PATH]
    for root, dirs, files in os.walk(BASE_PLUGINS_PATH):
        for d in dirs:
            #ignore cache and hidden folders
            if d.startswith(".") or d == "__pycache__":
                continue
            #add path to subfolder to list
            NEW_PLUGINS_PATH.append(os.path.join(root, d))
    
    #join all into string, seperated
    PLUGINS_PATH = os.pathsep.join(NEW_PLUGINS_PATH)
    
    all_nuke_paths = [USER_PATH, PLUGINS_PATH, ROOT_PATH]
    ORI_NUKE_PATHS = os.pathsep.join(all_nuke_paths)

    #copy the current system environment
    env = os.environ.copy()
    
    env["PYTHONPATH"] = os.path.join(ROOT_PATH, "python") + os.pathsep + env.get("PYTHONPATH", "")
    env["NUKE_PATH"] = ORI_NUKE_PATHS 
    os.environ['OCIO'] = OCIO_PATH

    try:
        subprocess.Popen([NUKE_EXE], env=env)
    except FileNotFoundError:
        print("Error: Nuke executable not found. Check the NUKE_EXE path.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    launch_nuke()