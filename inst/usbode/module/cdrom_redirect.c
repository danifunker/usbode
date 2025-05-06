/**
 * cdrom_redirect.c - USB Gadget CDROM redirection module
 * 
 * This module creates a USB gadget that redirects SCSI commands for CDROM
 * operations to /dev/sr0, including support for CD Audio playback.
 * 
 * Copyright (C) 2025 danifunker
 * License: GPL v2
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/usb/composite.h>
#include <linux/configfs.h>
#include <linux/usb/gadget.h>
#include <linux/fs.h>
#include <linux/blkdev.h>
#include <linux/cdrom.h>
#include <linux/scatterlist.h>
#include <linux/device.h>
#include <linux/kthread.h>
#include <linux/workqueue.h>
#include <linux/delay.h>
#include <linux/uaccess.h>
#include <linux/usb/storage.h>
#include <linux/usb/ch9.h>
#include <scsi/scsi.h>

/* Define constants if not provided by headers */
#ifndef USB_SC_SCSI
#define USB_SC_SCSI 0x06
#endif

#ifndef USB_PR_BULK
#define USB_PR_BULK 0x50
#endif

#define DRIVER_NAME	"cdrom_redirect"
#define DRIVER_VERSION	"1.0.0"

/* Module parameters */
static char *cdrom_device = "/dev/sr0";
module_param(cdrom_device, charp, 0644);
MODULE_PARM_DESC(cdrom_device, "Path to the CDROM device (default: /dev/sr0)");

/* USB descriptor strings */
#define STRING_MANUFACTURER		1
#define STRING_PRODUCT			2
#define STRING_SERIAL			3
#define STRING_CONFIG			4
#define STRING_INTERFACE		5

/* SCSI command definitions */
#define SC_READ_TOC			0x43
#define SC_READ_CD			0xbe
#define SC_PLAY_AUDIO_10		0x45
#define SC_PLAY_AUDIO_MSF		0x47
#define SC_PAUSE_RESUME			0x4b
#define SC_READ_SUBCHANNEL		0x42
#define SC_MODE_SENSE_6			0x1a
#define SC_MODE_SENSE_10		0x5a
#define SC_TEST_UNIT_READY		0x00
#define SC_REQUEST_SENSE		0x03
#define SC_INQUIRY			0x12
#define SC_READ_FORMAT_CAPACITIES	0x23
#define SC_READ_CAPACITY		0x25

/* CD-ROM capability flags - using different values to avoid conflicts */
#define CDROM_CAPS_PLAY_AUDIO   0x01
#define CDROM_CAPS_READ_SUBCHAN 0x02
#define CDROM_CAPS_READ_CD      0x04

/* Module global state structure */
struct cdrom_redirect {
    struct usb_composite_dev *cdev;
    struct usb_gadget *gadget;
    struct usb_function func;
    struct usb_ep *bulk_in;
    struct usb_ep *bulk_out;
    struct file *cdrom_file;
    bool cdrom_opened;
    struct mutex lock;
    struct task_struct *kthread;
    int thread_exit;
    wait_queue_head_t thread_wq;
    struct work_struct work;
    struct workqueue_struct *wq;
    int cdrom_intf;
};

static struct cdrom_redirect *g_cdrom_redirect;

/* ConfigFS structures */
struct cdrom_redirect_opts {
    struct config_group group;
    struct usb_function_instance func_inst;
    char device_path[64];
};

static inline struct cdrom_redirect_opts *to_cdrom_redirect_opts(struct config_item *item)
{
    return container_of(to_config_group(item), struct cdrom_redirect_opts, group);
}

/* Function prototypes */
static struct usb_request *alloc_usb_request(struct usb_ep *ep, unsigned len);
static void free_usb_request(struct usb_ep *ep, struct usb_request *req);
static int cdrom_redirect_open_device(void);
static void cdrom_redirect_close_device(void);
static int cdrom_redirect_handle_scsi_cmd(unsigned char *cmd, unsigned char *buffer, 
                                         unsigned int buf_len, int *transfer_len);
static void cdrom_redirect_free_inst(struct usb_function_instance *fi);
static void cdrom_redirect_complete_in(struct usb_ep *ep, struct usb_request *req);

/* USB descriptors */
static struct usb_interface_descriptor cdrom_intf_desc = {
    .bLength = sizeof(cdrom_intf_desc),
    .bDescriptorType = USB_DT_INTERFACE,
    .bInterfaceNumber = 0,
    .bNumEndpoints = 2,
    .bInterfaceClass = USB_CLASS_MASS_STORAGE,
    .bInterfaceSubClass = USB_SC_SCSI,
    .bInterfaceProtocol = USB_PR_BULK,
    .iInterface = STRING_INTERFACE,
};

static struct usb_endpoint_descriptor cdrom_fs_bulk_in_desc = {
    .bLength = USB_DT_ENDPOINT_SIZE,
    .bDescriptorType = USB_DT_ENDPOINT,
    .bEndpointAddress = USB_DIR_IN,
    .bmAttributes = USB_ENDPOINT_XFER_BULK,
    .wMaxPacketSize = cpu_to_le16(64),
};

static struct usb_endpoint_descriptor cdrom_fs_bulk_out_desc = {
    .bLength = USB_DT_ENDPOINT_SIZE,
    .bDescriptorType = USB_DT_ENDPOINT,
    .bEndpointAddress = USB_DIR_OUT,
    .bmAttributes = USB_ENDPOINT_XFER_BULK,
    .wMaxPacketSize = cpu_to_le16(64),
};

static struct usb_descriptor_header *cdrom_fs_descs[] = {
    (struct usb_descriptor_header *) &cdrom_intf_desc,
    (struct usb_descriptor_header *) &cdrom_fs_bulk_in_desc,
    (struct usb_descriptor_header *) &cdrom_fs_bulk_out_desc,
    NULL,
};

static struct usb_endpoint_descriptor cdrom_hs_bulk_in_desc = {
    .bLength = USB_DT_ENDPOINT_SIZE,
    .bDescriptorType = USB_DT_ENDPOINT,
    .bEndpointAddress = USB_DIR_IN,
    .bmAttributes = USB_ENDPOINT_XFER_BULK,
    .wMaxPacketSize = cpu_to_le16(512),
};

static struct usb_endpoint_descriptor cdrom_hs_bulk_out_desc = {
    .bLength = USB_DT_ENDPOINT_SIZE,
    .bDescriptorType = USB_DT_ENDPOINT,
    .bEndpointAddress = USB_DIR_OUT,
    .bmAttributes = USB_ENDPOINT_XFER_BULK,
    .wMaxPacketSize = cpu_to_le16(512),
};

static struct usb_descriptor_header *cdrom_hs_descs[] = {
    (struct usb_descriptor_header *) &cdrom_intf_desc,
    (struct usb_descriptor_header *) &cdrom_hs_bulk_in_desc,
    (struct usb_descriptor_header *) &cdrom_hs_bulk_out_desc,
    NULL,
};

static struct usb_endpoint_descriptor cdrom_ss_bulk_in_desc = {
    .bLength = USB_DT_ENDPOINT_SIZE,
    .bDescriptorType = USB_DT_ENDPOINT,
    .bEndpointAddress = USB_DIR_IN,
    .bmAttributes = USB_ENDPOINT_XFER_BULK,
    .wMaxPacketSize = cpu_to_le16(1024),
};

static struct usb_endpoint_descriptor cdrom_ss_bulk_out_desc = {
    .bLength = USB_DT_ENDPOINT_SIZE,
    .bDescriptorType = USB_DT_ENDPOINT,
    .bEndpointAddress = USB_DIR_OUT,
    .bmAttributes = USB_ENDPOINT_XFER_BULK,
    .wMaxPacketSize = cpu_to_le16(1024),
};

static struct usb_ss_ep_comp_descriptor cdrom_ss_bulk_in_comp_desc = {
    .bLength = sizeof(cdrom_ss_bulk_in_comp_desc),
    .bDescriptorType = USB_DT_SS_ENDPOINT_COMP,
};

static struct usb_ss_ep_comp_descriptor cdrom_ss_bulk_out_comp_desc = {
    .bLength = sizeof(cdrom_ss_bulk_out_comp_desc),
    .bDescriptorType = USB_DT_SS_ENDPOINT_COMP,
};

static struct usb_descriptor_header *cdrom_ss_descs[] = {
    (struct usb_descriptor_header *) &cdrom_intf_desc,
    (struct usb_descriptor_header *) &cdrom_ss_bulk_in_desc,
    (struct usb_descriptor_header *) &cdrom_ss_bulk_in_comp_desc,
    (struct usb_descriptor_header *) &cdrom_ss_bulk_out_desc,
    (struct usb_descriptor_header *) &cdrom_ss_bulk_out_comp_desc,
    NULL,
};

/* USB strings */
static struct usb_string cdrom_strings[] = {
    [STRING_MANUFACTURER]	= { .s = "Linux Kernel" },
    [STRING_PRODUCT]		= { .s = "CDROM Redirector" },
    [STRING_SERIAL]		= { .s = "0123456789" },
    [STRING_CONFIG]		= { .s = "CDROM Configuration" },
    [STRING_INTERFACE]		= { .s = "CDROM Interface" },
    { }
};

static struct usb_gadget_strings cdrom_stringtab = {
    .language	= 0x0409,	/* en-us */
    .strings	= cdrom_strings,
};

static struct usb_gadget_strings *cdrom_strings_tab[] = {
    &cdrom_stringtab,
    NULL,
};

/* Helper functions */
static struct usb_request *alloc_usb_request(struct usb_ep *ep, unsigned len)
{
    struct usb_request *req = usb_ep_alloc_request(ep, GFP_KERNEL);
    
    if (req) {
        req->length = len;
        req->buf = kmalloc(len, GFP_KERNEL);
        if (!req->buf) {
            usb_ep_free_request(ep, req);
            req = NULL;
        }
    }
    
    return req;
}

static void free_usb_request(struct usb_ep *ep, struct usb_request *req)
{
    if (req) {
        kfree(req->buf);
        usb_ep_free_request(ep, req);
    }
}

/* CDROM device handling */
static int cdrom_redirect_open_device(void)
{
    mutex_lock(&g_cdrom_redirect->lock);
    
    if (g_cdrom_redirect->cdrom_opened) {
        mutex_unlock(&g_cdrom_redirect->lock);
        return 0;
    }
    
    g_cdrom_redirect->cdrom_file = filp_open(cdrom_device, O_RDONLY | O_NONBLOCK, 0);
    
    if (IS_ERR(g_cdrom_redirect->cdrom_file)) {
        int err = PTR_ERR(g_cdrom_redirect->cdrom_file);
        g_cdrom_redirect->cdrom_file = NULL;
        mutex_unlock(&g_cdrom_redirect->lock);
        pr_err("cdrom_redirect: Failed to open device %s: %d\n", cdrom_device, err);
        return err;
    }
    
    g_cdrom_redirect->cdrom_opened = true;
    mutex_unlock(&g_cdrom_redirect->lock);
    
    pr_info("cdrom_redirect: Opened device %s\n", cdrom_device);
    return 0;
}

static void cdrom_redirect_close_device(void)
{
    mutex_lock(&g_cdrom_redirect->lock);
    
    if (!g_cdrom_redirect->cdrom_opened) {
        mutex_unlock(&g_cdrom_redirect->lock);
        return;
    }
    
    if (g_cdrom_redirect->cdrom_file) {
        filp_close(g_cdrom_redirect->cdrom_file, NULL);
        g_cdrom_redirect->cdrom_file = NULL;
    }
    
    g_cdrom_redirect->cdrom_opened = false;
    mutex_unlock(&g_cdrom_redirect->lock);
    
    pr_info("cdrom_redirect: Closed device %s\n", cdrom_device);
}

/* SCSI command handling */
static int cdrom_redirect_handle_scsi_cmd(unsigned char *cmd, unsigned char *buffer, 
                                         unsigned int buf_len, int *transfer_len)
{
    int ret = 0;
    *transfer_len = 0;
    
    if (!g_cdrom_redirect->cdrom_opened) {
        pr_err("cdrom_redirect: CDROM device not opened\n");
        return -ENODEV;
    }
    
    /* Process SCSI commands */
    switch (cmd[0]) {
    case SC_TEST_UNIT_READY:
        pr_debug("cdrom_redirect: TEST_UNIT_READY\n");
        break;
        
    case SC_INQUIRY:
        {
            unsigned char inquiry_response[36] = {
                0x05,   /* CD-ROM */
                0x80,   /* Removable */
                0x04,   /* SPC-2 compliance */
                0x02,
                0x20,   /* Additional length */
                0x00,
                0x00,
                0x00,
                'L', 'I', 'N', 'U', 'X', ' ', ' ', ' ',    /* Vendor */
                'C', 'D', '-', 'R', 'O', 'M', ' ', ' ',    /* Product */
                'R', 'e', 'd', 'i', 'r', 'e', 'c', 't',
                '1', '.', '0', '0'                         /* Revision */
            };
            
            memcpy(buffer, inquiry_response, min_t(unsigned int, sizeof(inquiry_response), buf_len));
            *transfer_len = min_t(unsigned int, sizeof(inquiry_response), buf_len);
        }
        break;
        
    case SC_READ_CAPACITY:
        {
            unsigned int sectors = 0;
            unsigned char capacity_response[8];
            int result;
            
            result = vfs_ioctl(g_cdrom_redirect->cdrom_file, BLKGETSIZE, (unsigned long)&sectors);
            
            if (result < 0) {
                pr_err("cdrom_redirect: Failed to get CDROM capacity: %d\n", result);
                return result;
            }
            
            /* Format capacity response (sectors-1, sector size=2048) */
            capacity_response[0] = (sectors - 1) >> 24;
            capacity_response[1] = (sectors - 1) >> 16;
            capacity_response[2] = (sectors - 1) >> 8;
            capacity_response[3] = (sectors - 1);
            capacity_response[4] = 0;
            capacity_response[5] = 0;
            capacity_response[6] = 8;  /* 2048 bytes per sector */
            capacity_response[7] = 0;
            
            memcpy(buffer, capacity_response, min_t(unsigned int, sizeof(capacity_response), buf_len));
            *transfer_len = min_t(unsigned int, sizeof(capacity_response), buf_len);
        }
        break;
        
    case SC_READ_TOC:
        {
            struct cdrom_tochdr toc_header;
            struct cdrom_tocentry toc_entry;
            unsigned char toc_response[12];
            int result;
            
            result = vfs_ioctl(g_cdrom_redirect->cdrom_file, CDROMREADTOCHDR, (unsigned long)&toc_header);
            
            if (result < 0) {
                pr_err("cdrom_redirect: Failed to read TOC header: %d\n", result);
                return result;
            }
            
            toc_response[0] = 0;      /* TOC Data Length MSB */
            toc_response[1] = 10;     /* TOC Data Length LSB */
            toc_response[2] = 1;      /* First Track Number */
            toc_response[3] = toc_header.cdth_trk1; /* Last Track Number */
            
            /* Get first track info */
            toc_entry.cdte_track = toc_header.cdth_trk0;
            toc_entry.cdte_format = CDROM_LBA;
            
            result = vfs_ioctl(g_cdrom_redirect->cdrom_file, CDROMREADTOCENTRY, (unsigned long)&toc_entry);
            
            if (result < 0) {
                pr_err("cdrom_redirect: Failed to read TOC entry: %d\n", result);
                return result;
            }
            
            /* First track descriptor */
            toc_response[4] = 0;      /* Reserved */
            toc_response[5] = 0x14;   /* ADR/Control (Digital data track, copyable) */
            toc_response[6] = toc_header.cdth_trk0; /* Track number */
            toc_response[7] = 0;      /* Reserved */
            
            /* Track start address (LBA format) */
            toc_response[8] = (toc_entry.cdte_addr.lba >> 24) & 0xFF;
            toc_response[9] = (toc_entry.cdte_addr.lba >> 16) & 0xFF;
            toc_response[10] = (toc_entry.cdte_addr.lba >> 8) & 0xFF;
            toc_response[11] = toc_entry.cdte_addr.lba & 0xFF;
            
            memcpy(buffer, toc_response, min_t(unsigned int, sizeof(toc_response), buf_len));
            *transfer_len = min_t(unsigned int, sizeof(toc_response), buf_len);
        }
        break;
        
    case SC_PLAY_AUDIO_10:
        {
            struct cdrom_msf play_audio;
            int result;
            
            /* Extract starting sector and play length from command */
            unsigned int start_sector = (cmd[2] << 24) | (cmd[3] << 16) | (cmd[4] << 8) | cmd[5];
            unsigned int num_sectors = (cmd[7] << 8) | cmd[8];
            
            play_audio.cdmsf_min0 = (start_sector / 75) / 60;
            play_audio.cdmsf_sec0 = (start_sector / 75) % 60;
            play_audio.cdmsf_frame0 = start_sector % 75;
            
            unsigned int end_sector = start_sector + num_sectors - 1;
            play_audio.cdmsf_min1 = (end_sector / 75) / 60;
            play_audio.cdmsf_sec1 = (end_sector / 75) % 60;
            play_audio.cdmsf_frame1 = end_sector % 75;
            
            result = vfs_ioctl(g_cdrom_redirect->cdrom_file, CDROMPLAYMSF, (unsigned long)&play_audio);
            
            if (result < 0) {
                pr_err("cdrom_redirect: Failed to play audio: %d\n", result);
                return result;
            }
        }
        break;
        
    case SC_PAUSE_RESUME:
        {
            int result;
            int resume = cmd[8] & 0x01;
            
            if (resume)
                result = vfs_ioctl(g_cdrom_redirect->cdrom_file, CDROMRESUME, 0);
            else
                result = vfs_ioctl(g_cdrom_redirect->cdrom_file, CDROMPAUSE, 0);
            
            if (result < 0) {
                pr_err("cdrom_redirect: Failed to pause/resume: %d\n", result);
                return result;
            }
        }
        break;
        
    case SC_READ_SUBCHANNEL:
        {
            struct cdrom_subchnl subchnl;
            unsigned char subchannel_response[16];
            int result;
            
            subchnl.cdsc_format = CDROM_MSF;
            
            result = vfs_ioctl(g_cdrom_redirect->cdrom_file, CDROMSUBCHNL, (unsigned long)&subchnl);
            
            if (result < 0) {
                pr_err("cdrom_redirect: Failed to read subchannel: %d\n", result);
                return result;
            }
            
            memset(subchannel_response, 0, sizeof(subchannel_response));
            
            subchannel_response[0] = 0;  /* Reserved */
            subchannel_response[1] = 0;  /* Audio Status */
            
            switch (subchnl.cdsc_audiostatus) {
            case CDROM_AUDIO_PLAY:
                subchannel_response[1] = 0x11;  /* Audio play operation in progress */
                break;
            case CDROM_AUDIO_PAUSED:
                subchannel_response[1] = 0x12;  /* Audio play operation paused */
                break;
            case CDROM_AUDIO_COMPLETED:
                subchannel_response[1] = 0x13;  /* Audio play operation completed successfully */
                break;
            case CDROM_AUDIO_ERROR:
                subchannel_response[1] = 0x14;  /* Audio play operation stopped due to error */
                break;
            case CDROM_AUDIO_NO_STATUS:
            default:
                subchannel_response[1] = 0x15;  /* No current audio status to return */
                break;
            }
            
            subchannel_response[2] = 0;  /* Data Length MSB */
            subchannel_response[3] = 12; /* Data Length LSB */
            subchannel_response[4] = 0x01; /* Format Code (Q) */
            
            /* Position data */
            subchannel_response[5] = (subchnl.cdsc_ctrl << 4) | subchnl.cdsc_adr;
            subchannel_response[6] = subchnl.cdsc_trk;
            subchannel_response[7] = subchnl.cdsc_ind;
            
            /* Absolute CD address (MSF) */
            subchannel_response[8] = 0;
            subchannel_response[9] = subchnl.cdsc_absaddr.msf.minute;
            subchannel_response[10] = subchnl.cdsc_absaddr.msf.second;
            subchannel_response[11] = subchnl.cdsc_absaddr.msf.frame;
            
            /* Relative Track address (MSF) */
            subchannel_response[12] = 0;
            subchannel_response[13] = subchnl.cdsc_reladdr.msf.minute;
            subchannel_response[14] = subchnl.cdsc_reladdr.msf.second;
            subchannel_response[15] = subchnl.cdsc_reladdr.msf.frame;
            
            memcpy(buffer, subchannel_response, min_t(unsigned int, sizeof(subchannel_response), buf_len));
            *transfer_len = min_t(unsigned int, sizeof(subchannel_response), buf_len);
        }
        break;
        
    case SC_MODE_SENSE_6:
    case SC_MODE_SENSE_10:
        {
            unsigned char mode_sense_response[24];
            memset(mode_sense_response, 0, sizeof(mode_sense_response));
            
            if (cmd[0] == SC_MODE_SENSE_6) {
                mode_sense_response[0] = 22;  /* Mode data length */
                mode_sense_response[1] = 0x05;  /* Medium type (CDROM) */
                mode_sense_response[2] = 0x80;  /* Device-specific parameter (write-protected) */
                mode_sense_response[3] = 0x08;  /* Block descriptor length */
            } else {
                mode_sense_response[0] = 0;     /* Mode data length MSB */
                mode_sense_response[1] = 22;    /* Mode data length LSB */
                mode_sense_response[2] = 0x05;  /* Medium type (CDROM) */
                mode_sense_response[3] = 0x80;  /* Device-specific parameter (write-protected) */
                mode_sense_response[6] = 0;     /* Block descriptor length MSB */
                mode_sense_response[7] = 0x08;  /* Block descriptor length LSB */
            }
            
            /* CD-ROM capabilities page */
            unsigned char *page;
            if (cmd[0] == SC_MODE_SENSE_6)
                page = &mode_sense_response[8];
            else
                page = &mode_sense_response[8];
            
            page[0] = 0x2A;  /* CD-ROM capabilities page code */
            page[1] = 16;     /* Page length */
            page[2] = CDROM_CAPS_PLAY_AUDIO | CDROM_CAPS_READ_SUBCHAN | CDROM_CAPS_READ_CD;  /* CD-ROM capabilities */
            page[3] = 0x03;   /* Can read CD-DA/CD-ROM */
            page[4] = 0x00;   /* No volume control */
            page[5] = 0x00;
            page[6] = 0x00;
            page[7] = 0x00;
            
            /* Maximum speed = 16X (16 * 176.4KB/s = 2822.4KB/s) */
            page[8] = 0x0B;
            page[9] = 0x06;   /* 2822 KB/s */
            
            /* Current speed = 16X */
            page[10] = 0x0B;
            page[11] = 0x06;  /* 2822 KB/s */
            
            memcpy(buffer, mode_sense_response, min_t(unsigned int, sizeof(mode_sense_response), buf_len));
            *transfer_len = min_t(unsigned int, sizeof(mode_sense_response), buf_len);
        }
        break;
    
    case SC_READ_CD:
        {
            int result;
            unsigned int sector = ((cmd[2] << 24) | (cmd[3] << 16) | (cmd[4] << 8) | cmd[5]);
            unsigned int count = ((cmd[6] << 16) | (cmd[7] << 8) | cmd[8]);
            loff_t pos = sector * 2048;  /* Assuming 2048 bytes per sector */
            
            result = vfs_llseek(g_cdrom_redirect->cdrom_file, pos, SEEK_SET);
            if (result < 0) {
                pr_err("cdrom_redirect: Failed to seek to sector %u: %d\n", sector, result);
                return result;
            }
            
            result = kernel_read(g_cdrom_redirect->cdrom_file, buffer, count * 2048, &pos);
            
            if (result < 0) {
                pr_err("cdrom_redirect: Failed to read sectors: %d\n", result);
                return result;
            }
            
            *transfer_len = result;
        }
        break;
        
    case SC_REQUEST_SENSE:
        {
            unsigned char sense_data[18] = {
                0x70,   /* Response Code */
                0,      /* Sense Key */
                0,      /* Additional Sense Code */
                0,      /* Additional Sense Code Qualifier */
                0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
            };
            
            memcpy(buffer, sense_data, min_t(unsigned int, sizeof(sense_data), buf_len));
            *transfer_len = min_t(unsigned int, sizeof(sense_data), buf_len);
        }
        break;
        
    case SC_READ_FORMAT_CAPACITIES:
        {
            unsigned char format_capacity_response[12] = {
                0, 0, 0, 8,  /* Capacity List Header (length = 8) */
                0, 0, 0, 0,  /* Number of blocks (to be filled) */
                0x02,        /* Descriptor type (formatted media) */
                0, 8, 0      /* Block length (2048) */
            };
            
            unsigned int sectors = 0;
            int result;
            
            result = vfs_ioctl(g_cdrom_redirect->cdrom_file, BLKGETSIZE, (unsigned long)&sectors);
            
            if (result < 0) {
                pr_err("cdrom_redirect: Failed to get CDROM capacity: %d\n", result);
                return result;
            }
            
            format_capacity_response[4] = (sectors >> 24);
            format_capacity_response[5] = (sectors >> 16);
            format_capacity_response[6] = (sectors >> 8);
            format_capacity_response[7] = sectors;
            
            memcpy(buffer, format_capacity_response, min_t(unsigned int, sizeof(format_capacity_response), buf_len));
            *transfer_len = min_t(unsigned int, sizeof(format_capacity_response), buf_len);
        }
        break;
        
    default:
        pr_warn("cdrom_redirect: Unhandled SCSI command: 0x%02x\n", cmd[0]);
        return -EINVAL;
    }
    
    return ret;
}

/* USB function callbacks */
static void cdrom_redirect_complete_out(struct usb_ep *ep, struct usb_request *req)
{
    struct cdrom_redirect *cdrom = ep->driver_data;
    
    if (req->status != 0) {
        pr_err("cdrom_redirect: Bulk OUT transfer error: %d\n", req->status);
        return;
    }
    
    /* Process SCSI command */
    unsigned char *cmd = req->buf;
    unsigned char response[512];
    int transfer_len = 0;
    int result;
    
    result = cdrom_redirect_handle_scsi_cmd(cmd, response, sizeof(response), &transfer_len);
    
    if (result < 0) {
        pr_err("cdrom_redirect: Failed to handle SCSI command: %d\n", result);
        /* Send error response */
        memset(response, 0, sizeof(response));
        transfer_len = 0;
    }
    
    /* Send response through IN endpoint */
    struct usb_request *in_req = alloc_usb_request(cdrom->bulk_in, transfer_len);
    if (!in_req) {
        pr_err("cdrom_redirect: Failed to allocate IN request\n");
        return;
    }
    
    memcpy(in_req->buf, response, transfer_len);
    in_req->length = transfer_len;
    in_req->complete = cdrom_redirect_complete_in;
    
    result = usb_ep_queue(cdrom->bulk_in, in_req, GFP_ATOMIC);
    if (result < 0) {
        pr_err("cdrom_redirect: Failed to queue IN request: %d\n", result);
        free_usb_request(cdrom->bulk_in, in_req);
    }
    
    /* Re-submit the OUT request for more commands */
    result = usb_ep_queue(cdrom->bulk_out, req, GFP_ATOMIC);
    if (result < 0) {
        pr_err("cdrom_redirect: Failed to requeue OUT request: %d\n", result);
        free_usb_request(cdrom->bulk_out, req);
    }
}

static void cdrom_redirect_complete_in(struct usb_ep *ep, struct usb_request *req)
{
    if (req->status != 0) {
        pr_err("cdrom_redirect: Bulk IN transfer error: %d\n", req->status);
    }
    
    free_usb_request(ep, req);
}

/* USB function callbacks */
static int cdrom_redirect_bind(struct usb_configuration *c, struct usb_function *f)
{
    struct cdrom_redirect *cdrom = container_of(f, struct cdrom_redirect, func);
    struct usb_composite_dev *cdev = c->cdev;
    int ret;
    
    /* Allocate interface */
    cdrom->cdrom_intf = usb_interface_id(c, f);
    if (cdrom->cdrom_intf < 0)
        return cdrom->cdrom_intf;
        
    cdrom_intf_desc.bInterfaceNumber = cdrom->cdrom_intf;
    
    /* Allocate endpoints */
    cdrom->bulk_in = usb_ep_autoconfig(cdev->gadget, &cdrom_fs_bulk_in_desc);
    if (!cdrom->bulk_in)
        goto fail;
        
    cdrom->bulk_out = usb_ep_autoconfig(cdev->gadget, &cdrom_fs_bulk_out_desc);
    if (!cdrom->bulk_out)
        goto fail;
        
    cdrom_hs_bulk_in_desc.bEndpointAddress = cdrom_fs_bulk_in_desc.bEndpointAddress;
    cdrom_hs_bulk_out_desc.bEndpointAddress = cdrom_fs_bulk_out_desc.bEndpointAddress;
    
    cdrom_ss_bulk_in_desc.bEndpointAddress = cdrom_fs_bulk_in_desc.bEndpointAddress;
    cdrom_ss_bulk_out_desc.bEndpointAddress = cdrom_fs_bulk_out_desc.bEndpointAddress;
    
    ret = usb_assign_descriptors(f, cdrom_fs_descs, cdrom_hs_descs, cdrom_ss_descs, NULL);
    if (ret)
        goto fail;
        
    /* Save our context in the endpoints */
    cdrom->bulk_in->driver_data = cdrom;
    cdrom->bulk_out->driver_data = cdrom;
    
    return 0;
    
fail:
    usb_free_all_descriptors(f);
    return -ENODEV;
}

static void cdrom_redirect_unbind(struct usb_configuration *c, struct usb_function *f)
{
    usb_free_all_descriptors(f);
}

static int cdrom_redirect_set_alt(struct usb_function *f, unsigned intf, unsigned alt)
{
    struct cdrom_redirect *cdrom = container_of(f, struct cdrom_redirect, func);
    int ret;
    
    /* Close previous endpoints if any */
    if (cdrom->bulk_in->driver_data) {
        usb_ep_disable(cdrom->bulk_in);
        cdrom->bulk_in->driver_data = NULL;
    }
    
    if (cdrom->bulk_out->driver_data) {
        usb_ep_disable(cdrom->bulk_out);
        cdrom->bulk_out->driver_data = NULL;
    }
    
    /* Enable the endpoints */
    ret = config_ep_by_speed(f->config->cdev->gadget, f, cdrom->bulk_in);
    if (ret)
        return ret;
        
    ret = usb_ep_enable(cdrom->bulk_in);
    if (ret)
        return ret;
        
    ret = config_ep_by_speed(f->config->cdev->gadget, f, cdrom->bulk_out);
    if (ret)
        goto fail_out_ep;
        
    ret = usb_ep_enable(cdrom->bulk_out);
    if (ret)
        goto fail_out_ep;
        
    cdrom->bulk_in->driver_data = cdrom;
    cdrom->bulk_out->driver_data = cdrom;
    
    /* Start receiving commands */
    struct usb_request *req = alloc_usb_request(cdrom->bulk_out, 512);
    if (!req)
        goto fail_alloc;
        
    req->complete = cdrom_redirect_complete_out;
    ret = usb_ep_queue(cdrom->bulk_out, req, GFP_ATOMIC);
    if (ret)
        goto fail_queue;
        
    /* Open the CDROM device */
    ret = cdrom_redirect_open_device();
    if (ret)
        goto fail_open;
        
    return 0;
    
fail_open:
    usb_ep_dequeue(cdrom->bulk_out, req);
fail_queue:
    free_usb_request(cdrom->bulk_out, req);
fail_alloc:
    usb_ep_disable(cdrom->bulk_out);
    cdrom->bulk_out->driver_data = NULL;
fail_out_ep:
    usb_ep_disable(cdrom->bulk_in);
    cdrom->bulk_in->driver_data = NULL;
    return ret;
}

static void cdrom_redirect_disable(struct usb_function *f)
{
    struct cdrom_redirect *cdrom = container_of(f, struct cdrom_redirect, func);
    
    /* Disable endpoints */
    if (cdrom->bulk_in->driver_data) {
        usb_ep_disable(cdrom->bulk_in);
        cdrom->bulk_in->driver_data = NULL;
    }
    
    if (cdrom->bulk_out->driver_data) {
        usb_ep_disable(cdrom->bulk_out);
        cdrom->bulk_out->driver_data = NULL;
    }
    
    /* Close the CDROM device */
    cdrom_redirect_close_device();
}

static struct usb_function *cdrom_redirect_alloc_func(struct usb_function_instance *fi)
{
    if (g_cdrom_redirect)
        return &g_cdrom_redirect->func;
        
    return ERR_PTR(-ENODEV);
}

/* ConfigFS attribute handling */
static ssize_t cdrom_redirect_device_path_show(struct config_item *item, char *page)
{
    struct cdrom_redirect_opts *opts = to_cdrom_redirect_opts(item);
    return sprintf(page, "%s\n", opts->device_path);
}

static ssize_t cdrom_redirect_device_path_store(struct config_item *item,
                                             const char *page, size_t len)
{
    struct cdrom_redirect_opts *opts = to_cdrom_redirect_opts(item);
    size_t copy_len = min_t(size_t, len, sizeof(opts->device_path) - 1);
    
    if (copy_len) {
        memcpy(opts->device_path, page, copy_len);
        opts->device_path[copy_len] = 0;
        if (opts->device_path[copy_len - 1] == '\n')
            opts->device_path[copy_len - 1] = 0;
            
        /* Update the global variable */
        cdrom_device = opts->device_path;
        
        /* If device is already opened, reopen it with new path */
        if (g_cdrom_redirect && g_cdrom_redirect->cdrom_opened) {
            cdrom_redirect_close_device();
            cdrom_redirect_open_device();
        }
    }
    
    return len;
}

CONFIGFS_ATTR(cdrom_redirect_, device_path);

static struct configfs_attribute *cdrom_redirect_attrs[] = {
    &cdrom_redirect_attr_device_path,
    NULL,
};

static struct config_item_type cdrom_redirect_func_type = {
    .ct_item_ops = NULL,
    .ct_attrs    = cdrom_redirect_attrs,
    .ct_owner    = THIS_MODULE,
};

static void cdrom_redirect_free_instance(struct usb_function_instance *fi)
{
    struct cdrom_redirect_opts *opts = container_of(fi, struct cdrom_redirect_opts, func_inst);
    kfree(opts);
}

static struct usb_function_instance *cdrom_redirect_alloc_instance(void)
{
    struct cdrom_redirect_opts *opts;
    
    opts = kzalloc(sizeof(*opts), GFP_KERNEL);
    if (!opts)
        return ERR_PTR(-ENOMEM);
        
    config_group_init_type_name(&opts->group, "cdrom_redirect", &cdrom_redirect_func_type);
    opts->func_inst.free_func_inst = cdrom_redirect_free_instance;
    
    /* Set initial configuration values */
    strncpy(opts->device_path, cdrom_device, sizeof(opts->device_path) - 1);
    
    return &opts->func_inst;
}

static struct usb_function_driver cdrom_redirect_driver = {
    .name = "cdrom_redirect",
    .alloc_inst = cdrom_redirect_alloc_instance,
    .alloc_func = cdrom_redirect_alloc_func,
};

/* Worker thread to handle long operations */
static void cdrom_redirect_worker(struct work_struct *work)
{
    struct cdrom_redirect *cdrom = container_of(work, struct cdrom_redirect, work);
    
    /* Worker thread can perform operations that might sleep */
    pr_debug("cdrom_redirect: Worker thread running\n");
    
    /* Example: Periodic check for media change */
    if (cdrom->cdrom_opened) {
        int status;
        
        status = vfs_ioctl(cdrom->cdrom_file, CDROM_MEDIA_CHANGED, 0);
        
        if (status > 0) {
            pr_info("cdrom_redirect: Media change detected\n");
            /* Handle media change if needed */
        }
    }
}

/* Kernel thread function */
static int cdrom_redirect_thread(void *data)
{
    struct cdrom_redirect *cdrom = data;
    
    pr_info("cdrom_redirect: Thread started\n");
    
    while (!kthread_should_stop() && !cdrom->thread_exit) {
        /* Schedule work periodically */
        queue_work(cdrom->wq, &cdrom->work);
        
        /* Sleep for 5 seconds */
        msleep_interruptible(5000);
    }
    
    pr_info("cdrom_redirect: Thread exiting\n");
    return 0;
}

/* Module initialization and cleanup */
static int __init cdrom_redirect_init(void)
{
    int ret;
    
    /* Allocate the global context */
    g_cdrom_redirect = kzalloc(sizeof(*g_cdrom_redirect), GFP_KERNEL);
    if (!g_cdrom_redirect)
        return -ENOMEM;
        
    /* Initialize the context */
    mutex_init(&g_cdrom_redirect->lock);
    g_cdrom_redirect->cdrom_opened = false;
    g_cdrom_redirect->cdrom_file = NULL;
    g_cdrom_redirect->thread_exit = 0;
    init_waitqueue_head(&g_cdrom_redirect->thread_wq);
    INIT_WORK(&g_cdrom_redirect->work, cdrom_redirect_worker);
    
    /* Create workqueue */
    g_cdrom_redirect->wq = create_singlethread_workqueue("cdrom_redirect_wq");
    if (!g_cdrom_redirect->wq) {
        ret = -ENOMEM;
        goto fail_wq;
    }
    
    /* Initialize USB function */
    g_cdrom_redirect->func.name = "cdrom_redirect";
    g_cdrom_redirect->func.bind = cdrom_redirect_bind;
    g_cdrom_redirect->func.unbind = cdrom_redirect_unbind;
    g_cdrom_redirect->func.set_alt = cdrom_redirect_set_alt;
    g_cdrom_redirect->func.disable = cdrom_redirect_disable;
    g_cdrom_redirect->func.strings = cdrom_strings_tab;
    
    /* Start kernel thread */
    g_cdrom_redirect->kthread = kthread_run(cdrom_redirect_thread, g_cdrom_redirect,
                                         "cdrom_redirect");
    if (IS_ERR(g_cdrom_redirect->kthread)) {
        ret = PTR_ERR(g_cdrom_redirect->kthread);
        goto fail_thread;
    }
    
    /* Register USB function driver */
    ret = usb_function_register(&cdrom_redirect_driver);
    if (ret)
        goto fail_register;
        
    pr_info("cdrom_redirect: Module loaded\n");
    return 0;
    
fail_register:
    kthread_stop(g_cdrom_redirect->kthread);
fail_thread:
    destroy_workqueue(g_cdrom_redirect->wq);
fail_wq:
    kfree(g_cdrom_redirect);
    g_cdrom_redirect = NULL;
    return ret;
}

static void __exit cdrom_redirect_exit(void)
{
    /* Unregister USB function */
    usb_function_unregister(&cdrom_redirect_driver);
    
    /* Stop kernel thread */
    if (g_cdrom_redirect && g_cdrom_redirect->kthread) {
        g_cdrom_redirect->thread_exit = 1;
        kthread_stop(g_cdrom_redirect->kthread);
    }
    
    /* Close CDROM device if open */
    if (g_cdrom_redirect && g_cdrom_redirect->cdrom_opened)
        cdrom_redirect_close_device();
        
    /* Clean up workqueue */
    if (g_cdrom_redirect && g_cdrom_redirect->wq)
        destroy_workqueue(g_cdrom_redirect->wq);
        
    /* Free global context */
    kfree(g_cdrom_redirect);
    g_cdrom_redirect = NULL;
    
    pr_info("cdrom_redirect: Module unloaded\n");
}

module_init(cdrom_redirect_init);
module_exit(cdrom_redirect_exit);

MODULE_LICENSE("GPL v2");
MODULE_AUTHOR("danifunker");
MODULE_DESCRIPTION("Linux kernel module that redirects CDROM SCSI commands to /dev/sr0");
MODULE_VERSION(DRIVER_VERSION);
