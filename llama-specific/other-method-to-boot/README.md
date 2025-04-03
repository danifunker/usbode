# Other simpler method of booting the Windows 98 Disc
I wish I knew about this before I went down the isolinux rabbit hole! It turns out Panasonic created a file `RAMFD.SYS` and when paired with the `USBASPI1.sys` with a /r switch, it allows the USB ASPI scanning to continue working.

This is the new method I am using now for the Windows 98 SE CD booting.

Here are the changes to the config.sys files I made:

```
device=ramfd.sys
DEVICE=a:\usbaspi1.sys /V /E /r
```

For each of the sections in the config.sys where I'm loading usbaspi.sys
