import RPi.GPIO as GPIO # Import Raspberry Pi GPIO library  
import time

LAST_BUTTON_TIME = 0;

def my_interrupt_handler(channel):
    global LAST_BUTTON_TIME    
    return True
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
    if (my_interrupt_handler(channel)):
        print("Previous Track Button was pushed!")
    
def button_callback_15(channel):
    if (my_interrupt_handler(channel)):
        print("Play/Pause Button was pushed!")
    
def button_callback_13(channel):
    if (my_interrupt_handler(channel)):
        print("Next Track Button was pushed!")
    
    
    
def start_button_controls():
    GPIO.setwarnings(False) # Ignore warning for now
    GPIO.setmode(GPIO.BOARD ) # Use physical pin numbering
    
 
    GPIO.setup(16, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Set pin 10 to be an input pin and set initial value to be pulled low (off)
    GPIO.setup(15, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Set pin 10 to be an input pin and set initial value to be pulled low (off)
    GPIO.setup(13, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Set pin 10 to be an input pin and set initial value to be pulled low (off)

    GPIO.add_event_detect(16,GPIO.FALLING,callback=button_callback_16, bouncetime=50) # Setup event on pin 10 rising edge
    GPIO.add_event_detect(15,GPIO.FALLING,callback=button_callback_15, bouncetime=50) # Setup event on pin 10 rising edge
    GPIO.add_event_detect(13,GPIO.FALLING,callback=button_callback_13, bouncetime=50) # Setup event on pin 10 rising edge
    


def rpi_gpio_solution():
    
    start_button_controls()
    message = input("Press enter to quit\n\n") # Run until someone presses enter
            
    GPIO.cleanup() # Clean up
        

"""def adadebounc_solution():
    
    pin16 = digitalio.DigitalInOut(board.16)
    pin16.direction = digitalio.Direction.INPUT
    pin16.pull = digitalio.Pull.UP
    switch16 = Debouncer(pin)
    
    try:
        while True:
            switch16.update()
            if switch.fell:
                button_callback_16('foo')
            
    except KeyboardInterrupt:
        GPIO.cleanup() # Clean up
"""



rpi_gpio_solution()
