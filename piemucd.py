 #!/usr/bin/env python3

import gpiozero
import time
import subprocess
import os
import shutil
from pathlib import Path
from flask import Flask
from threading import Thread
import time
import glob
import socket

def version():
    print("PiEmuCD - Turn your Pi Zero into one or more virtual USB CD-ROM drives!")
    print("Made by RaduTek 2022: https://github.com/RaduTek/PiEmuCD\n")
    print("Web Functionality added by Danifunker: https://github.com/danifunker/PiEmuCD\n")

store_dev = '/dev/mmcblk0p3'
store_mnt = '/mnt/imgstore'
to_mount_file = '/opt/usbode/to-be-mounted.txt'
update_file = 'update-piemucd.py'
allow_update_from_store = True

store_mounted = False
# Emulation mode
emu_mode = 1 # 0: Disabled; 1: CD-ROM; 2: Image Store
current_mode = 1

# Set up Flask webserver
app = Flask(__name__)
@app.route('/')
def index():
    return f"Welcome to USBODE, the USB Optical Drive Emulator!<br> My IP address is {socket.gethostbyname((socket.gethostname() + '.local'))}. <br> I am currently running from {os.path.abspath(__file__)} .<br>To switch modes click here: <a href='/switch'>/switch</a> <br> Current Image mounted are: {mounts_list}. <br> Current Mode is: {current_mode} <br> <a href='/list'>Load Another Image</a><br><br><br><br><a href='/shutdown'>Shutdown the pi</a>"
@app.route('/switch')  
def switch():
    switch_mode()
    return f'Switching mode... Current mode is {current_mode} (1=CD-Emulator, 2=ExFAT mode)<br><br><a href="/switch">Need to switch modes again?</a><br><br><a href="/setup">Return to Setup</a><br><br> <a href="/">Return to USBODE homepage</a>'
@app.route('/list')
def listFiles():
    fileList=list_images()
    response=""
    if {current_mode == 2}:
        response+="The USBODE cannot scan the files in ExFAT mode. <a href='/switch'>Switch Modes</a>, then go back to this page.<br><br>"
    for file in fileList:
        response+=f"<a href='/mount/{file}'>{file}</a><br><br>"
    return f"Current File Loaded: {mounts_list}<br><br>To load a different ISO, select it. Be aware the system will disconnect and reconnect the optical drive.<br><br> {response} <br> <a href='/'>Return to USBODE homepage</a>"
@app.route('/mount/<file>')
def mountFile(file):
    mount_new_image(file, to_mount_file)
    switch_store()
    switch_cdrom()
    return f"Attempting to mount {file}...<br> <a href='/'>Return to USBODE homepage</a>"
@app.route('/shutdown')
def shutdown():
    start_shutdown()
    return f"Shutting down the pi now"
@app.route('/setup')
def setup():
    fileList=list_images()
    if len(fileList) < 1:
        return f"No images found in {store_mnt}. Please add at least one ISO image and try again. <br>Adding images requires ExFAT support, connect this device to a system that supports ExFAT, then <a href='/switch'> switch modes</a> <br><br><a href='/shutdown'>Shutdown the pi</a>"
    else:
        response=""
        for file in fileList:
            response+=f"<a href='/mount/{file}'>{file}</a><br><br>"
        return f"Current File Loaded: NONE (First Setup!)<br><br>To load a different ISO, select it. Be aware the system will disconnect and reconnect the optical drive.<br><br> {response} <br> <a href='/'>Return to USBODE homepage</a>"

# Set up GPIO
led_mode = gpiozero.LED(26)
led_act = gpiozero.LED(19)
button = gpiozero.Button(5, pull_up=True)
button.hold_time = 3
btn_hold = False

def btn_pressed():
    btn_hold = False

button.when_pressed = btn_pressed

def btn_held():
    btn_hold = True
    # Button hold = Start shutdown
    start_shutdown()

button.when_held = btn_held


def btn_released():
    if not btn_hold:
        # Button short press = Switch mode
        switch_mode()

button.when_released = btn_released


def led_act_state(state):
    if state == 'error':
        led_act.blink(.1, .1)
    elif state == 'wait':
        led_act.blink(.5, .5)
    elif state == 'idle':
        led_act.blink(.1, 1.9)

def led_mode_state(state):
    if state == 'cdrom':
        led_mode.on()
    elif state == 'store':
        led_mode.blink(.9, .1)
    elif state == 'wait':
        led_mode.blink(.5, .5)
    elif state == 'update':
        led_mode.blink(.2, .2)

led_mode_state('wait')
led_act_state('wait')


# Print without endline
def prints(string):
    print(string, end=' ')


# Update this script from image store
def update_from_store():
    if not allow_update_from_store:
        return False

    update_path = os.path.join(store_mnt, update_file)

    # Check if update file exists
    if not os.path.isfile(update_path):
        return False

    led_mode_state('update')
    print("Found update file on image store, installing...")

    # Remount image store as read write
    unmount_store()
    mount_store(True)

    # Back up existing script
    shutil.move(__file__, __file__ + ".backup")
    # Move update in place of script
    shutil.move(update_path, __file__)

    # Ensuring the file is fully saved to disk
    subprocess.run('sync')
    time.sleep(.5)

    print("Installation succesful, relaunching script...")

    # Run new script
    subprocess.Popen(['sudo', 'python3', __file__])
    # Exit current script
    exit(0)


# Disable all emulation
def disable_emu():
    global emu_mode
    prints("Disabling emulation...")
    if emu_mode == 0:
        print("already disabled!")
        return True
    p = subprocess.run(['rmmod', 'g_mass_storage'])
    if p.returncode != 0:
        print("already disabled!")
    else:
        print("done!")
    emu_mode = 0
    return True


# Enable CD-ROM emulation with a list of images
def enable_cdrom(mount_args):
    global emu_mode
    prints("Enabling CD-ROM mode...")
    if emu_mode != 0:
        print("already enabled or other mode active!")
        return True
    args = ['modprobe', 'g_mass_storage']
    args.extend(mount_args)
    p = subprocess.run(args)
    if p.returncode != 0:
        print("failed!")
        return False
    else:
        emu_mode = 1
        print("done!")
        return True

def list_images():
    fileList = []
    print(f"Listing images in {store_mnt}...")
    dir_list=os.listdir(store_mnt)
    for file in dir_list:
        if file.lower().endswith(".iso") and not (file.startswith("._")): 
            fileList.append(file)
            print(file)
    fileListSorted=sorted(fileList, key=str.lower)
    print(f"Found {len(fileList)} files")
    return fileListSorted

def mount_new_image(name, to_mount_file):
    if name.find(" "): 
        name = '"' + name + '"'
    f = open(to_mount_file, "w")
    f.write(f"removable cdrom {name}" + "\n")
    f.close()
    

# Enable mass storage mode to edit the image store
def enable_store():
    global emu_mode
    prints("Enabling image store mode...")
    if emu_mode != 0:
        print("already enabled or other mode active!")
        return True
    p = subprocess.run(['modprobe', 'g_mass_storage', 'file=' + store_dev, 'removable=y'])
    if p.returncode != 0:
        print("failed!")
        return False
    else:
        emu_mode = 2
        print("done!")
        return True


# Mount the image store on the local system
def mount_store(rw: bool = True):
    global store_mounted
    prints(f"Mounting image store{' as writeable' if rw else ''}...")
    if store_mounted or os.path.ismount(store_mnt):
        store_mounted = True
        print("already mounted!")
        return True
    if not os.path.isdir(store_mnt):
        os.makedirs(store_mnt)
    args = ['mount']
    if not rw:
        args.extend(['-o', 'ro'])
    args.extend([store_dev, store_mnt, "-o", "umask=000"])
    print(f"Running command: {args}")
    p = subprocess.run(args)
    if p.returncode != 0:
        print("failed!")
        return False
    else:
        store_mounted = True
        print("done!")
        return True


# Unmount the image store from the local system
def unmount_store():
    global store_mounted
    prints("Unmounting image store...")
    if not store_mounted or not os.path.ismount(store_mnt):
        store_mounted = False
        print("already unmounted!")
        return True
    subprocess.run('sync') # Sync any changes to the partition
    p = subprocess.run(['umount', store_dev])
    if p.returncode != 0:
        print("failed!")
        return False
    else:
        store_mounted = False
        print("done!")
        return True


# Gets the list of image files to mount
# from the to_mount_file in the root of the image store
def get_images_to_mount():
    to_mount_file_path = to_mount_file
    print(f"Loading list of images to be mounted... ({to_mount_file_path})")
    if (os.path.isfile(to_mount_file_path)):
        with open(to_mount_file_path , 'r') as file:
            images = {
                'file': [],
                'removable': [],
                'cdrom': [],
                'ro': [],
                'nofua': []
            }
            global mounts_list
            mounts_list=[]
            mount_list = file.readlines()
            mount_count = 0
            for mount_item in mount_list:
                mount_item = mount_item.strip(" \n\r\t")
                # Exclude comments
                if mount_item[0] == '#':
                    continue
                if '#' in mount_item:
                    comment_start = mount_item.index('#')
                    mount_item = mount_item[0:comment_start]
                
                mount_item = mount_item.strip(' ')

                mount_words = mount_item.split(' ')

                # Get image file name, quoted or not
                file_name = ""
                if '"' in mount_words[-1]:
                    q_start = mount_item.index('"')
                    q_end = mount_item.index('"', q_start+1)
                    file_name = mount_item[q_start+1:q_end]
                else:
                    file_name = mount_words[-1]

                # Check if image file exists
                file_path = os.path.join(store_mnt, file_name)
                if not os.path.isfile(file_path):
                    print(f"Image file: {file_path} doesn't exist, not mounting!")
                    continue

                mount_count += 1
                mounts_list.append(file_path)

                print(f"Mount item {mount_count}: {mount_item}")

                # Check image mount arguments
                images['file'].append(file_path)
                images['removable'].append('y' if 'removable' in mount_words else 'n')
                images['cdrom'].append('y' if 'cdrom' in mount_words else 'n')
                images['ro'].append('y' if 'ro' in mount_words else 'n')
                images['nofua'].append('y' if 'nofua' in mount_words else 'n')

            if len(images['file']) > 0:
                # Prepare arguments for g_mass_storage module
                mount_args = []
                mount_args.append('file=' + ','.join(images['file']))
                mount_args.append('removable=' + ','.join(images['removable']))
                mount_args.append('cdrom=' + ','.join(images['cdrom']))
                mount_args.append('ro=' + ','.join(images['ro']))
                mount_args.append('nofua=' + ','.join(images['nofua']))
                return mount_args
            else:
                print("No valid images to mount! Please check the to be mounted file!")
                return None
    else:
        print("To be mounted file doesn't exist! Operation failed!")
        return None


# Switch to CD-ROM emulation mode
def switch_cdrom():
    global current_mode
    print("Switching to CD-ROM mode...")
    led_mode_state('cdrom')
    led_act_state('wait')

    # Disable emulation and mount image store
    r = True
    r = r and disable_emu()
    r = r and mount_store()

    # Check for update
    update_from_store()

    # Get images to mount
    mount_args = get_images_to_mount()
    r = r and (mount_args != None)

    # Pass images to emulation
    if mount_args != None:
        r = r and enable_cdrom(mount_args)

    if r:
        led_act_state('idle')
    else:
        led_act_state('error')
        print("Switching to CD-ROM mode failed!")
    current_mode = 1

# Switch to mass storage mode to edit the image store
def switch_store():
    global current_mode
    print("Switching to image store mode...")
    led_mode_state('store')
    led_mode_state('wait')

    # Disable emulation and unmount store
    r = True
    r = r and disable_emu()
    r = r and unmount_store()

    # Set store to emulation
    r = r and enable_store()

    if r:
        led_act_state('idle')
    else:
        led_act_state('error')
        print("Switching to image store mode failed!")
    led_mode_state('store')
    current_mode = 2


# Switch/toggle emulation mode
def switch_mode():
    prints(f"Current mode: {current_mode}, switching to mode:")
    if current_mode == 0 or current_mode == 2:
        print("1 - cdrom")
        switch_cdrom()
    elif current_mode == 1:
        print("2 - store")
        switch_store()


# Start shutdown of system
def start_shutdown():
    print("Shutdown in progress...")
    led_act_state('wait')
    led_mode_state('wait')
    disable_emu()
    unmount_store()
    subprocess.run(['shutdown', 'now'])


# Help information
help_cmds = [
    ['help', 'Displays this message'],
    ['version', 'Displays version info'],
    ['exit', 'Terminate the script'],
    ['shutdown', 'Shuts down the Pi'],
    ['disable', 'Disables the gadget'],
    ['mode', 'Get current mode'],
    ['switch [mode]', 'Switch to a specified mode (1=cdrom, 2=store)'],
    ['switch', 'Switch to the other mode (toggle like the hardware button)'],
    ['update', f'Check for update script ({update_file}) on the image store']
]

def start_flask():
    print("Starting Flask server...")
    app.run(host='0.0.0.0', port=80)

def main():
    version()
    daemon = Thread(target=start_flask, daemon=True, name='Server')
    daemon.start()    
    
    time.sleep(.5)  # Delay for previous version script to exit

    # Start CD mode
    switch_cdrom()

    # Simple command interpreter
    print(f"\nConnect to http://{socket.gethostbyname((socket.gethostname() + '.local'))}:80 from a remote machine")
    print("\nType 'help' for a list of commands.")
    while True:
        cmd = input("piemucd> ")
        cmd = cmd.strip(' ')
        cmd_args = cmd.split(' ')
        cmd = cmd_args[0]
        if cmd == 'help':
            for help_cmd in help_cmds:
                if len(help_cmd) == 0:
                    continue
                else:
                    print(f"{help_cmd[0]}", end='')
                    if len(help_cmd) == 2:
                        indent = '\t\t' if (len(help_cmd[0]) < 8) else '\t'
                        print(f"{indent}{help_cmd[1]}")
                    if len(help_cmd) > 2:
                        for i in range(2,len(help_cmd)):
                            print(f"\t\t{help_cmd[i]}")
        elif cmd == 'version':
            version()
        elif cmd == 'exit':
            disable_emu()
            print("Goodbye!")
            exit(0)
        elif cmd == 'shutdown':
            start_shutdown()
        elif cmd == 'disable':
            disable_emu()
        elif cmd == 'mode':
            print(f"Current mode: {current_mode}")
        elif cmd == 'switch':
            if len(cmd_args) == 1:
                switch_mode()
                continue
            elif cmd_args[1] == 'cdrom' or cmd_args[1] == '1':
                switch_cdrom()
            elif cmd_args[1] == 'store' or cmd_args[1] == '2':
                switch_store()
            else:
                print(f"Invalid arguments: {cmd_args[1:-1]}")
        elif cmd == 'update':
            if not allow_update_from_store:
                print("Updating from store is disabled in the script header!")
            else:
                r = update_from_store()
                if not r:
                    print("No update script is available!")
        else:
            if cmd.strip(' ') != '':
                print(f"Invalid command: {cmd}")


if __name__ == "__main__":
    main()
