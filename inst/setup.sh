#!/bin/bash
mount -t tmpfs tmp /run
mount / -o remount,rw

#exec 1> /boot/usbode-setup.log 2>&1
#set -xeo pipefail

#Partition SDCard 8G for system the rest for exFat
root_mount=$(findmnt -Ufnro SOURCE -M /)
root_drive=$(lsblk -npro PKNAME "$root_mount")
root_partition=${root_mount: -1}

parted -a optimal $root_drive --script mkpart primary 8092 100%
#Parted doesn't support building exFat partitions so use sfdisk to change the type
sfdisk "${root_drive}" 3 --part-type 7
/usr/sbin/mkfs.exfat -L imgstore "${root_drive}p3"
mkdir -p /mnt/imgstore

sfdisk --no-reread --no-tell-kernel -fN"$root_partition" "$root_drive" <<< ',+'
partprobe $root_drive
resize2fs -p $root_mount

#Install USBODE and enable service
mkdir -p /opt/usbode
cp -R /boot/firmware/usbode/* /opt/usbode
cp /boot/firmware/usbode.service /lib/systemd/system
chmod 664 /lib/systemd/system/usbode.service
systemctl enable usbode.service

#Continue with "normal" Pi installation including script
source /usr/lib/raspberrypi-sys-mods/firstbootpost

#Add the following to cmdline.txt at the end
# init=/bin/bash -c "mount -t proc proc /proc; mount -t sysfs sys /sys; mount /boot; source /boot/usbode-boot-setup.sh"