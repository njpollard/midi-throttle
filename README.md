# midi-throttle
Use a midi control surface (currently the Korg Nanokontrol 2) as a throttle for your JMRI controlled model railway / railroad layout. Supports eight locomotives per controller.

This is currently alpha / proof of concept software written in Python. It has only been tested on Raspbian Buster and Python 3.7.3 so far. 

The software communicates with JMRI using the withrottle protocol over a local network, so doesn't need to be installed on the same machine as JMRI.

## Dependencies

Requires the [rt-midi](https://pypi.org/project/python-rtmidi/) library and dependencies.

## Short installation instructions (Raspbian)

Install dependencies for rt-midi
```
sudo apt install libasound2-dev
sudo apt install libjack-dev
pip3 install python-rtmidi
```
Edit the config.json file to include a list of 8 DCC addresses (see *The Config File* below)

## Usage 
```
usage: throttle.py [-h] [-m MIDIPORT] [-c CONFIG] [--hostname HOSTNAME]
                   [--port PORT] [-v] [-d]

optional arguments:
  -h, --help            show this help message and exit
  -m MIDIPORT, --midiport MIDIPORT
                        Midi port that surface is connected to
  -c CONFIG, --config CONFIG
                        Config file to use for this controller. Default:
                        config.json
  --hostname HOSTNAME   Hostname of withrottle server. Default: localhost
  --port PORT           Port number of withrottle server. Default: 12090
  -v, --verbose         Enable verbose output
  -d, --debug           Enable debugging output

```

## Longer installation instructions (Raspbian)

Install dependencies for rt-midi
```
sudo apt install libasound2-dev
sudo apt install libjack-dev
```

Download midi-throttle and installing rt-midi in a virtual environment:
```
sudo apt-get install python3-pip
pip3 install virtualenv
cd
git clone https://github.com/njpollard/midi-throttle
virtualenv ~/midi-throttle
cd ~/midi-throttle
source bin/activate
pip3 install python-rtmidi
```

If you have installed rt-midi in a virtual environment, next time you reboot or open a new shell you'll need to switch to it before you start the software
```
cd ~/midi-throttle
source bin/activate
```
## The Config File

Configuration of the controller is done using a JSON formatted config file. You can specify a config file argument on the command line, otherwise ```config.json``` is used.

### Simple setup of locos with no functions

The DCC addresses of the (up to 8) locos you wish to control are set in the config.json file. In the example below, the first slider will control loco with the short DCC address 11 (S11),
the second slider will control the loco with the DCC address 12 and so on.

```
[
        {
                "dcc_address": "S11"
        },
        {
                "dcc_address": "S12"
        },
        {
                "dcc_address": "S13"
        },
        {
                "dcc_address": "S14"
        },
        {
                "dcc_address": "S15"
        }
]
```

### Assigning buttons to loco functions

Four of the buttons on the left of the controller can be used to send functions to the currently selected loco, such as light and sound. These are Rewind, Fast Forward, Play and Record. The Stop button is reserved.
The Track Left and Track Right buttons act as shift keys, giving 12 functions in total. The example below shows how to assign a slider to loco 15 with seven functions.

```
        {
                "dcc_address": "S15",
                "functions": {
                        "normal": { "rec": 0, "play": 1, "rw": 2, "ff": 3  },
                        "lshift": { "rec": 4, "ff": 5 },
                        "rshift": { "rec", 8 }
                }
         }
```

## Using the controller

```CYCLE``` - track power (toggle on/off)

```M``` (8 buttons) - take control of corresponding loco

```R``` (8 buttons) - set throttle to reverse (toggle)

```S``` (8 buttons) - select this loco to use function keys

Sliders (8) - throttle

```Stop``` - emergency stop selected loco, or all locos if none selected

```Play >``` ```Rewind <<``` ```Fast Forward >>``` ```Record O``` - user assigned functions on selected loco

```Marker right``` + ```Marker left``` - toggle lock all buttons, but not throttles (for demo / child use)
