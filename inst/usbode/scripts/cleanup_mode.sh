cd $1

rm configs/c.1/mass_storage.usb0
rmdir configs/c.1/strings/0x409
rmdir configs/c.1
rmdir functions/mass_storage.usb0
rmdir strings/0x409
cd ..
rmdir $1
