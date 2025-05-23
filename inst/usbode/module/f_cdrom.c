
#include <linux/module.h>
#include <linux/usb/composite.h>
#include <linux/fs.h>
#include <linux/uaccess.h>
#include <linux/file.h>
#include <linux/slab.h>
#include <scsi/sg.h>

#define FUNCTION_NAME "cdrom"

MODULE_LICENSE("GPL");
MODULE_AUTHOR("ChatGPT");
MODULE_DESCRIPTION("USB Gadget CD-ROM passthrough with ConfigFS");

struct f_cdrom {
    struct usb_function function;
    struct file *cdrom_file;
    char cdrom_path[256];
};

struct f_cdrom_opts {
    struct usb_function_instance func_inst;
};

static inline struct f_cdrom *func_to_cdrom(struct usb_function *f)
{
    return container_of(f, struct f_cdrom, function);
}

static void cdrom_disable(struct usb_function *f)
{
    pr_info("f_cdrom: disabled\n");
}

static int cdrom_set_alt(struct usb_function *f,
                         unsigned intf, unsigned alt)
{
    pr_info("f_cdrom: set_alt called\n");
    return 0;
}

static int cdrom_bind(struct usb_configuration *c, struct usb_function *f)
{
    pr_info("f_cdrom: bound to configuration\n");
    return 0;
}

static void cdrom_unbind(struct usb_configuration *c, struct usb_function *f)
{
    struct f_cdrom *cd = func_to_cdrom(f);
    pr_info("f_cdrom: unbound\n");
    if (cd->cdrom_file && !IS_ERR(cd->cdrom_file))
        filp_close(cd->cdrom_file, NULL);
}

static void cdrom_free_inst(struct usb_function_instance *fi)
{
    struct f_cdrom_opts *opts = container_of(fi, struct f_cdrom_opts, func_inst);
    kfree(opts);
}

static struct usb_function_instance *cdrom_alloc_inst(void)
{
    struct f_cdrom_opts *opts;

    opts = kzalloc(sizeof(*opts), GFP_KERNEL);
    if (!opts)
        return ERR_PTR(-ENOMEM);

    opts->func_inst.free_func_inst = cdrom_free_inst;
    return &opts->func_inst;
}

DECLARE_USB_FUNCTION_INIT(cdrom, cdrom_alloc_inst, NULL);
