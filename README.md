# USBODE: the USB Optical Drive Emulator
USBODE uses a Raspberry Pi Zero to emulate optical drives on retro computers equipped with USB. It appears to your computer as a standard CD drive, and you can load up .ISO files stored on the Pi's MicroSD card. It can be easily configured over a web interface, and it can also take advantage of the Waveshare OLED hat.

## What can it do?
By emulating a CD-ROM drive with USBODE, you can:
- Store a collection of ISO files on the SD card and quickly switch between them.
- Install and run CD-based games without the need for physical media. This includes multi-disc titles.
- Boot from the drive to install an operating system or use recovery media.
Note: It may not work with some forms of CD-ROM copy protection. Also, there is no CUE/BIN support _yet_.

## Requirements:
1. A Raspberry Pi Zero W or Zero 2 W (USBODE is optimized for the Pi Zero 2 W)
2. A MicroSD card. 32 GB or greater is recommended, however 8 GB is the absolute minimum. A fast card (e.g. A1 or A2) will improve boot and load times.
3. A setup computer with the ability to mount and image the MicroSD card.
4. A USB cable with male Type A on one side, and male [Micro B](https://en.wikipedia.org/wiki/USB_hardware#/media/File:MicroB_USB_Plug.jpg) on the other. Micro B is what most people think of as an ordinary Micro USB cable (as opposed to [Mini](https://en.wikipedia.org/wiki/USB_hardware#/media/File:Cable_Mini_USB.jpg)). This cable needs to be capable of data transfer, not just power.
5. The latest [USB-ODE Release Image](https://github.com/danifunker/usbode/releases).
6. The [Raspberry Pi Imager](https://www.raspberrypi.com/software/) application.
7. A target computer with a USB port that will be utilizing USBODE.

## USBODE Initial Setup
(From v1.8 onward; v1.7 and prior uses a different process)
1. Plug your Micro SD card into your setup computer.
2. Open the Raspberry Pi Imager tool. Under `Choose Device`, select the model of Pi you're using. Under `Choose OS`, select the USB-ODE image you downloaded. Under `Choose Storage`, select your MicroSD card.
3. Preconfigure your hostname, login info (for SSH), Wi-Fi information, and locale.
   - Note, the Pi Zero W and Pi Zero W 2 support 2.4 GHz networks up to Wireless N (802.11N). They do not support 5 GHz networks. If your router broadcasts in both modes, input the name that the 2.4 GHz mode uses. It's fine if both modes use the same name.
4. Once the Pi Imager Tool has completed, it will notify you. Eject the card and insert it into your Pi Zero.
5. Connect the Pi Zero to your setup computer. The Pi Zero has two Micro USB connections ports: one labeled USB and the other labeled PWR. Insert the Micro B end of the cable into the port labeled USB. The Pi’s indicator LED will begin flashing soon after.
6. The Pi will perform an initial setup boot, which can take a while (See the bullet on card speeds under "Other Notes"). When the initial setup is complete, a drive called IMGSTORE should appear on your setup computer. You can copy ISO images into this folder now if you’d like.
7. You should now be able to access the USBODE browser interface by entering its IP address (or the Hostname if you defined that earlier) in a web-browser. If your router automatically assigns IP addresses via DHCP, log into your router’s web interface to see the IP assigned to your Pi Zero device. See the section below on navigating the USBODE browser interface.
   - If you see "The connection has timed out", it is likely still booting. If you see a 500 error, this is usually resolved by rebooting the Pi.

The setup should now be complete. If you have any difficulties, help is available on [Discord](https://discord.gg/8qfuuUPBts).

## Using USBODE on the target computer
1. Shut down the target computer.
2. Connect the Pi Zero to the target computer. As above, the Micro B end of the cable needs to be plugged into the Pi's `USB` port, not `PWR`. The other end will plug into any of the target computer's USB ports.
3. Turn on the target computer. The Pi Zero's indicator LED will start blinking.
4. Once the target computer boots, it should be able to see the USBODE as a standard CD-ROM drive. See the Browser Interface section below to load images.

## Copying Images onto USBODE
USBODE stores your ISO images on the MicroSD card in a folder labeled IMGSTORE. You'll need to put ISO files directly into this folder. There are three ways to do this:
- Connect the Pi Zero to your setup computer via USB.
- Remove the MicroSD card from the Pi Zero and connect it directly to your setup computer. Transfer speeds are probably the fastest with this option.
- Connect to USBODE via SSH.

## Using the USBODE Browser Interface
The browser interface is used to switch modes, load an image, and shutdown the device.

### Switching Modes:
USBODE has two modes. _Mode 1: CD-Emulator_ and _Mode 2: Ex-FAT Storage Device_.

Use the _/switch_ link in the browser interface to switch between Modes 1 and 2.

In Mode 1, USBODE serves a single ISO image to the target computer. The target computer sees the image as CD-ROM media. In Mode 2, USBODE presents itself to a computer (target or setup) as a storage device named IMGSTORE. To copy images from a computer to USBODE storage, you must be in Mode 2.

### Loading an Image:
The image currently being served is displayed on the browser page after the text _Currently Serving_. To change the image being served, first make sure you are in Mode 1  then click _Load Another Image_. This will navigate to a page listing all the images stored on the device. Click on the image you would like to load, and you'll see a page informing you that it is attempting to mount the image. Click _Return to USBODE homepage_ to confirm that the image was loaded.

### Shutting Down USBODE:
On the USBODE homepage, click _Shutdown the pi_. The LED indicator will flash for several seconds and eventually turn off. It is now safe to unplug the device from the computer.

## Troubleshooting

### My target computer doesn't see the Pi as an Optical Drive.
This is likely because the ODE is stuck in Mode 2 or Mode 0. See below for a resolution.

### Windows: My computer doesn't see the `imgstore` partition on my SD card after imaging with the Pi Imager.
The partition is there, but did not get assigned a drive letter. Manually assigning a drive letter with your preferred tool will make it appear. If you're unfamiliar, search for "disk" in the Start Menu and one of the first results should be "Create and format hard disk partitions". Once it loads, find your SD card in the lower list of disks. You should see that there are three partitions on it, including imgstore. Right-click on `imgstore`, and select "Change Drive Letter and Paths". Click Add, then add whatever drive letter is most convenient for you. It should then immediately appear in Explorer for you to drag files to.

### How can I boot from the USBODE if it isn't ready until after my computer POSTs?
Use the `Pause/Break` key when you first see the POST screen. This will give the Pi enough time to boot. Once it's ready, load up an image using the browser interface (or a Hat if you have one). Then, press the `Enter` key to resume the POST. You should be able to go into the BIOS and select it as a bootable device at this time.

## Other notes
- USBODE supports the Waveshare 1.3" OLED HAT in SPI and I2C modes, giving you a very easy-to-navigate interface on the Pi itself. For details, visit (https://www.waveshare.com/wiki/1.3inch_OLED_HAT).
- If the device is in Mode 1, you can establish an FTP, SSH, or SFTP connection to it to transfer images. Keep in mind that the transfer speed of this will be limited to 802.11N speeds.
- You can change which Wi-Fi network the Pi is associated with. Put the MicroSD card into your computer, and open the `bootfs` volume. From there, copy the file `new-wifi_example.json` and rename the copy `new-wifi.json`. In that file, enter your new SSID and password. Safely eject the MicroSD card and place it back into the Raspberry Pi. The file will be read about 5 seconds after the USBODE starts, and it will attempt to connect to the new wifi. If any issues occur, shutdown the USBODE and plug the SD card back into the computer, and review the file named `new-wifi-output.txt` in the `bootfs` volume.
- Since the `configfs` settings are reloaded between configurations, and entirely destroyed on a reboot, I have opted to store the most recently loaded ISO filename into `/opt/usbode/usbode-iso.txt`. Not having this file should not cause any issues, since there is a setup endpoint that can be used for initial configuration, however I haven't tested that code path yet.
- Card Speeds and Long Boot Times: The Pi will take some time to perform its initial boot. On a C10/UHS1 card (with no 'A' class specification) and a first-gen Raspberry Pi Zero W, we saw initial boot times approaching 10 minutes. We hope this is the worst-case scenario. Subsequent boots were closer to a minute or so. Faster cards, especially those with the A1 specification (designed more for random read/writes as opposed to streaming video), will provide faster boots. Also, using a second gen Raspberry Pi Zero W 2 should grant additional speed benefits.

## Llama-ITX Notes
1. This works best with only a single ISO file being loaded
2. If booting from scratch, on my Pi Zero 2 W it takes about 45 seconds to boot up into the ISO, so if you are cold booting the Llama and want to boot from disk, wait a bit in the BIOS screen. 
3. Only a single USB is required to be connected to the Pi Zero 2 W for this application (so far) it CAN work with the data-only connection (USB Port closer to the HDMI/MicroSD slots)
4. When operating in storage mode, be reminded this is an interface via ExFAT, so it will not be possible to access the filesystem on Operating Systems prior to Windows XP with the hotfix installed.

## Known Limitations
- DOS - Due to limitations in `USBASPI1.SYS`, switching between modes 2 and 1 requires a reboot. The Pi has to disconnect from your machine and reconnect when swapping modes.

## Todo
- Add support for mounting Bin/Cue, enabling CDDA

## Strech goals:
- Make some way to change the mounted ISO through a DOS program or TSR? I have no experience with this and would appreciate any expertise you may have to offer.
- Make a second USB interface, perhaps a COM port, to be able to communicate with the app.

Feel free to contribute to the project.

## Discord Server
For updates on this project please visit the discord server here: (https://discord.gg/na2qNrvdFY)

## YouTube Video
I created a [YouTube video](https://www.youtube.com/watch?v=o7qsI4J0sys) which covers the old installation process. The new process is almost the same, just no files are required to copy after imaging the device.

This project is also featured on video on [PhilsComputerLab](https://www.youtube.com/channel/UCj9IJ2QvygoBJKSOnUgXIRA)!
Here is his [first video](https://www.youtube.com/watch?v=Is3ULD0ZXnI).

Please like and subscribe to Phil so you can stay up to date on this project and many other cool retro computing things!

## Donations
Support me on ko-fi!
(https://ko-fi.com/danifunker)

Readme updated by [Zarf](https://github.com/Zarf-42) and wayneknight_rider.
