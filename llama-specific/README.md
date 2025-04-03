# Why is this patch required?

Upon initialization process of the usbaspi1.sys, the virtualized boot floppy image as part of the Win98 ISO is lost. 

This patch resolves the issue by using isolinux and reading the virtual floppy image into memory first, prior to booting. 

This is not needed if using the built-in Windows 98 SE boot disk as part of the bios, however this does make the process a little more seemless, and doesn't require that VFD to be loaded.