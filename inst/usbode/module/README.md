# CDROM Redirection Kernel Module

This kernel module redirects CDROM-related SCSI commands to `/dev/sr0` (or another configurable CDROM device) through the USB Gadget subsystem. It allows a Linux system to expose a local CDROM device as a USB CDROM to another machine, complete with CD Audio playback support.

## Features

- Exposes a local CDROM device through USB Gadget subsystem
- Supports SCSI commands for CDROM operations
- Handles CD Audio playback commands
- Configurable through ConfigFS
- Compatible with Linux 6.6+

## Requirements

- Linux 6.6 or higher
- USB Gadget subsystem enabled in the kernel
- ConfigFS support
- CDROM/SCSI device access (`/dev/sr0` by default)

## Installation

1. Clone this repository:

2. Build the module:

`make`

3. Install the module

`sudo cp cdrom_redirect.ko /lib/modules/$(uname -r)/kernel/drivers/usb/gadget/`

4. Load the module:

`sudo modprobe cdrom_redirect`

## Configuration

The module uses ConfigFS to enable runtime configuration. After loading the module, mount ConfigFS if not already mounted:

Create a USB Gadget configuration:

`mkdir -p /sys/kernel/config/usb_gadget/cdrom_gadget cd /sys/kernel/config/usb_gadget/cdrom_gadget`

Configure basic gadget parameters:

```
echo "0x1d6b" > idVendor # Linux Foundation 
echo "0x0104" > idProduct # Multifunction Composite Gadget 
mkdir -p strings/0x409 echo "Your Name" > strings/0x409/manufacturer 
echo "CDROM Redirector" > strings/0x409/product 
echo "123456789" > strings/0x409/serialnumber

Create configuration

mkdir -p configs/c.1/strings/0x409 
echo "CDROM Configuration" > configs/c.1/strings/0x409/configuration

Add the cdrom_redirect function:

mkdir -p functions/cdrom_redirect.0

Configure the device path (optional, default is /dev/sr0)

echo "/dev/sr0" > functions/cdrom_redirect.0/device_path 
ln -s functions/cdrom_redirect.0 configs/c.1/

Enable the gadget:


echo "device_controller_name" > UDC # Replace with your UDC name, e.g., "dwc3-gadget.0"

## Usage

Once configured and enabled, the host system that connects to your USB port will detect a USB CDROM device. The content of `/dev/sr0` (or your configured CDROM device) will be available to the host.

The module supports standard SCSI CDROM commands including:
- TEST_UNIT_READY
- INQUIRY
- READ_CAPACITY
- READ_TOC
- READ_CD
- PLAY_AUDIO
- PAUSE_RESUME
- READ_SUBCHANNEL

## Removing the Module

To remove the module:

1. Disable the gadget:

cd /sys/kernel/config/usb_gadget/cdrom_gadget echo "" > UDC

2. Remove the function and clean up:

rm configs/c.1/cdrom_redirect.0 
rmdir functions/cdrom_redirect.0 
cd .. 
rmdir cdrom_gadget

3. Unload the module:

sudo modprobe -r cdrom_redirect

## Troubleshooting

Check kernel logs for debugging information:

dmesg | grep cdrom_redirect

## License

This module is licensed under GPL v2.

