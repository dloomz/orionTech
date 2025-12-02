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
        
        # DYNAMIC ROOT DETECTION
        current_script_path = os.path.abspath(__file__)
        # go up two levels: core/ -> root/
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
            # Fallback detection
            home_root = "O:\\"
            work_root = "P:\\all_work\\studentGroups\\ORION_CORPORATION"
            self.current_user = os.getlogin()
            
            if self.current_user in self.usernames:
                self.root_dir = work_root 
            else:
                self.root_dir = home_root
        
        # Determine Home/Work Status
        self.current_user = os.getlogin()
        if self.current_user in self.usernames:
            self.home_status = False  # At work
        else:
            self.home_status = True   # At home

        self.libs_path = os.path.join(self.root_dir,"60_config", "libs") 

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
        """
        Converts an absolute path to a path relative to the project root.
        Example: P:\...\ORION_CORPORATION\00_pipeline\40_shots\stc_0010 
        Returns: 00_pipeline\40_shots\stc_0010
        """
        try:
            # Ensure we are working with absolute paths
            abs_full = os.path.abspath(full_path)
            abs_root = os.path.abspath(self.root_dir)
            
            # This handles drive letter mismatches automatically if the root is correct
            if abs_full.startswith(abs_root):
                rel_path = os.path.relpath(abs_full, abs_root)
                return rel_path
            
            # Fallback: simple string replacement if paths are somehow divergent
            # but represent the same location
            if "ORION_CORPORATION" in abs_full:
                 parts = abs_full.split("ORION_CORPORATION")
                 if len(parts) > 1:
                     return parts[1].lstrip(os.sep)
            
            return full_path # Return original if conversion fails
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

    def check_shot_exists_in_db(self, shot_code):
        """Checks if a shot code exists in the DB."""
        conn = self.get_db_connection()
        try:
            row = conn.execute('SELECT 1 FROM shots WHERE code = ?', (shot_code,)).fetchone()
            return row is not None
        finally:
            conn.close()

    def rename_shot_code_in_db(self, old_code, new_code):
        """Updates the shot code in the database (e.g. stc0010 -> stc_0010)."""
        conn = self.get_db_connection()
        try:
            # Check if new code already taken
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
        """Updates the shot_path in the database using RELATIVE path."""
        conn = self.get_db_connection()
        # Convert to relative path before storing
        rel_path = self.get_relative_path(full_path)
        
        try:
            # Ensure column exists
            cursor = conn.execute("PRAGMA table_info(shots)")
            cols = [c[1] for c in cursor.fetchall()]
            if "shot_path" not in cols:
                conn.execute("ALTER TABLE shots ADD COLUMN shot_path TEXT")
            
            conn.execute('UPDATE shots SET shot_path = ? WHERE code = ?', (rel_path, shot_code))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error registering path: {e}")
            return False
        finally:
            conn.close()

    def simplify_shot_id(self, shot_code):
        """
        REPLACES the long UUID in the 'id' column with the clean 'code'.
        """
        conn = self.get_db_connection()
        try:
            conn.execute('UPDATE shots SET id = code WHERE code = ?', (shot_code,))
            conn.commit()
            print(f"DB: Simplified ID for {shot_code}")
            return True
        except Exception as e:
            print(f"Error simplifying ID: {e}")
            return False
        finally:
            conn.close()
    
    def get_shot_thread_id(self, shot_code):
        """Fetches the Discord Thread ID for a specific shot from the DB."""
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

    # --- TAGGING SYSTEM ---

    def create_meta_tag(self, folder_path, unique_code, data=None):
        """Creates orion_meta.json with RELATIVE path and .id_CODE marker."""
        if not os.path.exists(folder_path):
            return False

        # Convert to relative path before storing
        rel_path = self.get_relative_path(folder_path)

        meta_data = {
            "code": unique_code,
            "original_path": rel_path, 
            "created_by": os.getlogin(),
            "last_updated": str(datetime.now())
        }
        if data: meta_data.update(data)

        json_path = os.path.join(folder_path, "orion_meta.json")
        
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
            
            # ID Marker
            for file in os.listdir(folder_path):
                if file.startswith(".id_") and file != f".id_{unique_code}":
                    try: os.remove(os.path.join(folder_path, file))
                    except: pass

            id_marker = os.path.join(folder_path, f".id_{unique_code}")
            if not os.path.exists(id_marker):
                with open(id_marker, 'w') as f:
                    f.write(f"ID: {unique_code}")
            
            if os.name == 'nt':
                subprocess.run(["attrib", "+h", json_path], check=False, shell=True)
                subprocess.run(["attrib", "+h", id_marker], check=False, shell=True)
            
            return True
        except Exception as e:
            print(f"Tagging failed: {e}")
            return False

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

    def create_shot(self, shot_code, start, end, user):
        """Standard creation method."""
        shot_path = self.create_shot_structure(shot_code)
        
        # Tags handle path internally now
        self.create_meta_tag(shot_path, shot_code, {"type": "shot"})
        
        conn = self.get_db_connection()
        try:
            shot_id = shot_code 
            exists = conn.execute("SELECT 1 FROM shots WHERE code = ?", (shot_code,)).fetchone()
            
            # Get relative path for DB
            rel_path = self.get_relative_path(shot_path)

            if not exists:
                conn.execute(
                    'INSERT INTO shots (id, code, frame_start, frame_end, user_assigned, shot_path) VALUES (?, ?, ?, ?, ?, ?)',
                    (shot_id, shot_code, start, end, user, rel_path)
                )
            else:
                conn.execute('UPDATE shots SET shot_path = ? WHERE code = ?', (rel_path, shot_code))
            conn.commit()
        except: pass
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
        # Ensure libs path is importable
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