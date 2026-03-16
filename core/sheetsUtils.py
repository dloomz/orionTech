import sys

libs_path = r"P:\\all_work\\studentGroups\\ORION_CORPORATION\\60_config\\libs"

if libs_path not in sys.path:
    sys.path.insert(0, libs_path)

try:
    import gspread

except Exception as e:

    print(f"flop {e}")

SPREADSHEET_URL = r"https://docs.google.com/spreadsheets/d/1HHrXjXcD7V49V-kJ0KLhjyjwAtcrB1RidioTwZHWbc0/edit?gid=623638562#gid=623638562"
SPREADSHEET_ID = r"1HHrXjXcD7V49V-kJ0KLhjyjwAtcrB1RidioTwZHWbc0"
SHEET_ID = r"623638562"

class SheetsUtils:
    def __init__(self, Sheet):
        #setup connection
        self.gc = gspread.service_account(filename=r"P:\all_work\studentGroups\ORION_CORPORATION\00_pipeline\orionTech\data\orion-481810-8d30a4bccaa6.json")
        self.sh = self.gc.open_by_key(SPREADSHEET_ID)
        
        self.ws = self.sh.get_worksheet(int(Sheet))
        
        #fetch all data and headers 
        self.all_values = self.ws.get_all_values()
        self.headers = self.all_values[2] #row 3 is index 2
        
        #create map of header names to their column index number
        #example: {'Shot Code': 1, 'Description': 3}
        self.header_map = {name: i for i, name in enumerate(self.headers)}

    def get_shot_data(self, shot_code):
        #find row index where column B (index 1) matches the shot code
        #start searching from row 4 (index 3)
        target_row = None
        row_number = None
        
        for idx, row in enumerate(self.all_values[3:], start=3):
            if len(row) > 1 and row[1] == shot_code:
                target_row = row
                row_number = idx
                break
        
        if target_row:
            print(f"Full Data for {shot_code}")
            for header, value in zip(self.headers, target_row):
                if header:
                    print(f"{header}: {value}")
            return row_number #return in case 
        else:
            print(f"Shot {shot_code} not found.")
            return None

    def get_specific_value(self, shot_code, header_name):
        #check if header exists
        if header_name not in self.header_map:
            print(f"Error: Header '{header_name}' does not exist.")
            return

        col_index = self.header_map[header_name]
        
        #reuse logic to find the row
        for row in self.all_values[3:]:
            if len(row) > 1 and row[1] == shot_code:
                value = row[col_index]

                return value
        
        print(f"Shot {shot_code} not found.")

    def update_shot_value(self, shot_code, header_name, new_value):
        
        #get row number using our first function
        row_index = -1
        
        #refresh data
        self.all_values = self.ws.get_all_values()
        
        for i, row in enumerate(self.all_values):
            #skip header rows
            if i < 3: continue
            if len(row) > 1 and row[1] == shot_code:
                row_index = i + 1 
                break
        
        if row_index == -1:
            print("Shot not found, cannot update.")
            return

        if header_name in self.header_map:
            col_index = self.header_map[header_name] + 1 
            
            #update specific cell on sheets
            self.ws.update_cell(row_index, col_index, new_value)
            print(f"Updated {shot_code} [{header_name}] to: {new_value}")
        else:
            print(f"Header '{header_name}' invalid.")

    def get_shots_by_artist(self, artist_name):
        # find all shots assigned to specific person
        print(f"Finding shots for {artist_name}")
        
        if 'Comper' not in self.header_map:
            print("Column 'Comper' not found.")
            return

        artist_col_idx = self.header_map['Comper']
        
        found_any = False
        for row in self.all_values[3:]:
            if len(row) > artist_col_idx and row[artist_col_idx] == artist_name:
                print(f"Shot: {row[1]} | Status: {row[artist_col_idx]}")
                found_any = True
                
        if not found_any:
            print("No shots found for this artist.")

# EXAMPLES

#init
# compTracker = SheetsUtils(3)
# progTracker = SheetsUtils(1)

# # view all data for one shot
# # tracker.get_shot_data("stc_0010")

# # view just one specific column
# print(progTracker.get_specific_value("stc_0063", "Renders"))

# update a value (e.g. assigning a comper)
# tracker.update_shot_value("stc_0010", "CG Render", "New render")

# # useful extra: find all shots for 'Shruthi'
# tracker.get_shots_by_artist("Shruthi")
