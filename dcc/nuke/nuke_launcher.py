import os
import subprocess
import sys
from pathlib import Path
import shutil
import argparse

def launch_nuke(file_path=None, shot_code=None, frame_start=None, frame_end=None, discord_thread_id=None, shot_path=None):
    
    user = os.getlogin()
    
    #custom paths
    current_script_dir = Path(__file__).resolve().parent
    pipeline_root = current_script_dir.parent.parent
    
    print(pipeline_root)
    
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
    FLAG = "--nukex"

    ORI_ROOT_PATH = os.environ.get("ORI_ROOT_PATH")
    print("ORI_ROOT_PATH:", ORI_ROOT_PATH)

    if not ORI_ROOT_PATH:
        print("CRITICAL ERROR: ORI_ROOT_PATH is still missing. Check your .env file content.")
        return

    ROOT_PATH = os.path.join(ORI_ROOT_PATH, "60_config", "softwarePrefs", "nuke") 
    PIPELINE_PATH = os.path.join(ORI_ROOT_PATH, "00_pipeline", "orionTech")
    USER_PATH = os.path.join(ORI_ROOT_PATH, "60_config", "userPrefs", f"{user}", "nuke")
    
    WORKSPACE_SRC = os.path.join(USER_PATH, "Workspaces")
    WORKSPACE_DST = f"C:\\Users\\{user}\\.nuke\\Workspaces\\Nuke"
    
    try:
        shutil.copytree(WORKSPACE_SRC, WORKSPACE_DST, dirs_exist_ok=True)
    except Exception as e:
        print(f"Unable to copy workspaces: {e}")
    
    # OCIO_PATH = r"P:\all_work\studentGroups\ORION_CORPORATION\60_config\colorManagement\aces_1.2\config.ocio"

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
    
    all_nuke_paths = [USER_PATH, PLUGINS_PATH, ROOT_PATH, PIPELINE_PATH]
    ORI_NUKE_PATHS = os.pathsep.join(all_nuke_paths)

    #copy the current system environment
    env = os.environ.copy()
    
    env["PYTHONPATH"] = os.path.join(ROOT_PATH, "python") + os.pathsep + env.get("PYTHONPATH", "")
    # env["PYTHONPATH"] = PIPELINE_PATH + os.pathsep + env.get("PYTHONPATH", "")
    env["NUKE_PATH"] = ORI_NUKE_PATHS 
    env['ORI_PIPELINE_PATH'] = PIPELINE_PATH
    env["ORI_SHOT_CONTEXT"] = shot_code if shot_code else ""
    # os.environ['OCIO'] = OCIO_PATH
    
    env["ORI_SHOT_CONTEXT"] = shot_code if shot_code else ""
    env["ORI_DISCORD_THREAD_ID"] = str(discord_thread_id)
    env["ORI_SHOT_PATH"] = str(shot_path)
    env["ORI_SHOT_FRAME_START"] = str(frame_start)
    env["ORI_SHOT_FRAME_END"] = str(frame_end)

    cmd = [NUKE_EXE, FLAG]
    if file_path:
        cmd.append(file_path)

    try:
        subprocess.Popen(cmd, env=env)
    except FileNotFoundError:
        print("Error: Nuke executable not found.")

if __name__ == "__main__":
    #ARGUMENT PARSER
    parser = argparse.ArgumentParser(description="Launch Nuke with Orion Context")
    parser.add_argument("--file", help="Path to the Nuke file to open", default=None)
    parser.add_argument("--code", help="Shot Code", default=None)
    parser.add_argument("--start", help="Start Frame", default=None)
    parser.add_argument("--end", help="End Frame", default=None)
    parser.add_argument("--discord", help="Discord Thread ID", default=None)
    parser.add_argument("--shotpath", help="Shot Path on Disk", default=None)
    
    args = parser.parse_args()
    
    launch_nuke(
        file_path=args.file,
        shot_code=args.code,
        frame_start=args.start,
        frame_end=args.end,
        discord_thread_id=args.discord,
        shot_path=args.shotpath
    )