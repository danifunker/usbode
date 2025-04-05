#!/bin/bash
mount -t tmpfs tmp /run
mkdir -p /run/systemd
mount / -o remount,rw

#exec 1> /boot/usbode-setup.log 2>&1
#set -xeo pipefail

#Partition SDCard 8G for system the rest for exFat
root_mount=$(findmnt -Ufnro SOURCE -M /)
root_drive=$(lsblk -npro PKNAME "$root_mount")
root_partition=${root_mount: -1}

parted -a optimal $root_drive --script mkpart primary fat32 8092 100%
parted $root_drive --script set 1 msftdata on
chmod +x /boot/firmware/armv7l-mkfs.exfat
/boot/firmware/armv7l-mkfs.exfat -L imgstore "${root_drive}3"
mkdir -p /mnt/imgstore

sfdisk --no-reread --no-tell-kernel -fN"$root_partition" "$root_drive" <<< ',+'
partprobe $root_drive
resize2fs -p $root_mount

#Install USBODE and enable service
mkdir -p /opt/usbode
cp -R /boot/firmware/usbode/* /boot/firmware/opt/usbode
cp usbode.service /lib/systemd/system
systemctl daemon-reload
systemctl enable usbode.service

#Continue with "normal" Pi installation including script
sed -i 's| init=/bin/bash"||' /boot/firmware/cmdline.txt
/usr/lib/raspberrypi-sys-mods/firstboot

#Add the following to cmdline.txt at the end
# init=/bin/bash -c "mount -t proc proc /proc; mount -t sysfs sys /sys; mount /boot; source /boot/usbode-boot-setup.sh"