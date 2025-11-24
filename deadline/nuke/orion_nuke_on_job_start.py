import sys
import traceback

#path to the directory containing orionUtils.py
ORION_UTILS_DIR = "P:\\all_work\\studentGroups\\ORION_CORPORATION\\00_pipeline\\orionTech" 
# ---

if ORION_UTILS_DIR not in sys.path:
    sys.path.append(ORION_UTILS_DIR)

def __main__(*args):
    deadline_plugin = args[0]
    job = deadline_plugin.GetJob()

    try:
        #check if notifications are enabled via ExtraInfoKeyValue
        notify_enabled_str = job.GetJobExtraInfoKeyValueWithDefault("OrionDiscordNotify", "false")

        if notify_enabled_str.lower() != 'true':
            deadline_plugin.LogInfo("Orion Discord notifications disabled for this job.")
            return

        from core.orionUtils import OrionUtils

        job_name = job.JobName
        user = job.JobUserName
        comment = job.JobComment
        pool = job.JobPool
        priority = job.JobPriority
        task_count = job.JobTaskCount

        orion = OrionUtils() 
        if not orion.webhook_url:
             deadline_plugin.LogWarning("Orion Discord webhook URL is not configured in config.json.")
             return

        message = (
            f"🚀 **Nuke Render Started:** `{job_name}`\n"
            f"> **User:** {user}\n"
            f"> **Pool:** {pool} | **Priority:** {priority}\n"
            f"> **Frames:** {job.JobFrames} ({task_count} tasks)\n"
            f"> **Comment:** {comment}"
        )
        orion.send_discord_notification(message)
        deadline_plugin.LogInfo("Sent Orion Discord start notification.")

    except ImportError:
         deadline_plugin.LogWarning(f"!!! Discord Error: Could not import OrionUtils from '{ORION_UTILS_DIR}'. Is the path correct and accessible? \n{traceback.format_exc()}")
    except Exception as e:
        deadline_plugin.LogWarning(f"!!! Discord Error (on_job_start): {e}\n{traceback.format_exc()}")
