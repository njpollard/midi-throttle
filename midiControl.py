#!/usr/bin/env python
#
# midiControl.py
#
"""Library for handling inputs from KORG Nanokontrol2"""

import logging
import sys
import time

log = logging.getLogger("midi-logger")

from rtmidi.midiutil import open_midiinput, open_midioutput

_pressed = [False] * 0xFF
_midiout = None
_midiin = None

class Button:

    def __init__(self, control_number):
        self.__set_control_number(control_number)

    ## getter methods
    def __get_control_number(self):
        return self.__control_number

    def __get_channel(self):
        return self.__channel

    def __get_button(self):
        return self.__button

    ## setter methods
    def __set_control_number(self, control_number):
        self.__control_number = control_number
        self.__channel = control_number % 0x10
        self.__button = control_number // 0x10

    def __set_channel(self, channel):
        self.__channel = channel
        self.__control_number == self.__channel + (self.__button * 0x10)

    def __set_button(self, button):
        self.__button = button
        self.__control_number == self.__channel + (self.__button * 0x10)

    control_number = property(__get_control_number, __set_control_number)
    channel = property(__get_channel, __set_channel)
    button = property(__get_button, __set_channel)

    def __eq__(self, other):
        if not isinstance(other, Button):
            # don't attempt to compare against unrelated types
            return NotImplemented

        return self.control_number == other.control_number


# Called when a slider value changes
def __trigger_slider(channel, value, slider_callback):
    log.debug("Slider %d value %d" % (channel, value))
    if (slider_callback):
        slider_callback(channel, value)

# Called when a button is pressed or released
def __trigger_button(control_number, is_on, button_callback):

    if (is_on):
        _pressed[control_number] = True
    else:
        _pressed[control_number] = False

    if (button_callback != None):
        log.debug("Calling button callback function")
        button = Button(control_number)
        button_callback(button, is_on)
    else:
        log.debug("No button call back function defined")

# Is the specified button pressed?
def is_pressed(b):
    log.debug("Checking whether %d %d is pressed" % (b.channel, b.button))
    return _pressed[b.control_number]

# Animate LEDs - switch whole row on or off sequentially
def animate(row, led_on=True):
    if (led_on):
        val = 127
    else:
        val = 0
    for i in range(8):
        control_number = i + (row *0x10)
        led = [0xBF, control_number, val]
        log.debug("LED %r" %led)
        _midiout.send_message(led)
        if (led_on):
            time.sleep(0.15)

# Set LED for specified button
def set_led(led_on, p1, p2 = None):
    if (p2 == None):
        control_number = p1.control_number
    else:
        control_number = p1 + (p2 * 0x10);

    if (led_on):
        led = [0xBF, control_number, 127]
    else:
        led = [0xBF, control_number, 0]
    _midiout.send_message(led)

# Connect MIDI device
def start(port, button_callback, slider_callback):

    global _midiout, _midiin, _button_callback, _slider_callback
    log = logging.getLogger('midiin_poll')
    logging.basicConfig(level=logging.DEBUG)

    _button_callback = button_callback
    _slider_callback = slider_callback

    try:
        _midiin, port_in = open_midiinput(port)
    except (EOFError, KeyboardInterrupt):
        sys.exit()

    try:
        _midiout, port_out = open_midioutput(port)
    except (EOFError, KeyboardInterrupt):
        sys.exit()

    # Change LED modes
    led_external = [0xf0, 0x42, 0x40, 0x00, 0x01, 0x13, 0x00, 0x00, 0x00, 0x01, 0xf7]

    # Change LEDs to external control for Korg
    _midiout.send_message(led_external)

    _midiin.set_callback(handler)

 
def handler(msg, data):

    global _button_callback, _slider_callback
    message, delta = msg

    #log.debug("%X %X %X" % (message[0],message[1],message[2]))
    try:
        status_byte = message[0]
    except IndexError:
        return

    if (status_byte >= 0xB0 and status_byte <= 0xBF):
        # Control change message received

        try:
            control_number = message[1]
            value = message[2]
        except IndexError:
            return

        # Check for fader slide
        if (control_number <= 0xF):
            __trigger_slider(control_number, value, _slider_callback)

        if (control_number >= 0x20 and control_number <= 0x50):

            if (value > 0):
                __trigger_button(control_number, True, _button_callback)
            else:
                __trigger_button(control_number, False, _button_callback)


def cleanup():

    global _midiout, _midiin
    led_internal = [0xf0, 0x42, 0x40, 0x00, 0x01, 0x13, 0x00, 0x00, 0x00, 0x00, 0xf7]

    # Change LEDs back to internal control
    _midiout.send_message(led_internal)

    log.debug("Closing midi device")
    _midiin.close_port()
    _midiout.close_port()
    del _midiin
    del _midiout


CYCLE_BUTTON = Button(0x2E)
SET_BUTTON = Button(0x3C)
TRACK_L_BUTTON = Button(0x3A)
TRACK_R_BUTTON = Button(0x3B)
MARKER_L_BUTTON = Button(0x3D)
MARKER_R_BUTTON = Button(0x3E)
RW_BUTTON = Button(0x2B)
FF_BUTTON = Button(0x2C)
STOP_BUTTON = Button(0x2A)
PLAY_BUTTON = Button(0x29)
REC_BUTTON = Button(0x2D)
