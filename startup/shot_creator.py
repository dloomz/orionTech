import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox

from utils.orionUtils import OrionUtils
orion_utils = OrionUtils()

# --- Configuration ---
SHOT_SUBFOLDERS = [
    "ANIM",
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
    "FX",
    "LIGHTING",
    "ROTO",
    "MATCHMOVE",
    "CAMERA",
    "3D_RENDERS",
    "2D_RENDERS",
]

class ShotCreatorApp:

    def __init__(self, root):
        self.root = root
        self.root.title("Orion Shot Creator")
        self.root.geometry("450x300")

        # We will set this later, after the UI is built
        self.project_root = ""

        # --- UI Widgets (No changes in this section) ---
        frame_root = tk.Frame(root, padx=10, pady=10)
        frame_root.pack(fill='x')

        self.lbl_root_path = tk.Label(frame_root, text="Project Root: Not Selected", anchor='w')
        self.lbl_root_path.pack(fill='x')

        btn_browse = tk.Button(frame_root, text="Browse...", command=self._select_root_dir)
        btn_browse.pack(pady=5)

        separator1 = tk.Frame(root, height=2, bd=1, relief=tk.SUNKEN)
        separator1.pack(fill='x', padx=5, pady=5)

        frame_next = tk.Frame(root, padx=10, pady=5)
        frame_next.pack(fill='x')

        self.lbl_next_shot = tk.Label(frame_next, text="Next Shot: -", font=('Helvetica', 10, 'bold'))
        self.lbl_next_shot.pack()

        btn_create_next = tk.Button(frame_next, text="Create Next Shot", command=self._create_next_shot)
        btn_create_next.pack(pady=5)

        separator2 = tk.Frame(root, height=2, bd=1, relief=tk.SUNKEN)
        separator2.pack(fill='x', padx=5, pady=5)

        frame_specific = tk.Frame(root, padx=10, pady=5)
        frame_specific.pack(fill='x')

        lbl_specific_shot = tk.Label(frame_specific, text="Create Specific Shot (e.g., 15 for s0015):")
        lbl_specific_shot.pack()

        self.entry_specific_shot = tk.Entry(frame_specific)
        self.entry_specific_shot.pack(pady=5)

        btn_create_specific = tk.Button(frame_specific, text="Create Specified Shot", command=self._create_specified_shot)
        btn_create_specific.pack()

        self.lbl_status = tk.Label(root, text="Welcome!", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.lbl_status.pack(side=tk.BOTTOM, fill=tk.X)

        orion_root_path = os.path.join(orion_utils.get_root_dir(), '40_shots')
        self._set_project_root(orion_root_path)

    def _set_project_root(self, path):

        if path and os.path.isdir(path):
            self.project_root = path
            self.lbl_root_path.config(text=f"Project Root: {path}")
            self.lbl_status.config(text=f"Default Orion root loaded successfully.")
            self._update_next_shot_label()
        else:
            # Handle cases where the default path is not found
            self.project_root = ""
            self.lbl_root_path.config(text="Project Root: Not Selected")
            self.lbl_status.config(text="Warning: Default Orion root not found.")
            self.lbl_next_shot.config(text="Next Shot: -")

    def _select_root_dir(self):

        path = filedialog.askdirectory(title="Select Project Root Folder")
        if path:
            # Use the new centralized method to update everything
            self._set_project_root(path)

    def _update_next_shot_label(self):

        if not self.project_root:
            return

        try:
            highest_num = 0
            shot_pattern = re.compile(r'^s(\d{4})$')
            for item in os.listdir(self.project_root):
                full_path = os.path.join(self.project_root, item)
                if os.path.isdir(full_path):
                    match = shot_pattern.match(item)
                    if match:
                        num = int(match.group(1))
                        if num > highest_num:
                            highest_num = num

            next_shot_num = highest_num + 10
            self.lbl_next_shot.config(text=f"Next Shot: s{next_shot_num:04d}")
        except Exception as e:
            self.lbl_status.config(text=f"Error reading directory: {e}")
            self.lbl_next_shot.config(text="Next Shot: Error")

    def _create_shot_directory(self, shot_number):

        if not self.project_root:
            messagebox.showerror("Error", "Please select a project root directory first.")
            return

        shot_name = f"s{shot_number:04d}"
        shot_path = os.path.join(self.project_root, shot_name)

        if os.path.exists(shot_path):
            messagebox.showwarning("Warning", f"Shot '{shot_name}' already exists.")
            self.lbl_status.config(text=f"Shot '{shot_name}' already exists.")
            return

        try:
            print(f"Creating shot structure for '{shot_name}'...")
            for subfolder in SHOT_SUBFOLDERS:
                full_path = os.path.join(shot_path, subfolder.replace('/', os.sep))
                os.makedirs(full_path, exist_ok=True)

            messagebox.showinfo("Success", f"Successfully created shot '{shot_name}'!")
            self.lbl_status.config(text=f"Successfully created shot '{shot_name}'.")
            self._update_next_shot_label()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create folders: {e}")
            self.lbl_status.config(text=f"Error: {e}")

    def _create_next_shot(self):

        next_shot_text = self.lbl_next_shot.cget("text")
        match = re.search(r's(\d{4})', next_shot_text)
        if match:
            shot_num = int(match.group(1))
            self._create_shot_directory(shot_num)
        else:
            messagebox.showerror("Error", "Could not determine the next shot number. Is a root folder selected?")

    def _create_specified_shot(self):

        shot_num_str = self.entry_specific_shot.get()
        if not shot_num_str:
            messagebox.showerror("Error", "Please enter a shot number.")
            return

        try:
            shot_num = int(shot_num_str)
            self._create_shot_directory(shot_num)
        except ValueError:
            messagebox.showerror("Error", "Invalid input. Please enter a whole number.")
            self.lbl_status.config(text="Error: Input must be a number.")


if __name__ == "__main__":
    app_root = tk.Tk()
    app = ShotCreatorApp(app_root)
    app_root.mainloop()