import os
from urllib.parse import urlparse, parse_qs
from yt_dlp import YoutubeDL
import pandas as pd
import pl7 as aaplayer
import RPi.GPIO as GPIO # Import Raspberry Pi GPIO library  
from mfrc522 import SimpleMFRC522
import threading
import logging
from logging.handlers import RotatingFileHandler
import sys
import time
import configfile as CONFIG


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

# Create a rotating file handler to log to a file
#formatterForLogFile = logging.Formatter('%(asctime)s %(message)s -- %(funcName)s %(lineno)d')
#file_handler = RotatingFileHandler(CONFIG.LOG_FILE_LOCATION, maxBytes=1024*1024, backupCount=5)
#file_handler.setLevel(logging.DEBUG)
#file_handler.setFormatter(formatterForLogFile)
#logger.addHandler(file_handler)




#LIBRARY_CACHE_FOLDER = "/home/matt/dev/library/"
LIBRARY_CACHE_FOLDER = CONFIG.LIBRARY_CACHE_FOLDER

DB_SHEET_ID = CONFIG.DB_SHEET_ID
DB_SHEET_NAME = CONFIG.DB_SHEET_ID
DB = pd.DataFrame()

APP_RUNNING = True



#### COMMANDS

"""
Stops all playback, resets the player, reloads the database
"""
STOP_AND_RELOAD_DB = CONFIG.STOP_AND_RELOAD_DB 

"""
Tells the player to keep playing continuously. It will 
"""
PLAYBACK_CONTINUOUS = "12345"

"""
Tells the player to stop at the end of the album
"""
PLAYBACK_STOP_AT_ALBUM_END = "12345"

"""
Tells the player to shuffel the current playlist
"""
PLAYBACK_SHUFFEL_ALBUM = "12345"


def load_database():
    db_url = f'https://docs.google.com/spreadsheets/d/{DB_SHEET_ID}/gviz/tq?tqx=out:csv&sheet={DB_SHEET_NAME}'

    logger.info(f'DB URL: {db_url}s')
    # Read the spreadsheet
    return pd.read_csv(db_url)

"""
Checks to see if it recieved a command card. If it did, it executes the command provided by the ccard
    
"""
def command_card_handler(rfid_code):
    global DB, STOP_AND_RELOAD_DB
    command_code = str(rfid_code)
    
    if (command_code == STOP_AND_RELOAD_DB ):
        logger.debug('Executing Command Card Stop Player & Reload Database')
        DB = load_database()
        aaplayer.shutdown_player()
        aaplayer.startup()
        return True
    else:
        return False
    
    
    
"""
Finds a given value in a given column of the DB and returns the value from another column in that row.

    search_column - The column header for the field to search.
    search_term - The term to search for in the search column
    result_column - The name of the column from which to return a result

returns the value from column result_column in the row where search_term was found in search_column
"""
def lookup_field_by_field(df, search_column, search_term, result_column):
    # Get the value to look up
    #value_to_lookup = 2
    # Check if the value is found in the DataFrame
    search_term_string = str(search_term)
    
    if search_term_string in df[search_column].values:
    #if value_to_lookup in df["rfid"]:
        # Find the row where the value is located
        
        
        row_index = df[df[search_column] == search_term_string].index[0]
        # Get the value in the corresponding column
        result_value = df.loc[row_index, result_column]
        # Print the value
        
        logger.debug(f'Found {result_column}: {result_value}s')
        return result_value
    else:
        #didn't find that RFID in the sheet
        logger.warning(f'The value {search_term} was not found in the column {search_column}.')
        return 0

          
"""
Return true if the album is set to shuffle
    false otherwise            
"""                 
def is_album_shuffle(rfid_code):
    global DB
    
    suffle_album = lookup_field_by_field(DB, 'rfid', rfid_code, 'shuffle')  
    if suffle_album == 1:
        return True
    else:
        return False

"""
Return true if the album is set to repeat
    false otherwise            
"""                 
def is_album_repeat(rfid_code):
    global DB
    
    repeat = lookup_field_by_field(DB, 'rfid', rfid_code, 'repeat')  
    if repeat == 1:
        return True
    else:
        return False
                 
                 
def handle_rfid_read(rfid_code):
        global DB, THREAD_LOCK
        
        #THREAD_LOCK.acquire()
        
        logger.debug(f'Looking up album folder for RFID: {rfid_code}...')
    
        ## check if you recieved a command card
        ## Command cards handle system wide settings 
        if (command_card_handler(rfid_code) == True):
            logger.debug(f'Completed command card: {rfid_code}...')      
        else:
            ##album_folder_name = lookup_field_by_field(DB, 'rfid', rfid_code, 'folder')
            
            album_folder_name = lookup_field_by_field(DB, 'rfid', rfid_code, 'folder')
            logger.debug(f'Attemptting to play {album_folder_name}...')
    
            if (album_folder_name != 0):
                album_folder = LIBRARY_CACHE_FOLDER + album_folder_name

                logger.debug(f'Looking for {album_folder}...')
                
                if os.path.exists(album_folder):
                    #if os.path.isdir(folder_name): 
                    logger.debug (f'Album folder exists. Playing {album_folder_name}')
                    aaplayer.play_folder( album_folder, is_album_shuffle(rfid_code), is_album_repeat(rfid_code) )
                else:
                    logger.warning (f'Folder {album_folder} does not exist.')
                    
        

          
         
def button_callback_16(channel):
    print("Previous Track Button was pushed!")
    aaplayer.prev_track()

def button_callback_15(channel):
    print("Play/Pause Button was pushed!")
    aaplayer.play_pause_track()
    
def button_callback_13(channel):
    print("Next Track Button was pushed!")
    aaplayer.next_track()

def start_rfid_reader():
    global APP_RUNNING
    
    #try:
    reader = SimpleMFRC522()
    existing_id = 0
  
    while APP_RUNNING:
        
        id, text = reader.read()
        
        if (existing_id != id):    
            print("Place a new tag on the reader.")
            existing_id = id
            logger.info(f'RFID Read: {id}')
            #print(text)
            handle_rfid_read(id)


def start_button_controls():
    GPIO.setwarnings(False) # Ignore warning for now
    GPIO.setmode(GPIO.BOARD ) # Use physical pin numbering
    GPIO.setup(16, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # Set pin 10 to be an input pin and set initial value to be pulled low (off)
    GPIO.setup(15, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # Set pin 10 to be an input pin and set initial value to be pulled low (off)
    GPIO.setup(13, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # Set pin 10 to be an input pin and set initial value to be pulled low (off)



    GPIO.add_event_detect(16,GPIO.RISING,callback=button_callback_16, bouncetime=200) # Setup event on pin 10 rising edge
    GPIO.add_event_detect(15,GPIO.RISING,callback=button_callback_15, bouncetime=200) # Setup event on pin 10 rising edge
    GPIO.add_event_detect(13,GPIO.RISING,callback=button_callback_13, bouncetime=200) # Setup event on pin 10 rising edge



def main():
    global DB, APP_RUNNING
    
    #try:
    # Load the database of RFID tags and their matching albums
    DB = load_database()

    #with pd.option_context('display.max_rows', None, 'display.max_columns', None):  # more options can be specified also
    print(DB)

    

    # Set up the event handlers for the button controls
    start_button_controls()


    #set up the muisc player
    aaplayer.startup()

    reader = SimpleMFRC522()
    existing_id = 0
  
    logger.debug('Starting RFID Reader')
    print("Place a new tag on the reader.")
    
    try:
        while APP_RUNNING:
            
            rfid_code = reader.read_id_no_block()
        
            if (rfid_code != existing_id and rfid_code != None):  
                #logger.debug(f'Recieved RFID {rfid_code}')  
                existing_id = rfid_code
                logger.info(f'RFID Read: {rfid_code}')
                #print(text)
                handle_rfid_read(rfid_code)
        
            aaplayer.keep_playing()
            time.sleep(.2)
        logger.debug('APP_RUNNING = False While Loop Completed. RFID Reader')
    except KeyboardInterrupt:
       
    # wait until the user hits exit
        #message = input("Press enter to quit\n\n") # Run until someone presses enter
    
        #finally:
        logger.debug('Recieved CTRL-C - Shutting down')
        print("Cleaning up...")
        #rfidthread.stop
        #musicplayerthread.stop
        APP_RUNNING = False
        #rfidthread.join()
        time.sleep(.3)
        logger.debug('Shutting down buttons and RFID - GPIO.cleanup()')

        GPIO.cleanup() # Clean up
        try:
            logger.debug('Shutting down player - aaplayer.shutdown_player())')
            
            aaplayer.shutdown_player()
        finally:
            print("Program complete.")
            logger.debug('Program Complete.')
            sys.exit()



main()
    



