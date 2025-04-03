# PiEmuCD

### Turn your Pi Zero into one or more virtual USB CD-ROM drives!

PiEmuCD is a Python script that uses the Linux USB Gadget kernel modules to turn your Raspberry Pi Zero (W) or aspberry Pi Zero 2 (W) into one or more emulated USB CD-ROM drives.

**Documentation is a work in progress.**

## Installation

1. **Prepare the SD Card**

-   Flash Raspberry Pi OS Lite (Bullseye) to an SD Card (16 GB minimum recommended size)
    -   Use the Pi Imager tool to preconfigure hostname, login and locale
    -   If configuring wifi, remember, Pi Zero W and Zero 2 W models only supports 2.4ghz networks up to Wireless-N standards
-   Use a partitioning tool to:
    -   Extend system partition to 4 GiB
    -   Create new partition, exFAT for the rest of the SD card -> this partition is called the **image store**.
-   Edit files from boot partition
    -   Add `dtoverlay=dwc2` to `config.txt`
    -   From `cmdline.txt` remove `quiet` and `init=/usr/lib/raspberrypi-sys-mods/firstboot` to prevent the OS from resizing the root partition on first boot

2. **Configure the Raspberry Pi**

-   Connect to the Pi, either via HDMI + keyboard, SSH or Serial
-   Create a folder for the USBODE `sudo mkdir -p /opt/usbode`
-   Copy the `piemucd.py` to the folder
-   Install flask `sudo apt-get install python3-flask`
-   Add the following file to (will need sudo access)`/lib/systemd/system/usbode.service`
```
[Unit]
Description=USBODE
After=multi-user.target
Conflicts=getty@tty1.service

[Service]
Type=simple
ExecStart=/usr/bin/python3 /opt/usbode/piemucd.py
StandardInput=tty-force

[Install]
WantedBy=multi-user.target
```
-   Reload the systemd service `sudo systemctl daemon-reload`
-   Start the service  `sudo systemctl start usbode.service`
-   Enable the service to start automatically on boot `sudo systemctl enable usbode.service`
-   To check the status of the service type `sudo systemctl status usbode.service`
-   To stop the service type `sudo systemctl stop usbode.service`
-   If you need to debug everything entirely make sure the service is stopped, then navigate to `/opt/usbode` and execute the script with `sudo python3 piemucd.py`. Once you are done debugging, type exit at the shell and that will gracefully close off the script.

3. Main interface

-  The USBODE interface will take about 30 seconds to startup, once configured.
-  For Initial setup, follow instructions at `http://<IPAddress>/setup`
-  Once the first image is mounted, e
-  Everything is controlled via web, navigate to `http://<IPAddress>` or http://<name from preconfigured hostname in step 1>

4. Adding files via Network / wifi  -- This is limited to Wi-Fi N speeds (or slower)
   a. Make sure the device is in Mode 1 (ISO serving mode)
   b. Use an ssh / sftp client to connect to `<IPAddress>`. Nagivate to `/mnt/imgstore`. Drop files here
   c. To load the new file use the web interface. The file list is refereshed every time the `/setup` or `/list` is accessed.

## Llama-ITX Notes
1. This works best with only a single ISO file being loaded
2. If booting from scratch, on my Pi Zero 2 W it takes about 45 seconds to boot up into the ISO, so if you are cold booting the Llama and want to boot from disk, wait a bit in the BIOS screen. 
3. Only a single USB is required to be connected to the Pi Zero 2 W for this application (so far) it CAN work with the data-only connection (USB Port closer to the HDMI/MicroSD slots)
4. When operating in storage mode, be reminded this is an interface via ExFAT, so it will not be possible to access the filesystem on Operating Systems priror to Windows XP with the hotfix installed.


## Known Limitations
DOS - Due to limitations in `USBASPI1.SYS` switching the image requires a reboot. This is due to the way how the Pi handles the image swap (it disconnected and reconnects it when swapping images), and the driver doesn't support disconnect/reconnection.

This has been tested up to USBASPI 2.27.

## Todo
Since finding this project, I have the following todos:
- Mount Bin/Cue files to support CDDA 

## Strech goal:
Maybe create a method to change the ISO through a DOS program or TSR (I have no experience with this though)

Feel free to contribue to the project.
