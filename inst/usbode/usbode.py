#!/usr/bin/env python3
import sys
import os
ScriptPath=os.path.dirname(__file__)
sys.path.append(f"{ScriptPath}/waveshare")
global oledEnabled
global fontM
global fontS
global fontL
try:
    import SH1106
    from PIL import Image, ImageDraw, ImageFont
    oledEnabled = True
    fontL = ImageFont.truetype(f"{ScriptPath}/waveshare/Font.ttf",10)
    fontS = ImageFont.truetype(f"{ScriptPath}/waveshare/Font.ttf",9)
except:
    oledEnabled = False
import time
import subprocess
import requests
from gpiozero import *
from pathlib import Path
from threading import Thread
import time
import urllib.parse
from flask import Flask

store_dev = '/dev/mmcblk0p3'
store_mnt = '/mnt/imgstore'
allow_update_from_store = True
gadgetCDFolder = '/sys/kernel/config/usb_gadget/usbode'
iso_mount_file = '/opt/usbode/usbode-iso.txt'
cdemu_cdrom = '/dev/cdrom'
versionNum = "1.9"
global updateEvent
updateEvent = 0
global exitRequested
exitRequested = 0

def version():
    print("USBODE - Turn your Pi Zero/Zero 2 into one a virtual USB CD-ROM drive")
    print("Web Functionality and massive rewrite Danifunker: https://github.com/danifunker/usbode\n")
    print(f"USBODE version ${versionNum}")

global myIPAddress
myIPAddress = "Unable to determine IP address"

def getMyIPAddress():
    while True:
        global myIPAddress
        time.sleep(1)
        try:
            ipAddressAttempt = subprocess.check_output(['hostname', '-I']).decode('utf-8').strip().split(' ')[0]
        except:
            ipAddressAttempt = "Unable to determine IP address"
        if ipAddressAttempt != myIPAddress:
            global updateEvent
            updateEvent = 1
        myIPAddress = ipAddressAttempt

### Begining of Web Interface ###

app = Flask(__name__)

# HTML template with CSS styling embedded - all curly braces properly escaped
HTML_LAYOUT = """<!DOCTYPE html>
<html>
<head>
    <title>USBODE - USB Optical Drive Emulator</title>
    <style>
        body {{background-color: #EAEAEA; color: #333333; font-family: "Times New Roman", serif; margin: 0; padding: 0;}}
        h1, h2, h3 {{color: #1E4D8C;}}
        a {{color: #0066CC;}}
        a:visited {{color: #0066CC;}}
        .container {{width: 100%; margin: 0; padding: 0;}}
        .header {{background-color: #3A7CA5; padding: 10px; text-align: center; color: #FFFFFF;}}
        .header h1, .header h2 {{color: #FFFFFF; margin: 5px 0;}}
        .content {{padding: 10px; background-color: #FFFFFF; min-height: 300px;}}
        .footer {{background-color: #3A7CA5; padding: 10px; text-align: center; color: #FFFFFF;}}
        .button {{background-color: #4CAF50; padding: 7px 15px; text-decoration: none; color: #FFFFFF; margin: 5px; display: inline-block;}}
        .info-box {{background-color: #F5F5F5; padding: 10px; margin: 10px 0;}}
        .warning {{background-color: #FFDDDD; padding: 10px; margin: 10px 0; color: #990000;}}
        .file-link {{padding: 8px; margin: 5px 0; display: block; font-size: 16px;}}
        .file-link-even {{background-color: #E3F2FD;}}
        .file-link-odd {{background-color: #BBDEFB;}}
        .header-bar {{background-color: #2C5F7C; color: #FFFFFF; padding: 5px;}}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>USBODE</h1>
            <h2>USB Optical Drive Emulator</h2>
        </div>
        <div class="content">
            {content}
        </div>
        <div class="footer">
            <p>Version {version}</p>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    mode = checkState()
    mode_text = "(CD-Emulator)" if mode == 1 else "(ExFAT mode)" if mode == 2 else ""
    
    content = f"""
    <h3>Welcome to USBODE</h3>
    <div class="info-box">
        <p>My IP address is: {myIPAddress}</p>
        <p>Currently Serving: <strong>{getMountedCDName()}</strong></p>
        <p>Current Mode is: <strong>{mode} {mode_text}</strong></p>
    </div>
    
    <div>
        <a class="button" href="/switch">Switch Modes</a>
        <a class="button" href="/list">Load Another Image</a>
        <a class="button" href="/shutdown">Shutdown the Pi</a>
    </div>
    """
    
    return HTML_LAYOUT.format(content=content, version=versionNum)

@app.route('/switch')  
def switch_mode():
    switch()
    mode = checkState()
    mode_text = "(CD-Emulator)" if mode == 1 else "(ExFAT mode)" if mode == 2 else ""
    
    content = f"""
    <h3>Switching Mode</h3>
    <div class="info-box">
        <p>Switching mode complete.</p>
        <p>Current mode is <strong>{mode} {mode_text}</strong></p>
    </div>
    
    <div>
        <a class="button" href="/switch">Switch Modes Again</a>
        <a class="button" href="/">Return to Homepage</a>
    </div>
    """
    
    return HTML_LAYOUT.format(content=content, version=versionNum)

@app.route('/list')
def listFiles():
    fileList = list_images()
    is_exfat = (checkState() == 2)
    
    content = f"""
    <h3>File Selection</h3>
    <div class="info-box">
        <p>Current File Loaded: <strong>{getMountedCDName()}</strong></p>
        <p>To load a different ISO, select it. No disconnection between the OS and the USBODE will occur.</p>
    </div>
    """
    
    content += "<h4>Available Files:</h4>"
    # Add alternating colors to the file list
    for i, file in enumerate(fileList):
        encoded_file = urllib.parse.quote_plus(file)
        row_class = "file-link-even" if i % 2 == 0 else "file-link-odd"
        content += f'<div class="file-link {row_class}"><a href="/mount/{encoded_file}">{file}</a></div>'
    
    content += """
    <div>
        <a class="button" href="/">Return to Homepage</a>
    </div>
    """
    
    return HTML_LAYOUT.format(content=content, version=versionNum)

@app.route('/cdemu')
def mountCDEMU():
    change_Loaded_Mount(f"{cdemu_cdrom}")
    
    content = f"""
    <h3>Mounting File</h3>
    <div class="info-box">
        <p>Attempting to mount: <strong>CDEMU CDROM</strong></p>
    </div>
    
    <div>
        <a class="button" href="/">Return to Homepage</a>
        <a class="button" href="/list">Select Another File</a>
    </div>
    """
    
    return HTML_LAYOUT.format(content=content, version=versionNum)

@app.route('/mount/<file>')
def mountFile(file):
    decoded_file = urllib.parse.unquote_plus(file)
    change_Loaded_Mount(f"{store_mnt}/{decoded_file}")
    
    content = f"""
    <h3>Mounting File</h3>
    <div class="info-box">
        <p>Attempting to mount: <strong>{decoded_file}</strong></p>
    </div>
    
    <div>
        <a class="button" href="/">Return to Homepage</a>
        <a class="button" href="/list">Select Another File</a>
    </div>
    """
    
    return HTML_LAYOUT.format(content=content, version=versionNum)

@app.route('/shutdown')
def shutdown():
    start_shutdown()
    
    content = """
    <h3>System Shutdown</h3>
    <div class="warning">
        <p>Shutting down the Pi now...</p>
    </div>
    """
    
    return HTML_LAYOUT.format(content=content, version=versionNum)

@app.route('/exit')
def exit():
    start_exit()
    Thread.is_alive == 0
    
    content = """
    <h3>Application Exit</h3>
    <div class="warning">
        <p>Exiting the application now...</p>
    </div>
    """
    
    return HTML_LAYOUT.format(content=content, version=versionNum)
### END OF WEB INTERFACE ###

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
        if (file.lower().endswith(".iso") or file.lower().endswith("cue")) and not (file.startswith("._")):
            fileList.append(file)
            print(file)
    fileListSorted=sorted(fileList, key=str.lower)
    print(f"Found {len(fileList)} files")
    return fileListSorted
    
def cleanupMode(gadgetFolder=gadgetCDFolder):
    #Cleanup the gadget folder
    print("Unloading Gadget")
    subprocess.run(['sh', 'scripts/cleanup_mode.sh', gadgetFolder], cwd="/opt/usbode")
    time.sleep(.25)

def init_gadget(type):
    print(f"Initializing USBODE {type} gadget through configfs...")
    cleanupMode()
    os.makedirs(gadgetCDFolder, exist_ok=True)
    os.makedirs(gadgetCDFolder + "/strings/0x409", exist_ok=True)
    os.makedirs(gadgetCDFolder +"/configs/c.1/strings/0x409", exist_ok=True)
    os.makedirs(gadgetCDFolder +"/functions/mass_storage.usb0", exist_ok=True)
    if type == "cdrom":
        subprocess.run(['sh', 'scripts/cd_gadget_setup.sh',gadgetCDFolder ], cwd="/opt/usbode")
        with open(iso_mount_file, "r") as f:
            iso_filename = f.readline().strip()
        if iso_filename and os.path.exists(f"{iso_filename}"):
            change_Loaded_Mount(f"{iso_filename}")
        else:
            print(f"The requested file to load {iso_filename} does not exist, kicking into exFAT mode now.")
            disable_gadget()
    elif type == "exfat":
        subprocess.run(['sh', 'scripts/exfat_gadget_setup.sh', gadgetCDFolder], cwd="/opt/usbode")
        change_Loaded_Mount(f"{store_dev}")
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
            if len(list_images()) > 0:
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
    isoloading = False
    #Save the ISO filename to to persistent storage
    if checkState() == 1:
        subprocess.run(['sh', 'scripts/force_eject_iso.sh', gadgetCDFolder], cwd="/opt/usbode")
    if filename.endswith(".iso") or filename.endswith(".cue"): 
        f = open(iso_mount_file, "w")
        f.write(f"{filename}" + "\n")
        f.close()
        isoloading = True
    #Change the disk image in the gadget
    if not os.path.exists(gadgetCDFolder+"/functions/mass_storage.usb0/lun.0/file"):
        print("Gadget is not enabled, cannot change mount")
        updateDisplay(disp)
        return False
    else:
        print(gadgetCDFolder+"/functions/mass_storage.usb0/lun.0/file")
        with open(gadgetCDFolder+"/functions/mass_storage.usb0/lun.0/file", "w") as f:
            print(f"Changing mount to {filename}")
            f.write(f"{filename}")
            f.close()
            if checkState() == 2 and isoloading == True:
                switch()
        global updateEvent
        updateEvent = 1
        return True

def start_exit():
    global disp
    global oledEnabled
    if oledEnabled:
        stopPiOled()   
    disable_gadget()
    cleanupMode()
    subprocess.run(['rmmod', 'usb_f_mass_storage'])
    subprocess.run(['rmmod', 'libcomposite'])

def start_shutdown():
    print("Shutdown in progress...")
    subprocess.run(['shutdown', 'now'])

def start_flask():
    print("Starting Flask server...")
    app.run(host='::', port=80)

def changeISO_OLED(disp):
    file_list=list_images()
    iterator = 0
    if len(file_list) < 1:
        print("No images found in store, throwing error on screen.")
        disp.clear()
        image1 = Image.new('1', (disp.width, disp.height), "WHITE")
        draw = ImageDraw.Draw(image1)
        draw.text((0, 0), "No Images in store.", font = fontL, fill = 0 )
        draw.text((0, 14), "Please add an image first.", font = fontL, fill = 0 )
        disp.ShowImage(disp.getbuffer(image1))
        time.sleep(0.15)
        return False
    else:
        updateDisplay_FileS(disp, iterator, file_list)
        while True:
            time.sleep(0.15)
            if disp.RPI.digital_read(disp.RPI.GPIO_KEY_UP_PIN ) == 0:
                pass
            else:
                iterator = iterator - 1
                if iterator < 0:
                    iterator = len(file_list)-1
                updateDisplay_FileS(disp, iterator, file_list)
                print("Going up")
            if disp.RPI.digital_read(disp.RPI.GPIO_KEY_LEFT_PIN) == 0:
                pass
            else:
                print("left")
            if disp.RPI.digital_read(disp.RPI.GPIO_KEY_RIGHT_PIN) == 0:
                pass
            else:
                print("right")
            if disp.RPI.digital_read(disp.RPI.GPIO_KEY_DOWN_PIN) == 0:
                pass
            else: 
                iterator = iterator + 1
                if iterator > len(file_list)-1:
                    iterator = 0
                updateDisplay_FileS(disp, iterator, file_list)
                print (f"Selected {file_list[iterator]}")
            if disp.RPI.digital_read(disp.RPI.GPIO_KEY1_PIN) == 0: # button is released
                pass
            else: # button is pressed:
                print(f"loading {store_mnt}/{file_list[iterator]}")
                requests.request('GET', f'http://127.0.0.1/mount/{file_list[iterator]}')
                return True
            if disp.RPI.digital_read(disp.RPI.GPIO_KEY_PRESS_PIN) == 0: 
                pass
            else:
                print(f"loading {store_mnt}/{file_list[iterator]}")
                requests.request('GET', f'http://127.0.0.1/mount/{file_list[iterator]}')
                return True
            if disp.RPI.digital_read(disp.RPI.GPIO_KEY2_PIN) == 0:
                pass
            else: 
                print("CANCEL") 
                return True

def updateDisplay_FileS(disp, iterator, file_list):
    image1 = Image.new('1', (disp.width, disp.height), "WHITE")
    draw = ImageDraw.Draw(image1)
    draw.text((0, 0), "Select an ISO:", font = fontL, fill = 0 )
    draw.text((0, 12), "I: " + str.replace(getMountedCDName(),store_mnt+'/',''), font = fontL, fill = 0 )
    draw.text((1,25), file_list[iterator], font = fontL, fill = 0 )
    draw.line([(0,37),(127,37)], fill = 0)
    disp.ShowImage(disp.getbuffer(image1))

def updateDisplay(disp):
    image1 = Image.new('1', (disp.width, disp.height), "WHITE")
    draw = ImageDraw.Draw(image1)
    draw.text((0, 0), "USBODE v:" + versionNum, font = fontL, fill = 0 )
    draw.text((0, 12), "IP: " + myIPAddress, font = fontL, fill = 0 )
    draw.text((0, 24), "ISO: " + str.replace(getMountedCDName(),store_mnt+'/',''), font = fontL, fill = 0 )
    draw.text((0, 36), "Mode: " + str(checkState()), font = fontL, fill = 0 )
    disp.ShowImage(disp.getbuffer(image1))

def updateDisplay_Advanced(disp):
    image1 = Image.new('1', (disp.width, disp.height), "WHITE")
    draw = ImageDraw.Draw(image1)
    draw.text((0, 0), "Advanced Menu:" + versionNum, font = fontL, fill = 0 )
    draw.text((1,25), "Shutdown USBODE", font = fontS, fill = 0 )
    draw.line([(0,37),(127,37)], fill = 0)
    disp.ShowImage(disp.getbuffer(image1))
    while True:
        time.sleep(0.15)
        if disp.RPI.digital_read(disp.RPI.GPIO_KEY2_PIN) == 0:
            pass
        else: 
            print("CANCEL") 
            return True
        if disp.RPI.digital_read(disp.RPI.GPIO_KEY1_PIN) == 0: # button is released
            pass
        else: # button is pressed:
            requests.request('GET', f'http://127.0.0.1/shutdown')
        if disp.RPI.digital_read(disp.RPI.GPIO_KEY_PRESS_PIN) == 0: 
            pass
        else:
            requests.request('GET', f'http://127.0.0.1/shutdown')
       
def getOLEDinput():
    global disp
    disp.Init()
    disp.clear()
    updateDisplay(disp)
    global exitRequested
    global myIPAddress
    while exitRequested == 0:
        #Scan for IP address changes and update the screen if found
        global updateEvent
        time.sleep(0.15)
        if disp.RPI.digital_read(disp.RPI.GPIO_KEY3_PIN) == 0: # button is released
            pass
        else: # button is pressed:
            print("Changing MODE")
            switch()
            updateDisplay(disp)
        if disp.RPI.digital_read(disp.RPI.GPIO_KEY2_PIN) == 0: # button is released
            pass
        else: # button is pressed:
            print("ADVANCED MENU")
            updateDisplay_Advanced(disp)
            updateDisplay(disp)
        if disp.RPI.digital_read(disp.RPI.GPIO_KEY1_PIN) == 0: # button is released
            pass
        else: # button is pressed:
            print("OK")
            changeISO_OLED(disp)
            updateDisplay(disp)
        if updateEvent == 1:
            updateDisplay(disp)
            updateEvent = 0

def stopPiOled():
    global disp
    global exitRequested
    exitRequested = 1
    print("Stopping OLED")
    disp.RPI.module_exit()

def main():
    #Setup Environment
    global exitRequested
    print("Starting USBODE...")
    print(f"Mounting image store on {store_mnt}...")
    subprocess.run(['mount', store_dev, store_mnt, '-o', 'umask=000'])
    subprocess.run(['modprobe', 'libcomposite'])
    #Start IP scanning daemon, hopefully to speed up startup
    daemonIPScanner = Thread(target=getMyIPAddress, daemon=True, name='IP Scanner')
    daemonIPScanner.start()
    daemon = Thread(target=start_flask, daemon=True, name='Server')
    daemon.start()
    if os.path.exists(iso_mount_file):
        init_gadget("cdrom")
    else:
        init_gadget("exfat")
    global oledEnabled
    if oledEnabled:
        global disp
        disp = SH1106.SH1106()
        print("OLED Display Enabled")
        #Init 1.3" display
        print("done displaying output")
        oledDaemon = Thread(target=getOLEDinput, daemon=True, name='OLED')
        oledDaemon.start()
    while exitRequested == 0:
        time.sleep(0.15)
    start_exit()
    quit(0)

if __name__ == "__main__":
    main()

