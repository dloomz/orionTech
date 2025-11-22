import os
import subprocess
import sys
from dotenv import load_dotenv

def launch_maya():
    #custom paths
    
    ROOT_PATH = "O:\\05_sandbox\\do23aaf "
    
    print("ROOT PATH:", ROOT_PATH)
    #path to maya exe
    MAYA_EXE = r"C:\Program Files\Autodesk\Maya2026\bin\maya.exe"

    #copy the current system environment
    env = os.environ.copy()

    #set custom env var
    
    #PYTHONPATH: python find scripts in your 'scripts' folder
    #we add our path to the EXISTING path using os.pathsep (';' on Win, ':' on Mac/Linux)
    env["PYTHONPATH"] = os.path.join(ROOT_PATH, "scripts") + os.pathsep + env.get("PYTHONPATH", "")

    #MAYA paths: tell maya where to find various resources
    # env["MAYA_APP_DIR"] = ROOT_PATH
    env["MAYA_SHELF_PATH"] = os.path.join(ROOT_PATH, "shelves") + os.pathsep + env.get("MAYA_SHELF_PATH", "")
    env["MAYA_SCRIPT_PATH"] = os.path.join(ROOT_PATH, "scripts") + os.pathsep + env.get("MAYA_SCRIPT_PATH", "")
    env["MAYA_MODULE_PATH"] = os.path.join(ROOT_PATH, "modules") + os.pathsep + env.get("MAYA_SCRIPT_PATH", "")
    env["MAYA_PLUG_IN_PATH"] = os.path.join(ROOT_PATH, "plug-ins") + os.pathsep + env.get("MAYA_PLUG_IN_PATH", "")
    
    icons_path = os.path.join(ROOT_PATH, "icons")
    env["XBMLANGPATH"] = icons_path + os.pathsep + env.get("XBMLANGPATH", "")

    # env["MAYA_PROJECT"] = PROJECT_PATH

    print(f"Launching Maya from: {MAYA_EXE}")
    print(f"Loading tools from: {ROOT_PATH}")
    print(os.environ["ORI_ROOT_PATH"])

    #launch Maya with the modified environment
    #subprocess.Popen allows the script to finish while Maya keeps running
    # try:
    #     subprocess.Popen([MAYA_EXE], env=env)
    # except FileNotFoundError:
    #     print("Error: Maya executable not found. Check the MAYA_EXE path.")
    # except Exception as e:
    #     print(f"An error occurred: {e}")

if __name__ == "__main__":
    launch_maya()
