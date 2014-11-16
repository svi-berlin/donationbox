#!/usr/local/bin/python

import functools
import math
import os
import random
import RPi.GPIO as GPIO
import smbus
import strfile
import serial
import time
import ui
import printer
from datetime import datetime

fortune_base = '/usr/share/games/fortunes'
printer_tty = '/dev/ttyAMA0'
printer_baud = 19200
printer_currency_symbol = ''

buttons = (
    (16, 'black'),
    (12, 'white'),
    (22, 'green'),
    (18, 'red'),
    (23, 'blue'),
)

coin_input = 26
display_bus = 0
display_address = 0x24
debug = 0
print_bonus = 0
coin_values = {
    1: 10,
    2: 20,
    3: 50,
    4: 100
}

donation_options = [
    'Hungry Orphans',
    'Lonely Kittens',
    'Lonely Orphans',
    'Mad Scientists',
]

donation_totals = [0] * len(donation_options)

extra_fortunes = (
    'BONUS! Extra fortune:\n',
    'BONUS! Another extra fortune:\n',
    'BONUS! 3 for the price of 1!\n',
    'Super-secret extra fortune!\n'
)

hr = '-' * 32

databases = (
    (7,     ('disclaimer', 'miscellaneous', 'riddles')),
    (15,    ('platitudes', 'paradoxum', 'love')),
    (30,    ('fortunes', 'definitions')),
    (75,    ('politics', 'science', 'humorists')),
    (150,   ('literature', 'wisdom', 'tao')),
)

_______databases = (
    (7,     ('zitate', 'tips')),
    (15,    ('warmduscher', 'quiz')),
    (30,    ('zitate', 'vornamen')),
    (75,    ('stilblueten', 'warmduscher')),
    (150,   ('stilblueten', 'tips')),
)


databases = tuple((value,
                   tuple(strfile.Strfile(os.path.join(fortune_base, dbname))
                         for dbname in dbnames))
                  for value, dbnames in databases)

def move_servo(position): 
	frequencyHertz = 50
	servoGPIO = 24
	pwm = GPIO.PWM(servoGPIO, frequencyHertz)
	dutyCyclePercentage = position / 20
	pwm.start(dutyCyclePercentage)
	time.sleep(.5)

def pick_fortune_set(value):
    for v, dbs in databases:
        if v >= value:
            return dbs
    return databases[-1][1]

def pick_fortune_db(value):
    dbs = pick_fortune_set(value)
    total = sum(db.numstr for db in dbs)
    r = random.randrange(total)
    for db in dbs:
        if db.numstr > r:
            return db
        r -= db.numstr

def pick_fortune(value):
    db = pick_fortune_db(value)
    return db.read_random()

def unwrap(lines):
    """Takes line wrapped text and 'unwraps' it.
    
    Arguments:
      lines: A list of lines in the original text, optionally newline terminated.
    Returns:
      A list of paragraphs, not newline terminated.
    """
    if not lines:
        return lines
    paras = []
    current = [lines[0].strip()]
    for line in lines[1:]:
        if line.startswith('\t') or line.startswith('<'):
            # Indent or symbol means a mandatory linebreak
            paras.append(' '.join(current))
            current = [line.strip()]
        else:
            # Append to current line
            current.append(line.strip())
    paras.append(' '.join(current))
    return paras

def wrap(paras, maxlen=32):
    """Line wraps a set of paragraphs.
    
    Arguments:
      paras: A list of paragraph strings, not newline terminated.
      maxlen: Length to wrap at.
    Returns:
      A list of line strings each no longer than maxlen, newline
      terminated. Each paragraph is separated by a blank line.
    """
    lines = []
    for para in paras:
        while len(para) > maxlen:
            lastbreak = para.rfind(' ', 0, maxlen + 1)
            if lastbreak == -1:
                lastbreak = maxlen
            if lastbreak == maxlen:
                lines.append(para[:lastbreak])
            else:
                lines.append(para[:lastbreak] + '\n')
            para = para[lastbreak+1:]
        if len(para) == maxlen:
            lines.append(para)
        elif para.strip():
            lines.append(para + '\n')
        lines.append('\n')
    return lines


printer = serial.Serial(printer_tty, printer_baud)
printer.write('\x1B{1')

def print_message(lines):
	global print_bonus
	fobj = open("/usr/local/bin/donationbox/fortunes.txt", "a")
	for line in lines[::-1]:
        	print line
		fobj.write(str(line))
        	printer.write(line)
	fobj.close()
	time.sleep(0.5)
	#os.system("fswebcam -r 1280x720 /home/pi/webcam/photobooth.jpg")
	#os.system("python /home/pi/Python-Thermal-Printer/print-cam.py")
        #time.sleep(0.5)

def generate_wisdom(value):
    global print_bonus
    #move_servo(value)
    message = []
    message.append('\n')
    message.append('\n')
    message.append('\n')
    localtime = datetime.now().strftime('%A, %d.%B %Y %H:%M')
    message.append(localtime)
    message.append('\n')
    message.append('Herzlichsten Dank!\n')
    message.append('Deine Spende: %.2f Euro\n' % (value / 100.0))
    fobj = open("/usr/local/bin/donationbox/donations.txt", "r")
    for line in fobj:
    	donations = int(line)
    fobj.close()
    message.append('Bisher gespendet: %.2f Euro.\n' % (donations / 100.0))
    value *= random.random() + 0.5 # Increase or decrease the value a bit
    num_extra_fortunes = 0
    while value > 0:
    	message.append('\n')
        message.extend(wrap(unwrap(pick_fortune(value))))
        if (debug == 1):
		print 'value: ', value
        value += math.log(random.random()) / math.log(1/.995)
        value /= 2
        if value > 0:
            print_bonus = 1
            message.append('\n')
            message.append(extra_fortunes[num_extra_fortunes])
	    message.append('\n')
            message.extend(wrap(unwrap(pick_fortune(100))))
            num_extra_fortunes = min(num_extra_fortunes + 1, len(extra_fortunes) - 1)
    	message.append('\n')
	return message

def dispense_wisdom(value):
	message = generate_wisdom(value)
	print_message(message)
	if (debug == 1):
		print message

class MenuHandler(object):
    MENU_UP = '\xa2'
    MENU_DN = '\xa3'
    
    def __init__(self, options):
        self.options = options
        self.display = display
        self.position = 0

    def draw_menu(self):
        display = self.display
        display.clear()
        if self.position > 0:
            display.message(self.MENU_UP)
        else:
            display.message(' ')
        display.message(self.options[self.position].rjust(15))
        display.setCursor(0, 1)
        if len(self.options) > self.position + 2:
            display.message(self.MENU_DN)
        else:
            display.message(' ')
        if len(self.options) > self.position + 1:
            display.message(self.options[self.position + 1].rjust(15))

    def handle_input(self, event):
        if event.args == 'black' and self.position > 0:
            self.position -= 1
            self.draw_menu()
            return None
        elif event.args == 'white' and self.position < len(self.options) - 2:
            self.position += 1
            self.draw_menu()
            return None
        elif event.args == 'red':
            return self.position
        elif event.args == 'green':
            return self.position + 1
	else:
	    return 1

            
class STATES(object):
    IDLE = 1
    IN_USE = 2
    DONATE = 3

    
class AdvisorApplication(object):
    def __init__(self, ui_thread):
        self.ui_thread = ui_thread
        self.balance = 0
        self.state = STATES.IDLE
        self.donation_menu = None
        self._show_insert_coin()
        
    def _show_insert_coin(self):
        time.sleep(0.01)
        time.sleep(0.01)
        print "INSERT COIN"
        if (debug == 1):
		
		exit(0)
        	#self.balance = 1
        	#dispense_wisdom(self.balance)

    def _show_total(self):
        time.sleep(0.01)
        time.sleep(0.01)
        time.sleep(0.01)
        print "Advise Me"
	self._dispense_wisdom()
	
    def _dispense_wisdom(self):
        #self.display.clear()
        print "Dispensing"
        #self.display.setCursor(0, 1)
        fobj = open("/usr/local/bin/donationbox/donations.txt", "r")
	for line in fobj: 
    		donations = int(line)
		total_donations = donations + self.balance 
	fobj.close()
	
	fobj = open("/usr/local/bin/donationbox/donations.txt", "w")
	fobj.write(str(total_donations))
	fobj.close()

	print "wisdom ..."
        dispense_wisdom(self.balance)
        self.balance = 0
        self._show_insert_coin()

    def _dispense_wisdom_XXX(self):
        dispense_wisdom(self.balance)
        self.balance = 0
        self._show_insert_coin()

    def _idle_event(self, event):
        if event.args == 'coin':
            self.balance += coin_values[event.state]
            self._show_total()
            return STATES.IN_USE
        else:
            return STATES.IDLE    
    
    def _in_use_event(self, event):
        if event.args == 'coin':
            self.balance += coin_values[event.state]
            self._show_total()
            return STATES.IN_USE
        elif event.args == 'green':
            self._dispense_wisdom()
            return STATES.IDLE
        #elif event.args == 'white':
        #    self.donation_menu = MenuHandler(donation_options, self.display)
        #    self.donation_menu.draw_menu()
        #    return STATES.DONATE
        else:
            return STATES.IN_USE
    
    def _donate_event(self, event):
        selection = self.donation_menu.handle_input(event)
        if selection:
            donation_totals[selection] = self.balance
            self._dispense_wisdom()
            return STATES.IDLE
        else:
            return STATES.DONATE
    
    event_handlers = {
        STATES.IDLE: _idle_event,
        STATES.IN_USE: _in_use_event,
        STATES.DONATE: _donate_event,
    }
    
    def run(self):
        self.ui_thread.start()
        try:
            for event in self.ui_thread:
                if isinstance(event, ui.TimeoutEvent):
                	print "hi"
		else:
                    if event.args == 'coin' or event.state == False:
                        self.state = self.event_handlers[self.state](self, event)
        finally:
            self.ui_thread.stop()

            
def main():
    GPIO.setmode(GPIO.BOARD)
    #GPIO.setup(24, GPIO.OUT)    
    for pin, name in buttons:
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    input_handlers = [ui.InputEventHandler(functools.partial(GPIO.input, pin), name)
                      for pin, name in buttons]
    
    GPIO.setup(coin_input, GPIO.IN)
    input_handlers.append(ui.MultiPulseEventHandler(
        functools.partial(GPIO.input, coin_input),
        True,
        0.1,
        'coin'))
    ui_thread = ui.UIEventGenerator(0.01, input_handlers)

    try:
        AdvisorApplication(ui_thread).run()
    finally:
        GPIO.cleanup() # this ensures a clean exit    
        print "finally"

        
if __name__ == '__main__':
    main()
