# Makefile for cdrom_redirect kernel module

ifneq ($(KERNELRELEASE),)
# kbuild part of Makefile
obj-m := cdrom_redirect.o

else
# normal Makefile
KDIR ?= /lib/modules/$(shell uname -r)/build
PWD := $(shell pwd)

all:
	$(MAKE) -C $(KDIR) M=$(PWD) modules

clean:
	$(MAKE) -C $(KDIR) M=$(PWD) clean

install: all
	$(MAKE) -C $(KDIR) M=$(PWD) modules_install
	depmod -a

uninstall:
	rm -f /lib/modules/$(shell uname -r)/extra/cdrom_redirect.ko
	depmod -a

endif
