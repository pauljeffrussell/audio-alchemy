#import RPi.GPIO as GPIO # Import Raspberry Pi GPIO library  
import time
from gpiozero import Button
import logging
import sys

# Create the logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Create a formatter
formatter = logging.Formatter('%(message)s -- %(funcName)s %(lineno)d')
# Create a stream handler to log to STDOUT
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.DEBUG)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

LAST_BUTTON_TIME = 0;

def my_interrupt_handler(channel):
    global LAST_BUTTON_TIME    
    
    interrupt_time = int(round(time.time() * 1000))
    #interrupt_time = millis();
    ## If interrupts come faster than 200ms, assume it's a bounce and ignore
    if (interrupt_time - LAST_BUTTON_TIME > 200):
        LAST_BUTTON_TIME = interrupt_time
        return True
    else:
        LAST_BUTTON_TIME = interrupt_time
        print(f'Debounced {channel}' )
        return False





def button_callback_16(channel):
    logger.info("16")
    if (my_interrupt_handler(channel)):
        logger.info("Previous Track Button was pushed!")
        #aaplayer.prev_track()

def button_callback_15(channel):
    logger.info("15")
    if (my_interrupt_handler(channel)):
        logger.info("Play/Pause Button was pushed!")
        #aaplayer.play_pause_track()
    
def button_callback_13(channel):
    logger.info("13")
    if (my_interrupt_handler(channel)):
        logger.info("Next Track Button was pushed!")
        #aaplayer.next_track()


## PINS https://gpiozero.readthedocs.io/en/stable/recipes.html#pin-numbering
## constructor https://gpiozero.readthedocs.io/en/stable/api_input.html#gpiozero.Button
##button16 = Button("BOARD16", pull_up=False, active_state=None, bounce_time=0.2,hold_time=0.1, hold_repeat=False, pin_factory=None)
#button15 = Button("BOARD15", pull_up=False, active_state=None, bounce_time=0.2,hold_time=0.1, hold_repeat=False, pin_factory=None)
#button13 = Button("BOARD13", pull_up=False, active_state=None, bounce_time=0.2,hold_time=0.1, hold_repeat=False, pin_factory=None)
button16 = Button("BOARD16")#, pull_up=False, active_state=None, bounce_time=0.2,hold_time=0.1, hold_repeat=False, pin_factory=None)
button15 = Button("BOARD15")#, pull_up=False, active_state=None, bounce_time=0.2,hold_time=0.1, hold_repeat=False, pin_factory=None)
button13 = Button("BOARD13")#, pull_up=False, active_state=None, bounce_time=0.2,hold_time=0.1, hold_repeat=False, pin_factory=None)


button16.when_pressed = button_callback_16
button15.when_pressed = button_callback_15
button13.when_pressed = button_callback_13


logger.info("Starting button monitor!")

while True:
    try: 
        time.sleep(5)
    except KeyboardInterrupt: 
        break

logger.info("Cleaning up!")

button16.close()
button15.close()
button13.close()

logger.info("exiting!")

    

