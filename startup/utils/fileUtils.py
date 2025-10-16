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