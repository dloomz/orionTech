import nuke
import os

####################ORION TOOLS####################

#add orionNukeSubmitter
try:
    import orionNukeSubmitter
    orionNukeSubmitter.add_orion_menu()
except ImportError:
    print("Warning: Could not import orionNukeSubmitter")
except Exception as e:
    print("error adding orion: {e}")
    
#add nodeMail
try:   
    import orion_nodemail
except ImportError:
    print("Warning: Could not import nodeMail")
except Exception as e:
    print("error adding nodemail: {e}")
    
####################ORION TOOLS####################

NUKE_DIR = os.path.expanduser("~/.nuke")
TOOLSET_DIR = os.path.join(NUKE_DIR, "ToolSets", "Favorites")
GIZMO_DIR = os.path.join(NUKE_DIR, "gizmos")

# --- Top Menu: Extra ---
mainMenu = nuke.menu("Nuke")
extraMenu = mainMenu.addMenu("Extra")
orionMenu = mainMenu.addMenu("ORION")

try:
    start_nodemail = "orion_nodemail.start()"
    orionMenu.addCommand("Nodemail™", start_nodemail)
except Exception as e:
    print(f"unable to add nodemail: {e}")

#load workspaces from custom path
def register_user_path():
    #get user and ori root
    user = os.getlogin()
    env_root = os.environ.get("ORI_ROOT_PATH")
    
    if not env_root:
        print("ORI_ROOT_PATH not set.")
        return

    custom_nuke_dir = os.path.join(env_root, "60_config", "userPrefs", user, "nuke", "Workspaces")

    #add it to Nuke's plugin path
    if os.path.exists(custom_nuke_dir):
        nuke.pluginAddPath(custom_nuke_dir)
        print(f"Registered user path: {custom_nuke_dir}")
    else:
        print(f"Could not find path: {custom_nuke_dir}")

    # OCIO_PATH = r"P:\all_work\studentGroups\ORION_CORPORATION\60_config\colorManagement\aces_1.2\config.ocio"
    # os.environ['OCIO'] = OCIO_PATH

register_user_path()
  
# Function to load a ToolSet by name
def load_toolset(path):
    if os.path.exists(path):
        nuke.nodePaste(path)
    else:
        nuke.message(f"ToolSet '{path}' not found")

# Add all ToolSets in Favorites automatically
if os.path.exists(TOOLSET_DIR):
    for f in os.listdir(TOOLSET_DIR):
        if f.endswith('.nk'):
            toolset_name = os.path.splitext(f)[0]
            path = os.path.join(TOOLSET_DIR, f)
            extraMenu.addCommand(toolset_name, f"load_toolset(r'{path}')")

# Add AutoShuffle command
extraMenu.addSeparator()
extraMenu.addCommand('Lighting/&Auto Shuffle', 'nukeAutoShuffle.start()', 'shift+L')

# Utility: open .nuke folder
def open_nuke_folder():
    path = NUKE_DIR
    if os.name == "nt":
        os.startfile(path)
    elif os.name == "posix":
        os.system(f"open '{path}'")

extraMenu.addSeparator()
extraMenu.addCommand("Open .nuke Folder", "open_nuke_folder()")

# --- Gizmo Toolbar ---
toolbar = nuke.menu('Nodes')
uhMenu = toolbar.addMenu("UH COMP TOOLS", "uh_toolbar_icon.jpg")
ETCMenu = toolbar.addMenu("ETC", "ETC_logo.png")

# Auto-add all gizmos in ~/.nuke/gizmos/
if os.path.exists(GIZMO_DIR):
    for top_level in os.listdir(GIZMO_DIR):
        top_path = os.path.join(GIZMO_DIR, top_level)
        if os.path.isdir(top_path):
            # Register the folder as plugin path
            nuke.pluginAddPath(top_path)

            # Create top-level menu
            topMenu = nuke.menu('Nodes').addMenu(top_level)

            for root, dirs, files in os.walk(top_path):
                for d in dirs:
                    nuke.pluginAddPath(os.path.join(root, d))  # register subfolders

                for f in files:
                    if f.endswith('.gizmo'):
                        gizmo_name = os.path.splitext(f)[0]
                        rel_path = os.path.relpath(root, top_path).replace("\\", "/")
                        menu_path = gizmo_name if rel_path == "." else f"{rel_path}/{gizmo_name}"
                        topMenu.addCommand(menu_path, f'nuke.createNode("{gizmo_name}")')

#ROOT SET-UP
nuke.knobDefault("Root.format", "UHD_4K")
nuke.Root()['format'].setValue('UHD_4K')
nuke.Root()['fps'].setValue(24)



