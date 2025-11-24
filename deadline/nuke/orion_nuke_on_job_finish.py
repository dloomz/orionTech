import sys
import time
import traceback

ORION_UTILS_DIR = "P:\\all_work\\studentGroups\\ORION_CORPORATION\\00_pipeline\\orionTech\\startup"

if ORION_UTILS_DIR not in sys.path:
    sys.path.append(ORION_UTILS_DIR)

def __main__(*args):
    deadline_plugin = args[0]
    job = deadline_plugin.GetJob()

    try:
        notify_enabled_str = job.GetJobExtraInfoKeyValueWithDefault("OrionDiscordNotify", "false")
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
            f"✅ **Nuke Render Finished:** `{job_name}`\n"
            f"> **User:** {user}\n"
        )
        orion.send_discord_notification(message)
        deadline_plugin.LogInfo("Sent Orion Discord finish notification.")

    except ImportError:
         deadline_plugin.LogWarning(f"!!! Discord Error: Could not import OrionUtils from '{ORION_UTILS_DIR}'. Is the path correct and accessible? \n{traceback.format_exc()}")
    except Exception as e:
        deadline_plugin.LogWarning(f"!!! Discord Error (on_job_finish): {e}\n{traceback.format_exc()}")