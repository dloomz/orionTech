import mari
import sys
import os
import inspect
import PySide2.QtCore

try:
    filename = __file__
except NameError:
    filename = inspect.getfile(inspect.currentframe())

current_dir = os.path.dirname(os.path.abspath(filename))

import mari_exporter

def run_orion_exporter():
    """Helper to launch the UI"""
    mari_exporter.show_ui()

def apply_orion_defaults(project):
    """
    Callback function that runs whenever a project is opened.
    Sets viewport defaults, buffer resolution, and navigation mode.
    """
    print(f"[Orion] Applying studio defaults for: {project.name()}")
    
    try:

        mari.prefs.set("Canvas/Navigation/Navigation Mode", "Maya")
        
        pb = mari.canvases.paintBuffer()
        pb.setScale(PySide2.QtCore.QSizeF(0.95, 0.95))
        pb.setResolution(PySide2.QtCore.QSize(4096, 4096))
        
        canvas = mari.canvases.current()
        if canvas:
            canvas.setDisplayProperty("Grid/UvGridVisible", False)
            
        print("[Orion] Defaults Successfully Applied: Maya Nav, 4K Buffer, No Grid.")
            
    except Exception as e:
        print(f"[Orion] Error applying defaults: {e}")

#menu item
try:
    mari.menus.addAction(
        mari.actions.create('Orion Exporter', 'run_orion_exporter()'),
        'MainWindow/Orion'
    )
except Exception as e:
    print(f"Error registering Orion menu: {e}")

try:
    mari.projects.opened.connect(apply_orion_defaults)
except Exception as e:
    print(f"Error connecting startup signal: {e}")