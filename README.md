# USBODE: the USB Optical Drive Emulator
USBODE uses a Raspberry Pi Zero to emulate an optical drive over USB. It appears to your computer as a standard CD drive, and you can load up .ISO files stored on the Pi's MicroSD card. It can be easily configured over a web interface, and it can also take advantage of the Waveshare OLED hat.

## What can it do?
By emulating a generic CD drive, you can:
- Install and run CD-based games without the need for physical media
- Boot from the drive to install an operating system or use recovery media
- It even works for titles that use multiple CDs
Since it uses a Pi to do the heavy lifting, you can also:
- Store a collection of .ISO files on an SD card and quickly switch between them (No .CUE/.BIN support _yet_)
- Mount .ISO images on operating systems that never had support for things like DaemonTools

## Requirements:
1. A Raspberry Pi Zero W or Zero 2 W
2. A MicroSD card you're willing to format. We suggest a 32 GB card, but you can get away with as little as 8.
3. A USB cable with male Type A on one side, and male Micro B on the other. Micro B is what most people think of as an ordinary Micro USB cable. This cable needs to be capable of data transfer, not just power.
4. The latest [USB-ODE Release Image](https://github.com/danifunker/usbode/releases).
5. The [Raspberry Pi Imager](https://www.raspberrypi.com/software/) application.
6. A computer with a USB port (if you're using a modern computer to set this up, great. If you're intending to use this on a retro PC, it also needs a USB port).

## Setting Up USBODE
(Current as of v1.8; 1.7 and before have a different process)
1. Open the Pi Imager tool. Under `Choose Device`, select the model of Pi you're using. Under `Choose OS`, select the USB-ODE image you downloaded. Under `Choose Storage`, select your MicroSD card.
2. Preconfigure your hostname, login info (for SSH), WiFi information, and locale.
   - Note, the Pi Zero W and Pi Zero W 2 support 2.4 GHz networks up to Wireless N (802.11N). They do not support 5 GHz networks. If your router broadcasts in both modes, input the name that the 2.4 GHz mode uses. It's fine if both modes use the same name.
2. Once the Pi Imager Tool has completed, it will notify you. You should then eject the card and insert it into your Pi.
3. Plug the USB cable into the computer you intend to emulate an optical drive on. The Pi has two Micro USB ports, one labled PWR and the other USB. Plug the Micro A end into the one labled USB, _not_ the one labled PWR. After a half-second or so, you should see the Pi's indicator LED flashing randomly, then in a pattern.
4. The Pi is now performing an initial boot, which can take up to 10 minutes to complete on a first-gen Zero W (subsequent boots will be much faster, and the first boot will be faster if you have a faster SD card or a Zero W 2). Once this process is complete, the Pi will connect to the wifi network you assigned earlier. You should now be able to access the ODE by entering its IP address in a browser.
   - If you see "The connection has timed out", it is likely still booting. If you see a 500 error, this is usually resolved by rebooting the Pi.

The setup should now be complete, and you're ready to go. If you have any difficulties, come check out the [Discord](https://discord.gg/na2qNrvdFY).

## Using USBODE
USBODE loads ISO images from the MicroSD card that the Pi boots from. You'll need to put ISO files on that card for your device to see them. While you can transfer files over the network or over the Pi's USB cable, transfer speeds are much faster if you can plug your MicroSD card into a computer. Here's what that process looks like:

1. Shut down the Pi if it's currently running. You can do so from the ODE's web page.
2. Wait for the Pi to shut down, then unplug the USB cable and remove the MicroSD card.
3. Plug the MicroSD card into your computer. Just about any adapter or USB reader should work. Once it's in, your computer should detect 3 partitions, including `imgstore` (See below if it doesn't appear).
4. Copy one or more ISO files into the root of the `imgstore` partition. At this time, the ISOs must all be lower-case (I.E. _image.iso_, not _IMAGE.ISO_ or _image.ISO_). We know for sure that underscores work, but other special characters might not.
5. Once you've copied your ISO(s) over, safely eject the SD card from your computer.
6. Put the card back into the Pi and do the same with the USB cable. Again, it should go into the port labled USB, not PWR.
7. Once the device boots (this time it should take somewhere between 18-30 seconds), navigate in your browser to `http://<IPAddress>`; for example, `http://192.168.0.50`. If you configured a hostname during the setup, you can also use that instead of an IP address; for example, `http://rpiODE`. The host name is case-sensitive. You can use the "Load another Image" link if one is not already loaded. This will allow you to select the ISO you want your emulated drive to load.
8. If it is not already in Mode 1, make sure to use the Switch Modes option. This should switch from Mode 2 to Mode 1.

The device's browser page is purposefully kept pretty simple, so it can still work on very old browsers. This allows you to change images from the computer you're emulating on, if you can connect to the same network.

## Troubleshooting

### My target computer doesn't see the Pi as an Optical Drive.
This is likely because the ODE is stuck in Mode 2 or Mode 0. See below for a resolution.

### I can't switch to Mode 1; switching from Mode 2 takes me to Mode 0.
This can be resolved by manually creating a text file. SSH into the Pi, then create a file at /opt/usbode/usbode-iso.txt.

### After imaging with the Pi Imager, I only see two partitions on my card, and imgstore isn't one of them.
This is a known issue on Windows. It's likely that the partition is there, but needs to be assigned a Drive Letter. It's easy to use the Disk Management tool to fix this. In the Start Menu, look for "Create and format hard disk partitions". Once this tool loads, find your SD card in the lower list of disks. You should see that there are three partitions. Right-click on `imgstore`, and select "Change Drive Letter and Paths". Click Add, then add whatever drive letter is most convenient for you. It should then immediately appear for you to drag files to.

## Other notes
- USBODE supports the Waveshare 1.3" OLED HAT in SPI and I2C modes, giving you a very easy-to-navigate interface on the Pi itself. For details, visit (https://www.waveshare.com/wiki/1.3inch_OLED_HAT).
- If the device is in Mode 1, you can establish an FTP, SSH, or SFTP connection to it to transfer images. Keep in mind that the transfer speed of this will be limited to 802.11N speeds.
- You can change which WiFi network the Pi is associated with. Put the MicroSD card into your computer, and open the `bootfs` volume. From there, copy the file `new-wifi_example.json` and rename the copy `new-wifi.json`. In that file, enter your new SSID and password. Safely eject the microsd card and place it back into the Raspberry Pi. The file will be read about 5 seconds after the USBODE starts, and it will attempt to connect to the new wifi. If any issues occur, shutdown the USBODE and plug the SDCard back into the computer, and review the file named `new-wifi-output.txt` in the `bootfs` volume.
- Since the configfs settings are reloaded between configurations, and entirely destroyed on a reboot, I have opted to store the most recently loaded ISO filename into `/opt/usbode/usbode-iso.txt`. Not having this file should not cause any issues, since there is a setup endpoint that can be used for initial configuration, however I haven't tested that code path yet.

## Llama-ITX Notes
1. This works best with only a single ISO file being loaded
2. If booting from scratch, on my Pi Zero 2 W it takes about 45 seconds to boot up into the ISO, so if you are cold booting the Llama and want to boot from disk, wait a bit in the BIOS screen. 
3. Only a single USB is required to be connected to the Pi Zero 2 W for this application (so far) it CAN work with the data-only connection (USB Port closer to the HDMI/MicroSD slots)
4. When operating in storage mode, be reminded this is an interface via ExFAT, so it will not be possible to access the filesystem on Operating Systems priror to Windows XP with the hotfix installed.

## Known Limitations
DOS - Due to limitations in `USBASPI1.SYS`, switching between modes 2 and 1 requires a reboot. The Pi has to disconnect from your machine and reconnect when swapping modes. 
Case Sensitivity - Currently, any ISO you load needs to be all lower-case, including the file extension.

## Todo
- Add support for mounting Bin/Cue, enabling CDDA

## Strech goals:
- Make some way to change the mounted ISO through a DOS program or TSR? I have no experience with this and would appreciate any expertise you may have to offer.
- Make a second USB interface, perhaps a COM port, to be able to communicate with the app.

Feel free to contribue to the project.

## Discord Server
For updates on this project please visit the discord server here: (https://discord.gg/na2qNrvdFY)

## Youtube Video
I created a [YouTube video](https://www.youtube.com/watch?v=o7qsI4J0sys) which covers the old installation process. The new process is almost the same, just no files are required to copy after imaging the device.

This project is also featured on video on [PhilsComputerLab](https://www.youtube.com/channel/UCj9IJ2QvygoBJKSOnUgXIRA)!
Here is his [first video](https://www.youtube.com/watch?v=Is3ULD0ZXnI).
Please like and subscribe to Phil so you can stay up to date on this project and many other cool retro computing things!

## Donations
Support me on ko-fi!
(https://ko-fi.com/danifunker)
