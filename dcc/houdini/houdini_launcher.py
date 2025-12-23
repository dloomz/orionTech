import os
import subprocess
import sys
from pathlib import Path

def launch_houdini(file_path=None, shot_code=None):
    
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
    
    #path to houdini exe
    HOUDINI_EXE = r"C:\Program Files\Side Effects Software\Houdini 20.5.584\bin\houdini.exe"

    ORI_ROOT_PATH = os.environ.get("ORI_ROOT_PATH")
    print("ORI_ROOT_PATH:", ORI_ROOT_PATH)

    if not ORI_ROOT_PATH:
        print("CRITICAL ERROR: ORI_ROOT_PATH is still missing. Check your .env file content.")
        return

    ROOT_PATH = os.path.join(ORI_ROOT_PATH, "60_config", "softwarePrefs", "houdini")
    PIPELINE_PATH = os.path.join(ORI_ROOT_PATH, "00_pipeline", "orionTech")
    PACKAGE_PATH = os.path.join(ROOT_PATH, "packages")

    #copy the current system environment
    env = os.environ.copy()
    
    env['ORI_PIPELINE_PATH'] = PIPELINE_PATH
    env["HOUDINI_PACKAGE_DIR"] = PACKAGE_PATH + os.pathsep + env.get("HOUDINI_PACKAGE_DIR", "")
    env["HOUDINI_USER_PREF_DIR"] = f"P:/all_work/studentGroups/ORION_CORPORATION/60_config/userPrefs/{user}/prefs/houdini__HVER__"
    env["ORI_SHOT_CONTEXT"] = shot_code if shot_code else ""
    
    # launch Houdini with the modified environment
    cmd = [HOUDINI_EXE]
    if file_path:
        cmd.append(file_path) # Add file to launch args

    try:
        subprocess.Popen(cmd, env=env)
    except FileNotFoundError:
        print("Error: Houdini executable not found.")

if __name__ == "__main__":
    # Check if a file path was passed as a command line argument
    path_arg = sys.argv[1] if len(sys.argv) > 1 else None
    launch_houdini(file_path=path_arg)