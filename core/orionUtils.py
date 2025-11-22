import os
import json
import sys
import sqlite3
import uuid
import re
import traceback
import requests
import shutil

class OrionUtils():
    
    # Standard Folder Structure for new shots
    SHOT_SUBFOLDERS = [
        "ANIM/PUBLISH",
        "ANIM/WORK",
        "COMP/Apps/Nuke/Scripts",
        "COMP/Apps/Hiero/Templates",
        "COMP/Apps/Photoshop",
        "COMP/Apps/Syntheyes",
        "COMP/Apps/Mocha_Pro",
        "COMP/Plates/Source",
        "COMP/Plates/Comp",
        "COMP/Prep/Denoise",
        "COMP/Review/IMG",
        "COMP/Review/VID",
        "COMP/Tools",
        "FX/PUBLISH",
        "FX/WORK",
        "LIGHTING/WORK",
        "LIGHTING/PUBLISH",
        "ROTO/WORK",
        "ROTO/PUBLISH",
        "MATCHMOVE/WORK",
        "MATCHMOVE/PUBLISH",
        "CAMERA/WORK",
        "CAMERA/PUBLISH",
        "3D_RENDERS",
        "2D_RENDERS",
    ]

    def __init__(self):
        #DYNAMIC ROOT DETECTION
        #root based on where file is located
        current_script_path = os.path.abspath(__file__)
        #go up two levels: core/ -> root/
        self.root_dir = os.path.dirname(os.path.dirname(current_script_path))

        #DEFINE KEY PATHS
        self.config_path = os.path.join(self.root_dir, "config")
        self.data_path = os.path.join(self.root_dir, "data")
        self.db_path = os.path.join(self.data_path, "project.db")
        
        #LOAD CONFIG
        config_file = os.path.join(self.config_path, "config.json")
        if os.path.exists(config_file):
            config_data = self.read_json(config_file)
        else:

            print(f"Warning: Config not found at {config_file}")
            config_data = {}

        self.usernames = config_data.get("usernames", [])
        self.software = config_data.get("software", [])
        self.webhook_url = config_data.get("discord_webhook_url", "")
        
        # Determine Home/Work Status
        self.current_user = os.getlogin()
        self.home_status = self.current_user not in self.usernames

        #SETUP LIBS
        self.libs_path = os.path.join(self.root_dir, "libs") # Or config/libs depending on your prefs
        # Ensure libs path is importable
        if self.libs_path not in sys.path:
            sys.path.insert(0, self.libs_path)

    # --- UTILITY METHODS ---
    
    def get_root_dir(self):
        return self.root_dir

    def read_json(self, file_path):
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading JSON {file_path}: {e}")
            return {}
            
    def get_libs_path(self):
        return self.libs_path

    # --- DATABASE METHODS ---

    def get_db_connection(self):
        """Creates a connection to the SQLite DB"""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found at {self.db_path}. Run init_db.py first.")
            
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Allows accessing columns by name
        conn.execute("PRAGMA foreign_keys = ON") # Enforce integrity
        return conn

    def get_all_shots(self):
        """Returns a list of all shots, sorted by code."""
        conn = self.get_db_connection()
        try:
            shots = conn.execute('SELECT * FROM shots ORDER BY code').fetchall()
            return shots
        finally:
            conn.close()

    def get_shot(self, shot_code):
        """Fetches a single shot's data."""
        conn = self.get_db_connection()
        try:
            shot = conn.execute('SELECT * FROM shots WHERE code = ?', (shot_code,)).fetchone()
            return shot
        finally:
            conn.close()

    # --- SHOT CREATION & MANAGEMENT ---

    def get_next_shot_code(self):
        """Scans the file system (40_shots) to find the next logical shot number."""
        shots_root = os.path.join(self.root_dir, '40_shots')
        
        if not os.path.exists(shots_root):
            return "stc_0010"

        highest_num = 0
        shot_pattern = re.compile(r'^stc_(\d{4})$')
        
        try:
            for item in os.listdir(shots_root):
                if os.path.isdir(os.path.join(shots_root, item)):
                    match = shot_pattern.match(item)
                    if match:
                        num = int(match.group(1))
                        if num > highest_num:
                            highest_num = num
        except Exception as e:
            print(f"Error scanning shots directory: {e}")
            return "stc_0010"

        next_num = highest_num + 10
        return f"stc_{next_num:04d}"

    def create_shot_structure(self, shot_code):
        """Generates folder structure on disk."""
        shots_root = os.path.join(self.root_dir, '40_shots')
        shot_path = os.path.join(shots_root, shot_code)

        if not os.path.exists(shot_path):
            os.makedirs(shot_path)
            
        for subfolder in self.SHOT_SUBFOLDERS:
            full_path = os.path.join(shot_path, subfolder.replace('/', os.sep))
            if not os.path.exists(full_path):
                os.makedirs(full_path)
        
        return shot_path

    def create_shot(self, shot_code, start, end, user):
        """Creates Shot in Database AND File System."""
        conn = self.get_db_connection()
        try:
            shot_id = str(uuid.uuid4())
            conn.execute(
                'INSERT INTO shots (id, code, frame_start, frame_end, user_assigned) VALUES (?, ?, ?, ?, ?)',
                (shot_id, shot_code, start, end, user)
            )
            conn.commit()
            print(f"DB: Shot {shot_code} logged.")
        except sqlite3.IntegrityError:
            print(f"DB: Shot {shot_code} already exists in DB, creating missing folders only.")
        finally:
            conn.close()

        # Create physical folders
        self.create_shot_structure(shot_code)

    def update_shot_frames(self, shot_code, new_start, new_end):
        """Updates frame range in DB."""
        conn = self.get_db_connection()
        try:
            conn.execute(
                'UPDATE shots SET frame_start = ?, frame_end = ? WHERE code = ?',
                (new_start, new_end, shot_code)
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating shot: {e}")
            return False
        finally:
            conn.close()
                 

    def delete_shot(self, shot_code):
        """Deletes a shot from DB (Folders are kept for safety)."""
        conn = self.get_db_connection()
        shots_root = os.path.join(self.root_dir, '40_shots')
        shot_path = os.path.join(shots_root, shot_code)
        
        try:
            shutil.rmtree(shot_path, ignore_errors=False)
            conn.execute('DELETE FROM shot_assets WHERE shot_code = ?', (shot_code,))
            conn.execute('DELETE FROM shots WHERE code = ?', (shot_code,))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting shot: {e}")
            return False
        finally:
            conn.close()

    # --- NOTIFICATIONS ---

    def send_discord_notification(self, message):
        if not self.webhook_url:
            return
        
        data = {"content": message}
        headers = {"Content-Type": "application/json"}
        try:
            requests.post(self.webhook_url, json=data, headers=headers, timeout=5)
        except Exception as e:
            print(f"Discord notification failed: {e}")