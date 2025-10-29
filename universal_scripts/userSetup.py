import os

import maya.cmds as cmds

#store original MAYA_PLUG_IN_PATH
og_maya_plugin_path = (os.getenv("MAYA_PLUG_IN_PATH"))

'''CODE FROM https://www.regnareb.com/pro/2018/01/improve-maya-usability/'''
if not cmds.optionVar(exists="firstLaunch"):
    # Force Auto load all plugins to False
    pluginList = cmds.pluginInfo(query=True, listPlugins=True) or []
    for plugin in pluginList:
        cmds.pluginInfo(plugin, edit=True, autoload=False)

    cmds.undoInfo(state=True, infinity=True)
    cmds.optionVar(iv=("undoIsInfinite", 1))
    cmds.optionVar(iv=("isIncrementalSaveEnabled", 1))
    cmds.optionVar(iv=("RecentBackupsMaxSize", 10 ))
    cmds.optionVar(iv=("RecentFilesMaxSize", 10))
    cmds.optionVar(iv=("RecentProjectsMaxSize", 10))
    cmds.optionVar(iv=("firstLaunch", 1))

try:
    cmds.commandPort(name=":7001", sourceType='mel')
    cmds.commandPort(name=":7002", sourceType='python')
except RuntimeError:
    pass

'''CODE FROM https://www.regnareb.com/pro/2018/01/improve-maya-usability/'''

#set to custom plug in path, load from only those paths
os.environ['MAYA_PLUG_IN_PATH'] = 'C:/Docs/maya/2026/plug-ins;C:/Docs/maya/plug-ins'
cmds.loadPlugin( allPlugins=True )

#restore original plug in path
os.environ['MAYA_PLUG_IN_PATH'] = og_maya_plugin_path

#ensure maya usd is loaded
mayaUsdPlugin = "mayaUsdPlugin"
if not cmds.pluginInfo(mayaUsdPlugin, query=True, loaded=True):
    try:
        cmds.loadPlugin(mayaUsdPlugin)
    except RuntimeError:
        pass
    
