import maya.cmds as cmds
import maya.utils
import maya.OpenMaya as om

from maya.plugin.timeSliderBookmark.timeSliderBookmark import createBookmark

from functools import partial
import os

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
    cmds.playbackOptions(playbackSpeed=1.0)

#SHOT CONTEXT
def set_shot_context(shot_code, start_frame, end_frame, discord_thread_id, shot_path, *args):
    #function runs when shot in the menu is clicked
    #receives specific data for shot
    print(f"Setting Context to: {shot_code}")
    print(f"Frame Range: {start_frame} - {end_frame}")
    
    os.environ["ORI_SHOT_CONTEXT"] = shot_code
    os.environ["ORI_DISCORD_THREAD_ID"] = str(discord_thread_id) if discord_thread_id else ""
    os.environ["ORI_SHOT_PATH"] = shot_path
    os.environ["ORI_SHOT_FRAME_START"] = str(start_frame)
    os.environ["ORI_SHOT_FRAME_END"] = str(end_frame)
    
    #set maya timeline to shot range
    set_frames_from_shot()

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
        discord_thread_id = shot['discord_thread_id']
        shot_path = shot['shot_path']
        
        #create the menu item
        #use partial to pass the specific shot data to the command
        cmds.menuItem(
            parent=menu_name,
            label=code,
            command=partial(set_shot_context, code, start, end, discord_thread_id, shot_path)
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

def generate_thumbnail(clientData=None):
    #get current scene path
    scene_path = cmds.file(q=True, sn=True)
    if not scene_path:
        return

    #construct thumbnail path in .thumbnails subfolder
    folder = os.path.dirname(scene_path)
    filename = os.path.basename(scene_path)
    name_only = os.path.splitext(filename)[0]
    
    thumb_dir = os.path.join(folder, "thumbnails")
    if not os.path.exists(thumb_dir):
        os.makedirs(thumb_dir)

    thumb_path = os.path.join(thumb_dir, f"{name_only}.jpg")

    #capture Viewport
    try:
        editor = cmds.playblast(activeEditor=True)
        cmds.playblast(
            frame=cmds.currentTime(q=True),
            format="image",
            compression="jpg",
            completeFilename=thumb_path,
            showOrnaments=False,
            viewer=False,
            percent=100,
            widthHeight=[512, 288],
            forceOverwrite=True
        )
        print(f"Orion: Thumbnail saved to {thumb_path}")
    except Exception as e:
        print(f"Orion: Thumbnail generation failed: {e}")

def set_frames_from_shot():
    #check if the bookmark plugin is loaded first
    if not cmds.pluginInfo("timeSliderBookmark", query=True, loaded=True):
        cmds.loadPlugin("timeSliderBookmark")

    #get end frame from env var
    end_frame_string = os.environ.get("ORI_SHOT_FRAME_END")
    
    #default 1250 otherwise use the env var
    if end_frame_string:
        end_bookmark = int(end_frame_string) 
    else:
        end_bookmark = 1250 

    start_bookmark = 1011
    
    #scene handles padding
    start_frame = 1001
    end_frame = end_bookmark + 10
    start_scene = 981
    
    #apply timeline ranges
    cmds.playbackOptions(min=start_frame, max=end_frame)
    cmds.playbackOptions(ast=start_scene, aet=end_frame)

    try:
        createBookmark(name="MainAction", start=start_bookmark, stop=end_bookmark, color=(1.0, 0.37, 0.0))
        print(f"Set frames and bookmark: {start_bookmark} to {end_bookmark}")
    except Exception as e:
        print(f"Error creating bookmark: {e}")

def register_orion_callback():
    om.MSceneMessage.addCallback(
        om.MSceneMessage.kAfterSave, 
        generate_thumbnail
    )


cmds.evalDeferred("register_orion_callback()")
    
maya.utils.executeDeferred(setup_animation)
maya.utils.executeDeferred(add_button_to_toolbox)

try:
    maya.utils.executeDeferred(set_frames_from_shot)
except Exception as e:
    print(f"Error setting frames from shot: {e}")
    pass

print("User setup script loaded.")