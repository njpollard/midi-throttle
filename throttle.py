#!/usr/bin/env python
#
# main.py
#
"""Control trains using MIDI control surface"""

import argparse
import socket
import re
import os, sys
import time
import logging
import json
from withrottle import withrottle
from pprint import pprint
import midiControl
from time import sleep

log = logging.getLogger("throttle-logger")

# How often to send throttle position to server (in seconds)
UPDATE_INTERVAL = 0.25

locked = False
power = False

train = [None] * 8
reverse = [False] * 8
selected = None

slider_updated = [False] * 8
slider_value = [0] * 8

# Called when server has confirmed that loco has been added
def add_confirmed(id):
    global train
    if id in dcc_address_list:
        channel = dcc_address_list.index(id)
        midiControl.set_led(True, channel, 3)
        train[channel] = id

# Called when server has confirmed that loco has been released
def release_confirmed(id):
    global train
    if id in dcc_address_list:
        channel = dcc_address_list.index(id)
        midiControl.set_led(False, channel, 3)
        train[channel] = None

# Called when server indicates that (new) loco is in reverse
def reverse_confirmed(id):
    global train
    if id in dcc_address_list:
        channel = dcc_address_list.index(id)
        midiControl.set_led(True, channel, 4)
        reverse[channel] = True

# Called when server indicates that (new) loco is facing forwards
def forward_confirmed(id):
    global train
    if id in dcc_address_list:
        channel = dcc_address_list.index(id)
        midiControl.set_led(False, channel, 4)
        reverse[channel] = False

# Called when server indicates power is on
def power_on_confirmed():
    global power
    midiControl.set_led(True, midiControl.CYCLE_BUTTON)
    power = True

# Called when server indicates power is off
def power_off_confirmed():
    global power
    midiControl.set_led(False, midiControl.CYCLE_BUTTON)
    power = False

# Called periodlically to send new slider positions
def update_throttles():
    global throttle, train
    for i, updated in enumerate(slider_updated):
        if updated:
            slider_updated[i] = False
            log.debug("Slider %d updated to %d" % (i, slider_value[i]))
            if (train[i] != None):
                throttle.set_speed(dcc_address_list[i], slider_value[i])

# Called when slider is moved
def slider_callback(channel, value):
    global slider_updated, slider_value
    slider_updated[channel] = True
    slider_value[channel] = value
    return

# Called when a button is pressed
def button_callback(b, is_on):

    global locked, train, reverse, selected, throttle, power

    channel = b.channel
    button = b.button

    # Button pressed
    if (is_on):
        log.debug("Pressed %d %d" % (channel, button))

        # Lock controls?
        if (b == midiControl.MARKER_L_BUTTON and midiControl.is_pressed(midiControl.MARKER_R_BUTTON)):
            locked = not locked

        # Power cycle (works even when buttons are locked)
        if (b == midiControl.CYCLE_BUTTON):
            throttle.power(not power)

        # If controls are locked, do nothing
        if locked:
            return

        # Select throttles to use (M buttons)
        if button == 3 and channel <= 8 and channel < len(dcc_address_list):
            if (train[channel] == None):
                throttle.add_loco(dcc_address_list[channel])
            else:
                # Unselect throttle
                throttle.release_loco(dcc_address_list[channel])
                # Turn off reverse LED
                if reverse[channel]:
                    reverse[channel] = False
                    midiControl.set_led(False, channel, 4)
                # Turn off 'selected' LED and unselect
                if selected == channel:
                    selected = None
                    midiControl.set_led(False, channel, 2)

        # Reverse (R buttons)
        if (button == 4 and channel <= 8 and train[channel] != None):
            reverse[channel] = not reverse[channel]
            if reverse[channel]:
                throttle.set_reverse(dcc_address_list[channel])
            else:
                throttle.set_forward(dcc_address_list[channel])
            midiControl.set_led(reverse[channel], channel, 4)

        # Select train (S butons)
        if (button == 2 and channel <= 8 and train[channel] != None):
            if (selected != None):
                # turn old LED off
                midiControl.set_led(False, selected, 2)
            # Toggle off
            if (selected == channel):
                selected = None
            else:
                selected = channel
                midiControl.set_led(True, selected, 2)

        # Stop button
        if (b == midiControl.STOP_BUTTON and selected != None):
            throttle.stop(dcc_address_list[selected])

	# Stop all (when no trains are selected)
        if (b == midiControl.STOP_BUTTON and selected == None):
            for loco in dcc_address_list:
                throttle.stop(loco)

    # Function buttons - only operated if a loco is selected using corresponding S button

    if (selected != None):

        # The 'track left' and 'track right' buttons act as different shift keys
        if midiControl.is_pressed(midiControl.TRACK_L_BUTTON):
            function_bank = function_list[selected].get('lshift')
        elif midiControl.is_pressed(midiControl.TRACK_R_BUTTON):
            function_bank = function_list[selected].get('rshift')
        else:
            function_bank = function_list[selected].get('normal')

        if (function_bank):
            log.debug("Function bank is %s" % function_bank)

            # function mapped to this button
            function = None
            # is pressed button a function button?
            is_f_button = False

            # Map button to function
            if (b == midiControl.REC_BUTTON):
                is_f_button = True
                log.debug("REC button pressed")
                function = function_bank.get('rec')
            elif (b == midiControl.PLAY_BUTTON):
                is_f_button = True
                log.debug("PLAY button pressed")
                function = function_bank.get('play')
            elif (b == midiControl.FF_BUTTON):
                is_f_button = True
                log.debug("FF button pressed")
                function = function_bank.get('ff')
            elif (b == midiControl.RW_BUTTON):
                is_f_button = True
                log.debug("RW button pressed")
                function = function_bank.get('rw')

            if is_f_button:
                if (function is not None):
                    throttle.send_function(dcc_address_list[selected], function, is_on)
                else:
                    log.debug("No function button mapped")

#main function
if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--midiport", help="Midi port that surface is connected to", type=int)
    parser.add_argument("-c", "--config", help="Config file to use for this controller. Default: config.json")
    parser.add_argument("--hostname", help="Hostname of withrottle server. Default: localhost")
    parser.add_argument("--port", help="Port number of withrottle server. Default: 12090", type=int)
    parser.add_argument("-v", "--verbose", help="Enable verbose output", action="store_true")
    parser.add_argument("-d", "--debug", help="Enable debugging output", action="store_true")

    args = parser.parse_args()

    # Prompts user for MIDI input and output port, unless a valid port number
    # is given as an argument on the command line.
    # API backend defaults to ALSA on Linux.
    midiport = args.midiport

    # JSON config file
    if args.config:
        config_file = args.config
    else:
        config_file = "config.json" 

    # Hostname of withrottle server, default localhost
    if args.hostname:
        host = args.hostname
    else:
        host = "localhost"

    # Port for withrottle server, default 12090
    if args.port:
        port = args.port
    else:
        port = 12090

    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    elif args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)

    # read config file and import
    dirname = os.path.dirname(__file__)
    config_file = os.path.join(dirname, config_file)

    with open(config_file, 'r') as f:
        config = json.load(f)

    # List of DCC addresses, corresponding to sliders 0-7
    dcc_address_list = []
    # List of function button mappings, corresponding to sliders 0-7
    function_list = []

    for entry in config:
        if 'dcc_address' in entry:
            dcc_address_list.append(entry['dcc_address'])
            log.debug("Adding DCC address %s" % entry['dcc_address']) 
        else:
            log.warn("Missing DCC address in config")
        if 'functions' in entry:
            function_list.append(entry['functions'])
            log.debug("Adding function key mapping")
        else:
            function_list.append(None)

    # Connect to midi controller and set up callback functions
    midiControl.start(midiport, button_callback, slider_callback)
    midiControl.animate(2)
    log.info("Connected MIDI controller")

    # Connect to withrottle server
    throttle = withrottle(host, port)
    midiControl.animate(3)
    log.info("Connected to withrottle server")
    throttle.set_name("Korg"+str(midiport))

    heartbeat_interval = 1
    start = time.time()
    # Main loop
    try:
        while True:

            actionlist = throttle.process_input()

            for item in actionlist:
                (action, id) =  item

                if (action == withrottle.ADDED):
                    add_confirmed(id)
                elif (action == withrottle.REMOVED):
                    release_confirmed(id)
                elif (action == withrottle.REVERSE):
                    reverse_confirmed(id)
                elif (action == withrottle.FORWARD):
                    forward_confirmed(id)
                elif (action == withrottle.POWER_ON):
                    power_on_confirmed()
                elif (action == withrottle.POWER_OFF):
                    power_off_confirmed()
                elif (action == withrottle.HEARTBEAT):
                    heartbeat_interval = int(id)
                    log.debug("Got heartbeat interval of %d" % (heartbeat_interval))
                    log.info("Received response from withrottle server")
                    midiControl.animate(4)
                    sleep(1)
                    for i in range(3):
                        midiControl.animate(i+2, False)

            # Send throttle positions to server
            update_throttles()

            sleep(UPDATE_INTERVAL)
            if time.time() - start > (heartbeat_interval / 2):
                throttle.send_heartbeat()
                start = time.time()

    except KeyboardInterrupt:
        midiControl.cleanup()

