cd $1

echo "0x0525" > idVendor  # Linux Foundation - must be adopted by your ID
echo "0xa4a5" > idProduct # Linux-USB file backed Storage Gadget - must be adopted by your ProductID
echo 0x0100 > bcdDevice   # v1.0.0
echo 0x0200 > bcdUSB      # USB 2.0

echo "1111111111" > strings/0x409/serialnumber
echo "Linux" > strings/0x409/manufacturer
echo "USBODE-v1.10-ExFAT" > strings/0x409/product

echo "Config 1: USBODE-USB" > configs/c.1/strings/0x409/configuration
echo 0 > configs/c.1/MaxPower

echo 0 > functions/mass_storage.usb0/lun.0/cdrom
echo 0 > functions/mass_storage.usb0/lun.0/ro
echo 1 > functions/mass_storage.usb0/lun.0/removable
ln -s functions/mass_storage.usb0 configs/c.1
