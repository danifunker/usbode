# Llama-Specific Patched Windows 98 SE ISO (ENG) for 
To use this patch:
1. Locate and download the file `EN_WIN98SE_115_OEM_WPLUS.ISO` MD5SUM: `0ac28bfbb29df0b788482388f7d5b11d` sha1: `2b68161b1fb2d905a6c05c82087fa1c20b47a8fd` CRC32: `0fff0609`
2. Download the latest DeltaPatcher for your platform from https://github.com/marco-calautti/DeltaPatcher/releases/
3. Apply the patch to the file dowwnloaded in step 1. 
4. Copy the patched file to the USBODE into `/mnt/imgstore`
5. Use the USBODE interface to select the patched file
6. Boot ITXLlama with USBODE connected, wait about 30 seconds in the BIOS Setup, then restart with CTRL+ALT+DEL and press ESC and select the USB CDROM
7. Follow the on-screen instructions to install Windows 98.



## How this patch was created:
1. Created isolinux folder & files (see attached) in `/isolinux`
2. Added the Windows 98 drivers from the ITX-Llama repo, changed filenames so they are 8.3. Drivers are placed in to `/drivers/itxllama` folder
3. Edited the Windws 98 Boot image file, added `usbaspi1.sys` and `usbcd.sys` to the root and changed `config.sys` and `autoexec.bat` (see included files) and placed the modified `.img` file into `/isolinux`
4. I used `UltraISO` for Windows to update a new ISO.
    a. Load Original ISO file
    b. Add files in steps 1-3 into respective folders
    c. Used boot-info.bin as the Boot File Info for `UltraISO`
    d. Enabled `Generate Bootinfotable`
    e. Saved the ISO as a new file
5. Use DeltaPatcher to create the patch between the original file `EN_WIN98SE_115_OEM_WPLUS.ISO` MD5SUM: `0ac28bfbb29df0b788482388f7d5b11d` sha1: `2b68161b1fb2d905a6c05c82087fa1c20b47a8fd` CRC32: `0fff0609` and the newly patched ISO. 

