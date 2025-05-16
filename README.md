# USBODE
USBODE allows you to emulate an optical drive on nearly any computer equipped with a working USB port. It's like a Gotek Floppy Emulator, but for CD drives! It uses a Raspberry Pi Zero W or Zero W 2 to do the heavy lifting, and images are stored as .ISO files on a MicroSD card (no .Cue/.Bin support _yet_).

## Requirements:
1. A Raspberry Pi Zero W or Zero 2 W
2. A MicroSD card you're willing to format. We suggest a 32 GB card, but you can get away with as little as 8.
3. A USB cable with male Type A on one side, and male Micro B on the other. Micro B is what most people think of as an ordinary Micro USb cable. This cable needs to be capable of data transfer, not just power.
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
4. The Pi is now performing an initial boot, which can take up to 10 minutes to complete on a first-gen Zero W (subsequent boots will be much faster, and the first boot will be faster if you have a faster SD card and a Zero W 2). Once this process is complete, the Pi will connect to the wifi network you assigned earlier. You should now be able to access the ODE by entering its IP address in a browser.
   - If you see "The connection has timed out", it is likely still booting. If you see a 500 error, this is usually resolved by rebooting the Pi.

The setup should now be complete, and you're ready to go. If you have any difficulties, come check out the [Discord](https://discord.gg/na2qNrvdFY).

## Using USBODE
USBODE loads ISO images from the MicroSD card that the Pi boots from. You'll need to put ISO files on that card for your device to see them. While you can transfer files over the network or over the Pi's USB cable, transfer speeds are much faster if you can plug your MicroSD card into a computer.

1. Shut down the Pi if it's currently running. You can do so from the ODE's web page.
2. Wait for the Pi to shut down, then unplug the USB cable and remove the MicroSD card.
3. Plug the MicroSD card into your computer. Just about any adapter or USB reader should work. Once it's in, your computer should detect 3 partitions, including `imgstore` (See below if it doesn't appear).
4. Copy one or more ISO files into the imgmount folder. At this time, the ISOs must all be lower-case (I.E. _image.iso_, not _IMAGE.ISO_ or _image.ISO_). We know for sure that underscores work, but other special characters might not.
5. Once you've copied your ISO(s) over, safely eject the SD card from your computer.
6. Put the card back into the pi and plug the USB cable back in. Again, it should go into the port labled USB, not PWR. Also, if it's not already, plug the other end of the USB cable into your target device.
7. Once the device boots, visit the device's IP address in a browser. You can use the "Select an Image" link if one is not already loaded. This will allow you to select the ISO you want your emulated drive to load.
8. If it is not already in Mode 1, make sure to use the Switch Modes option. This should switch from Mode 2 to Mode 1.

The device's browser page is purposefully kept minimalist, so it will work on very old browsers. This allows you to change images from the computer you're emulating on, if you can connect to the same network.

## Old documentation resumes here.

## Usage
3. Main interface

-  The USBODE interface will take about 30 (18 seconds with an A2 class microSD card) seconds to startup, once configured.
-  Initially drop some files from your computer into imgstore
-  Everything is controlled via web, navigate to `http://<IPAddress>` or http://<name from preconfigured hostname in step 1>
-  This project also supports the Waveshare 1.3" OLED HAT in SPI and I2C modes, details: https://www.waveshare.com/wiki/1.3inch_OLED_HAT

4. Adding files via Network / wifi  -- This is limited to Wi-Fi N speeds (or slower)
   a. Make sure the device is in Mode 1 (ISO serving mode)
   b. Use an FTP / ssh / sftp client to connect to `<IPAddress>`. Nagivate to `/mnt/imgstore`. Drop files here. If using FTP the path will automatically be set for you, don't forget to use port 21 as the port, and there is no encryption through this method.
   d. To load the new file use the web interface, or the on-screen display.

5. To change the Wireless network the Raspberry Pi is associated with, shutdown the Pi, eject the microSD card and place it back into the computer. Open up the `bootfs` volume and copy the new-wifi_example.json to new-wifi.json. Enter the new SSID and password. Since this is a JSON file, only to change what is between the `" "`. Safely eject the microsd card and place it back into the Raspberry Pi. The file will be read about 5 seconds after the USBODE starts and it will attempt to connect to the new wifi. If any issues occur, shutdown the USBODE and plug the SDCard back into the computer, and review the file named `new-wifi-output.txt` in the `bootfs` volume.

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

## Discord Server
For updates on this project please visit the discord server here: https://discord.gg/na2qNrvdFY

## Youtube Video
I created a youtube video which covers the old installation process. The new process is almost the same, just no files are required to copy after imaging the device.

Here is a link to my how-to video: https://www.youtube.com/watch?v=o7qsI4J0sys

This project will also be featured on video on [PhilsComputerLab](https://www.youtube.com/channel/UCj9IJ2QvygoBJKSOnUgXIRA)!
Here is his [first video](https://www.youtube.com/watch?v=Is3ULD0ZXnI).
Please like and subscribe to Phil so you can stay up to date on this project and many other cool retro computing things!

## Donations

Support me on ko-fi!
https://ko-fi.com/danifunker
