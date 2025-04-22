#!/usr/bin/env python3
import sys
import os
import time
import subprocess
import json
global NetworkSettingsFileContents

settingsFile='/boot/firmware/new-wifi.json'
outputFile='/boot/firmware/new-wifi-output.txt'

if os.path.exists(settingsFile):
    try:
        with open(settingsFile) as f:
            NetworkSettingsFileContents=json.load(f)
    except Exception as e:
        #with open(outputFile, 'w+') as o:
        #    o.write(f"Error reading JSON file: {e}\n")
        print(f"There was an rrror reading JSON file, this is the error : \n\n{e}\n")
else:
    print("No new-wifi.json file found, nothing to be done.")
    quit(0)

if NetworkSettingsFileContents:
    runCommands=[]
    time.sleep(5)
    runCommands.append(f"nmcli d wifi")
    if NetworkSettingsFileContents['IsSSIDHidden']:
        runCommands.append(f"nmcli c add type wifi con-name {NetworkSettingsFileContents['SSID']} ifname wlan0 ssid {NetworkSettingsFileContents['SSID']}")
        if NetworkSettingsFileContents['Password']:
            runCommands.append(f"nmcli c modify {NetworkSettingsFileContents['SSID']} {NetworkSettingsFileContents['SecurityType']} password '{NetworkSettingsFileContents['Password']}'")
        runCommands.append(f"nmcli c up {NetworkSettingsFileContents['SSID']}")
    else:
        if NetworkSettingsFileContents['Password']:
            runCommands.append(f"nmcli d wifi connect {NetworkSettingsFileContents['SSID']} password '{NetworkSettingsFileContents['Password']}'")
        else:
            runCommands.append(f"nmcli d wifi connect {NetworkSettingsFileContents['SSID']}")
    with open(outputFile, 'w+') as o:
        for command in runCommands:
            try:
                o.write(f"Attempting to run command {command}\n")
                print(f"Running command: {command}")
                result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
                print(f"Command output: {result.stdout}")
                o.write(f"Command output: {result.stdout}\n")
                subprocess.run("rm -f /boot/firmware/new-wifi.json", shell=True)
            except subprocess.CalledProcessError as e:
                print(f"Command failed with error: {e.stderr}")
                o.write(f"Command failed with error: {e.stderr}\n")
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
                o.write(f"An unexpected error occurred: {e}\n")
    
