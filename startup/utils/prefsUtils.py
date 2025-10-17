import os
import shutil
from datetime import datetime

class PrefsUtils:

    def __init__(self, orion_utils):
        self.orion = orion_utils
        self.pref_paths = self.orion.read_config("pref_paths")

    def get_user_pref_path(self, software, user):
        #Constructs the destination path for a user's saved prefs.
        dest_template = self.pref_paths['destination']
        
        # Replace placeholders with actual user and software names
        relative_path = dest_template.format(user=user, software=software)
        
        # Join with the root directory to get the full path
        return os.path.join(self.orion.get_root_dir(), relative_path)

    def get_source_pref_path(self, software, user):
        #Constructs the source path of a software's prefs
        source_template = self.pref_paths['source'].get(software)
        if not source_template:
            return None
        # Replace the user placeholder
        return source_template.format(user=user)

    def save_prefs(self, software, user):
        #Saves preferences by copying them from the source to the destination
        source_path = self.get_source_pref_path(software, user)
        dest_path = self.get_user_pref_path(software, user)

        if not source_path or not os.path.exists(source_path):
            print(f"Source path for {software} not found: {source_path}")
            return f"Source path for {software} not found."

        try:
            # Ensure the destination directory exists
            os.makedirs(dest_path, exist_ok=True)
            
            shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
            print(f"Successfully saved {software} prefs for {user} to {dest_path}")
            
            return f"Successfully saved {software} prefs."
        except Exception as e:
            print(f"Error saving {software} prefs: {e}")
            return f"Error saving {software} prefs: {e}"

    def load_prefs(self, software, user):
        #Loads preferences by copying them from the destination to the source
        source_path = self.get_user_pref_path(software, user)
        dest_path = self.get_source_pref_path(software, user)

        if not dest_path:
            return f"No destination path configured for {software}."
        if not os.path.exists(source_path):
            print(f"Saved prefs for {software} not found at: {source_path}")
            return f"No saved prefs found for {software}."
        
        try:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
            print(f"Successfully loaded {software} prefs for {user} from {source_path}")
            return f"Successfully loaded {software} prefs."
        except Exception as e:
            print(f"Error loading {software} prefs: {e}")
            return f"Error loading {software} prefs: {e}"