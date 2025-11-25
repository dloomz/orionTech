import sqlite3
# Adjust path to your project.db
conn = sqlite3.connect(r'P:\all_work\studentGroups\ORION_CORPORATION\00_pipeline\orionTech\data\project.db') 
try:
    conn.execute("ALTER TABLE shots ADD COLUMN shot_path TEXT")
    print("Column 'shot_path' added successfully.")
except sqlite3.OperationalError:
    print("Column already exists.")
conn.commit()
conn.close()