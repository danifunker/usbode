#!/usr/bin/env python3
import sys
import os
import logging
import datetime
from logging.handlers import RotatingFileHandler
import time
import subprocess
import requests
from gpiozero import *
from pathlib import Path
from threading import Thread, Lock
import time
import urllib.parse
from flask import Flask

def setup_logging():
    """Configure logging to both console and file"""
    log_file = '/boot/firmware/usbode-logs.txt'
    
    # Create logger
    logger = logging.getLogger('usbode')
    logger.setLevel(logging.INFO)
    
    # Create formatter
    log_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)
    
    try:
        # Create rotating file handler (10 MB max size, keep 3 backup files)
        file_handler = RotatingFileHandler(
            log_file, 
            maxBytes=10*1024*1024,  # 10 MB
            backupCount=3
        )
        file_handler.setFormatter(log_format)
        logger.addHandler(file_handler)
        
        # Log a startup message
        logger.info(f"=== USBODE v{versionNum} started at {datetime.datetime.now().isoformat()} ===")
    except Exception as e:
        # If we can't write to the log file, log to console only
        logger.error(f"Failed to set up file logging to {log_file}: {e}")
    
    return logger

# Add this line after your imports but before any function definitions
logger = setup_logging()

ScriptPath=os.path.dirname(__file__)
sys.path.append(f"{ScriptPath}/waveshare")
global oledEnabled
global fontM
global fontS
global fontL
global st7789Enabled
oledEnabled = False
st7789Enabled = False

try:
    import st7789
    from PIL import Image, ImageDraw, ImageFont
    st7789Enabled = True
    # Pirate Audio display is 240x240 pixels, so we can use larger fonts
    st_fontL = ImageFont.truetype(f"{ScriptPath}/waveshare/Font.ttf", 18)
    st_fontS = ImageFont.truetype(f"{ScriptPath}/waveshare/Font.ttf", 14)
    logger.info("ST7789 Display Enabled (Pirate Audio)")
except Exception as e:
    logger.warning(f"Failed to import ST7789: {e}, Pirate Audio display will not be used.")
    st7789Enabled = False

# Only try to import SH1106 if ST7789 is not available to avoid pin conflicts
if not st7789Enabled:
    try:
        import SH1106
        from PIL import Image, ImageDraw, ImageFont
        oledEnabled = True
        fontL = ImageFont.truetype(f"{ScriptPath}/waveshare/Font.ttf", 10)
        fontS = ImageFont.truetype(f"{ScriptPath}/waveshare/Font.ttf", 9)
        logger.info("WaveShare Display Enabled")
    except Exception as e:
        logger.warning(f"Failed to import SH1106 or PIL: {e}, waveshare display will not be used.")
        oledEnabled = False

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

# First, add a lock to protect the updateEvent variable
update_lock = Lock()

# Add this near the top of your file after other imports

def version():
    logger.info("USBODE - Turn your Pi Zero/Zero 2 into a virtual USB CD-ROM drive")
    logger.info("Web Functionality and massive rewrite Danifunker: https://github.com/danifunker/usbode")
    logger.info(f"USBODE version {versionNum}")

global myIPAddress
myIPAddress = "Unable to determine IP address"

def getMyIPAddress():
    while True:
        global myIPAddress, updateEvent
        time.sleep(1)
        try:
            ipAddressAttempt = subprocess.check_output(['hostname', '-I']).decode('utf-8').strip().split(' ')[0]
        except Exception as e:
            ipAddressAttempt = "Unable to determine IP address"
            logger.error(f"Failed to get IP address: {e}")
        
        if ipAddressAttempt != myIPAddress:
            logger.info(f"IP address changed from {myIPAddress} to {ipAddressAttempt}")
            myIPAddress = ipAddressAttempt
            
            # Use the lock to safely set the update event
            with update_lock:
                updateEvent = 1

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
        logger.exception("Error: ISO Not Set")
    with open(gadgetCDFolder+"/functions/mass_storage.usb0/lun.0/file", "r") as f:
        return f.readline().strip()

# Print without endline
def prints(string):
    print(string, end=' ')

def list_images():
    fileList = []
    dir_list=os.listdir(store_mnt)
    for file in dir_list:
        if (file.lower().endswith(".iso") or file.lower().endswith("cue")) and not (file.startswith("._")):
            fileList.append(file)
    fileListSorted=sorted(fileList, key=str.lower)
    logger.info(f"Found {len(fileList)} files")
    return fileListSorted
    
def cleanupMode(gadgetFolder=gadgetCDFolder):
    #Cleanup the gadget folder
    print("Unloading Gadget")
    logger.info(subprocess.run(['sh', 'scripts/cleanup_mode.sh', gadgetFolder], cwd="/opt/usbode", capture_output=True, text=True))
    time.sleep(.25)

def init_gadget(type):
    logger.info(f"Initializing USBODE {type} gadget through configfs...")
    cleanupMode()
    try:
        os.makedirs(gadgetCDFolder, exist_ok=True)
        os.makedirs(gadgetCDFolder + "/strings/0x409", exist_ok=True)
        os.makedirs(gadgetCDFolder +"/configs/c.1/strings/0x409", exist_ok=True)
        os.makedirs(gadgetCDFolder +"/functions/mass_storage.usb0", exist_ok=True)
        
        if type == "cdrom":
            result = subprocess.run(['sh', 'scripts/cd_gadget_setup.sh', gadgetCDFolder], cwd="/opt/usbode", capture_output=True, text=True)
            if result.returncode != 0:
                logger.exception(f"CDROM gadget setup failed: {result.stderr}")
            
            with open(iso_mount_file, "r") as f:
                iso_filename = f.readline().strip()
            
            if iso_filename and os.path.exists(f"{iso_filename}"):
                logger.info(f"Loading ISO: {iso_filename}")
                change_Loaded_Mount(f"{iso_filename}")
            else:
                logger.warning(f"The requested file to load {iso_filename} does not exist, switching to exFAT mode.")
                disable_gadget()
                
        elif type == "exfat":
            result = subprocess.run(['sh', 'scripts/exfat_gadget_setup.sh', gadgetCDFolder], cwd="/opt/usbode", capture_output=True, text=True)
            if result.returncode != 0:
                logger.exception(f"ExFAT gadget setup failed: {result.stderr}")
            else:
                logger.info(f"Loading ExFAT: {store_dev}")
            change_Loaded_Mount(f"{store_dev}")
            
        enable_gadget()
    except Exception as e:
        logger.exception(f"Failed to initialize {type} gadget: {e}")

def enable_gadget():
    p = subprocess.run(['sh', 'scripts/enablegadget.sh', gadgetCDFolder], cwd="/opt/usbode")
    if p.returncode != 0:
        logger.exception(f"failed: {p.returncode} {p.stderr} {p.stdout}")
        return False
    else:
        return True

def disable_gadget():
    subprocess.run(['sh', 'scripts/disablegadget.sh', gadgetCDFolder], cwd="/opt/usbode")

def switch():
    if checkState(gadgetCDFolder) == 0:
        logger.error("Both modes are disabled, enabling exfat mode")
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
        logger.error(f"{gadgetFolder}/UDC not found")
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
                logger.error(f"Could not read from {gadgetFolder}/functions/mass_storage.usb0/lun.0/cdrom")
                return 0

def change_Loaded_Mount(filename):
    isoloading = False
    #Save the ISO filename to to persistent storage
    if checkState() == 1:
        subprocess.run(['sh', 'scripts/force_eject_iso.sh', gadgetCDFolder], cwd="/opt/usbode")
    if filename.lower().endswith(".iso") or filename.lower().endswith(".cue"): 
        f = open(iso_mount_file, "w")
        f.write(f"{filename}" + "\n")
        f.close()
        isoloading = True
    #Change the disk image in the gadget
    if not os.path.exists(gadgetCDFolder+"/functions/mass_storage.usb0/lun.0/file"):
        logger.error("Gadget is not enabled, cannot change mount")
        updateDisplay(disp)
        return False
    else:
        print(gadgetCDFolder+"/functions/mass_storage.usb0/lun.0/file")
        with open(gadgetCDFolder+"/functions/mass_storage.usb0/lun.0/file", "w") as f:
            logger.info(f"Changing mount to {filename}")
            f.write(f"{filename}")
            f.close()
            if checkState() == 2 and isoloading == True:
                switch()
        global updateEvent
        updateEvent = 1
        return True

def start_exit():
    global disp, st_disp, exitRequested, oledEnabled, st7789Enabled
    exitRequested = 1
    
    if st7789Enabled:
        try:
            import RPi.GPIO as GPIO
            GPIO.cleanup()
            logger.info("ST7789 GPIO cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up GPIO: {e}")
            
    elif oledEnabled:
        try:
            disp.RPI.module_exit()
            logger.info("OLED display stopped")
        except Exception as e:
            logger.error(f"Error stopping OLED: {e}")
            
    disable_gadget()
    cleanupMode()
    logger.info(subprocess.run(['rmmod', 'usb_f_mass_storage'], capture_output=True, text=True))
    logger.info(subprocess.run(['rmmod', 'libcomposite'], capture_output=True, text=True))

def start_shutdown():
    print("Shutdown in progress...")
    subprocess.run(['shutdown', 'now'])

def start_flask():
    print("Starting Flask server...")
    app.run(host='::', port=80)

def changeISO_OLED(disp):
    file_list = list_images()
    iterator = 0
    
    if len(file_list) < 1:
        print("No images found in store, throwing error on screen.")
        disp.clear()
        image1 = Image.new('1', (disp.width, disp.height), "WHITE")
        draw = ImageDraw.Draw(image1)
        draw.text((0, 0), "No Images in store.", font=fontL, fill=0)
        draw.text((0, 14), "Please add an image first.", font=fontL, fill=0)
        disp.ShowImage(disp.getbuffer(image1))
        time.sleep(1.0)  # Show error for a second
        return False
        
    # Button pins to monitor
    button_pins = [
        disp.RPI.GPIO_KEY_UP_PIN,
        disp.RPI.GPIO_KEY_DOWN_PIN,
        disp.RPI.GPIO_KEY1_PIN,
        disp.RPI.GPIO_KEY_PRESS_PIN,
        disp.RPI.GPIO_KEY2_PIN
    ]
    
    # Button state tracking for debouncing
    last_button_states = {pin: 1 for pin in button_pins}
    debounce_time = 0.2  # seconds
    last_press_time = {pin: 0 for pin in button_pins}
    
    updateDisplay_FileS(disp, iterator, file_list)
    
    while True:
        current_time = time.time()
        
        for i, pin in enumerate(button_pins):
            current_state = disp.RPI.digital_read(pin)
            
            # Button release detected (transition from 0 to 1)
            if current_state == 1 and last_button_states[pin] == 0:
                last_button_states[pin] = 1
                
                # Check debounce
                if current_time - last_press_time[pin] > debounce_time:
                    last_press_time[pin] = current_time
                    
                    # Handle button actions
                    if i == 0:  # Up button
                        iterator = (iterator - 1) % len(file_list)
                        updateDisplay_FileS(disp, iterator, file_list)
                        print("Going up")
                    elif i == 1:  # Down button
                        iterator = (iterator + 1) % len(file_list)
                        updateDisplay_FileS(disp, iterator, file_list)
                        print(f"Selected {file_list[iterator]}")
                    elif i == 2 or i == 3:  # OK button or Press button
                        print(f"loading {store_mnt}/{file_list[iterator]}")
                        requests.request('GET', f'http://127.0.0.1/mount/{file_list[iterator]}')
                        return True
                    elif i == 4:  # Cancel button
                        print("CANCEL")
                        return True
            
            # Update button state
            last_button_states[pin] = current_state
                
        time.sleep(0.05)  # More responsive polling

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

def showLEDLights():
    #Creates a musicical pattern on the LED to indicate that the USBODE is ready
    os.system('echo 1 > /sys/class/leds/ACT/brightness') # led on
    time.sleep(.3)
    os.system('echo 0 > /sys/class/leds/ACT/brightness') # led off
    time.sleep(.1)
    os.system('echo 1 > /sys/class/leds/ACT/brightness') # led on
    time.sleep(.3)
    os.system('echo 0 > /sys/class/leds/ACT/brightness') # led off
    time.sleep(.1)
    os.system('echo 1 > /sys/class/leds/ACT/brightness') # led on
    time.sleep(.3)
    os.system('echo 0 > /sys/class/leds/ACT/brightness') # led off
    time.sleep(.1)
    os.system('echo 1 > /sys/class/leds/ACT/brightness') # led on
    time.sleep(.7)
    os.system('echo 0 > /sys/class/leds/ACT/brightness') # led off
    time.sleep(.1)
    os.system('echo 1 > /sys/class/leds/ACT/brightness') # led on
    time.sleep(.3)
    os.system('echo 0 > /sys/class/leds/ACT/brightness') # led off
    time.sleep(.1)
    os.system('echo 1 > /sys/class/leds/ACT/brightness') # led on
    time.sleep(.3)
    os.system('echo 0 > /sys/class/leds/ACT/brightness') # led off
    time.sleep(.1)
    os.system('echo 1 > /sys/class/leds/ACT/brightness') # led on
    time.sleep(.7)
    os.system('echo 0 > /sys/class/leds/ACT/brightness') # led off
    time.sleep(.1)
    os.system('echo 1 > /sys/class/leds/ACT/brightness') # led on


def getDisplayInput():
    global disp, st_disp, exitRequested, updateEvent, oledEnabled, st7789Enabled
    
    # Set up appropriate display and buttons based on what's available
    if st7789Enabled:
        logger.info("Initializing ST7789 display")
        # GPIO mode is already set at import time, no need to set again
        st_disp = init_st7789()
        
        # Pirate Audio buttons (GPIO numbers)
        # 5 = Up, 6 = Down, 16 = Mode (KEY1), 24 = Advanced (KEY2)
        import RPi.GPIO as GPIO
        
        # Pirate Audio buttons
        st_button_pins = [16, 24, 5, 6]  # Mode, Advanced, Up, Down
        for pin in st_button_pins:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Initial display update for ST7789
        if st_disp:
            updateST7789Display(st_disp)
    
    # Check waveshare OLED buttons if enabled
    if oledEnabled:
        logger.info("Initializing SH1106 OLED display")
        disp = SH1106.SH1106()
        disp.Init()
        disp.clear()
        
        # SH1106 buttons from waveshare
        button_pins = [
            disp.RPI.GPIO_KEY3_PIN,  # Mode button
            disp.RPI.GPIO_KEY2_PIN,  # Advanced menu button
            disp.RPI.GPIO_KEY1_PIN   # OK button
        ]
        
        # Initial display update
        updateDisplay(disp)
    
    # Button state tracking for debouncing (works for both display types)
    last_button_states = {}
    debounce_time = 0.2  # seconds
    last_press_time = {}
    
    # Initialize button states for appropriate display
    if oledEnabled:
        for pin in button_pins:
            last_button_states[pin] = 1  # 1 = released, 0 = pressed
            last_press_time[pin] = 0
    
    if st7789Enabled:
        for pin in st_button_pins:
            last_button_states[pin] = 1  # 1 = released, 0 = pressed
            last_press_time[pin] = 0
    
    # Track last update time for periodic updates
    last_update_time = time.time()
    update_interval = 5  # Check for updates every 5 seconds
    
    while not exitRequested:
        current_time = time.time()
        
        # Check waveshare OLED buttons if enabled
        if oledEnabled:
            for i, pin in enumerate(button_pins):
                current_state = disp.RPI.digital_read(pin)
                
                # Button press detected (transition from 1 to 0)
                if current_state == 0 and last_button_states[pin] == 1:
                    last_button_states[pin] = 0
                    
                # Button release detected (transition from 0 to 1)
                elif current_state == 1 and last_button_states[pin] == 0:
                    last_button_states[pin] = 1
                    
                    # Check debounce
                    if current_time - last_press_time[pin] > debounce_time:
                        last_press_time[pin] = current_time
                        
                        # Handle button actions
                        if i == 0:  # Mode button
                            logger.info("Changing MODE (OLED button)")
                            switch()
                            updateDisplay(disp)
                            if st7789Enabled and st_disp:
                                updateST7789Display(st_disp)
                        elif i == 1:  # Advanced menu button
                            logger.info("ADVANCED MENU (OLED button)")
                            updateDisplay_Advanced(disp)
                            updateDisplay(disp)
                            if st7789Enabled and st_disp:
                                updateST7789Display_Advanced(st_disp)
                                updateST7789Display(st_disp)
                        elif i == 2:  # OK button
                            logger.info("OK (OLED button)")
                            changeISO_OLED(disp)
                            updateDisplay(disp)
                            if st7789Enabled and st_disp:
                                updateST7789Display(st_disp)
                
                # Update button state
                last_button_states[pin] = current_state
        
        # Check Pirate Audio buttons if enabled
        if st7789Enabled:
            for i, pin in enumerate(st_button_pins):
                current_state = GPIO.input(pin)  # 1 = released, 0 = pressed
                
                # Button press detected (transition from 1 to 0)
                if current_state == 0 and last_button_states[pin] == 1:
                    last_button_states[pin] = 0
                    
                # Button release detected (transition from 0 to 1)
                elif current_state == 1 and last_button_states[pin] == 0:
                    last_button_states[pin] = 1
                    
                    # Check debounce
                    if current_time - last_press_time[pin] > debounce_time:
                        last_press_time[pin] = current_time
                        
                        # Handle button actions
                        if i == 0:  # Mode button (GPIO 16)
                            logger.info("Changing MODE (Pirate button)")
                            switch()
                            if oledEnabled:
                                updateDisplay(disp)
                            if st_disp:
                                updateST7789Display(st_disp)
                        elif i == 1:  # Advanced menu button (GPIO 24)
                            logger.info("ADVANCED MENU (Pirate button)")
                            if st_disp:
                                updateST7789Display_Advanced(st_disp)
                                time.sleep(0.5)  # Give user time to see the screen
                                # Wait for button press/release
                                while True:
                                    if GPIO.input(16) == 0:  # Confirm
                                        requests.request('GET', 'http://127.0.0.1/shutdown')
                                        break
                                    if GPIO.input(24) == 0:  # Cancel
                                        break
                                    time.sleep(0.1)
                                updateST7789Display(st_disp)
                            if oledEnabled:
                                updateDisplay_Advanced(disp)
                                updateDisplay(disp)
                        elif i == 2 or i == 3:  # Up/Down buttons (GPIO 5/6)
                            logger.info("ISO selection (Pirate button)")
                            if st_disp:
                                changeST7789ISO(st_disp)
                            if oledEnabled:
                                changeISO_OLED(disp)
                                updateDisplay(disp)
                
                # Update button state
                last_button_states[pin] = current_state
        
        # Handle display updates separately from button presses
        should_update = False
        with update_lock:
            if updateEvent == 1:
                updateEvent = 0
                should_update = True
        
        # Check for periodic updates even if no explicit event
        if current_time - last_update_time > update_interval:
            last_update_time = current_time
            should_update = True
        
        if should_update:
            if oledEnabled:
                updateDisplay(disp)
            if st7789Enabled and st_disp:
                updateST7789Display(st_disp)
            
        # More efficient sleep that doesn't block too long
        time.sleep(0.05)

def stopPiOled():
    global disp
    global exitRequested
    exitRequested = 1
    print("Stopping OLED")
    disp.RPI.module_exit()

def init_st7789():
    """Initialize the ST7789 display used in Pirate Audio boards"""
    try:
        import RPi.GPIO as GPIO
        # Set GPIO mode explicitly before any GPIO operations
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)  # Disable warnings
        
        # Initialize display with Pirate Audio specific configuration
        # Using values from the reference implementation
        logger.info("Creating ST7789 object with Pirate Audio parameters")
        display = st7789.ST7789(
            port=0,                  # SPI port 0
            cs=1,                    # SPI CS pin 1 (BG_SPI_CS_FRONT)
            dc=9,                    # GPIO pin 9 for data/command - DIFFERENT from your current value!
            backlight=13,            # Use backlight pin directly in constructor
            width=240,               # Display width
            height=240,              # Display height
            rotation=90,             # Pirate Audio uses 90 degree rotation
            spi_speed_hz=80000000,   # 80MHz - same as reference
            offset_left=0,
            offset_top=0
        )
        
        # Initialize display
        logger.info("Beginning display initialization sequence")
        display.begin()
        time.sleep(0.1)  # Brief pause after initialization
        
        # Test the display with a sequence of colors
        logger.info("Testing display with color sequence")
        
        # Create a solid red image
        red_image = Image.new('RGB', (display.width, display.height), color=(255, 0, 0))
        display.display(red_image)
        logger.info("Displayed red test pattern")
        time.sleep(0.5)
        
        # Create a solid green image
        green_image = Image.new('RGB', (display.width, display.height), color=(0, 255, 0))
        display.display(green_image)
        logger.info("Displayed green test pattern")
        time.sleep(0.5)
        
        # Create a solid blue image
        blue_image = Image.new('RGB', (display.width, display.height), color=(0, 0, 255))
        display.display(blue_image)
        logger.info("Displayed blue test pattern")
        time.sleep(0.5)
        
        # Create a solid white image
        white_image = Image.new('RGB', (display.width, display.height), color=(255, 255, 255))
        display.display(white_image)
        logger.info("Displayed white test pattern")
        
        logger.info("ST7789 display initialization complete")
        return display
        
    except Exception as e:
        logger.error(f"Failed to initialize ST7789 display: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

# Add these new functions to provide a consistent interface

def updateST7789Display(display):
    """Update the ST7789 display with current status information"""
    image = Image.new('RGB', (display.width, display.height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    # Draw header
    draw.rectangle([(0, 0), (240, 30)], fill=(58, 124, 165))
    draw.text((10, 5), "USBODE v:" + versionNum, font=st_fontL, fill=(255, 255, 255))
    
    # Draw content
    draw.text((10, 40), "IP: " + myIPAddress, font=st_fontL, fill=(0, 0, 0))
    
    iso_name = str.replace(getMountedCDName(), store_mnt+'/', '')
    # Truncate if too long
    if len(iso_name) > 20:
        iso_name = iso_name[:17] + "..."
    draw.text((10, 70), "ISO: " + iso_name, font=st_fontL, fill=(0, 0, 0))
    
    mode = checkState()
    mode_text = "(CD-Emulator)" if mode == 1 else "(ExFAT mode)" if mode == 2 else ""
    draw.text((10, 100), f"Mode: {mode} {mode_text}", font=st_fontL, fill=(0, 0, 0))
    
    # Draw button labels at bottom
    draw.rectangle([(0, 190), (240, 240)], fill=(58, 124, 165))
    draw.text((20, 200), "Change Mode", font=st_fontS, fill=(255, 255, 255))
    draw.text((160, 200), "Select ISO", font=st_fontS, fill=(255, 255, 255))
    
    display.display(image)

def updateST7789Display_FileS(display, iterator, file_list):
    """Show file selection screen on ST7789 display"""
    image = Image.new('RGB', (display.width, display.height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    # Draw header
    draw.rectangle([(0, 0), (240, 30)], fill=(58, 124, 165))
    draw.text((10, 5), "Select ISO", font=st_fontL, fill=(255, 255, 255))
    
    # Current ISO
    current_iso = str.replace(getMountedCDName(), store_mnt+'/', '')
    if len(current_iso) > 20:
        current_iso = current_iso[:17] + "..."
    draw.text((10, 40), "Current: " + current_iso, font=st_fontS, fill=(0, 0, 0))
    
    # Draw selection
    draw.rectangle([(0, 70), (240, 110)], fill=(187, 222, 251))
    selected_file = file_list[iterator]
    if len(selected_file) > 25:
        selected_file = selected_file[:22] + "..."
    draw.text((10, 80), selected_file, font=st_fontL, fill=(0, 0, 0))
    
    # Show navigation help
    draw.rectangle([(0, 190), (240, 240)], fill=(58, 124, 165))
    draw.text((20, 200), "Up/Down", font=st_fontS, fill=(255, 255, 255))
    draw.text((160, 200), "Select", font=st_fontS, fill=(255, 255, 255))
    
    display.display(image)

def updateST7789Display_Advanced(display):
    """Show advanced menu on ST7789 display"""
    image = Image.new('RGB', (display.width, display.height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    # Draw header
    draw.rectangle([(0, 0), (240, 30)], fill=(58, 124, 165))
    draw.text((10, 5), "Advanced Menu", font=st_fontL, fill=(255, 255, 255))
    
    # Menu options
    draw.text((20, 80), "Shutdown USBODE", font=st_fontL, fill=(0, 0, 0))
    
    # Draw button labels
    draw.rectangle([(0, 190), (240, 240)], fill=(58, 124, 165))
    draw.text((20, 200), "Cancel", font=st_fontS, fill=(255, 255, 255))
    draw.text((160, 200), "Confirm", font=st_fontS, fill=(255, 255, 255))
    
    display.display(image)

# Add this function for ST7789 ISO selection

def changeST7789ISO(display):
    """Handle ISO selection on ST7789 display"""
    import RPi.GPIO as GPIO
    # Ensure GPIO mode is set
    if not hasattr(GPIO, "gpio_function"):  # Check if mode is set
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
    
    file_list = list_images()
    iterator = 0
    
    if len(file_list) < 1:
        logger.warning("No images found in store")
        image = Image.new('RGB', (display.width, display.height), color=(255, 255, 255))
        draw = ImageDraw.Draw(image)
        
        # Draw error header
        draw.rectangle([(0, 0), (240, 30)], fill=(220, 53, 69))
        draw.text((10, 5), "Error", font=st_fontL, fill=(255, 255, 255))
        
        # Error message
        draw.text((10, 60), "No ISO images found", font=st_fontL, fill=(0, 0, 0))
        draw.text((10, 90), "Please add images to", font=st_fontL, fill=(0, 0, 0))
        draw.text((10, 120), "the storage device", font=st_fontL, fill=(0, 0, 0))
        
        display.display(image)
        time.sleep(2.0)  # Show error for 2 seconds
        return False
    
    # Update display with first file
    updateST7789Display_FileS(display, iterator, file_list)
    
    # Button pins: 5 = Up, 6 = Down, 16 = Select, 24 = Cancel
    select_button = 16
    cancel_button = 24
    up_button = 5
    down_button = 6
    
    # Track button states
    last_states = {
        up_button: 1,
        down_button: 1,
        select_button: 1,
        cancel_button: 1
    }
    
    while True:
        time.sleep(0.05)
        
        # Check Up button
        current_up = GPIO.input(up_button)
        if current_up == 0 and last_states[up_button] == 1:  # Pressed
            last_states[up_button] = 0
        elif current_up == 1 and last_states[up_button] == 0:  # Released
            iterator = (iterator - 1) % len(file_list)
            updateST7789Display_FileS(display, iterator, file_list)
            logger.info(f"Up button: selected {file_list[iterator]}")
            last_states[up_button] = 1
        
        # Check Down button
        current_down = GPIO.input(down_button)
        if current_down == 0 and last_states[down_button] == 1:  # Pressed
            last_states[down_button] = 0
        elif current_down == 1 and last_states[down_button] == 0:  # Released
            iterator = (iterator + 1) % len(file_list)
            updateST7789Display_FileS(display, iterator, file_list)
            logger.info(f"Down button: selected {file_list[iterator]}")
            last_states[down_button] = 1
        
        # Check Select button
        current_select = GPIO.input(select_button)
        if current_select == 0 and last_states[select_button] == 1:  # Pressed
            last_states[select_button] = 0
        elif current_select == 1 and last_states[select_button] == 0:  # Released
            logger.info(f"Loading {store_mnt}/{file_list[iterator]}")
            requests.request('GET', f'http://127.0.0.1/mount/{urllib.parse.quote_plus(file_list[iterator])}')
            return True
        
        # Check Cancel button
        current_cancel = GPIO.input(cancel_button)
        if current_cancel == 0 and last_states[cancel_button] == 1:  # Pressed
            last_states[cancel_button] = 0
        elif current_cancel == 1 and last_states[cancel_button] == 0:  # Released
            logger.info("Cancel button pressed")
            return False

def main():
    #Setup Environment
    global exitRequested
    logger.info("Starting USBODE...")
    logger.info(f"Mounting image store on {store_mnt}...")
    
    try:
        result = subprocess.run(['mount', store_dev, store_mnt, '-o', 'umask=000'], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Failed to mount image store: {result.stderr}")
        
        #Append sbin paths for cron install
        os.environ['PATH'] = f"{os.environ['PATH']}:/sbin:/usr/sbin:/usr/local/sbin"
        logger.info(f"Path is currently set to: {os.environ['PATH']}")
        subprocess.run(['modprobe', 'libcomposite'], capture_output=True, text=True)
        
        #Start IP scanning daemon, hopefully to speed up startup
        daemonIPScanner = Thread(target=getMyIPAddress, daemon=True, name='IP Scanner')
        daemonIPScanner.start()
        logger.info("IP scanner thread started")
        
        daemon = Thread(target=start_flask, daemon=True, name='Server')
        try: 
            daemon.start()
            logger.info("Flask server thread started")
        except Exception as e:
            logger.error(f"Failed to start Flask server: {e}")
        
        if os.path.exists(iso_mount_file):
            init_gadget("cdrom")
        else:
            init_gadget("exfat")

        #LED Lights aren't working yet
        # daemonLEDBlinker = Thread(target=showLEDLights, daemon=True, name='LED Blinker')
        # try:
        #     daemonLEDBlinker.start()
        #     logger.info("LED blinker thread started")
        # except Exception as e:
        #     logger.error(f"Failed to start LED blinker: {e}")

        # Start display thread if any display is enabled
        if st7789Enabled or oledEnabled:
            displayDaemon = Thread(target=getDisplayInput, daemon=True, name='Display')
            try:
                displayDaemon.start()
                if st7789Enabled:
                    logger.info("ST7789 display thread started")
                elif oledEnabled:
                    logger.info("Waveshare OLED thread started")
            except Exception as e:
                logger.error(f"Failed to start display thread: {e}")
            
        while exitRequested == 0:
            time.sleep(0.15)
            
        start_exit()
        logger.info("Clean exit completed")
        quit(0)
    except Exception as e:
        logger.exception(f"Fatal error in main thread: {e}")
        quit(1)

if __name__ == "__main__":
    main()