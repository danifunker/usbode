# -*- coding:utf-8 -*-
import SH1106
import time
import config
import traceback

import time
import subprocess

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont


from gpiozero import *


# 240x240 display with hardware SPI:
disp = SH1106.SH1106()
disp.Init()

# Clear display.
disp.clear()
# time.sleep(1)
     
#init GPIO
# for P4:
# sudo vi /boot/config.txt
# gpio=6,19,5,26,13,21,20,16=pu

# Create blank image for drawing.
# Make sure to create image with mode '1' for 1-bit color.
image = Image.new('1', (disp.width, disp.height), "WHITE")

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

# UP = Button(6)

# print("The button was pressed!",UP.value)

try:
    while True:
        # with canvas(device) as draw:
        if disp.RPI.digital_read(disp.RPI.GPIO_KEY_UP_PIN ) == 0: # button is released
            draw.polygon([(20, 20), (30, 2), (40, 20)], outline=255, fill=0)  #Up
        else: # button is pressed:
            draw.polygon([(20, 20), (30, 2), (40, 20)], outline=255, fill=1)  #Up filled
            print("Up")
            
        if disp.RPI.digital_read(disp.RPI.GPIO_KEY_LEFT_PIN) == 0: # button is released
            draw.polygon([(0, 30), (18, 21), (18, 41)], outline=255, fill=0)  #left
        else: # button is pressed:
            draw.polygon([(0, 30), (18, 21), (18, 41)], outline=255, fill=1)  #left filled
            print("left")
            
        if disp.RPI.digital_read(disp.RPI.GPIO_KEY_RIGHT_PIN) == 0: # button is released
            draw.polygon([(60, 30), (42, 21), (42, 41)], outline=255, fill=0) #right
        else: # button is pressed:
            draw.polygon([(60, 30), (42, 21), (42, 41)], outline=255, fill=1) #right filled
            print("right")
            
        if disp.RPI.digital_read(disp.RPI.GPIO_KEY_DOWN_PIN) == 0: # button is released
            draw.polygon([(30, 60), (40, 42), (20, 42)], outline=255, fill=0) #down
        else: # button is pressed:
            draw.polygon([(30, 60), (40, 42), (20, 42)], outline=255, fill=1) #down filled
            print("down")

        if disp.RPI.digital_read(disp.RPI.GPIO_KEY_PRESS_PIN) == 0: # button is released
            draw.rectangle((20, 22,40,40), outline=255, fill=0) #center 
        else: # button is pressed:
            draw.rectangle((20, 22,40,40), outline=255, fill=1) #center filled
            print("center")
            
        if disp.RPI.digital_read(disp.RPI.GPIO_KEY1_PIN) == 0: # button is released
            draw.ellipse((70,0,90,20), outline=255, fill=0) #A button
        else: # button is pressed:
            draw.ellipse((70,0,90,20), outline=255, fill=1) #A button filled
            print("KEY1")
            
        if disp.RPI.digital_read(disp.RPI.GPIO_KEY2_PIN) == 0: # button is released
            draw.ellipse((100,20,120,40), outline=255, fill=0) #B button]
        else: # button is pressed:
            draw.ellipse((100,20,120,40), outline=255, fill=1) #B button filled
            print("KEY2")
            
        if disp.RPI.digital_read(disp.RPI.GPIO_KEY3_PIN) == 0: # button is released
            draw.ellipse((70,40,90,60), outline=255, fill=0) #A button
        else: # button is pressed:
            draw.ellipse((70,40,90,60), outline=255, fill=1) #A button filled
            print("KEY3")
            
        disp.ShowImage(disp.getbuffer(image))
    
except IOError as e:
    print(e)
    
except KeyboardInterrupt:    
    print("ctrl + c:")
    disp.RPI.module_exit()
    exit()
