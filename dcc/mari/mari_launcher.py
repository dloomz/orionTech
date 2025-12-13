import os
import subprocess
import sys
from pathlib import Path

def launch_mari():
    
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
    
    try:
        from core.prefsUtils import PrefsUtils
    except ImportError as e:
        print(f"CRITICAL ERROR: Could not import PrefsUtils. Checked path: {pipeline_root}")
        print(f"Error details: {e}")
        return
    
    orion = OrionUtils()

    ORI_PROJECT_PATH = orion.get_root_dir()
    print(f"Pipeline Root Detected: {ORI_PROJECT_PATH}")

    if not ORI_PROJECT_PATH:
        print("CRITICAL ERROR: ORI_PROJECT_PATH not found. Check your data/.env file.")
        return
    
    #path to mari exe
    MARI_EXE = r"C:\Program Files\Mari7.1v2\Bundle\bin\Mari7.1v2.exe"

    ORI_ROOT_PATH = os.environ.get("ORI_ROOT_PATH")
    print("ORI_ROOT_PATH:", ORI_ROOT_PATH)

    if not ORI_ROOT_PATH:
        print("CRITICAL ERROR: ORI_ROOT_PATH is still missing. Check your .env file content.")
        return

    ROOT_PATH = os.path.join(ORI_ROOT_PATH, "60_config", "softwarePrefs", "mari")
    PIPELINE_PATH = os.path.join(ORI_ROOT_PATH, "00_pipeline", "orionTech")



    try:
        subprocess.Popen([MARI_EXE], env=env)
    except FileNotFoundError:
        print("Error: Mari executable not found. Check the MARI_EXE path.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    launch_mari()
