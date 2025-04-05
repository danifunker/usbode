# USBODE

### Turn your Pi Zero W / Zero W 2 into a virtual USB CD-ROM drive!

USBODE is a set of scripts that uses the Linux USB Gadget kernel modules to turn your Raspberry Pi Zero (W) or aspberry Pi Zero 2 (W) into one or more emulated USB CD-ROM drives. This new version utilizes `configfs`.

**Documentation is a work in progress.**

## New Install process (not yet completed)
1. **Prepare the SD Card**
-   Using the Pi Imager tool, flash Raspberry Pi OS Lite (bookwork) 32-bit images to an SD Card (32 GB minimum recommended size)
    -   Use the Pi Imager tool to preconfigure hostname, login and locale
    -   If configuring wifi, remember, Pi Zero W and Zero 2 W models only supports 2.4ghz networks up to Wireless-N standards
2. Eject the SDCard from the computer when prompted, and re-insert the sdcard.
3. Copy all the files from the `/inst` folder to the `bootfs` partition on the SDCard. Replace `config.txt` when prompted.
4. Edit the file cmdline.txt, remove `init=` (all of the stuff after init before the space) and replace it with `init=/bin/bash`. Eject the SDCard rom the computer.

5. **Start the Pi with Keyboard and Video connected**. Plug in a keyboard, video and the MicroSD card into the Pi (keyboard was tested using an OTG dongle). Remember to use the USB port closer to the HDMI port. Boot it up, when you see the `#` prompt, type in the following commands:
    * `mount /boot/firmware`
    * `/boot/firmware/setup.sh`

6. Wait for the auto configure and everything to start, give it a few minutes, once the pi reboots unplug the keyboard from the Pi (the keyboard is incomptaible with USB host mode).

The above documention might be missing stuff, please be patient with me during this time.

## Installation 

1. **Prepare the SD Card**

-   Flash Raspberry Pi OS Lite (Bullseye) to an SD Card (16 GB minimum recommended size)
    -   Use the Pi Imager tool to preconfigure hostname, login and locale
    -   If configuring wifi, remember, Pi Zero W and Zero 2 W models only supports 2.4ghz networks up to Wireless-N standards
-   Use a partitioning tool to:
    -   Extend system partition to 8-16 GiB* (This has been increased, as I am continuing to work on other features for this script and we might need some additional space)
    -   Create new partition, exFAT for the rest of the SD card -> this partition is called the **image store**.
-   Edit files from boot partition
    -   Add `dtoverlay=dwc2` to `config.txt`
    -   From `cmdline.txt` remove `quiet` and `init=/usr/lib/raspberrypi-sys-mods/firstboot` to prevent the OS from resizing the root partition on first boot

2. **Configure the Raspberry Pi**

-   Connect to the Pi, either via HDMI + keyboard, SSH or Serial
-   Create a folder for the USBODE `sudo mkdir -p /opt/usbode`
-   Copy the `usbode.py` to the folder
-   Copy the `scripts` folder and all of the contents into the same folder. Folder setup should loook like this:
```
/opt/usbode
├── scripts
│   ├── cd_gadget_setup.sh
│   ├── cleanup_mode.sh
│   ├── disablegadget.sh
│   ├── enablegadget.sh
│   └── exfat_gadget_setup.sh
└── usbode.py
```
-   Install flask `sudo apt-get install python3-flask`
-   Add the following file to (will need sudo access)`/lib/systemd/system/usbode.service`
```
[Unit]
Description=USBODE
After=multi-user.target
Conflicts=getty@tty1.service

[Service]
Type=simple
ExecStart=/usr/bin/python3 /opt/usbode/usbode.py
StandardInput=tty-force
Restart=on-failure

[Install]
WantedBy=multi-user.target
```
-   Reload the systemd service `sudo systemctl daemon-reload`
-   Start the service  `sudo systemctl start usbode.service`
-   Enable the service to start automatically on boot `sudo systemctl enable usbode.service`
-   To check the status of the service type `sudo systemctl status usbode.service`
-   To stop the service type `sudo systemctl stop usbode.service`
-   If you need to debug everything entirely make sure the service is stopped, then navigate to `/opt/usbode` and execute the script with `sudo python3 usbode.py`. Once you are done debugging, type exit at the shell and that will gracefully close off the script.

3. Main interface

-  The USBODE interface will take about 30 seconds to startup, once configured.
-  For Initial setup, follow instructions at `http://<IPAddress>/setup`
-  Once the first image is mounted, e
-  Everything is controlled via web, navigate to `http://<IPAddress>` or http://<name from preconfigured hostname in step 1>

4. Adding files via Network / wifi  -- This is limited to Wi-Fi N speeds (or slower)
   a. Make sure the device is in Mode 1 (ISO serving mode)
   b. Use an ssh / sftp client to connect to `<IPAddress>`. Nagivate to `/mnt/imgstore`. Drop files here
   c. To load the new file use the web interface. The file list is refereshed every time the `/setup` or `/list` is accessed.

## Application notes
* Since the configfs settings are reloaded between configurations, and entirely destroyed on a reboot, I have opted to store the most recently loaded ISO filename into `/opt/usbode/usbode-iso.txt`. Not having this file should not cause any issues, since there is a setup endpoint that can be used for initial configuration, however I haven't tested that code path yet.

## Llama-ITX Notes
1. This works best with only a single ISO file being loaded
2. If booting from scratch, on my Pi Zero 2 W it takes about 45 seconds to boot up into the ISO, so if you are cold booting the Llama and want to boot from disk, wait a bit in the BIOS screen. 
3. Only a single USB is required to be connected to the Pi Zero 2 W for this application (so far) it CAN work with the data-only connection (USB Port closer to the HDMI/MicroSD slots)
4. When operating in storage mode, be reminded this is an interface via ExFAT, so it will not be possible to access the filesystem on Operating Systems priror to Windows XP with the hotfix installed.


## Known Limitations
DOS - Due to limitations in `USBASPI1.SYS` switching between exFAT mode and ISO serving a reboot. This is due to the way how the Pi handles the image swap it disconnected and reconnects it when switching modes. The previous limitation of switching ISOs in DOS mode has been lifted due to this re-write.

This has been tested up to USBASPI 2.27.

## Todo
Since finding this project, I have the following todos:
- Mount Bin/Cue files to support CDDA 

## Strech goal:
Maybe create a method to change the ISO through a DOS program or TSR (I have no experience with this though)

It is also possible to startup a second USB interface, possibly a COM port to be able to communicate with the app maybe.

Feel free to contribue to the project.

## Donations

Support me on ko-fi!
https://ko-fi.com/danifunker
