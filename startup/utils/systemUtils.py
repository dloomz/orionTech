import os
import subprocess
import ctypes

class SystemUtils:

    def run_terminal_command(self, command):
        """
        Runs a command in the terminal.

        Args:
            command (str): The command to execute.
        """
        try:
            subprocess.run(command, shell=True, check=True)
            print(f"Successfully executed command: {command}")
        except subprocess.CalledProcessError as e:
            print(f"Error executing command: {e}")

    def change_wallpaper(self, image_path):
        """
        Changes the desktop wallpaper.
        Args:
            image_path (str): The full path to the wallpaper image.
        """
        if os.name == 'nt': # Check if the OS is Windows
            try:
                ctypes.windll.user32.SystemParametersInfoW(20, 0, image_path, 3)
                print(f"Wallpaper changed to {image_path}")
            except Exception as e:
                print(f"Error changing wallpaper: {e}")
        else:
            print("Wallpaper change is only supported on Windows in this example.")