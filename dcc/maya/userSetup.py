import maya.cmds as cmds
import maya.utils
from functools import partial

from core.orionUtils import OrionUtils
orion_utils = OrionUtils()

#GENERAL USE
cmds.undoInfo(state=True, infinity=True)
cmds.optionVar(iv=("undoIsInfinite", 1))
cmds.optionVar(iv=("RecentBackupsMaxSize", 10 ))
cmds.optionVar(iv=("RecentFilesMaxSize", 10))
cmds.optionVar(iv=("RecentProjectsMaxSize", 10))
cmds.optionVar(iv=("firstLaunch", 1))

#ANIMATION
def setup_animation():
    cmds.playbackOptions(loop='continuous')
    cmds.playbackOptions(ast=1001, aet=1500)
    cmds.playbackOptions(min=1001, max=1500)
    cmds.playbackOptions(playbackSpeed=1.0)

#SHOT CONTEXT
def set_shot_context(shot_code, start_frame, end_frame, *args):
    #function runs when shot in the menu is clicked
    #receives specific data for shot
    print(f"Setting Context to: {shot_code}")
    print(f"Frame Range: {start_frame} - {end_frame}")
    
    #set maya timeline to shot range
    cmds.playbackOptions(min=start_frame, max=end_frame)
    cmds.playbackOptions(ast=start_frame, aet=end_frame)

def populate_shot_menu(menu_name, *args):
    #clear existing items 
    cmds.popupMenu(menu_name, edit=True, deleteAllItems=True)
    
    #fetch all shots from database
    shots = orion_utils.get_all_shots()
    
    for shot in shots:
        #extract info from the db row
        code = shot['code']
        start = shot['frame_start']
        end = shot['frame_end']
        
        #create the menu item
        #use partial to pass the specific shot data to the command
        cmds.menuItem(
            parent=menu_name,
            label=code,
            command=partial(set_shot_context, code, start, end)
        )

def add_button_to_toolbox():
    """
    Adds a custom button to the Maya Tool Box (Left Toolbar).
    """
    ICON_PATH = r"P:\all_work\studentGroups\ORION_CORPORATION\20_pre\branding\logos\orion_simple_white.png"
    CLICKED_ICON_PATH = r"P:\all_work\studentGroups\ORION_CORPORATION\20_pre\branding\logos\orion_simple_colour.png"
    shot_switcher = "ORION_Shot_Switcher"
    
    if cmds.control(shot_switcher, exists=True):
        cmds.deleteUI(shot_switcher)
    
    parent_layout = "flowLayout2"
    
    shot_button = cmds.iconTextButton(
        shot_switcher,           
        parent=parent_layout,    
        style='iconOnly',         
        image=ICON_PATH, 
        width=34,                 #34x34
        height=34,
        highlightImage=CLICKED_ICON_PATH, 
        annotation='Change Mayas shot context!', 
        command='print("The button was clicked!")'
    )
    
    #create the popup menu
    #postMenuCommand calls our function to build the list just before showing it
    cmds.popupMenu(
        parent=shot_button, 
        postMenuCommand=populate_shot_menu
    )
    
maya.utils.executeDeferred(setup_animation)
maya.utils.executeDeferred(add_button_to_toolbox)

print("User setup script loaded.")