<<<<<<< HEAD
def add_line_to_file(self, file_path, line_to_add):
        """
        Appends a new line to the end of a file.

        Args:
            file_path (str): The full path to the file.
            line_to_add (str): The line of text to add.
        """
        try:
            with open(file_path, 'a') as f:
                f.write(f"\n{line_to_add}")
            print(f"Successfully added line to {file_path}")
        except FileNotFoundError:
            print(f"Error: The file at {file_path} was not found.")
        except Exception as e:
            print(f"An error occurred: {e}")
=======
import os
from datetime import datetime

class FileUtils():
    
    def __init__(self):
        # variables here
        pass
         
    def get_modified_files(self, path):

        config_dir = path
        config_files = os.listdir(config_dir)
        current_day = datetime.today().date()

        files_modified = []

        for f in config_files:
            full_path = os.path.join(config_dir, f)
            mtime = os.path.getmtime(full_path)
            file_date = datetime.fromtimestamp(mtime).date()

            if file_date == current_day:
                files_modified.append(f)

        return files_modified


>>>>>>> 793ea1eb118d93a8ef4924ca44dace7529893d41
