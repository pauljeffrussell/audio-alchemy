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
import random
import time
import configfile as CONFIG
import requests
import subprocess
import numpy as np
from dateutil.parser import parse
from datetime import datetime, timedelta
import smtplib
from email.message import EmailMessage
from email.header import Header
from email.mime.text import MIMEText


"""
#################################################################################

            Logger 

#################################################################################"""

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

"""
#################################################################################

            Global Variables 

#################################################################################"""


#LIBRARY_CACHE_FOLDER = "/home/matt/dev/library/"
## This is where all the audio files for the albums are stored
LIBRARY_CACHE_FOLDER = CONFIG.LIBRARY_CACHE_FOLDER

DB_SHEET_ID = CONFIG.DB_SHEET_ID
DB_SHEET_NAME = CONFIG.DB_SHEET_ID

## This is the in memory version of the Catalog of albums
DB = pd.DataFrame()

# This is the in memory version of the album of the day cache
DB_AOTD_CACHE = pd.DataFrame()

APP_RUNNING = True

## This is the fiel I use to cache the DB so I don't 
## have to get it from the web every time.
DB_CACHE = CONFIG.DB_CACHE_LOCATION + "dbcache.csv"

## This is where the album of the day cache
## It stores the album of the day and we use that to keep 
## the album of the day from repeating too frequently.
FILE_AOTD_CACHE = CONFIG.DB_CACHE_LOCATION + "aotdcache.csv"

"""
## Used to calculate the number of days before an album can be chosed for
## album of the day after being selected. the equation is
## #of albums available for random selection * AOTD_REPEAT_LIMIT
## I did a bumch of testing and this creates a comfortable random feeling withot
## to frequent repeats. Here are some results from bulk testing I did.

    5000 Test Loops 
    13.698630136986301 Years of albums of the day 
    271 possible albums
    Minimum number of days between album repeat: 228

    18 played 20 times
    127 played 19 times
    90 played 18 times
    32 played 17 times
    3 played 16 times
    1 played 15 times


    300 Test Loops 
    0.8 Years of albums of the day 
    271 possible albums
    Minimum number of days between album repeat: 228

    54 played 2 times
    192 played 1 times
    25 played 0 times
"""
AOTD_REPEAT_LIMIT = .7


#### THESE ARE NEW
BLANK = 'BLANK'

SUPPORTED_EXTENSIONS = ['.mp3', '.MP3', '.wav', '.WAV', '.ogg', '.OGG']

BUTTON_HOLD_DURATION = CONFIG.BUTTON_HOLD_DURATION

#### COMMANDS

"""
This is used to deal with hardware duplicate button pushes and RF bleed between GPIO pins.
"""
LAST_BUTTON_TIME = 0

"""
Track if the last button push was to skip to the next album
"""
LAST_BUTTON_HELD = False


"""
Set to true when the current album has been shuffled using a card or holding the play button
"""
CURRENT_ALBUM_SHUFFLED = False

"""
THE CURRENT ALBUM OF THE DAY DATE.
We'll use this as a seed for pulling the album of the day.
"""
ALBUM_OF_THE_DAY_DATE = 0

"""
Matches the format of the Album of the day date. 
This value is sent when the email goes out. 
"""
ALBUM_OF_THE_DAY_LAST_EMAIL_DATE = 0


"""
The current album of the day rfid
"""
ALBUM_OF_THE_DAY_RFID = 0 



## This is the counter to see roughly how long has 
## past since the album of the day was sent
COUNTER_FOR_ALBUM_OF_THE_DAY = 0

## I want to check every hour so every 3600 seconds
## we'll check if it's time yet
CHECK_ALBUM_OF_THE_DAY_COUNT_LIMIT = 36000



"""
#################################################################################

           Initiallization - Database and Catalog and Main Loop

#################################################################################"""

def load_database(LOAD_FROM_WEB):
    global DB
    
    DB_LOADED = False
    
    if not LOAD_FROM_WEB:
        if os.path.exists(DB_CACHE):
            logging.debug(f'Attempting to load the DB from {DB_CACHE}')
            DB = pd.read_csv(DB_CACHE)
            logging.debug("SUCCESS! DB loaded from cache.")
            DB_LOADED = True
            
            DB['sub_genre'] = DB['sub_genre'].fillna(BLANK)
            DB['genre'] = DB['genre'].fillna(BLANK)
            DB['folder'] = DB['folder'].fillna(BLANK)
            DB['labels'] = DB['labels'].fillna(BLANK)
            
            
            return DB
        else:
            logging.debug("No Cached DB available. Attempting to load from web.")
            

    while not DB_LOADED:
        try:
            
            ## update the system data so that your call to google works.
            set_ststem_date()
            
            logging.debug("Attempting to load the DB from the internet.")
            db_url = f'https://docs.google.com/spreadsheets/d/{DB_SHEET_ID}/gviz/tq?tqx=out:csv&sheet={DB_SHEET_NAME}'
            logger.info(f'DB URL: {db_url}s')
            # Read the spreadsheet
        
            #logger.debug('This is the response for the URL.')
            #response = requests.get(db_url)

            
            #logger.debug(response)
            #logger.debug("\n\n")
        
            logger.debug('ready to read the csv from url.')
            DB = pd.read_csv(db_url)
            logging.debug("SUCCESS! The DB loaded from the web.")
            

            
            backup_cache(DB_CACHE)
            DB.to_csv(DB_CACHE, index=False)
            DB['sub_genre'] = DB['sub_genre'].fillna(BLANK)
            DB['genre'] = DB['genre'].fillna(BLANK)
            DB['folder'] = DB['folder'].fillna(BLANK)
            DB['labels'] = DB['labels'].fillna(BLANK)
            
            
            DB_LOADED = True
            return DB
        except Exception as e:
            logging.debug(f'An exception occurred:')
            logging.debug(str(e))
            logging.debug("DB load failed. Retrying in 3 seconds.")
            time.sleep(3)

def load_album_of_the_day_cache():
    """
    Loads the cache of previous Albums of the day from a file in the
    dbcache. 
    
    If it can't find the file it will create one.
    """
    global FILE_AOTD_CACHE
    
    # Check if file exists
    if not os.path.exists(FILE_AOTD_CACHE):
        # If not, create an empty DataFrame with specified columns
        empty_df = pd.DataFrame(columns=["date", "rfid", "album_name"])
        
        # Save the empty DataFrame to a CSV file
        empty_df.to_csv(FILE_AOTD_CACHE, index=False)
        print(f"{FILE_AOTD_CACHE} has been created with the specified columns.")
        
    # Read the contents into a DataFrame (whether the file initially existed or was just created)
    return pd.read_csv(FILE_AOTD_CACHE)

def update_aotd_cache(date, rfid, album_name):
    """
    Updates the in memory album of the day data frame and saves it to disk
    """
    global DB_AOTD_CACHE, FILE_AOTD_CACHE
    
    # Create a new DataFrame with the provided data
    # Create a new DataFrame with the provided data
    #new_data = pd.DataFrame([[date, rfid, album_name]])
    #new_data.columns = DB_AOTD_CACHE.columns
    
    new_data = pd.DataFrame({
        'date': [date],
        'rfid': [rfid],
        'album_name': [album_name]
    })
    #new_data.columns = DB_AOTD_CACHE.columns
    
    # Append the new data to the cache
    #newcache = DB_AOTD_CACHE.append(new_data, ignore_index=True)
    
    DB_AOTD_CACHE = pd.concat([DB_AOTD_CACHE, new_data], ignore_index=True)
    
    try:
        # Append the new data to the existing CSV file
        DB_AOTD_CACHE.to_csv(FILE_AOTD_CACHE, mode='w', header=True, index=False)
    except:
        logger.ERROR('Unable to save the Album of the Day CACHE to disk')

def set_ststem_date():
    """ 
    Because the system is read only, every time you reboot the system thinks the date is 
    June 17 2023 which is when OS was set to read only.
            
    Intenet requests to google to get the catalog will fail if the system date out of date
    """

    logging.debug('Starting set_ststem_date()')
    response = requests.get('http://worldtimeapi.org/api/timezone/America/New_York')
    data = response.json()

    # Parsing the datetime string
    dt = parse(data['datetime'])

    # Formatting date time as required by the 'date' command
    formatted_dt = dt.strftime("%Y-%m-%d %H:%M:%S")

    # Form the command
    cmd = f"date -s '{formatted_dt}'"

    logging.debug(f'Setting system date {cmd}')
    # Execute the command
    subprocess.run(['sudo', 'bash', '-c', cmd])    
    
def backup_cache(cache_file):
    logging.debug('Starting backup_cache().')
    logging.debug(f'Attempting to backup existing cache {cache_file}')
    if os.path.exists(cache_file):
        # Create a timestamp for the backup file name
       
        current_time = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())
        milliseconds = int((time.time() - int(time.time())) * 1000)

        current_datetime_with_ms = f"{current_time}-{milliseconds:03d}"
    
        # Backup the existing file with a timestamp in the file name
        backup_path = f'{cache_file}_backup_{current_datetime_with_ms}.csv'
        os.rename(cache_file, backup_path)
        logging.debug(f'Backed upexisting cache to {backup_path}')
    else:
        logging.debug(f'No cache file found at {cache_file} to backup. ')

def main():
    global DB, APP_RUNNING, ALBUM_OF_THE_DAY_DATE, ALBUM_OF_THE_DAY_LAST_EMAIL_DATE, DB_AOTD_CACHE
    
    #try:
    # Load the database of RFID tags and their matching albums
    DB = load_database(False)
    
    
    ## the read only OS thinks the date is June 2023 on reboot. In order for 
    ## album of the day to work properly, you need to fitch the current date
    ## and set the system time.
    set_ststem_date()



    ## Load the album of the day cache.
    ## If there isn't one, make one.
    ## This has to happen first, because we need the file to be there
    ## for the next step
    DB_AOTD_CACHE = load_album_of_the_day_cache()

   
    ## We set this at statup so that we don't send an email
    ## every time the system restarts restart the system. Album of the day will instead 
    ## be sent the day after the system is rebooted.
    set_album_of_the_day_date_and_rfid()
    ALBUM_OF_THE_DAY_LAST_EMAIL_DATE = ALBUM_OF_THE_DAY_DATE
      

    # Set up the event handlers for the button controls
    start_button_controls()


    #set up the muisc player
    aaplayer.startup()

    reader = SimpleMFRC522()
    
    ## The RFID the app thinks is current. This is reset to 0 if the 
    ## Reader doesn't see this card for some period. After it has stopped playing. 
    CURRRENT_RFID = 0
    
    ## A counter of the number of times the loop below happened
    ## when there was no card and the player wasn't playing
    COUNT_SINCE_CARD_REMOVED = 0
    
    LOOP_SLEEP_DURATION = .1
    
    
    ## The COUNT_SINCE_CARD_REMOVED is incremented every time the loop below
    ## doesn't find a card while the player isn't playing
    ##
    ## so LOOP_SLEEP_DURATION * NO_CARD_THREASHOLD is how long a card has to be 
    ## off the player when it's not playing for the player to treat it like a 
    ##  new card when you put it back on.
    NO_CARD_THREASHOLD = 8
    

 
  
    logger.debug('Starting RFID Reader')
    print("Place a new tag on the reader.")
    
    try:
        while APP_RUNNING:
            
            ## read the RFID from the reader
            rfid_code = reader.read_id_no_block()
        
            ## TAGS will only be read once 
            if (rfid_code != CURRRENT_RFID and rfid_code != None):  
                ## you just read a new card!!!
                CURRRENT_RFID = rfid_code
                logger.info(f'RFID Read: {rfid_code}')
                handle_rfid_read(rfid_code)
                COUNT_SINCE_CARD_REMOVED = 0
                
            elif (rfid_code == CURRRENT_RFID):
                ## You've already read this card but just in case there was a blip
                ## where the reader missed it for a second, lets remind the app
                ## that we can still see it.
                ##
                ## We reset the counter so that the card really has to be off the 
                ## devide for a duration of at least LOOP_SLEEP_DURATION * COUNT_SINCE_CARD_REMOVED
                COUNT_SINCE_CARD_REMOVED = 0
                
            elif (CURRRENT_RFID !=0 and rfid_code == None and not aaplayer.is_playing()):
                ## The card has been removed from the reader and
                ## the player is not playing
                COUNT_SINCE_CARD_REMOVED = COUNT_SINCE_CARD_REMOVED +1
                
                if COUNT_SINCE_CARD_REMOVED >= NO_CARD_THREASHOLD:
                    ## the card has been off the player for at least
                    ## LOOP_SLEEP_DURATION * COUNT_SINCE_CARD_REMOVED
                    ##
                    ## So we need to tell the app it's no longer the current
                    ## card so it will be treated as new the next time it is seen 
                    CURRRENT_RFID = 0



            aaplayer.keep_playing()
            
            
            
            ## This will tell the app to send an email once a day.
            ## all controlls for manaing when the email is sent
            ## are handled in the email_album_of_the_day() funciton
            if not aaplayer.is_playing():
                ## Only try emailing if the player 
                ## isn't playing. We don't want anything messing up the music
                check_album_of_the_day_email()
            
            
            
            time.sleep(LOOP_SLEEP_DURATION)
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




"""
#################################################################################

            Button Logic and Handlers

#################################################################################"""



def handle_rfid_read(rfid_code):
    global DB
    
    
    genre_card = lookup_field_by_field(DB, 'rfid', rfid_code, 'genre_card')

    label_card = lookup_field_by_field(DB, 'rfid', rfid_code, 'label_card')
    #except:
    #    logger.warning("Could not load genre or label card on RFID read.")
    
    if (command_card_handler(rfid_code) == True):
        ## You found a command card. It's been executed. Don't do anything else.
        logger.debug(f'Completed command card: {rfid_code}...')
        
    elif (genre_card == 1):
        ## this card is meant to play a genre instead of a specific album
        genre = lookup_field_by_field(DB, 'rfid', rfid_code, 'genre')
        sub_genre = lookup_field_by_field(DB, 'rfid', rfid_code, 'sub_genre')
        
        #get the list of all the folders from this genre
        genre_album_folder_list = get_albums_for_genre(genre, sub_genre, is_album_shuffle(rfid_code))
        
        tracks = get_tracks(genre_album_folder_list, is_song_shuffle(rfid_code))
        
        if (len(tracks) > 0):
            logger.debug (f'Album folder exists. Playing Genre')
            aaplayer.play_tracks(tracks, is_album_repeat(rfid_code) )   
            CURRENT_ALBUM_SHUFFLED = False
    
    elif (label_card == 1):
        #this card is a label card. It is intended to play all of the albums with a matching lable.
        label = lookup_field_by_field(DB, 'rfid', rfid_code, 'labels')
        label_album_folder_list = get_albums_for_label(label, is_album_shuffle(rfid_code))
        tracks = get_tracks(label_album_folder_list, is_song_shuffle(rfid_code))
        
        if (len(tracks) > 0):
            logger.debug (f'Album folder exists. Playing Genre')
            aaplayer.play_tracks(tracks, is_album_repeat(rfid_code) )
            CURRENT_ALBUM_SHUFFLED = False
    
    else:
        album_folder_name = lookup_field_by_field(DB, 'rfid', rfid_code, 'folder')
        logger.debug(f'Attemptting to play album: {album_folder_name}...')


        if album_folder_name != 0:

            album_folder = LIBRARY_CACHE_FOLDER + album_folder_name
        
        
            tracks = get_tracks([album_folder], is_song_shuffle(rfid_code))

            if (len(tracks) > 0):
                logger.debug (f'Album has tracks. Playing...')
                aaplayer.play_tracks(tracks, is_album_repeat(rfid_code) )
                CURRENT_ALBUM_SHUFFLED = False
            else:
                logger.warning (f'No tracks found for folder {album_folder}.')    
        else:
            logger.warning(f'RFID {rfid_code} is unknown to the app. Consider adding it to the DB...')
            

def command_card_handler(rfid_code):
    """
    Checks to see if it recieved a command card. 
    If it did, this function will execute the command
    """
    global DB, APP_RUNNING
    command_code = str(rfid_code)
    
    if (command_code == CONFIG.COMMAND_PLAY_ALBUM_OF_THE_DAY):
        logger.debug('Playing Album of the day.')
        play_album_of_the_day()
        CURRENT_ALBUM_SHUFFLED = False
        return True 
    elif (command_code == CONFIG.COMMAND_STOP_AND_RELOAD_DB ):
        logger.debug('Executing Command Card Stop Player & Reload Database')
        DB = load_database(True)
        aaplayer.shutdown_player()
        aaplayer.startup()
        CURRENT_ALBUM_SHUFFLED = False
        return True
    elif (command_code == CONFIG.COMMAND_SHUT_DOWN_APP ):
        logger.debug('Read RFID to shutdown application')
        APP_RUNNING = False
        return True
    elif (command_code == CONFIG.COMMAND_PLAY_RANDOM_ALBUMS ):
        logger.debug('Read RFID to play random albums')
        play_random_albums()
        CURRENT_ALBUM_SHUFFLED = False
        return True 
    elif (command_code == CONFIG.COMMAND_PLAY_IN_ORDER_FROM_RANDOM_TRACK):
        logger.debug('Read RFID to play in order from a random track')
        aaplayer.play_in_order_from_random_track()
        return True 
    else:
        return False
    
    
def start_button_controls():
 
    button16 = Button("BOARD16")
    button15 = Button("BOARD15")
    button13 = Button("BOARD13")


    #button16.when_pressed = button_callback_16
    #button15.when_pressed = button_callback_15
    #button13.when_pressed = button_callback_13


    ## Previous button
    button16.when_released = button_callback_16
    button16.hold_time = BUTTON_HOLD_DURATION
    button16.when_held = button_backward_held_callback
    
    ## Play Pause Button
    button15.when_released = button_callback_15
    button15.hold_time = BUTTON_HOLD_DURATION
    button15.when_held = button_shuffle_current_songs
    
    ## Next Button
    button13.when_released = button_callback_13
    button13.hold_time = BUTTON_HOLD_DURATION
    button13.when_held = button_forward_held_callback

           
def button_callback_16(channel):
    
    # make sure to debounce partial button pushes AND
    # skip this button release if the last button push was held down. 
    if (my_interrupt_handler(channel) and not last_button_held()):
        logger.info("Previous Track Button was pushed!")
        aaplayer.prev_track()


def button_callback_15(channel):
    
    # make sure to debounce partial button pushes AND
    # skip this button release if the last button push was held down.
    if (my_interrupt_handler(channel) and not last_button_held()):
        logger.info("Play/Pause Button was pushed!")
        aaplayer.play_pause_track()

    
def button_callback_13(channel):
    
    # make sure to debounce partial button pushes AND
    # skip this button release if the last button push was held down.
    if (my_interrupt_handler(channel) and not last_button_held()):
        logger.info("Next Track Button was pushed!")
        aaplayer.next_track()
        
        
def button_forward_held_callback(channel):
    global LAST_BUTTON_HELD
    LAST_BUTTON_HELD = True
    logger.info("SKIP TO NEXT ALBUM!")
    aaplayer.jump_to_next_album()
 
    
def button_backward_held_callback(channel):
    global LAST_BUTTON_HELD
    LAST_BUTTON_HELD = True
    logger.info("SKIP TO PREVIOUS ALBUM!")
    aaplayer.jump_to_previous_album()
 
    
def button_shuffle_current_songs(channel):
    global LAST_BUTTON_HELD, CURRENT_ALBUM_SHUFFLED
    LAST_BUTTON_HELD = True
    
    if CURRENT_ALBUM_SHUFFLED == False:
        logger.info("Suffle Current tracks!")
        aaplayer.shuffle_current_songs()
        CURRENT_ALBUM_SHUFFLED = True
    else:
        logger.info("Unshuffle current tracks!")
        aaplayer.unshuffle_current_songs()
        CURRENT_ALBUM_SHUFFLED = False
    

def last_button_held():
    """
    Returns: True if the last button action was a held button.      
    """
    global LAST_BUTTON_HELD
    
    current_value = LAST_BUTTON_HELD
    LAST_BUTTON_HELD = False
    return current_value
    
    
    
    


def my_interrupt_handler(channel):
    """
    Called whenever a button push is detected. Makes sure that 
    it was an actual button press instead of electrical jitter
    happening faster than bruce lee could have pushed the button 
    twice.
    
    Returns: True if it's a valid button push. Flase if it's invalid.    
    """
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


"""
#################################################################################

            Catalog Lookup Functions

#################################################################################"""

        

def lookup_field_by_field(df, search_column, search_term, result_column):
    """
    Finds a given value in a given column of the DB and returns the value from another column in that row.

    Parameters:
    - search_column: The column header for the field to search.
    - search_term: The term to search for in the search column.
    - result_column: The name of the column from which to return a result.

    Returns:
    string The value from column result_column in the row where search_term was found in search_column
    """
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
        
        
        
        
def replace_non_strings(variable):
    """
    This is a helper function used with lookup_field_by_field
    
    Sometimes the pandas DB sends back results that aren't strings even though
    we're expecting strtings. When that happens all hell breaks loose.
    
    So this function is passed something we want to be a sting and deals with it.
    
    Attributes:
    - variable: any variable you want confirmed is a string.
    
    Returns: 
    String: either the variable if it''s a string, or an empty string.
    """
    if isinstance(variable, str):
       return variable
    else:
        return ""
        
       
def is_song_shuffle(rfid_code):
    """
    Detremines if the songs for the given card should be shuffled
    
    Attributes:
    - rfid_code: an RFID code for a card

    Returns:
    Boolean: True if the song is set to shuffle. False otherwise.            
    """
    global DB
    
    suffle_songs = lookup_field_by_field(DB, 'rfid', rfid_code, 'shuffle_songs')  
    if suffle_songs == 1:
        return True
    else:
        return False
        

def is_album_shuffle(rfid_code):
    """
    Detremines if the albums for a label or genre card should be shuffled.
    If Ture, it means the order of the albums will change, but the songs should 
    still play in order. If you want to find out if songs should shuffle. 
    Seeis_song_shuffle(rfid_code)
    
    Attributes:
    - rfid_code: an RFID code for a card

    Returns:
    Boolean: True if the albums are set to shuffle. False otherwise.            
    """
    global DB
    
    suffle_album = lookup_field_by_field(DB, 'rfid', rfid_code, 'shuffle_albums')  
    if suffle_album == 1:
        return True
    else:
        return False
        
         
def is_album_repeat(rfid_code):
    """
    Detremines if the album should repeat or not.
    
    Attributes:
    - rfid_code: an RFID code for a card

    Returns:
    Boolean: True if the albums should repeat. False otherwise.            
    """
    global DB
    
    repeat = lookup_field_by_field(DB, 'rfid', rfid_code, 'repeat')  
    if repeat == 1:
        return True
    else:
        return False


def get_albums_for_genre(genre, sub_genre, shuffle_albums):
    """
    Returns: a list of the paths to the library folders that match the provided genre and sub_genre    
    """
          
    if (len(genre) != 0 and len(sub_genre) != 0):      
        condition = "genre == '" + genre + "' and sub_genre == '" + sub_genre + "'"   
        logger.debug(f'Looking up tracks for genre: {genre}:{sub_genre}...')   
    elif (len(genre) == 0 and len(sub_genre) != 0):     
        condition = "sub_genre == '" + sub_genre + "'"
        logger.debug(f'Looking up tracks for sub genre: {sub_genre}...') 
    elif (len(genre) != 0 and len(sub_genre) == 0): 
        condition = "genre == '" + genre + "'"
        logger.debug(f'Looking up tracks for genre: {genre}...') 
    else:
        condition = "genre == '" + BLANK + "' and sub_genre == '" + BLANK + "'"
        logger.debug('Looking up tracks for genre: '+BLANK+':'+BLANK )  
        
        ## add this so the app doesn't choke if the folder for the genre tag is empty
        condition = condition + " and folder != '" +  BLANK + "'"
        
    logger.debug(f'Attemptting to play: {condition}...')

    # Use the query method to filter the DataFrame and extract the 'folder' column
    matching_folders = DB.query(condition)['folder']

    # Convert the matching folders to a list
    matching_folders_list = matching_folders.tolist()
    
    if(shuffle_albums):
        random.shuffle(matching_folders_list)
    else:
        matching_folders_list.sort()
    
    matching_folders_list = [LIBRARY_CACHE_FOLDER + folder for folder in matching_folders_list]

    return matching_folders_list


def get_albums_for_label(label, shuffle_albums):

    logger.debug(f'Looking up albums with label: {label}...')

    #matching_rows = DB[DB['labels'].apply(lambda x: label in x)]
    matching_rows = DB[DB['labels'].astype(str).str.contains(label)]
    #DB.query(condition)['folder']
    matching_folders = matching_rows.query("folder != '"+BLANK+"'")['folder']
    
    # Convert the matching folders to a list
    matching_folders_list = matching_folders.tolist()
        
    if(shuffle_albums):
        random.shuffle(matching_folders_list)
    else:
        matching_folders_list.sort()
    
    matching_folders_list = [LIBRARY_CACHE_FOLDER + folder for folder in matching_folders_list]

    return matching_folders_list


def get_random_rfid_value():
    """
    Returns: A random RFID out of the catalog database
    """
    global DB
    rfid = BLANK
    
    while rfid == BLANK or isinstance(rfid, float) or not str(rfid).isdigit():
        random_index = np.random.choice(DB.index)
        rfid = DB.loc[random_index, 'rfid']
    
    #print(f'Found rfid: {rfid}')
    return rfid


def get_tracks(folders, shuffle_tracks):
    """
    Gets the tracks for a list of folders
    
    Parameters: 
    - folders: an array of folders that thoretircally contain music files
    - shuffle_tracks: True if the tracks should be shuffled. False if they should not
    
    Returns: A list of the full path to tracks for a list of folders. 
             If  shuffle_tracks == True, the resulting list of tracks 
            will be randomly shuffled.
    """
    global SUPPORTED_EXTENSIONS
    
    all_tracks = []
    
    #shuffle the albums so we don't always start with the same album
    #random.shuffle(folders)
    
    for folder in folders:
        #folder_path = os.path.join(base_folder_path, folder)  # Assuming a base folder path
    
        if os.path.exists(folder):
            logger.debug(f'Getting files for {folder}...')
            album_songs = [os.path.join(folder, f) for f in os.listdir(folder) if os.path.splitext(f)[1] in SUPPORTED_EXTENSIONS]
            album_songs.sort()
            all_tracks.extend(album_songs)
        
    if(shuffle_tracks == True):
        random.shuffle(all_tracks)  
    
    
    #print (all_tracks)
    for mp3_file in all_tracks:
        logger.debug(f'Found Track: {mp3_file}...') 

    return all_tracks   





"""
#################################################################################

            Album of the day & Random Albums Mechanics

#################################################################################"""

def play_album_of_the_day():
    global DB, ALBUM_OF_THE_DAY_RFID
    
    #found_rfid = get_album_of_the_day_rfid()
    
    set_album_of_the_day_date_and_rfid()
    
    album_folder_name = lookup_field_by_field(DB, 'rfid', ALBUM_OF_THE_DAY_RFID, 'folder')
    logger.debug(f'Attemptting to load album: {album_folder_name}...')
    album_folder = LIBRARY_CACHE_FOLDER + album_folder_name

    
    tracks = get_tracks([album_folder], False)
    if (len(tracks) > 0):
        foo = 3
        logger.debug (f'Album has tracks. Playing...')
        aaplayer.play_tracks(tracks, False )
    else:
        logger.warning (f'No tracks found for folder {album_folder}.')

    return tracks
    

def set_album_of_the_day_date_and_rfid():
    """ 
    If it's a new day then this funciton

        1. Sets the global ALBUM_OF_THE_DAY_DATE which is used as a seed for looking up the RFID.
        2. Sets the global ALBUM_OF_THE_DAY_RFID   
        3. returns true so we know it's a new day

    If it's not a new day it returns false
            
            
    This way we can update the DB as much as we want and the album of the 
    day will always be the same after the first time we email or play the 
    album.
            
    Of course, if we kill the app, then we're starting all over.
    
    Note: This was the old def get_album_of_the_day_rfid(): 

    """
    global DB, ALBUM_OF_THE_DAY_DATE, ALBUM_OF_THE_DAY_RFID
    rfid = BLANK
    
    #use today's date YYYYMMDD as the seed for pulling random albums
    # the goal is to get the same answer all day
    todays_seed = get_album_of_the_day_seed() 
    logger.debug(f'Looking up album for today: {todays_seed}...')
    
    if ALBUM_OF_THE_DAY_DATE == todays_seed:
        # the date and RFID were already set
        
        # return false so they know there's not a new album of the day.
        return False
    else:
        """
        This was the old logic before we started using the album of the day cache
        
        # Set the seed with today's date so we always get the same answer
        np.random.seed(todays_seed)
    
        ## don't use rows with a 1 in the 
        filtered_df = DB[DB['exclude_from_random'] != 1]
    
        ## get a pile of results so at least one of them doesn't get excluded
        sample_size = min(len(filtered_df), 50)
    
        todays_rfid_list = filtered_df.sample(n=sample_size, random_state=todays_seed)['rfid'].tolist()
    

        #found_rfid = None  # This will store the found rfid value


        #check throgh the list of RFIDs for one that is approved
        for rfid in todays_rfid_list:
            if rfid == BLANK or isinstance(rfid, float) or not str(rfid).isdigit():
                continue
            else:
                ALBUM_OF_THE_DAY_RFID = rfid  # Store the rfid that passed the check
                ALBUM_OF_THE_DAY_DATE = todays_seed # store the current album of the day date/seed
                return True
         """
        rfid = get_album_of_the_day_rfid(todays_seed)
        
        ALBUM_OF_THE_DAY_RFID = rfid  # Store the rfid that passed the check
        ALBUM_OF_THE_DAY_DATE = todays_seed # store the current album of the day date/seed
        
        folder = replace_non_strings(lookup_field_by_field(DB, "rfid", rfid, "folder"))
        
        if check_aotd_cache_for_today(todays_seed) == None:
            ## We appear to have't saveded the album of the day in the cache. 
            ## I guess this is our first time doing this. 
            update_aotd_cache(todays_seed, rfid, folder)
            
        return True
               
                
def get_album_of_the_day_seed():
    return int(datetime.today().strftime('%Y%m%d'))


def check_album_of_the_day_email():
    """
    This function determines if it's time to send the album of the day email.
    If it is, and it hasn't been sent yet, it calls the function to send
    the email.
    """
    global COUNTER_FOR_ALBUM_OF_THE_DAY, CHECK_ALBUM_OF_THE_DAY_COUNT_LIMIT, ALBUM_OF_THE_DAY_DATE, ALBUM_OF_THE_DAY_RFID, ALBUM_OF_THE_DAY_LAST_EMAIL_DATE

    #logger.info(f'Checking email of the day... current count: {COUNTER_FOR_ALBUM_OF_THE_DAY}')

    ## first see if it's been long enough
    if COUNTER_FOR_ALBUM_OF_THE_DAY < CHECK_ALBUM_OF_THE_DAY_COUNT_LIMIT:
        ## We haven't looped enough times yet 
        COUNTER_FOR_ALBUM_OF_THE_DAY = COUNTER_FOR_ALBUM_OF_THE_DAY + 1
    else:
        ## It's been long enough, lets see if we need to send an email
        
        # Start by resetting the counter so that we start the loop over 
        # and come back in a bit no matter what.         
        COUNTER_FOR_ALBUM_OF_THE_DAY = 0
        
        #make sure the album of the day is up to date.
        set_album_of_the_day_date_and_rfid()
        
        
        #new_seed = get_album_of_the_day_rfid()

        if ALBUM_OF_THE_DAY_LAST_EMAIL_DATE != ALBUM_OF_THE_DAY_DATE:
            ## We haven't send an email today
            ## but we don't want to send the email before 4am
            if is_past_send_time():         
                ## It's a new day and past 4am!!!
                logger.info(f'New Album of the day available. Seed: {ALBUM_OF_THE_DAY_DATE}')
                
                ## let's record that we've now sent an email today
                ALBUM_OF_THE_DAY_LAST_EMAIL_DATE = ALBUM_OF_THE_DAY_DATE

                # and lets send the email
                send_album_of_the_day_email(ALBUM_OF_THE_DAY_RFID)
            else:
                hour = datetime.now().hour
                logger.info(f'New Album of the day available. BUT its not 4am yet. Current hour{hour}')
                COUNTER_FOR_ALBUM_OF_THE_DAY = 0

       
def is_past_send_time():
    # Get the current hour
    current_hour = datetime.now().hour
    
    # Check if current hour is past 5 AM
    return current_hour >= 3


def send_album_of_the_day_email(rfid):    
    
    logger.info(f'Sending an album of the day email...')
    
    
    album_name = replace_non_strings(lookup_field_by_field(DB, 'rfid', rfid, 'Album'))
    album_folder_name = replace_non_strings(lookup_field_by_field(DB, 'rfid', rfid, 'folder'))
    artist_name = replace_non_strings(lookup_field_by_field(DB, 'rfid', rfid, 'Artist'))
    album_url = replace_non_strings(lookup_field_by_field(DB, 'rfid', rfid, 'url'))
    

    body = f"""Today's album of the day is:<br><br>
    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"""
    
    if album_url != "":
        body = body + f'<a href="{album_url}">'
    
    body = body + f"""<b style="font-size: 2em;">{album_name}"""
    if album_url != "":
        body = body + f'</a>'
    
    if (artist_name != "" or artist_name == "Various Artists"):
        body = body + "<BR>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;by " + artist_name
        
    if album_url != "":
        body = body + f'</a>'

        
    body = body + f"""</b><BR><BR><BR><BR>
    <div style="font-size: smaller; color: grey;">Use the hammer to play the album.</div>"""
    
    
    
    # Email settings
    SMTP_SERVER = 'smtp.gmail.com'
    SMTP_PORT = 587
    SENDER_EMAIL = CONFIG.EMAIL_SENDER_ADDRESS  # Change this to your Gmail
    SENDER_PASSWORD = CONFIG.EMAIL_SENDER_PASSWORD      # Change this to your password or App Password

    # Create the message
    msg = EmailMessage()
    
    
    
    #msg.set_content(f"Today's date is {datetime.now().strftime('%Y-%m-%d')}")
    
    msg = MIMEText(body, 'html') 
    
    #msg['From'] = Header(f'{CONFIG.EMAIL_SENDER_NAME} <{CONFIG.EMAIL_SENDER_ADDRESS}>', 'utf-8')  # Set sender name here
    
                      
    msg['Subject'] = album_name
    msg['From'] = CONFIG.EMAIL_SENDER_NAME
    msg['To'] = CONFIG.EMAIL_SEND_TO  # The receiver's email

    #print("Subject ", msg['Subject'])

    # Send the email
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.starttls()  # Upgrade the connection to secure encrypted SSL/TLS connection
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)
            logger.info(f'Email sent successfully!')
    except Exception as e:
        print(f"Error occurred: {e}")


def play_random_albums():
    """
        Gets CONFIG.RANDOM_ALBUMS_TO_PLAY from the DB as long as they are labeled with 
        'random' and the plays them.
    """
    global DB
    
    album_rfid_list = []
    
    
    """while len(album_rfid_list) <= CONFIG.RANDOM_ALBUMS_TO_PLAY -1:
        ## get another album
        rfid = get_random_rfid_value()
        labels = lookup_field_by_field(DB, 'rfid', rfid, 'labels')
        if 'random' in labels and rfid not in album_rfid_list:
            album_rfid_list.append(rfid)
        else:
            print("Found a non random album.")"""
    
    ## replaced the above code to skip albums labled norandom instead of 
    ## requiring the albums be labled with "random"
    while len(album_rfid_list) <= CONFIG.RANDOM_ALBUMS_TO_PLAY -1:
        logger.debug(f'Looking for an rfid...') 
        ## get another album
        rfid = get_random_rfid_value()
        logger.debug(f'Past getting rfid...') 
        
        exclude_from_random = lookup_field_by_field(DB, 'rfid', rfid, 'exclude_from_random')
        if exclude_from_random == 1:
            logger.debug(f'Found a album marked for skipping random selection.". Skipping...')
        elif rfid not in album_rfid_list:
            logger.debug(f'Appending rfid {rfid}')
            album_rfid_list.append(rfid)
        else:
             logger.debug(f'Found a rfid already added to the list. Skipping...')

    album_folder_list = []

    for rfid in album_rfid_list:
        album_folder_name = lookup_field_by_field(DB, 'rfid', rfid, 'folder')
        logger.debug(f'Attemptting to load album: {album_folder_name}...')

        if album_folder_name != 0:
            album_folder = LIBRARY_CACHE_FOLDER + album_folder_name
            album_folder_list.append(album_folder)
        
    tracks = get_tracks(album_folder_list, False)
    if (len(tracks) > 0):
        logger.debug (f'Album has tracks. Playing...')
        aaplayer.play_tracks(tracks, False)
    else:
        logger.warning (f'No tracks found for folder {album_folder}.')

    return tracks


def get_album_of_the_day_rfid(seed_for_random_lookup=get_album_of_the_day_seed()):
    """
        pulls a random RFID out of the database making sure it's hasn't been the album of 
        the day reciently
    """
    global DB, DB_AOTD_CACHE, AOTD_REPEAT_LIMIT
    rfid = BLANK
    
    seed_for_random_lookup = int(seed_for_random_lookup)
    
    
    ## Let's see if there already was an album of the day
    
    found_rfid = check_aotd_cache_for_today(seed_for_random_lookup)  # This will store the found rfid value
    
    if found_rfid != None:
        ## We appear to have already saved the album of the day in the cache. So no need to look it up again. 
        return found_rfid
    
    
    ## Load the x previous albums of the day
    try:
        aotd_block_list = DB_AOTD_CACHE.tail(int(len(DB)*AOTD_REPEAT_LIMIT))
    except (FileNotFoundError, pd.errors.EmptyDataError):
        # If the albumoftheday.csv file is not found or empty, then all albums in catalog are available
        aotd_block_list = pd.DataFrame(columns=DB_AOTD_CACHE.columns)  # Empty DataFrame with same columns
        logger.DEBUG(f'Found no blocked albums. Created blank list')
    
    
    # Filter the catalog DataFrame to only include rows where the album name is not in the last 30 of albumoftheday
    #available_albums = catalog_df[~catalog_df['Album Name'].isin(last_30_albums['Album Name'])]
    available_albums = DB[(~DB['rfid'].isin(aotd_block_list['rfid'])) & (DB['exclude_from_random'] != "1")]
    
    
    sample_size = len(available_albums)
    
    #logger.debug(f'Available album list has {sample_size} albums.')
    
    
    todays_rfid_list = available_albums.sample(n=sample_size, random_state=seed_for_random_lookup)['rfid'].tolist()
    

    # This was replaced by the above code.
    # found_rfid = None  # This will store the found rfid value

    for rfid in todays_rfid_list:
        if rfid == BLANK or isinstance(rfid, float) or not str(rfid).isdigit():
            continue
        else:
            found_rfid = rfid  # Store the rfid that passed the check
            break
    
    #print (found_rfid)
    return found_rfid


def check_aotd_cache_for_today(date_to_check):
    """
    Checks the album of the day cache to see if we've already saved today's
    album of the day. 
    
    Returns: the album of the day rfid if the date matches. None otherwise
    """
    global DB_AOTD_CACHE
    
    if not DB_AOTD_CACHE.empty:
        last_date = DB_AOTD_CACHE['date'].iloc[-1]
    else:
        last_date = None
    
    if last_date == date_to_check:
        logger.debug("Found album of the day in the cache.")
        return DB_AOTD_CACHE['rfid'].iloc[-1]
    else:
        return None



"""
#################################################################################

            Old Code you should purge after 2023-09-02

#################################################################################"""
""" If this is still here after 2023-09-02 and you're not fixing a bug, you can delete it.
    Originally commented out 2023-08-22 I'm pretty sure this hasn't been used in months.
                   
def handle_rfid_read_old(rfid_code):
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
                aaplayer.play_folder( album_folder, is_song_shuffle(rfid_code), is_album_repeat(rfid_code) )
            else:
                logger.warning (f'Folder {album_folder} does not exist.')
                
             
def handle_rfid_read(rfid_code):
        global DB
        
        #THREAD_LOCK.acquire()
        
        logger.debug(f'Looking up album folder for RFID: {rfid_code}...')
    
        ## check if you recieved a command card
        ## Command cards handle system wide settings 
        if (command_card_handler(rfid_code) == True):
            logger.debug(f'Completed command card: {rfid_code}...')      
        else:
            ##album_folder_name = lookup_field_by_field(DB, 'rfid', rfid_code, 'folder')
            
          
            
            genere_card = lookup_field_by_field(DB, 'rfid', rfid_code, 'genere_card')
            
            if (genere_card = 1):
                ## this card is meant to play a genre instead of a specific album
                genre_name = lookup_field_by_field(DB, 'rfid', rfid_code, 'genre')
                sub_genre_name = lookup_field_by_field(DB, 'rfid', rfid_code, 'sub_genre')
                if (len(sub_genre_name) == 0):
                    logger.debug(f'Attemptting to play genre: {genre_name}...')
                else:
                    logger.debug(f'Attemptting to play genre: {genre_name}:{sub_genre_name}...')
                    
                
                
                #get the list of all the folders from this genre
                genre_album_folder_list = get_albums_for_genre(genre_full_name)
                
                
                ## play all 
                aaplayer.play_genre(genre_album_list, is_song_shuffle(rfid_code), is_album_repeat(rfid_code))
                
                
            else:
                ## This card is meant to play a single album
                
                album_folder_name = lookup_field_by_field(DB, 'rfid', rfid_code, 'folder')
                logger.debug(f'Attemptting to play album: {album_folder_name}...')
    
                if (album_folder_name != 0):
                    album_folder = LIBRARY_CACHE_FOLDER + album_folder_name

                    logger.debug(f'Looking for {album_folder}...')
                
                    if os.path.exists(album_folder):
                        #if os.path.isdir(folder_name): 
                        logger.debug (f'Album folder exists. Playing {album_folder_name}')
                        aaplayer.play_folder( album_folder, is_song_shuffle(rfid_code), is_album_repeat(rfid_code) )
                    else:
                        logger.warning (f'Folder {album_folder} does not exist.')
                    
        
"""






main()
    



