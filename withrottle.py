import socket, select, string, sys, re, logging
from time import sleep

log = logging.getLogger("withrottle-logger")

class withrottle:

    ADDED = 1
    REMOVED = 2
    CONNECTED = 3
    HEARTBEAT = 4
    FORWARD = 5
    REVERSE = 6
    POWER_ON = 7
    POWER_OFF = 8

    def __init__(self, host, port):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # connect to remote host
        try :
            self.s.connect((host, port))
        except :
            log.error('Unable to connect to %s %d' % (host, port))
            sys.exit()

        self.s.setblocking(0)
        log.debug("Connected")


    # Read latest input from withrottle server
    def read(self):
        try:
            data = self.s.recv(4096)
            return data.decode()
        except:
            return ''

    # Send message to withrottle server
    def write(self, message):
        message = message + '\n'
        log.debug("Sending %s" % (message))
        self.s.send(message.encode())

    # Set name of throttle
    def set_name(self, name):
        message = "N%s" % (name)
        self.write(message)

    # Send a stay-alive heartbeat
    def send_heartbeat(self):
        message = "*"
        self.write(message)

    # Add a loco to this controller
    def add_loco(self, id):
        message = "MT+%s<;>%s" % (id,id)
        self.write(message)

    # Release a loco from this controller
    def release_loco(self, id):
        message = "MT-%s<;>r" % (id)
        self.write(message)

    # Set forward direction
    def set_forward(self, id):
        message = "MTA%s<;>R1" % (id)
        self.write(message)

    # Set reverse direction
    def set_reverse(self, id):
        message = "MTA%s<;>R0" % (id)   
        self.write(message)

    # Set speed of loco
    def set_speed(self, id, speed):
        if (speed > 126):
            speed = 126
        message = "MTA%s<;>V%d" % (id, speed)
        self.write(message)

    # Emergency stop loco
    def stop(self, id):
        message = "MTA%s<;>X" % (id)
        self.write(message)

    # Track power 
    def power(self, status):
        if (status):
            message = "PPA1" 
        else:
            message = "PPA0"
        self.write(message)

    # Send dcc decoder function (lights etc.)
    def send_function(self, id, fn, is_pressed):
        if (is_pressed):
            x = 0
        else:
            x = 1
        message = "MTA%s<;>F%d%s" % (id, x, fn)
        self.write(message)

    def process_input(self):
        message = self.read()
        if message != '':
            log.debug(message)
        lines = message.split('\n')
        r = []
        for line in lines:

            # Added loco to controller
            m = re.match("MT\+(.*?)\<;\>", line)
            if m:
                log.debug("Added %s successfully" % (m.group(1)))
                r.append((self.ADDED, m.group(1)))

            # Removed loco from controller
            m = re.match("MT\-(.*?)\<;\>", line)
            if m:
                log.debug("Removed %s successfully" % (m.group(1)))
                r.append((self.REMOVED, m.group(1)))

            # Loco is set to reverse direction
            m = re.match("MTA(.*?)\<;\>R0", line)
            if m:
                log.debug("Loco %s set to reverse" % (m.group(1)))
                r.append((self.REVERSE, m.group(1)))

            # Loco is set to forward direction
            m = re.match("MTA(.*?)\<;\>R1", line)
            if m:
                log.debug("Loco %s set to forward" % (m.group(1)))
                r.append((self.FORWARD, m.group(1)))

            # Controller is connected to server
            m = re.match("PW(.*)", line)
            if m:
                log.debug("Connected successfully to port %s" % (m.group(1)))
                r.append((self.CONNECTED, m.group(1)))

            # Track power is off
            m = re.match("PPA0", line)
            if m:
                log.debug("Power off")
                r.append((self.POWER_OFF, 1))

            # Track power is on
            m = re.match("PPA1", line)
            if m:
                log.debug("Power on")
                r.append((self.POWER_ON, 0))

            # Heartbeat interval
            m = re.match("\*(\d*)", line)
            if m:
                log.debug("Heartbeat required every %s seconds" % (m.group(1)))
                r.append((self.HEARTBEAT, m.group(1)))

        return r
