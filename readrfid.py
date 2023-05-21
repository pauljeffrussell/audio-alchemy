""" Starts an RFID reader and prints out the RFID of any tag it reads

    The reader will read the tag mucltiple times but only print out the 
    tags ID once until a new card is read.


"""

import os
import threading
import logging
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
import time
import sys

logging.basicConfig(format=' %(message)s -- %(funcName)s %(lineno)d', level=logging.WARNING)


APP_RUNNING = True


def start_rfid_reader():
    global APP_RUNNING
    
    reader = SimpleMFRC522()
    existing_id = 0
    
    
    print("Place a new tag on the reader.\n\n")
    while APP_RUNNING:
        

        id = reader.read_id_no_block()
        if (id != existing_id and id != None):   
            
            existing_id = id
            print("RFID Read: ", id,"\n\n")
            
            time.sleep(.3)
 




def main():
    global APP_RUNNING
   
    # start the thread listening to the rfid reader

    try:
        start_rfid_reader()
    except KeyboardInterrupt:
    
        print("Cleaning up...")
        APP_RUNNING = False
        time.sleep(.5)
        GPIO.cleanup() # Clean up
        print("Clean up complete...")
        sys.exit()
        


main()
    



