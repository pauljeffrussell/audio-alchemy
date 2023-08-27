""" Starts an RFID reader and prints out the RFID of any tag it reads

    The reader will read the tag mucltiple times but only print out the 
    tags ID once until a new card is read.


"""

import os
import threading
import logging
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
#import SimpleMFRC522
import time
import sys

logging.basicConfig(format=' %(message)s -- %(funcName)s %(lineno)d', level=logging.WARNING)

LOOP_DURATION = .2

APP_RUNNING = True


def start_rfid_reader():
    global APP_RUNNING
    
    reader = SimpleMFRC522()
    existing_id = 0
    
    none_count = 0
    id_count = 0
    
    max_none_count = 0
    
    read_something = False
    
    current read
    
    
    counter = 1
    print("Place a new tag on the reader.\n\n")
    while APP_RUNNING:
        

        uid = reader.read_id_no_block()
        
        if uid == None:
            none_count = none_count + 1
        else:
            id_count = id_count +1
            
            
        if uid == None:
            max_none_count = max_none_count + 1
        
        
        if success:
          print("UID:", uid)
        else:
          print("Failed to read UID")
        
        if uid == None:
            print(counter, " RFID Read Status: ", success)
            print(counter, " RFID: ", uid,"\n")

        counter = counter +1
        
        
        
    
        """uid, success = reader.read_id_no_block()
        print("RFID Read: ", uid)
        print("Success: ", success,"/n")
        """
        
        
        time.sleep(LOOP_DURATION)
    
    
"""    if (id != existing_id and id != None):   
            
            existing_id = id
            print("RFID Read: ", id,"\n\n")
            
            time.sleep(.5)
 """




def main():
    global APP_RUNNING
   
    # start the thread listening to the rfid reader

    try:
        start_rfid_reader()
    except KeyboardInterrupt:
    
        print("Cleaning up...")
        APP_RUNNING = False
        time.sleep(LOOP_DURATION + .1)
        GPIO.cleanup() # Clean up
        print("Clean up complete...")
        sys.exit()
        


main()
    



