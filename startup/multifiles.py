from core.config_manager import OrionUtils
import os

orion = OrionUtils()
pref_path = "O:\\00_pipeline\\userPrefs"

users = os.listdir(pref_path)
software = orion.software

for u in users:
    for s in software:
        outputs = os.path.join(pref_path, u, s)
        os.makedirs(outputs)
        print(outputs)
