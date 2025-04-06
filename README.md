# USBODE

### Turn your Pi Zero W / Zero W 2 into a virtual USB CD-ROM drive!

USBODE is a set of scripts that uses the Linux USB Gadget kernel modules to turn your Raspberry Pi Zero (W) or aspberry Pi Zero 2 (W) into one or more emulated USB CD-ROM drives. This new version utilizes `configfs`.

**Documentation is a work in progress.**

## New Install process (not yet completed)
1. **Prepare the SD Card**
-   Using the Pi Imager tool, flash the included image (see releases). This is a customized version of Raspberry Pi OS Lite (bookwork) 32-bit image (original file `2024-11-19-raspios-bookworm-armhf-lite.img.xz`) to an SD Card (32 GB minimum recommended size) 
    -   Use the Pi Imager tool to preconfigure hostname, login and locale
    -   If configuring wifi, remember, Pi Zero W and Zero 2 W models only supports 2.4ghz networks up to Wireless-N standards
2. Eject the SDCard from the computer when prompted, and re-insert the sdcard.
3. Copy all the files from the `/inst` folder to the `bootfs` partition on the SDCard. Replace `config.txt` when prompted.
6. Wait for the auto configure and everything to start, give it a few minutes, once the pi reboots unplug the keyboard from the Pi (the keyboard is incomptaible with USB host mode). If the usbode page gives a 500 error, reboot the pi then try again.

## First Startup
If no iso files are found on the sdcard, USBODE will automatically go into "USB Mass Storage" mode, allowing the user to populate the sdcard with ISO files. Once at least one ISO file is on the sdcard in the `imgstore` partition, access the USBODE interface through a web browser on another system, then load an ISO. Once the ISO is loaded, be sure to switch the mode, so it's in mode `1` CD-ROM mode. I am currently looking into some logic to make sure whenever an ISO is loaded, the device stays in CD-ROM mode.

## Usage
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
