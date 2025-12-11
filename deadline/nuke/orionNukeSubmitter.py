from __future__ import print_function
import nuke
import nukescripts
import os
import subprocess
import traceback
from tempfile import NamedTemporaryFile
import locale
import sys

#config
ORION_STARTUP_PATH = "P:\\all_work\\studentGroups\\ORION_CORPORATION\\00_pipeline\\orionTech\\startup"
EVENT_SCRIPT_DIR = "P:\\all_work\\studentGroups\\ORION_CORPORATION\\00_pipeline\\orionTech\\deadline\\nuke"

def get_deadline_command():
    """Finds the deadlinecommand executable."""
    #force path due to error
    forced_path = r"C:\Program Files\Thinkbox\Deadline10\bin\deadlinecommand.exe" 
    print(f"DEBUG: Attempting to use forced path: {forced_path}") 
    if os.path.exists(forced_path):
        print(f"DEBUG: Forced path exists.")
        return forced_path
    else:
         print(f"ERROR: Forced path does not exist: {forced_path}")
         nuke.message(f"ERROR: Hardcoded Deadline Command path not found:\n{forced_path}")
         #fall back just in case something is really weird
         return "deadlinecommand"

def call_deadline_command(arguments, hide_window=True):
    """Executes deadlinecommand with given arguments."""
    deadline_command = get_deadline_command()
    command = [deadline_command] + arguments

    startupinfo = None
    if hide_window and os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    try:
        proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo, universal_newlines=True)
        output, errors = proc.communicate()
        if proc.returncode != 0:
            print(f"Deadline Command Error:\n{errors}")
            return f"Error: {errors}"
        return output
    except OSError as e:
        print(f"Error executing deadlinecommand: {e}. Is it in your PATH or DEADLINE_PATH?")
        nuke.message(f"Error executing deadlinecommand: {e}. Is it in your PATH or DEADLINE_PATH?")
        return f"Error: {e}"
    except Exception as e:
        print(f"An unexpected error occurred: {e}\n{traceback.format_exc()}")
        return f"Error: {e}"

#submission dialog 
class OrionSubmitDialog(nukescripts.PythonPanel):
    def __init__(self, pools, groups, max_priority):
        super(OrionSubmitDialog, self).__init__("Orion Nuke Submitter", "com.orion.nukesubmit")
        self.setMinimumSize(550, 500)

        # --- Job Details ---
        self.tab_job = nuke.Tab_Knob("Job", "Job Options")
        self.addKnob(self.tab_job)

        self.jobName = nuke.String_Knob("jobName", "Job Name:")
        self.addKnob(self.jobName)
        self.jobName.setTooltip("The name for the Deadline job.")
        default_name = os.path.basename(nuke.root().name()) if nuke.root().name() != "Root" else "Untitled Nuke Job"
        self.jobName.setValue(default_name)

        self.comment = nuke.String_Knob("comment", "Comment:")
        self.addKnob(self.comment)
        self.comment.setTooltip("Optional comment for the job.")

        self.department = nuke.String_Knob("department", "Department:")
        self.addKnob(self.department)
        self.department.setTooltip("Optional department tag.")

        self.separator1 = nuke.Text_Knob("sep1", "")
        self.addKnob(self.separator1)

        # --- Scheduling ---
        self.pool = nuke.Enumeration_Knob("pool", "Pool:", pools)
        self.addKnob(self.pool)
        self.pool.setTooltip("Primary Deadline pool.")
        if "none" in pools: self.pool.setValue("none")

        self.group = nuke.Enumeration_Knob("group", "Group:", groups)
        self.addKnob(self.group)
        self.group.setTooltip("Deadline group.")
        if "none" in groups: self.group.setValue("none")

        self.priority = nuke.Int_Knob("priority", "Priority:")
        self.addKnob(self.priority)
        self.priority.setRange(0, max_priority)
        self.priority.setValue(max_priority // 2)
        self.priority.setValue(max_priority // 2)
        self.priority.setTooltip(f"Job priority (0-{max_priority}).")

        self.separator2 = nuke.Text_Knob("sep2", "")
        self.addKnob(self.separator2)

        # --- Nuke Options ---
        self.tab_nuke = nuke.Tab_Knob("Nuke", "Nuke Options")
        self.addKnob(self.tab_nuke)

        self.frameList = nuke.String_Knob("frameList", "Frame List:")
        self.addKnob(self.frameList)
        start = nuke.root().firstFrame()
        end = nuke.root().lastFrame()
        self.frameList.setValue(f"{start}-{end}")
        self.frameList.setTooltip("Frames to render (e.g., 1-10, 1,3,5, 1-10x2).")

        self.chunkSize = nuke.Int_Knob("chunkSize", "Frames Per Task:")
        self.addKnob(self.chunkSize)
        self.chunkSize.setValue(5)
        self.chunkSize.setTooltip("Number of frames each Deadline task will render.")

        self.threads = nuke.Int_Knob("threads", "Render Threads:")
        self.addKnob(self.threads)
        self.threads.setValue(0)
        self.threads.setTooltip("Number of threads Nuke should use (0 = auto).")

        self.useNukeX = nuke.Boolean_Knob("useNukeX", "Use NukeX License")
        self.addKnob(self.useNukeX)
       
        nukex_env_value = nuke.env.get('nukex', '0')
        self.useNukeX.setValue(bool(int(nukex_env_value)))
        
        self.useNukeX.setTooltip("Requires a NukeX license on the farm.")
        
        self.submitSceneFile = nuke.Boolean_Knob("submitSceneFile", "Submit Scene File")
        self.addKnob(self.submitSceneFile)
        self.submitSceneFile.setValue(False)
        self.submitSceneFile.setTooltip("Copies the Nuke script with the job.")
        
        self.separator3 = nuke.Text_Knob("sep3", "")
        self.addKnob(self.separator3)

        # --- Discord Notifications ---
        self.discordNotify = nuke.Boolean_Knob("discordNotify", "Send Discord Notifications")
        self.addKnob(self.discordNotify)
        self.discordNotify.setValue(True)
        self.discordNotify.setTooltip("Send job status updates to Discord via OrionUtils.")

    def show_dialog(self):
        return self.showModalDialog()

#main submission logic
def submit_to_orion_deadline():
    #check if script is saved
    root = nuke.root()
    script_path = root.name()
    if script_path == 'Root':
        nuke.message("Please save your Nuke script before submitting.")
        return

    #save current changes
    if root.modified():
        nuke.scriptSave()
        
    #get deadline info 
    try:
        pools_output = call_deadline_command(["-pools"])
        groups_output = call_deadline_command(["-groups"])
        max_priority_output = call_deadline_command(["-getmaximumpriority"])

        pools = pools_output.strip().split('\n') if pools_output else ['none']
        groups = groups_output.strip().split('\n') if groups_output else ['none']
        max_priority = int(max_priority_output.strip()) if max_priority_output and max_priority_output.strip().isdigit() else 100
        
    except Exception as e:
        nuke.message(f"Failed to get Deadline configuration: {e}")
        traceback.print_exc()
        return

    #show dialog
    dialog = OrionSubmitDialog(pools, groups, max_priority)
    if not dialog.show_dialog():
        print("Submission cancelled by user.")
        return # User cancelled

    #gather submission data 
    job_name = dialog.jobName.value()
    comment = dialog.comment.value()
    department = dialog.department.value()
    pool = dialog.pool.value()
    group = dialog.group.value()
    priority = dialog.priority.value()
    frame_list = dialog.frameList.value()
    chunk_size = dialog.chunkSize.value()
    threads = dialog.threads.value()
    use_nukex = dialog.useNukeX.value()
    submit_scene = dialog.submitSceneFile.value()
    discord_notify = dialog.discordNotify.value()
    ######################################################
    orion_ocio = r"\\monster\projects\all_work\studentGroups\ORION_CORPORATION\60_config\colorManagement\aces_1.2\config.ocio"

    #basic validation 
    if not frame_list:
        nuke.message("Frame List cannot be empty.")
        return
    if chunk_size < 1:
        nuke.message("Frames Per Task must be 1 or greater.")
        return
        
    #prepare submission files
    deadline_temp = os.path.join(os.path.expanduser("~"), "temp") # Basic temp dir
    try:
        os.makedirs(deadline_temp, exist_ok=True)
    except Exception as e:
        print(f"Could not create temp directory {deadline_temp}: {e}")
        nuke.message(f"Could not create temp directory: {e}")
        return

    job_info_file = None
    plugin_info_file = None
    
    try:
        #create job info file
        job_file_handle = NamedTemporaryFile(mode='w', dir=deadline_temp, suffix='.job', delete=False)
        job_info_file = job_file_handle.name
        
        job_file_handle.write(f"Plugin=Nuke\n")
        job_file_handle.write(f"Name={job_name}\n")
        job_file_handle.write(f"Comment={comment}\n")
        job_file_handle.write(f"Department={department}\n")
        job_file_handle.write(f"Pool={pool}\n")
        job_file_handle.write(f"Group={group}\n")
        job_file_handle.write(f"Priority={priority}\n")
        job_file_handle.write(f"Frames={frame_list}\n")
        job_file_handle.write(f"ChunkSize={chunk_size}\n")
        job_file_handle.write(f"UserName={os.environ.get('USERNAME', 'unknown')}\n") #get username
        
        #OCIO TEST
        job_file_handle.write(f"EnvironmentKeyValue2=OCIO={orion_ocio}\n")

        #add discord notification setup if enabled
        if discord_notify:
            on_job_start = os.path.join(EVENT_SCRIPT_DIR, "orion_nuke_on_job_start.py").replace("\\", "/")
            on_job_finish = os.path.join(EVENT_SCRIPT_DIR, "orion_nuke_on_job_finish.py").replace("\\", "/")
            on_job_fail = os.path.join(EVENT_SCRIPT_DIR, "orion_nuke_on_job_fail.py").replace("\\", "/")

            job_file_handle.write(f"PreJobScript={on_job_start}\n")
            job_file_handle.write(f"PostJobScript={on_job_finish}\n")

            #job_file_handle.write(f"ExtraInfoKeyValue0=OnJobFailureScript={on_job_fail}\n") 
            '''FAIL JOB TEST USING EVENT LISTENER'''
            job_file_handle.write(f"ExtraInfoKeyValue0=OnJobFailureScript={on_job_fail}\n") 

            job_file_handle.write(f"ExtraInfoKeyValue1=OrionDiscordNotify=True\n")
            #add PYTHONPATH (ensure key index doesn't clash if adding more)
            job_file_handle.write(f"EnvironmentKeyValue0=PYTHONPATH={ORION_STARTUP_PATH}\n")
        else:
             job_file_handle.write(f"ExtraInfoKeyValue0=OrionDiscordNotify=False\n")
            
        job_file_handle.close()

        #create plugin info file
        plugin_file_handle = NamedTemporaryFile(mode='w', dir=deadline_temp, suffix='.job', delete=False)
        plugin_info_file = plugin_file_handle.name
        
        if not submit_scene:
            plugin_file_handle.write(f"SceneFile={script_path}\n")
            
        nuke_version = f"{nuke.env['NukeVersionMajor']}.{nuke.env['NukeVersionMinor']}"
        plugin_file_handle.write(f"Version={nuke_version}\n")
        plugin_file_handle.write(f"Threads={threads}\n")
        plugin_file_handle.write(f"NukeX={use_nukex}\n")

        plugin_file_handle.close()

        #submit
        print("Submitting Nuke job to Deadline...")
        args_to_pass = [job_info_file, plugin_info_file]
        if submit_scene:
            args_to_pass.append(script_path)
            
        #ensure paths use correct encoding if needed
        if sys.version_info[0] < 3:
            preferred_encoding = locale.getpreferredencoding()
            args_to_pass = [arg.encode(preferred_encoding) if isinstance(arg, unicode) else arg for arg in args_to_pass]

        submission_result = call_deadline_command(args_to_pass, hide_window=False)
        
        print("Submission Result:\n" + submission_result)
        nuke.message("Job Submitted to Deadline.\n\n" + submission_result)

    except Exception as e:
        error_msg = f"An error occurred during submission:\n{e}\n{traceback.format_exc()}"
        print(error_msg)
        nuke.message(error_msg)
    finally:
        #cleanup
        try:
            if job_info_file and os.path.exists(job_info_file):
                os.remove(job_info_file)
            if plugin_info_file and os.path.exists(plugin_info_file):
                os.remove(plugin_info_file)
        except Exception as e:
            print(f"Warning: Failed to clean up temporary submission files: {e}")

def add_orion_menu():
    """Adds the Orion Submitter to the Nuke Render menu."""
    try:
        mainMenu = nuke.menu("Nuke")
        if mainMenu:
            orionMenu = mainMenu.addMenu("ORION")
            orionMenu.addCommand("Render/Submit to Deadline", submit_to_orion_deadline)
        else:
            #fallback
             mainMenu.addCommand("Orion/Submit Nuke to Deadline", submit_to_orion_deadline)
        print("Orion Nuke Submitter added to Render menu.")
    except Exception as e:
        print(f"Failed to add Orion menu item: {e}")
        
    #     render_menu = menu_bar.findItem("Render")
    #     if render_menu:
    #         render_menu.addCommand("Orion/Submit Nuke to Deadline", submit_to_orion_deadline)
    #     else:
    #         #fallback if Render menu doesn't exist
    #          menu_bar.addCommand("Orion/Submit Nuke to Deadline", submit_to_orion_deadline)
    #     print("Orion Nuke Submitter added to Render menu.")
    # except Exception as e:
    #     print(f"Failed to add Orion menu item: {e}")

# Run when Nuke starts (e.g., in menu.py)
# add_orion_menu()