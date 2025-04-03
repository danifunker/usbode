 #!/usr/bin/env python3

import gpiozero
import time
import subprocess
import os
from pathlib import Path
from flask import Flask
from threading import Thread
import time
import socket

def version():
    print("USBODE - Turn your Pi Zero/Zero 2 into one a virtual USB CD-ROM drive")
    print("Idea by RaduTek 2022: https://github.com/RaduTek/PiEmuCD\n")
    print("Web Functionality and massive rewrite Danifunker: https://github.com/danifunker/PiEmuCD\n")

store_dev = '/dev/mmcblk0p3'
store_mnt = '/mnt/imgstore'
allow_update_from_store = True
gadgetCDFolder = '/sys/kernel/config/usb_gadget/usbode'
iso_mount_file = '/opt/usbode/usbode-iso.txt'

app = Flask(__name__)
@app.route('/')
def index():
    return f"Welcome to USBODE, the USB Optical Drive Emulator!<br> My IP address is {socket.gethostbyname((socket.gethostname() + '.local'))}. <br> I am currently running from {os.path.abspath(__file__)} .<br>To switch modes click here: <a href='/switch'>/switch</a> <br> Current Image mounted are: {getMountedCDName()}. <br> Current Mode is: {checkState()} <br> <a href='/list'>Load Another Image</a><br><br><br><br><a href='/shutdown'>Shutdown the pi</a>"
@app.route('/switch')  
def switch():
    switch()
    return f'Switching mode... Current mode is {checkState()} (1=CD-Emulator, 2=ExFAT mode)<br><br><a href="/switch">Need to switch modes again?</a><br><br><a href="/setup">Return to Setup</a><br><br> <a href="/">Return to USBODE homepage</a>'
@app.route('/list')
def listFiles():
    fileList=list_images()
    response=""
    if {checkState() == 2}:
        response+="The USBODE cannot scan the files in ExFAT mode. <a href='/switch'>Switch Modes</a>, then go back to this page.<br><br>"
    for file in fileList:
        response+=f"<a href='/mount/{file}'>{file}</a><br><br>"
    return f"Current File Loaded: {getMountedCDName()}<br><br>To load a different ISO, select it. Be aware the system will disconnect and reconnect the optical drive.<br><br> {response} <br> <a href='/'>Return to USBODE homepage</a>"
@app.route('/mount/<file>')
def mountFile(file):
    change_Loaded_Mount(f"{store_mnt}/{file}")
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

def getMountedCDName():
    if not os.path.exists(gadgetCDFolder+"/functions/mass_storage.usb0/lun.0/file"):
        print("Error: ISO Not Set")
    with open(gadgetCDFolder+"/functions/mass_storage.usb0/lun.0/file", "r") as f:
        return f.readline().strip()

# Print without endline
def prints(string):
    print(string, end=' ')

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
    
def cleanupMode(gadgetFolder=gadgetCDFolder):
    #Cleanup the gadget folder
    print("Unloading Gadget")
    subprocess.run(['sh', 'scripts/cleanup_mode.sh', gadgetFolder], cwd="/opt/usbode")
    time.sleep(1)

def init_gadget(type):
    print("Initializing USBODE CD-ROM gadget through configfs...")
    cleanupMode()
    os.makedirs(gadgetCDFolder, exist_ok=True)
    os.chdir(gadgetCDFolder)
    os.makedirs("strings/0x409", exist_ok=True)
    os.makedirs("configs/c.1/strings/0x409", exist_ok=True)
    os.makedirs("functions/mass_storage.usb0", exist_ok=True)
    if type == "cdrom":
        subprocess.run(['sh', 'scripts/cd_gadget_setup.sh',gadgetCDFolder ], cwd="/opt/usbode")
        with open(iso_mount_file, "r") as f:
            iso_filename = f.readline().strip()
        change_Loaded_Mount(f"{iso_filename}")
    elif type == "exfat":
        subprocess.run(['sh', 'scripts/exfat_gadget_setup.sh', gadgetCDFolder], cwd="/opt/usbode")
    enable_gadget()

def enable_gadget():
    p = subprocess.run(['sh', 'scripts/enablegadget.sh', gadgetCDFolder], cwd="/opt/usbode")
    if p.returncode != 0:
        print(f"failed: {p.returncode} {p.stderr} {p.stdout}")
        return False
    else:
        return True

def disable_gadget():
    subprocess.run(['sh', 'scripts/disablegadget.sh', gadgetCDFolder], cwd="/opt/usbode")

def switch():
    if checkState(gadgetCDFolder) == 0:
        print("Both modes are disabled, enabling exfat mode")
        disable_gadget()
        init_gadget("exfat")
        change_Loaded_Mount(f"{store_dev}")
        enable_gadget()
    else:
        if checkState(gadgetCDFolder) == 1:
            print("Switching to ExFAT mode")
            disable_gadget()
            init_gadget("exfat")
            change_Loaded_Mount(f"{store_dev}")
            enable_gadget()
        else:
            print("Switching to CD-ROM mode")
            subprocess.run('sync')            
            disable_gadget()
            init_gadget("cdrom")
            enable_gadget()

def checkState(gadgetFolder=gadgetCDFolder):
    #Return Mode of the gadget 0 = not enabled, 1 = cdrom, 2 = exfat
    if not os.path.exists(gadgetFolder+"/UDC"):
        print (f"{gadgetFolder}/UDC not found")
        return 0
    else:
        UDCContents=open(gadgetFolder+"/UDC", "r")
        UDCchar = UDCContents.read(1)
        UDCContents.close()
        if UDCchar ==  "\n":
            return 0
        else:
            cdromState = open(f"{gadgetFolder}/functions/mass_storage.usb0/lun.0/cdrom", "r").readline().rstrip()
            if cdromState == "1":
                return 1
            elif cdromState == "0":
                return 2
            else:
                print(f"Could not read from {gadgetFolder}/functions/mass_storage.usb0/lun.0/cdrom")
                return 0

def change_Loaded_Mount(filename):
    #Save the ISO filename to to persistent storage
    if filename.endswith(".iso"): 
        f = open(iso_mount_file, "w")
        f.write(f"{filename}" + "\n")
        f.close()
    #Change the disk image in the gadget
    if not os.path.exists(gadgetCDFolder+"/functions/mass_storage.usb0/lun.0/file"):
        print("Gadget is not enabled, cannot change mount")
        return False
    else:
        print(gadgetCDFolder+"/functions/mass_storage.usb0/lun.0/file")
        with open(gadgetCDFolder+"/functions/mass_storage.usb0/lun.0/file", "w") as f:
            print(f"Changing mount to {filename}")
            f.write(f"{filename}")
            f.close()
        return True

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
]

def start_exit():
    disable_gadget()
    cleanupMode()
    subprocess.run(['rmmod', 'usb_f_mass_storage'])
    subprocess.run(['rmmod', 'libcomposite'])    

def start_shutdown():
    print("Shutdown in progress...")
    subprocess.run(['shutdown', 'now'])

def start_flask():
    print("Starting Flask server...")
    app.run(host='0.0.0.0', port=80)

def main():
    #Setup Environment
    print("Starting USBODE...")
    print(f"Mounting image store on {store_mnt}...")
    subprocess.run(['mount', store_dev, store_mnt, '-o', 'umask=000'])
    subprocess.run(['modprobe', 'libcomposite'])
    daemon = Thread(target=start_flask, daemon=True, name='Server')
    daemon.start()
    init_gadget("cdrom")
    time.sleep(.5)  # Delay for previous version script to exit
    while True:
        cmd = input("usbode> ")
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
            start_exit()
            exit(0)
        elif cmd == 'shutdown':
            start_exit()
            start_shutdown()
        elif cmd == 'switch':
            switch()
        else:
            if cmd.strip(' ') != '':
                print(f"Invalid command: {cmd}")            

if __name__ == "__main__":
    main()
