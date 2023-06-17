import os
from urllib.parse import urlparse, parse_qs
from yt_dlp import YoutubeDL
import pandas as pd
import pl7 as aaplayer
import RPi.GPIO as GPIO # Import Raspberry Pi GPIO library  
from gpiozero import Button
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
formatter = logging.Formatter('%(asctime)s -- %(message)s -- %(funcName)s %(lineno)d')
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

DB_CACHE_FOLDER = CONFIG.DB_CACHE_LOCATION

DB_CACHE = DB_CACHE_FOLDER + "dbcache.csv"


#### COMMANDS

"""
Stops all playback, resets the player, reloads the database
"""
STOP_AND_RELOAD_DB = CONFIG.STOP_AND_RELOAD_DB 

"""
Shuts down the application and exits.
"""
SHUT_DOWN_APP = CONFIG.SHUT_DOWN_APP

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

"""
This is used to deal with hardware duplicate button pushes and RF bleed between GPIO pins.
"""
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
        logging.debug(f'Debounced {channel}')
        return False


"""def load_database():
    
    
    #At app start look for the cached DB
    
    #if you find it load it.
    
    #if you don't find it, load it from the web and save it
    
    
    
    
    DB_LOADED = False
    
    while not DB_LOADED:
        try:
            logging.debug("Attempting to load the DB from the internet.")
            db_url = f'https://docs.google.com/spreadsheets/d/{DB_SHEET_ID}/gviz/tq?tqx=out:csv&sheet={DB_SHEET_NAME}'

            logger.info(f'DB URL: {db_url}s')
            # Read the spreadsheet
            
            loaded_db = pd.read_csv(db_url)
            logging.debug("SUCCESS! The mixer loaded.")
            DB_LOADED = True
            return loaded_db
        except:
            logging.debug("DB load failed. Retrying in 3 seconds.")
            time.sleep(3)
    """
     
     
def load_database(LOAD_FROM_WEB):
    
    
    DB_LOADED = False
    
    if not LOAD_FROM_WEB:
        if os.path.exists(DB_CACHE):
            logging.debug(f'Attempting to load the DB from {DB_CACHE}')
            loaded_db = pd.read_csv(DB_CACHE)
            logging.debug("SUCCESS! DB loaded from cache.")
            DB_LOADED = True
            return loaded_db
        else:
            logging.debug("No Cached DB available. Attempting to load from web.")
            

    while not DB_LOADED:
        try:
            logging.debug("Attempting to load the DB from the internet.")
            db_url = f'https://docs.google.com/spreadsheets/d/{DB_SHEET_ID}/gviz/tq?tqx=out:csv&sheet={DB_SHEET_NAME}'

            logger.info(f'DB URL: {db_url}s')
            # Read the spreadsheet
        
            loaded_db = pd.read_csv(db_url)
            logging.debug("SUCCESS! The DB loaded from the web.")
            
            backup_cache()
            loaded_db.to_csv(DB_CACHE, index=False)
                
            DB_LOADED = True
            return loaded_db
        except:
            #logging.debug(f'An exception occurred: {str(e)}')
            logging.debug("DB load failed. Retrying in 3 seconds.")
            time.sleep(3)

            
        
    
def backup_cache():
    logging.debug(f'Attempting to backup existing cache {DB_CACHE}')
    if os.path.exists(DB_CACHE):
        # Create a timestamp for the backup file name
       
        current_time = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())
        milliseconds = int((time.time() - int(time.time())) * 1000)

        current_datetime_with_ms = f"{current_time}-{milliseconds:03d}"
    
        # Backup the existing file with a timestamp in the file name
        backup_path = f'{DB_CACHE}_backup_{current_datetime_with_ms}.csv'
        os.rename(DB_CACHE, backup_path)
        logging.debug(f'Backed upexisting cache to {backup_path}')
    else:
        logging.debug(f'No cache file found at {DB_CACHE} to backup. ')
    

        
"""
Checks to see if it recieved a command card. If it did, it executes the command provided by the ccard
    
"""
def command_card_handler(rfid_code):
    global DB, STOP_AND_RELOAD_DB, SHUT_DOWN_APP, APP_RUNNING
    command_code = str(rfid_code)
    
    if (command_code == STOP_AND_RELOAD_DB ):
        logger.debug('Executing Command Card Stop Player & Reload Database')
        DB = load_database(True)
        aaplayer.shutdown_player()
        aaplayer.startup()
        return True
    elif (command_code == SHUT_DOWN_APP ):
        logger.debug('Read RFID to shutdown application')
        APP_RUNNING = False
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
        
        #logger.debug(f'Found {result_column}: {result_value}s')
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
    if (my_interrupt_handler(channel)):
        logger.info("Previous Track Button was pushed!")
        aaplayer.prev_track()

def button_callback_15(channel):
    if (my_interrupt_handler(channel)):
        logger.info("Play/Pause Button was pushed!")
        aaplayer.play_pause_track()
    
def button_callback_13(channel):
    if (my_interrupt_handler(channel)):
        logger.info("Next Track Button was pushed!")
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
    """GPIO.setwarnings(False) # Ignore warning for now
    GPIO.setmode(GPIO.BOARD ) # Use physical pin numbering
    
    if (CONFIG.BUTTON_HIGH):
    
        GPIO.setup(16, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # Set pin 10 to be an input pin and set initial value to be pulled low (off)
        GPIO.setup(15, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # Set pin 10 to be an input pin and set initial value to be pulled low (off)
        GPIO.setup(13, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # Set pin 10 to be an input pin and set initial value to be pulled low (off)

        GPIO.add_event_detect(16,GPIO.RISING,callback=button_callback_16, bouncetime=200) # Setup event on pin 10 rising edge
        GPIO.add_event_detect(15,GPIO.RISING,callback=button_callback_15, bouncetime=200) # Setup event on pin 10 rising edge
        GPIO.add_event_detect(13,GPIO.RISING,callback=button_callback_13, bouncetime=200) # Setup event on pin 10 rising edge
    else:
        GPIO.setup(16, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Set pin 10 to be an input pin and set initial value to be pulled low (off)
        GPIO.setup(15, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Set pin 10 to be an input pin and set initial value to be pulled low (off)
        GPIO.setup(13, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Set pin 10 to be an input pin and set initial value to be pulled low (off)

        GPIO.add_event_detect(16,GPIO.FALLING,callback=button_callback_16, bouncetime=200) # Setup event on pin 10 rising edge
        GPIO.add_event_detect(15,GPIO.FALLING,callback=button_callback_15, bouncetime=200) # Setup event on pin 10 rising edge
        GPIO.add_event_detect(13,GPIO.FALLING,callback=button_callback_13, bouncetime=200) # Setup event on pin 10 rising edge
        
    """   
    button16 = Button("BOARD16")
    button15 = Button("BOARD15")
    button13 = Button("BOARD13")


    button16.when_pressed = button_callback_16
    button15.when_pressed = button_callback_15
    button13.when_pressed = button_callback_13



def main():
    global DB, APP_RUNNING
    
    #try:
    # Load the database of RFID tags and their matching albums
    DB = load_database(False)

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

    #GPIO.cleanup() # Clean up
    
    try:
        logger.debug('Shutting down player - aaplayer.shutdown_player())')
        
        aaplayer.shutdown_player()
    finally:
        print("Program complete.")
        logger.debug('Program Complete.')
        sys.exit()



main()
    



