import os
import subprocess
import sys
from pathlib import Path
import shutil

def launch_maya():
    
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
    
    #path to maya exe
    MAYA_EXE = r"C:\Program Files\Autodesk\Maya2026\bin\maya.exe"

    ORI_ROOT_PATH = os.environ.get("ORI_ROOT_PATH")
    print("ORI_ROOT_PATH:", ORI_ROOT_PATH)

    if not ORI_ROOT_PATH:
        print("CRITICAL ERROR: ORI_ROOT_PATH is still missing. Check your .env file content.")
        return

    ROOT_PATH = os.path.join(ORI_ROOT_PATH, "60_config", "softwarePrefs", "maya")
    PIPELINE_PATH = os.path.join(ORI_ROOT_PATH, "00_pipeline", "orionTech")

    #copy the current system environment
    env = os.environ.copy()
    
    #PYTHONPATH: python find scripts in 'scripts' folder
    MAYA_SCRIPT_PATH = os.path.join(ROOT_PATH, "scripts")
    ORI_LIBS_PATH = os.path.join(ORI_ROOT_PATH, "60_config", "libs")
    
    all_maya_paths = [MAYA_SCRIPT_PATH, ORI_LIBS_PATH, PIPELINE_PATH]
    ORI_MAYA_PATHS = os.pathsep.join(all_maya_paths)

    env["PYTHONPATH"] = ORI_MAYA_PATHS + os.pathsep + env.get("PYTHONPATH", "")

    #MAYA paths
    env["MAYA_SHELF_PATH"] = os.path.join(ROOT_PATH, "shelves") + os.pathsep + env.get("MAYA_SHELF_PATH", "")
    env["MAYA_MODULE_PATH"] = os.path.join(ROOT_PATH, "modules") + os.pathsep + env.get("MAYA_SCRIPT_PATH", "")
    env["MAYA_PLUG_IN_PATH"] = os.path.join(ROOT_PATH, "plug-ins") + os.pathsep + env.get("MAYA_PLUG_IN_PATH", "")
    
    base_scripts_path = os.path.join(ROOT_PATH, "scripts")
    all_script_paths = [base_scripts_path]
    for root, dirs, files in os.walk(base_scripts_path):
        for d in dirs:
            #ignore cache and hidden folders
            if d.startswith(".") or d == "__pycache__":
                continue
            #add path to subfolder to list
            all_script_paths.append(os.path.join(root, d))
    
    #join all into string, seperated
    new_script_paths = os.pathsep.join(all_script_paths)
    
    #add to script path
    env["MAYA_SCRIPT_PATH"] = new_script_paths + os.pathsep + env.get("MAYA_SCRIPT_PATH", "")
    
    icons_path = os.path.join(ROOT_PATH, "icons")
    env["XBMLANGPATH"] = icons_path + os.pathsep + env.get("XBMLANGPATH", "")

    #speedup maya startup
    env["MAYA_DISABLE_CLIC_IPM"] = "1"
    env["MAYA_DISABLE_CIP"] = "1"
    env["MAYA_DISABLE_CER"] = "1"

    # env["MAYA_PROJECT"] = ORI_PROJECT_PATH
    env["ORI_PROJECT_PATH"] = ORI_PROJECT_PATH
    
    # WORKSPACE_SRC = os.path.join(MAYA_SCRIPT_PATH, "userSetup.py")
    # WORKSPACE_DST = [r"C:\Docs\maya\2026\scripts\userSetup.py", r"C:\Docs\maya\2025\scripts\userSetup.py", r"C:\Docs\maya\scripts\userSetup.py"]
    
    # for dst in WORKSPACE_DST:
    #     try:
    #         shutil.copyfile(WORKSPACE_SRC, dst)
    #     except Exception as e:
    #         print(f"Unable to copy userprefs: {e}")

    pref = PrefsUtils(orion)
    pref.load_prefs("maya", user)
    
    #launch Maya with the modified environment
    try:
        subprocess.Popen([MAYA_EXE], env=env)
    except FileNotFoundError:
        print("Error: Maya executable not found. Check the MAYA_EXE path.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    launch_maya()


#import syncsketchGUI.actions
#syncsketchGUI.actions.install_shelf()

# import syncsketchGUI.actions
# syncsketchGUI.actions.build_menu()