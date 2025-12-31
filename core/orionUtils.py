import os
import json
import sys
import sqlite3
import uuid
import re
import traceback
import subprocess
import shutil
from datetime import datetime 

class OrionUtils():
    
    # Standard Folder Structure
    SHOT_SUBFOLDERS = [
        "ANIM",
        "COMP/Apps/Nuke/Scripts", #nuke files .nk
        "COMP/Apps/Photoshop", #photoshop clean plates
        "COMP/Apps/Syntheyes", #syntheyes
        "COMP/Apps/Mocha_Pro",
        "COMP/Plates/Source", #for 4k exrs
        "COMP/Plates/Comp", #footage as exrs
        "COMP/Plates/Offline", #low res mp4 for edit, for ref
        "COMP/Prep/Denoise",
        "COMP/Review/IMG",
        "COMP/Review/VID",
        "COMP/Tools",
        "CFX",
        "FX",
        "LIGHTING",
        "CAMERA",
        "CAMERA/PLATES", #tiff sequences for footage
        "3D_RENDERS", #cg renders after lighting
        "2D_RENDERS", #comped renders
    ]
    
    ASSET_TASKS = [
        "GEO",
        "RIG",
        "USD",
        "TEX",
        "CFX",
        "GRM",
        "REF",
    ]
    
    # ASSET_TASKS = {
    #     "GEO": ["WORK", "PUBLISH"],
    #     "SCULPT": ["WORK", "PUBLISH"],
    #     "RIG": ["WORK", "PUBLISH"],
    #     "USD": ["WORK", "PUBLISH"],
    #     "TEX": ["WORK", "PUBLISH"]
    # }

    def __init__(self, check_schema=True):
        
        # DYNAMIC ROOT DETECTION
        current_script_path = os.path.abspath(__file__)
        self.pipeline_dir = os.path.dirname(os.path.dirname(current_script_path))
        
        # LOAD .ENV
        self.config_path = os.path.join(self.pipeline_dir, "config")
        self.data_path = os.path.join(self.pipeline_dir, "data")
        self.db_path = os.path.join(self.data_path, "project.db")
        self.env_file = os.path.join(self.data_path, ".env")
        
        self.load_env_file()

        self.webhook_url = os.environ.get("ORI_DISCORD_WEBHOOK", "")
        self.fps = int(os.environ.get("ORI_FPS", "24"))
        
        raw_users = os.environ.get("ORI_USERNAME", "")
        self.usernames = [u.strip() for u in raw_users.split(",") if u.strip()]
        
        raw_software = os.environ.get("ORI_SOFTWARE", "")
        self.software = [s.strip() for s in raw_software.split(",") if s.strip()]
        
        # PATH LOGIC
        project_root = os.environ.get("ORI_ROOT_PATH", "")
        if project_root and os.path.exists(project_root):
            self.root_dir = project_root
        else:
            home_root = "O:\\"
            work_root = "P:\\all_work\\studentGroups\\ORION_CORPORATION"
            self.current_user = os.getlogin()
            
            if self.current_user in self.usernames:
                self.root_dir = work_root 
            else:
                self.root_dir = home_root
        
        self.current_user = os.getlogin()
        self.home_status = self.current_user not in self.usernames
        self.libs_path = os.path.join(self.root_dir,"60_config", "libs") 

        #ensure DB is up to date
        if check_schema:
            self.check_and_update_schema()

    def load_env_file(self):
        if not os.path.exists(self.env_file):
            return
        try:
            with open(self.env_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"): continue
                    if "=" in line:
                        key, value = line.split("=", 1)
                        os.environ[key.strip()] = value.strip().strip("'").strip('"')
        except Exception as e:
            print(f"Failed to parse .env file: {e}")

    def get_root_dir(self):
        return self.root_dir
    
    def get_usernames(self):
        return self.usernames
    
    def is_at_home(self):
        return self.home_status
    
    def get_libs_path(self):
        return self.libs_path

    def read_json(self, file_path):
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading JSON {file_path}: {e}")
            return {}

    def get_relative_path(self, full_path):
        try:
            abs_full = os.path.abspath(full_path)
            abs_root = os.path.abspath(self.root_dir)
            if abs_full.startswith(abs_root):
                rel_path = os.path.relpath(abs_full, abs_root)
                return rel_path
            
            if "ORION_CORPORATION" in abs_full:
                 parts = abs_full.split("ORION_CORPORATION")
                 if len(parts) > 1:
                     return parts[1].lstrip(os.sep)
            return full_path 
        except Exception as e:
            print(f"Path conversion error: {e}")
            return full_path

    # --- DATABASE METHODS ---

    def get_db_connection(self):
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found at {self.db_path}")
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row 
        conn.execute("PRAGMA foreign_keys = ON") 
        return conn

    def check_and_update_schema(self):
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # SHOTS TABLE
            cursor.execute('''CREATE TABLE IF NOT EXISTS shots (
                id TEXT PRIMARY KEY,
                code TEXT UNIQUE,
                frame_start INTEGER,
                frame_end INTEGER,
                shot_path TEXT,
                description TEXT,
                discord_thread_id TEXT,
                thumbnail_path TEXT
            )''')
            
            # ASSETS TABLE
            cursor.execute('''CREATE TABLE IF NOT EXISTS assets (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE,
                type TEXT,
                path TEXT,
                description TEXT,
                thumbnail_path TEXT
            )''')
            
            # --- MIGRATION LOGIC ---
            
            # 1. Check SHOTS columns
            cursor.execute("PRAGMA table_info(shots)")
            shot_cols = [info[1] for info in cursor.fetchall()]
            if "description" not in shot_cols: cursor.execute("ALTER TABLE shots ADD COLUMN description TEXT")
            if "discord_thread_id" not in shot_cols: cursor.execute("ALTER TABLE shots ADD COLUMN discord_thread_id TEXT")
            if "thumbnail_path" not in shot_cols: cursor.execute("ALTER TABLE shots ADD COLUMN thumbnail_path TEXT")

            # 2. Check ASSETS columns (THIS FIXES YOUR ERROR)
            cursor.execute("PRAGMA table_info(assets)")
            asset_cols = [info[1] for info in cursor.fetchall()]
            if "description" not in asset_cols: cursor.execute("ALTER TABLE assets ADD COLUMN description TEXT")
            if "thumbnail_path" not in asset_cols: cursor.execute("ALTER TABLE assets ADD COLUMN thumbnail_path TEXT")

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Schema Check Failed: {e}")

    def check_shot_exists_in_db(self, shot_code):
        conn = self.get_db_connection()
        try:
            row = conn.execute('SELECT 1 FROM shots WHERE code = ?', (shot_code,)).fetchone()
            return row is not None
        finally:
            conn.close()

    def rename_shot_code_in_db(self, old_code, new_code):
        conn = self.get_db_connection()
        try:
            existing = conn.execute('SELECT 1 FROM shots WHERE code = ?', (new_code,)).fetchone()
            if existing:
                return False, "New code already exists in DB."

            conn.execute('UPDATE shots SET code = ? WHERE code = ?', (new_code, old_code))
            try:
                conn.execute('UPDATE shot_assets SET shot_code = ? WHERE shot_code = ?', (new_code, old_code))
            except: pass 
            
            conn.commit()
            return True, "Updated"
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

    def register_shot_path(self, shot_code, full_path):
        conn = self.get_db_connection()
        rel_path = self.get_relative_path(full_path)
        try:
            conn.execute('UPDATE shots SET shot_path = ? WHERE code = ?', (rel_path, shot_code))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error registering path: {e}")
            return False
        finally:
            conn.close()
    
    def get_shot_thread_id(self, shot_code):
        conn = self.get_db_connection()
        try:
            cursor = conn.execute("PRAGMA table_info(shots)")
            columns = [info[1] for info in cursor.fetchall()]
            if "discord_thread_id" not in columns: return None

            row = conn.execute('SELECT discord_thread_id FROM shots WHERE code = ?', (shot_code,)).fetchone()
            if row and row['discord_thread_id']:
                return row['discord_thread_id']
            return None
        except Exception as e:
            print(f"DB Error fetching thread ID: {e}")
            return None
        finally:
            conn.close()

    # --- TAGGING SYSTEM (FIXED PERMISSION ERROR) ---

    def create_meta_tag(self, folder_path, shot_code, data=None, shot_id=None):
        """
        Creates orion_meta.json.
        FIX: Handles Windows hidden file permission errors by unhiding before writing.
        """
        if not os.path.exists(folder_path):
            return False

        # Fallback to shot_code if no specific ID provided
        if not shot_id:
            shot_id = shot_code

        rel_path = self.get_relative_path(folder_path)

        meta_data = {
            "code": shot_code,
            "id": shot_id,
            "original_path": rel_path, 
            "created_by": os.getlogin(),
            "last_updated": str(datetime.now())
        }
        if data: meta_data.update(data)

        json_path = os.path.join(folder_path, "orion_meta.json")
        
        # --- PERMISSION FIX START ---
        # If file exists and is hidden, unhide it so we can write to it
        if os.name == 'nt' and os.path.exists(json_path):
            subprocess.run(["attrib", "-h", json_path], check=False, shell=True)
        # ----------------------------

        try:
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    try:
                        existing = json.load(f)
                        existing.update(meta_data)
                        meta_data = existing
                    except: pass

            with open(json_path, 'w') as f:
                json.dump(meta_data, f, indent=4)
            
            # Handle ID Markers
            for file in os.listdir(folder_path):
                if file.startswith(".id_") and file != f".id_{shot_id}":
                    try: os.remove(os.path.join(folder_path, file))
                    except: pass

            id_marker = os.path.join(folder_path, f".id_{shot_id}")
            if not os.path.exists(id_marker):
                with open(id_marker, 'w') as f:
                    f.write(f"ID: {shot_id}\nCODE: {shot_code}")
            
            # Re-apply Hidden Attribute
            if os.name == 'nt':
                subprocess.run(["attrib", "+h", json_path], check=False, shell=True)
                subprocess.run(["attrib", "+h", id_marker], check=False, shell=True)
            
            return True
        except Exception as e:
            print(f"Tagging failed: {e}")
            return False

    def asset_create_meta_tag(self, folder_path, asset_code, data=None, asset_id=None):
        if not os.path.exists(folder_path): return False
        if not asset_id: asset_id = asset_code

        meta_data = {
            "code": asset_code,
            "id": asset_id,
            "original_path": self.get_relative_path(folder_path), 
            "created_by": os.getlogin(),
            "last_updated": str(datetime.now())
        }
        if data: meta_data.update(data)

        json_path = os.path.join(folder_path, "orion_meta.json")
        
        # Windows hidden file fix
        if os.name == 'nt' and os.path.exists(json_path):
            subprocess.run(["attrib", "-h", json_path], check=False, shell=True)

        try:
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    try:
                        existing = json.load(f)
                        existing.update(meta_data)
                        meta_data = existing
                    except: pass

            with open(json_path, 'w') as f:
                json.dump(meta_data, f, indent=4)
            
            # Re-hide
            if os.name == 'nt':
                subprocess.run(["attrib", "+h", json_path], check=False, shell=True)
            return True
        except Exception as e:
            print(f"Tagging failed: {e}")
            return False

    # --- ASSET METHODS ---

    def asset_create_meta_tag(self, folder_path, asset_code, data=None, asset_id=None):
        if not os.path.exists(folder_path): return False
        if not asset_id: asset_id = asset_code

        # FIX: Variable names match arguments now
        meta_data = {
            "code": asset_code,
            "id": asset_id,
            "original_path": self.get_relative_path(folder_path), 
            "created_by": os.getlogin(),
            "last_updated": str(datetime.now())
        }
        if data: meta_data.update(data)

        json_path = os.path.join(folder_path, "orion_meta.json")
        
        # Windows hidden file fix (same as shots)
        if os.name == 'nt' and os.path.exists(json_path):
            subprocess.run(["attrib", "-h", json_path], check=False, shell=True)

        try:
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    try:
                        existing = json.load(f)
                        existing.update(meta_data)
                        meta_data = existing
                    except: pass

            with open(json_path, 'w') as f:
                json.dump(meta_data, f, indent=4)
            
            # Re-hide
            if os.name == 'nt':
                subprocess.run(["attrib", "+h", json_path], check=False, shell=True)
            return True
        except Exception as e:
            print(f"Tagging failed: {e}")
            return False

    def create_asset(self, name, asset_type, user, description="", thumbnail_path=""):
        # Structure: 30_assets/name
        asset_path = os.path.join(self.root_dir, '30_assets', name)

        if not os.path.exists(asset_path):
            os.makedirs(asset_path)
            
        for subfolder in self.ASSET_TASKS:
            full_path = os.path.join(asset_path, subfolder.replace('/', os.sep))
            if not os.path.exists(full_path):
                os.makedirs(full_path)
        
        # # Create Folders based on ASSET_TASKS
        # for task_group, subfolders in self.ASSET_TASKS.items():
        #     # Create main group (e.g., GEO)
        #     group_path = os.path.join(asset_path, task_group)
        #     os.makedirs(group_path, exist_ok=True)
            
        #     # Create subfolders (e.g., WORK, PUBLISH)
        #     for sub in subfolders:
        #         os.makedirs(os.path.join(group_path, sub), exist_ok=True)
                
        new_id = str(uuid.uuid4())
        self.asset_create_meta_tag(asset_path, name, {"type": "asset", "asset_type": asset_type, "description": description}, asset_id=new_id)
        
        conn = self.get_db_connection()
        try:
  
            rel_path = self.get_relative_path(asset_path)
            
            conn.execute(
                'INSERT OR REPLACE INTO assets (id, name, type, path, description, thumbnail_path) VALUES (?, ?, ?, ?, ?, ?)',
                (new_id, name, asset_type, rel_path, description, thumbnail_path)
            )
            conn.commit()
            return new_id
        except Exception as e:
            print(f"Asset Creation Error: {e}")
            raise e
        finally: conn.close()

    def delete_asset(self, name):
        conn = self.get_db_connection()
        try:
            conn.execute('DELETE FROM assets WHERE name = ?', (name,))
            conn.commit()
            
            #remove directory
            full_path = os.path.join(self.root_dir, '30_assets', name)
            if os.path.exists(full_path):
                shutil.rmtree(full_path, ignore_errors=True)
            return True
        except Exception as e:
            print(f"Delete Asset Error: {e}")
            return False
        finally: conn.close()
        
    def get_all_assets(self):
        """
        Retrieves all rows from the 'assets' table, ordered by name.
        Used by the UI to populate the Assets list.
        """
        conn = self.get_db_connection()
        try:
            return conn.execute('SELECT * FROM assets ORDER BY name').fetchall()
        except Exception as e:
            print(f"Error fetching all assets: {e}")
            return []
        finally:
            conn.close()

    def get_asset(self, name):
        """
        Retrieves a single row from the 'assets' table by name.
        Used by the UI when entering Edit Mode for an asset.
        """
        conn = self.get_db_connection()
        try:
            return conn.execute('SELECT * FROM assets WHERE name = ?', (name,)).fetchone()
        except Exception as e:
            print(f"Error fetching asset '{name}': {e}")
            return None
        finally:
            conn.close()

    # --- FOLDER CREATION ---

    def get_next_shot_code(self):
        shots_root = os.path.join(self.root_dir, '40_shots')
        if not os.path.exists(shots_root): return "stc_0010"
        highest = 0
        pat = re.compile(r'^stc_(\d{4})$')
        try:
            for item in os.listdir(shots_root):
                if os.path.isdir(os.path.join(shots_root, item)):
                    m = pat.match(item)
                    if m:
                        num = int(m.group(1))
                        if num > highest: highest = num
        except: pass
        return f"stc_{(highest + 10):04d}"

    def create_shot_structure(self, shot_code, base_path=None):
        shots_root = base_path if base_path else os.path.join(self.root_dir, '40_shots')
        shot_path = os.path.join(shots_root, shot_code)

        if not os.path.exists(shot_path):
            os.makedirs(shot_path)
            
        for subfolder in self.SHOT_SUBFOLDERS:
            full_path = os.path.join(shot_path, subfolder.replace('/', os.sep))
            if not os.path.exists(full_path):
                os.makedirs(full_path)
        
        return shot_path

    def create_shot(self, shot_code, start, end, user, description="", thumbnail_path=""):
        """Creates a shot with unique UUID and supports Description/Thumbnail."""
        self.check_and_update_schema()
        
        shot_path = self.create_shot_structure(shot_code)
        
        # GENERATE UUID FOR ID
        new_id = str(uuid.uuid4())

        # Create tags (Pass UUID as shot_id)
        self.create_meta_tag(shot_path, shot_code, {"type": "shot", "description": description}, shot_id=new_id)
        
        conn = self.get_db_connection()
        try:
            exists = conn.execute("SELECT 1 FROM shots WHERE code = ?", (shot_code,)).fetchone()
            rel_path = self.get_relative_path(shot_path)

            if not exists:
                conn.execute(
                    'INSERT INTO shots (id, code, frame_start, frame_end, user_assigned, shot_path, description, thumbnail_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                    (new_id, shot_code, start, end, user, rel_path, description, thumbnail_path)
                )
            else:
                conn.execute('UPDATE shots SET shot_path = ?, description = ?, thumbnail_path = ? WHERE code = ?', (rel_path, description, thumbnail_path, shot_code))
            conn.commit()
            return new_id
        except Exception as e:
            print(f"DB Insert Error: {e}")
            return None
        finally: conn.close()

    def get_all_shots(self):
        conn = self.get_db_connection()
        try: return conn.execute('SELECT * FROM shots ORDER BY code').fetchall()
        finally: conn.close()

    def get_shot(self, code):
        conn = self.get_db_connection()
        try: return conn.execute('SELECT * FROM shots WHERE code = ?', (code,)).fetchone()
        finally: conn.close()

    def update_shot_frames(self, code, start, end):
        conn = self.get_db_connection()
        try:
            conn.execute('UPDATE shots SET frame_start = ?, frame_end = ? WHERE code = ?', (start, end, code))
            conn.commit()
            return True
        except: return False
        finally: conn.close()

    def delete_shot(self, code):
        conn = self.get_db_connection()
        try:
            conn.execute('DELETE FROM shots WHERE code = ?', (code,))
            conn.commit()
            path = os.path.join(self.root_dir, '40_shots', code)
            shutil.rmtree(path, ignore_errors=True)
            return True
        except: return False
        finally: conn.close()

    # --- NOTIFICATIONS ---

    def send_discord_notification(self, message):
        if self.libs_path not in sys.path:
            sys.path.insert(0, self.libs_path)

        try:
            import requests
        except:
            print("ORION WARNING: Unable to load requests module, discord functions will fail.")
            return
        
        if not self.webhook_url:
            return
        
        data = {"content": message}
        headers = {"Content-Type": "application/json"}
        try:
            requests.post(self.webhook_url, json=data, headers=headers, timeout=5)
        except Exception as e:
            print(f"Discord notification failed: {e}")