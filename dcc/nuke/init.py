import nuke
import os

# Define base path
NUKE_DIR = os.path.expanduser("~/.nuke")

# Define subfolders
folders = ["gizmos", "ToolSets", "ToolSets/Favorites", "icons", "scripts", "PxF", "NST"]

# Ensure all folders exist and add them to Nuke path
for folder in folders:
    path = os.path.join(NUKE_DIR, folder)
    if not os.path.exists(path):
        os.makedirs(path)
    nuke.pluginAddPath(path)

#OCIO SET-UP

def set_ocio_color_management():
    
    OCIO_PATH = r"//monster/projects/all_work/studentGroups/ORION_CORPORATION/60_config/colorManagement/aces_1.2/config.ocio"
    
    if nuke.Root()['colorManagement'].value() == 'Nuke':
        nuke.Root()['colorManagement'].setValue('OCIO')
        
        nuke.Root()['OCIO_config'].setValue('custom')
        nuke.Root()['customOCIOConfigPath'].setValue(OCIO_PATH)
             
        nuke.Root()['colorManagement'].setValue('Nuke')
        nuke.Root()['colorManagement'].setValue('OCIO')

nuke.addOnCreate(set_ocio_color_management, nodeClass='Root')

##############################ORION##################################################

# # ---------------------------
# # DAG / Node Graph
# # ---------------------------

# nuke.knobDefault("Root.format", "HD")
# nuke.knobDefault("note_font_size", "15")
# nuke.knobDefault("StickyNote.note_font_size", "30")
# nuke.knobDefault("BackdropNode.note_font_size", "100")

# try:
#     nuke.root()['tile_width'].setValue(80)
#     nuke.root()['tile_height'].setValue(22)
#     nuke.root()['grid_width'].setValue(110)
#     nuke.root()['grid_height'].setValue(75)
# except Exception:
#     pass

# # Snap threshold
# try:
#     if 'snap_threshold' in nuke.root().knobs():
#         nuke.root()['snap_threshold'].setValue(8)
# except Exception:
#     pass

# # Global group view disable
# try:
#     if 'global_group_view' in nuke.root().knobs():
#         nuke.root()['global_group_view'].setValue(False)
# except Exception:
#     pass

# # ---------------------------
# # Color Management
# # ---------------------------
# try:
#     nuke.root()['OCIO_config'].setValue("aces 1.2")
#     nuke.root()['defaultViewerLUT'].setValue("rec709")
# except Exception:
#     pass

# # ---------------------------
# # Control Panels
# # ---------------------------
# try:
#     nuke.preferences()['max_nodes_in_properties_bin'] = 1
# except Exception:
#     pass

# # ---------------------------
# # Startup Workspace
# # ---------------------------
# try:
#     # Set your personal workspace at startup
#     nuke.activeWorkspace("Shruthi_Workspace")
# except Exception:
#     pass


# nuke.knobDefault('Roto.feather_type', 'smooth')
# nuke.knobDefault('RotoPaint.feather_type', 'smooth')
# # ---------------------------
# # End of preferences snippet
# # ---------------------------