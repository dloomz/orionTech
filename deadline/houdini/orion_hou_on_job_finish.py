import sys
import time
import traceback

ORION_UTILS_DIR = "P:\\all_work\\studentGroups\\ORION_CORPORATION\\00_pipeline\\orionTech"

if ORION_UTILS_DIR not in sys.path:
    sys.path.append(ORION_UTILS_DIR)
    
try:
    from core.sheetsUtils import SheetsUtils
except ImportError:
    print("SheetsUtils not found. Google sheet features will be disabled.")
    SheetsUtils = None

def __main__(*args):
    deadline_plugin = args[0]
    job = deadline_plugin.GetJob()

    try:
        notify_enabled_str = job.GetJobExtraInfoKeyValueWithDefault("OrionDiscordNotify", "false")
        shot_context = job.GetJobEnvironmentKeyValue("ORI_SHOT_CONTEXT")
        
        if notify_enabled_str.lower() != 'true':
            deadline_plugin.LogInfo("Orion Discord notifications disabled for this job.")
            return

        from core.orionUtils import OrionUtils

        job_name = job.JobName
        user = job.JobUserName
        
        orion = OrionUtils()
        if not orion.webhook_url:
             deadline_plugin.LogWarning("Orion Discord webhook URL is not configured in config.json.")
             return

        message = (
            f"✅ **Houdini Render Finished:** `{job_name}`\n"
            f"> **User:** {user}\n"
        )
        orion.send_discord_notification(message)
        deadline_plugin.LogInfo("Sent Orion Discord finish notification.")

    except ImportError:
         deadline_plugin.LogWarning(f"!!! Discord Error: Could not import OrionUtils from '{ORION_UTILS_DIR}'. Is the path correct and accessible? \n{traceback.format_exc()}")
    except Exception as e:
        deadline_plugin.LogWarning(f"!!! Discord Error (on_job_finish): {e}\n{traceback.format_exc()}")
    try:
        progTracker = SheetsUtils(1) if SheetsUtils else None
        compTracker = SheetsUtils(3) if SheetsUtils else None
        
        progTracker.update_shot_value({shot_context}, "Renders", "Rendered")
        compTracker.update_shot_value({shot_context}, "CG Render", "New render")
        
    except Exception as e:
        deadline_plugin.LogWarning(f"!!! Sheets Error (on_job_start): {e}\n{traceback.format_exc()}")