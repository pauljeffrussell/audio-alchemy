import os
from urllib.parse import urlparse, parse_qs
from yt_dlp import YoutubeDL
import pandas as pd
#import pl7 as aaplayer
## TODO 2024-12-28 Replacing this with the Audio Manager
#import AlchemyPlayer as aaplayer
from audio_manager import AudioManager
import RPi.GPIO as GPIO # Import Raspberry Pi GPIO library  
from gpiozero import Button
from mfrc522 import SimpleMFRC522
import threading
import logging
from logging.handlers import RotatingFileHandler
import sys
import random
import time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
import configfile as CONFIG
import requests
import subprocess
import numpy as np
from dateutil.parser import parse
from datetime import datetime, timedelta
import calendar
import smtplib
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.header import Header
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import argparse
import re
import traceback
import aareporter
from gtts import gTTS
import signal
import psutil
import objsize
import gc
import markdown
import json



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

LAST_ALBUM_CARD = 0

LAST_COMMAND_CARD = 0

LAST_COMMAND_MUSIC_CARD = 0

COUNT_SINCE_CARD_REMOVED = 0

SLEEP_DURATION_MAIN_LOOP = 60*60

## This is the sleep duration for the RFID reader loop
SLEEP_DURATION_RFID_READ_LOOP = 0.2

## This is the number of times the RFID reader can read nothing before it
## considers a card removed
MAX_COUNT_SINCE_CARD_REMOVED = 4

## This is the fiel I use to cache the DB so I don't 
## have to get it from the web every time.
DB_CACHE = CONFIG.DB_CACHE_LOCATION + "dbcache.csv"

## This is where the album of the day cache
## It stores the album of the day and we use that to keep 
## the album of the day from repeating too frequently.
FILE_AOTD_CACHE = CONFIG.DB_CACHE_LOCATION + "aotdcache.csv"

## This is where blocked tracks are stored
## It stores tracks that the user has requested to never play again
BLOCKED_TRACKS_FILE = CONFIG.DB_CACHE_LOCATION + "blocked_tracks.json"

## In-memory hashmap of blocked tracks
BLOCKED_TRACKS = {}

"""
## Used to calculate the number of days before an album can be chosed for
## album of the day after being selected. the equation is
## #of albums available for random selection * AOTD_REPEAT_LIMIT set to .7
## I did a bumch of testing and this creates a comfortable random feeling withot
## to frequent repeats. Here are some results from bulk testing I did.

## 2023-12-31 I updated the limit to .9 because it helped with Christmas and the bigger library.

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
AOTD_REPEAT_LIMIT = .9


#### THESE ARE NEW
BLANK = 'BLANK'

SUPPORTED_EXTENSIONS = ['.mp3', '.MP3', '.wav', '.WAV', '.ogg', '.OGG', '.flac', '.FLAC']

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
THE CURRENT ALBUM OF THE DAY DATE.
We'll use this as a seed for pulling the album of the day.
"""
ALBUM_OF_THE_DAY_DATE = 0

"""
Matches the format of the Album of the day date. 
This value is sent when the email goes out. 
"""
##Deprecated 2024-05-20 when we moved to the scheduler
#ALBUM_OF_THE_DAY_LAST_EMAIL_DATE = 0


"""
The current album of the day rfid
"""
ALBUM_OF_THE_DAY_RFID = 0 

"""
The flag that tells the app if it should send an email of the day.
"""
FLAG_AOTD_ENABLED = False

"""
When set to true the first album of the day email will be sent at application start.
"""
FLAG_AOTD_SEND_NOW = False

"""
Command line argument that tells the app to load the DB from the web.
"""
FLAG_LOAD_DB_FROM_THE_WEB = False

"""
The command line parameter to inject a fake date into the application.
"""
PARAM_COMMAND_LINE_SEED_DAY = None

## This is the counter to see roughly how long has 
## past since the album of the day was sent
## Deprecated 2024-05-20 when scheduler was installed
#COUNTER_FOR_ALBUM_OF_THE_DAY = 39995

## I want to check every hour so every 3600 seconds
## we'll check if it's time yet
## Deprecated 2024-05-20 when scheduler was installed
#CHECK_ALBUM_OF_THE_DAY_COUNT_LIMIT = 36000

"""
Tracks if the system date has been set. If it has, we don't try to set it
again because we have what we need and every new attempt can only
make things the same or worse.
"""
IS_SYSTEM_DATE_SET = False

"""
When set to True, card taps and track plays will be recorded to an external Google sheet.
"""
ENABLE_REPORT_TO_WEB = False

aaplayer = None

"""
This is the global logger. It gets set when the application starts. 
"""
logger = None

"""
#################################################################################

            Logger 

#################################################################################"""
def start_logger(debug_set):
    global logger
    
    file_location=CONFIG.LOG_FILE_LOCATION 
    log_out_level=logging.INFO
    
    if debug_set == True:
        log_out_level=logging.DEBUG
        print ("Setting logging level to DEBUG.")
    else:
        print ("Setting logging level to WARNING.")    
    
    # Create the logger
    logger = logging.getLogger()
    logger.setLevel(log_out_level)

    # Suppress logging from apscheduler by setting its log level higher
    logging.getLogger('apscheduler').setLevel(logging.WARNING)


    # Create a formatter
    #formatter = logging.Formatter('%(asctime)s -- %(message)s -- %(funcName)s %(lineno)d')
    formatter = logging.Formatter('%(asctime)s -- %(filename)s:%(lineno)d -- %(funcName)s -- %(message)s')
    # Create a stream handler to log to STDOUT
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(log_out_level)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)



    # Create a rotating file handler to log to a file
    formatterForLogFile = logging.Formatter('%(levelname)s %(asctime)s %(message)s -- %(funcName)s %(lineno)d')
    file_handler = RotatingFileHandler(file_location, maxBytes=1024*1024, backupCount=5)
    #file_handler = RotatingFileHandler("./logs/error.log", maxBytes=1024*1024, backupCount=5)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatterForLogFile)
    logger.addHandler(file_handler)
    
    return logger;


"""
#################################################################################

           Initiallization - Database and Catalog and Main Loop

#################################################################################"""

def load_database(LOAD_FROM_WEB):
    global DB, IS_SYSTEM_DATE_SET
    
    DB_LOADED = False
    
    if not LOAD_FROM_WEB:
        ## they didn't tell us to use the web so we'll use the cache
        if os.path.exists(DB_CACHE):
            logging.debug(f'Attempting to load the DB from {DB_CACHE}')
            
            
            
            DB = read_db(DB_CACHE)
              
            
            logging.debug("SUCCESS! DB loaded from cache.")
            DB_LOADED = True
            
            clean_up_catalog_db_column_types()
            
            return DB
        else:
            logging.debug("No Cached DB available. Attempting to load from web.")
            

    while not DB_LOADED:
        try:
            
            ## update the system data so that your call to google works.
            if (IS_SYSTEM_DATE_SET == False):
                set_ststem_date()
                
            
            logging.debug("Attempting to load the DB from the internet.")
            db_url = f'https://docs.google.com/spreadsheets/d/{DB_SHEET_ID}/gviz/tq?tqx=out:csv&sheet={DB_SHEET_NAME}'
            logger.debug(f'DB URL: {db_url}s')
            # Read the spreadsheet
        
            #logger.debug('This is the response for the URL.')
            #response = requests.get(db_url)

            
            #logger.debug(response)
            #logger.debug("\n\n")
        
            logger.debug('ready to read the csv from url.')
            #DB = pd.read_csv(db_url)
            
            DB = read_db(db_url)
            
            
            logging.debug("SUCCESS! The DB loaded from the web.")
            


            clean_up_catalog_db_column_types()
            
            backup_cache(DB_CACHE)
            DB.to_csv(DB_CACHE, index=False)
            
            """replaced by the previous line
            DB['sub_genre'] = DB['sub_genre'].fillna(BLANK)
            DB['genre'] = DB['genre'].fillna(BLANK)
            DB['folder'] = DB['folder'].fillna(BLANK)
            DB['labels'] = DB['labels'].fillna(BLANK)
            """
            
            DB_LOADED = True
            
            
            return DB
        except Exception as e:
            logging.debug(f'An exception occurred:')
            logging.debug(str(e))
            logging.debug("DB load failed. Retrying in 3 seconds.")
            time.sleep(3)


def read_db(csv):
    """
    read in the db and return a pandas dataframe 
    with typed fields the way the ap expects it
    """
    try:
        return pd.read_csv(csv, dtype={'genre_card': float, 'label_card': float, \
                                       'is_stream': float, 'is_audiobook': float, \
                                       'shuffle_albums': float, 'shuffle_songs': float, \
                                       'repeat': float, 'christmas_aotd': float, \
                                       'exclude_from_random': float, 'aotd_date': str, \
                                       'rfid': str, 'loaded_hq': str, 'remember_position': float, \
                                       'album_story': str} )
    except Exception as e:
        ## this can happen if some chucklehead accidentally puts a letter in one of the fields 
        ## that's supposed to have a float. And by some chcklehead, I, of course mean me.
        logger.error(f'Error while reading the DB. {e}')
    
   

def clean_up_catalog_db_column_types():
    """
    This function cleans up the columns coming from the google sheet. One stray space in a column 
    of integers and everything becomes a sting. So we clean it all up before using it. 
    """
    global DB
    
    ## fill in any empty columns with BLANKs
    DB['sub_genre'] = DB['sub_genre'].fillna(BLANK)
    DB['genre'] = DB['genre'].fillna(BLANK)
    DB['folder'] = DB['folder'].fillna(BLANK)
    DB['labels'] = DB['labels'].fillna(BLANK)
    DB['aotd_greeting'] = DB['aotd_greeting'].fillna(BLANK)
    DB['album_story'] = DB['album_story'].fillna(BLANK)
    
   

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
    return pd.read_csv(FILE_AOTD_CACHE, dtype={'date': str, 'rfid': str, 'album_name': str})
    

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

def is_rfid_codes_match(rfid1,rfid2):
    
    return str(rfid1) == str(rfid2)
    


def set_ststem_date():
    """ 
    Because the system is read only, every time you reboot the system thinks the date is 
    June 17 2023 which is when OS was set to read only.
            
    Intenet requests to google to get the catalog will fail if the system date out of date.
    
    2023-09-17 I have a theory, that the reason the app fails to load sometimes is because the internet 
    isn't set up and we're trying to set the current time from the internet. So I've added this code
    to make it try 3 times and then give up, but it should never die.
    """
    global IS_SYSTEM_DATE_SET
    
    if (IS_SYSTEM_DATE_SET == False):
        ## the idea here is to only do this if we haven't already 
        ## set the date and we haven't failed a lot already. 
        ##
        ## if it keeps failing we'll give up and log an error
        ATTEMPTS_MADE = 0

        ## It seems to take 15 seconds before this ever works. 
        if (not is_ntp_synced()):
            time.sleep(15)
        while (ATTEMPTS_MADE < 2 and not is_ntp_synced()):
            ATTEMPTS_MADE = ATTEMPTS_MADE +1
            time.sleep(5)
            logger.info(f"RETRY: The system clock is NOT synchronized! Trying Again... ")
        
        if (ATTEMPTS_MADE == 0 or is_ntp_synced()):
            IS_SYSTEM_DATE_SET = True
            logger.debug(f"SUCCESS: The System clock is synchronized! ")
        else:
            ## NTP isn't synchronized so use the AOTD Date.
            logger.warning(f"BUMMER: The NTP service is not synchronized. Using last AOTD Date.")
            set_date_from_last_aotd()



        '''
        #This was the old way of doing it. Now that we have NTP working
        # this is obsolete 2024-05-20  
        try:
            ATTEMPTS_MADE = ATTEMPTS_MADE +1
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
            
            IS_SYSTEM_DATE_SET = True
        
        except Exception as e:
            ## if anything goes wrong, write it to a log file.
            ## Only Errors will be logged. 
        
            logger.error(f"An exception occurred while trying to set the system date: {e}")
            stack_trace = traceback.format_exc()
            logger.error(f"{stack_trace}")
            time.sleep(3)'''


    

def is_ntp_synced():
    try:
        result = subprocess.run(['timedatectl', 'status'], capture_output=True, text=True, check=True)
        if result is not None:
            output = result.stdout
            if ("NTP service: active" in output and "System clock synchronized: yes" in output):
                ## The NTP service is synchronized
                return True
            else:
                ## The NTP service is not synchronized
                return False
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running timedatectl: {e}")
        return False

def set_date_from_last_aotd():
        

    if not DB_AOTD_CACHE.empty:
        try:

            last_date = DB_AOTD_CACHE['date'].iloc[-1]

            year = last_date[:4]
            month = last_date[4:6]
            day = last_date[6:8]

            # Format the date and time for the 'date' command (YYYY-MM-DD HH:MM)
            cmd = f"date -s '{year}-{month}-{day} 00:01:01'"
            
            logging.debug(f'Setting system date {cmd}')
            # Execute the command to set the date
            subprocess.run(['sudo', 'bash', '-c', cmd])    

            ## Note that we're really just guessing at the date, so we're not going to 
            ## set IS_SYSTEM_DATE_SET = True becaause we want alchemy to try to set the date later.
            logging.info(f'Set system date to last known Album of the Date date: {cmd}')

        except Exception as e:
            logger.error(f"An exception occurred while trying to set the system date: {e}") 
    else:
        logger.error(f"AOTD Cache is empty. Unable to set temp system date from AOTD Cache.") 
        
    
def rfid_reader_thread(callback):
    """
    RFID reader thread function that continuously reads RFID tags and calls a callback function with the RFID code.

    Args:
        callback (function): A function to be called with the RFID code whenever a tag is detected.

    This function initializes an instance of the SimpleMFRC522 reader, starts an infinite loop to read RFID tags,
    and calls the provided callback function with the RFID code. If an exception occurs, it logs the error and performs GPIO cleanup.
    """
    reader = SimpleMFRC522()
    try:
        logger.debug("Starting RFID Reader Thread.")
        while APP_RUNNING:
            rfid_code = reader.read_id_no_block()
            callback(rfid_code)
            time.sleep(SLEEP_DURATION_RFID_READ_LOOP)
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.error(f"Error in RFID thread loop. {e}. {stack_trace}")
        
    finally:
        GPIO.cleanup()
        logger.debug(f"Exiting RFID thread loop.")


def start_rfid_thread():
    """
    Starts a new thread that runs the RFID reader function.

    Returns:
        threading.Thread: The thread object that is running the RFID reader function.

    This function creates and starts a daemon thread that runs the `rfid_reader_thread` function with `handle_tag_detected` as its argument.
    The thread is set as a daemon so it will not prevent the program from exiting.
    """
    thread = threading.Thread(target=rfid_reader_thread, args=(handle_tag_detected,))
    thread.daemon = True
    thread.start()
    return thread

def signal_handler(sig, frame):
    """
    Signal handler for graceful shutdown.
    """
    logger.info("Received signal to terminate. Shutting down...")
    app_shutdown()

def confirm_aotd_send(date_str, artist_name, album_name):
    """Helper function to show AOTD confirmation prompt and get user response"""
    print(f"\nAbout to send AOTD email:\n")
    print(f"Date: {date_str}")
    print(f"Artist: {artist_name}")
    print(f"Album: {album_name}")
    print(f"Sending To: {CONFIG.EMAIL_SEND_TO}\n")
    print("\nType 'YES' to proceed, or anything else to cancel: ", end='')
    
    confirmation = input().strip()
    if confirmation != "YES":
        print("Cancelled sending Album of the Day.")
        sys.exit(0)

def log_memory_usage():
    """
    Log detailed memory usage information, broken down by major components.
    """
    try:
        process = psutil.Process()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Overall process memory
        process_memory = process.memory_info().rss / 1024 / 1024  # Convert to MB
        
        logger.info(f"\n=== Memory Usage Report at {timestamp} ===")
        logger.info(f"Total Process Memory: {process_memory:.2f} MB")
        
        if 'aaplayer' in globals():
            logger.info("\n=== Audio Players ===")
            
            # Stream Player (VLC-based)
            if hasattr(aaplayer, 'stream_player'):
                stream_size = objsize.get_deep_size(aaplayer.stream_player) / 1024 / 1024
                logger.info(f"Stream Player Total: {stream_size:.2f} MB")
                
                # Get detailed VLC memory info for stream player
                if hasattr(aaplayer.stream_player, 'instance'):
                    vlc_size = objsize.get_deep_size(aaplayer.stream_player.instance) / 1024 / 1024
                    logger.info(f"  - VLC Instance: {vlc_size:.2f} MB")
                    
                    # Get media info if playing
                    if hasattr(aaplayer.stream_player, 'player') and aaplayer.stream_player.player is not None:
                        media = aaplayer.stream_player.player.get_media()
                        if media:
                            media_size = objsize.get_deep_size(media) / 1024 / 1024
                            logger.info(f"  - Current Media: {media_size:.2f} MB")
            
            # Podcast Player (VLC-based)
            if hasattr(aaplayer, 'podcast_player'):
                podcast_size = objsize.get_deep_size(aaplayer.podcast_player) / 1024 / 1024
                logger.info(f"Podcast Player Total: {podcast_size:.2f} MB")
                
                # Get detailed VLC memory info for podcast player
                if hasattr(aaplayer.podcast_player, 'player_instance'):
                    vlc_size = objsize.get_deep_size(aaplayer.podcast_player.player_instance) / 1024 / 1024
                    logger.info(f"  - VLC Instance: {vlc_size:.2f} MB")
                    
                    # Get media info if playing
                    if hasattr(aaplayer.podcast_player, 'player') and aaplayer.podcast_player.player is not None:
                        media = aaplayer.podcast_player.player.get_media()
                        if media:
                            media_size = objsize.get_deep_size(media) / 1024 / 1024
                            logger.info(f"  - Current Media: {media_size:.2f} MB")
            
            # Files Player (Pygame-based)
            if hasattr(aaplayer, 'file_player'):
                files_size = objsize.get_deep_size(aaplayer.file_player) / 1024 / 1024
                logger.info(f"Files Player Total: {files_size:.2f} MB")
                if hasattr(aaplayer.file_player, 'track_list'):
                    tracklist_size = objsize.get_deep_size(aaplayer.file_player.track_list) / 1024 / 1024
                    logger.info(f"  - Track List: {tracklist_size:.2f} MB")
                if hasattr(aaplayer.file_player, 'playback_manager'):
                    manager_size = objsize.get_deep_size(aaplayer.file_player.playback_manager) / 1024 / 1024
                    logger.info(f"  - Playback Manager: {manager_size:.2f} MB")
        
        # Database memory
        logger.info("\n=== Database ===")
        if 'DB' in globals():
            db_size = objsize.get_deep_size(DB) / 1024 / 1024
            logger.info(f"Main Database: {db_size:.2f} MB")
        if 'DB_AOTD_CACHE' in globals():
            cache_size = objsize.get_deep_size(DB_AOTD_CACHE) / 1024 / 1024
            logger.info(f"AOTD Cache: {cache_size:.2f} MB")
        
        # Major Libraries Total Memory from memory maps
        logger.info("\n=== Major Libraries ===")
        maps = process.memory_maps()
        vlc_total = 0
        vlc_shared = 0
        vlc_private = 0
        pygame_total = 0
        
        for m in maps:
            if 'vlc' in m.path.lower():
                vlc_total += m.rss / 1024 / 1024
                if m.path.endswith('.so'):  # Shared libraries
                    vlc_shared += m.rss / 1024 / 1024
                else:  # Private memory
                    vlc_private += m.rss / 1024 / 1024
            elif 'pygame' in m.path.lower():
                pygame_total += m.rss / 1024 / 1024
                
        logger.info(f"VLC Total: {vlc_total:.2f} MB")
        logger.info(f"  - Shared Libraries: {vlc_shared:.2f} MB")
        logger.info(f"  - Private Memory: {vlc_private:.2f} MB")
        logger.info(f"Pygame Total: {pygame_total:.2f} MB")
        
        # Active Threads
        logger.info("\n=== Active Threads ===")
        active_threads = threading.enumerate()
        logger.info(f"Total Threads: {len(active_threads)}")
        for thread in active_threads:
            thread_type = ""
            if "rfid_reader" in thread.name.lower():
                thread_type = "(RFID Reader)"
            elif "write_worker" in thread.name.lower():
                thread_type = "(Reporter)"
            elif thread.name == "MainThread":
                thread_type = "(Main)"
            elif "held" in thread.name.lower():
                thread_type = "(Held)"
            logger.info(f"  {thread.name} {thread_type}")
            
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"Error in memory logging: {e}")
        logger.error(traceback.format_exc())

def alchemy_app_runtime():
    global DB, APP_RUNNING, ALBUM_OF_THE_DAY_DATE, DB_AOTD_CACHE, AOTD_SCHEDULER, aaplayer

    print ("Setting System Date...")

    ## the read only OS thinks the date is June 2023 on reboot. In order for 
    ## album of the day to work properly, you need to fetch the current date
    ## and set the system time.
    set_ststem_date()

    logger.info("Starting AlchemyAlchemy...")
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    ## Load the album of the day cache.
    ## If there isn't one, make one.
    ## This has to happen first, because we need the file to be there
    ## for the next step
    DB_AOTD_CACHE = load_album_of_the_day_cache()
    
    # Load the database of RFID tags and their matching albums
    DB = load_database(FLAG_LOAD_DB_FROM_THE_WEB)
    
    # Load blocked tracks
    load_blocked_tracks()
    
    ## Every time the system restarts restart the system. Album of the day will instead 
    ## be sent the day after the system is rebooted.
    set_album_of_the_day_date_and_rfid()
    
    AOTD_SCHEDULER = BackgroundScheduler()
    
    # Define timezone once for all scheduler jobs
    eastern = pytz.timezone('America/New_York')
    
    if FLAG_AOTD_ENABLED == True and not FLAG_AOTD_SEND_NOW:
        ## We should schedule the sending of the album of the day.
        logger.debug("Scheduling the AOTD for 4:20am Eastern Time.")
        AOTD_SCHEDULER.add_job(schedule_handler_send_aotd, CronTrigger(hour=4, minute=20, timezone=eastern))
        
    logger.debug("Scheduling error log email for 4:25am Eastern Time.")
    AOTD_SCHEDULER.add_job(schedule_handler_send_receint_errors, CronTrigger(hour=4, minute=25, timezone=eastern))

    logger.debug("Scheduling player shutdown to address times when the player is left on overnight.")
    AOTD_SCHEDULER.add_job(schedule_handler_shutdown_player, CronTrigger(hour=3, minute=15, timezone=eastern))
    
    #AOTD_SCHEDULER.add_job(schedule_handler_shutdown_player, CronTrigger(minute='*/1', timezone=eastern))
    


    # Schedule memory usage logging every 10 minutes
    #logger.debug("Scheduling memory usage logging.")
    #AOTD_SCHEDULER.add_job(log_memory_usage, CronTrigger(minute='*/5', timezone=eastern))

    AOTD_SCHEDULER.start()

    if FLAG_AOTD_SEND_NOW == True:

        if PARAM_COMMAND_LINE_SEED_DAY != None:
            # Using provided seed date
            print(f'Looking up album for date: {PARAM_COMMAND_LINE_SEED_DAY}...')
            date_str = PARAM_COMMAND_LINE_SEED_DAY
            
            cached_rfid = get_aotd_rfid_for_date(PARAM_COMMAND_LINE_SEED_DAY)
        else:
            # Get today's date in YYYYMMDD format
            date_str = datetime.today().strftime('%Y%m%d')
            cached_rfid = check_aotd_cache_for_today(date_str)
        
        
        if cached_rfid is None:
            sys.exit(f"\n\nExiting - no cached album of the day found for {date_str}")
            
        # Get album details and confirm
        album_name = replace_non_strings(lookup_field_by_field(DB, 'rfid', cached_rfid, 'Album'))
        artist_name = replace_non_strings(lookup_field_by_field(DB, 'rfid', cached_rfid, 'Artist'))
        
        confirm_aotd_send(date_str, artist_name, album_name)
        
        # Send the email using the cached RFID
        ## if we're doing this then The larger application is
        # probably running somewhere and we need to kill this version
        # After we send the email so that it doesn't
        # Interfere with the other one.
        send_album_of_the_day_email(cached_rfid)
        sys.exit("\n\nShutting down AOTD Sender script")

    # Set up the event handlers for the button controls
    start_button_controls()


    ### TODO: This is the new audio player. We've replaceed AlchemyPlayer.py with the new AudioManager
    ### from audio_manager import AudioManager
    ### AudioAlchemy shouldn't see any difference between the two, but the AudioManager 
    ### allows us to switch between the file player and the stream player
    aaplayer = AudioManager()
    
    #set the logger for the music player
    aaplayer.set_logger(logger)
    aareporter.set_logger(logger)
    if (ENABLE_REPORT_TO_WEB):
        logger.debug('Web reporting is enabled.')
        aareporter.enable_sheet_logger()
    else:
        logger.debug('Web reporting is disabled. Nothing will be logged to the reporting google sheet.')
        

    logger.debug('Starting AlchemyPlayer.')
    #set up the music player
    aaplayer.startup()
    
    logger.debug('Loaded AlchemyPlayer.')

    ## start reading from the RFID reader
    start_rfid_thread()
    

    

    try:
        while APP_RUNNING:
            logger.debug('Main Loop Refresh.')
            aareporter.log_system_metrics()
            #aareporter.send_logs_home()
            time.sleep(SLEEP_DURATION_MAIN_LOOP)
            

        
            
        logger.debug('Exiting Main Application Loop. APP_RUNNING = False.')
    except KeyboardInterrupt:
        logger.debug('Recieved KeyboardInterrupt - Shutting down')
        
    
    app_shutdown()
    


def app_shutdown():
    global APP_RUNNING 

    APP_RUNNING = False
    time.sleep(.5)

    try:
        logger.debug('Starting shutdown.')
        aaplayer.shutdown_player()
        AOTD_SCHEDULER.shutdown()
        GPIO.cleanup()
        logger.info('Shutting down AudioAlchemy.')
    finally:
        sys.exit(0)

"""
#################################################################################

            Button Logic and Handlers

#################################################################################"""

def handle_tag_detected(rfid):
    global LAST_ALBUM_CARD, LAST_COMMAND_CARD, LAST_COMMAND_MUSIC_CARD, COUNT_SINCE_CARD_REMOVED

    #logger.debug(f"\n\nrfid: {rfid}.")
    #logger.debug(f"LAST_ALBUM_CARD: {LAST_ALBUM_CARD}.")
    #logger.debug(f"LAST_COMMAND_CARD: {LAST_COMMAND_CARD}.")
    #logger.debug(f"LAST_COMMAND_MUSIC_CARD: {LAST_COMMAND_MUSIC_CARD}.")
    #logger.debug(f"COUNT_SINCE_CARD_REMOVED: {COUNT_SINCE_CARD_REMOVED}.")

    if (rfid == LAST_ALBUM_CARD):
        #logger.debug("Matched last album card.")
        ## The RFID reader won't successfully read every time, so this counter will go up
        ## We reset it back to zero every time we get a matched read.
        COUNT_SINCE_CARD_REMOVED = 0

        ## the last thing that happened wasn't a command card, so reset it.
        ## so if we see it again it will work right away.
        LAST_COMMAND_CARD = 0
        return
    
    if (rfid == LAST_COMMAND_CARD):
        #logger.debug("Matched last command card.")
        ## The RFID reader won't successfully read every time, so this counter will go up
        ## We reset it back to zero every time we get a matched read.
        COUNT_SINCE_CARD_REMOVED = 0
        return

    if (rfid == LAST_COMMAND_MUSIC_CARD):
        #logger.debug("Matched last random albums card.")
        ## The RFID reader won't successfully read every time, so this counter will go up
        ## We reset it back to zero every time we get a matched read.
        COUNT_SINCE_CARD_REMOVED = 0
        LAST_COMMAND_CARD = 0
        return
    
    ## This is where we check and see if the card has stopped seeing a card.
    ## The rule is, album cards can be removed and placed back any time without 
    ## changing app behavior according to the rules in this function.
    if (rfid == None):
        #logger.debug("RFID == None")
        ## A card was read and then nothing was read.
        COUNT_SINCE_CARD_REMOVED += 1

        if (COUNT_SINCE_CARD_REMOVED > MAX_COUNT_SINCE_CARD_REMOVED):
            ## only execute this if the last album hasn't been cleared AND the music isn't playing.
            ## this alows us to pick up the album card and look at it as long as we want
            ## as long as the music is playing.
            #if (LAST_ALBUM_CARD != 0 and not aaplayer.is_playing()):
                ## if no card is read for x times and the player is stopped, 
                ## remove this card from the last list so it can be tapped again.
            #    LAST_ALBUM_CARD = 0

            # Clear random albums card memory only if music is not playing
            if not aaplayer.is_playing():
                LAST_COMMAND_MUSIC_CARD = 0
                LAST_ALBUM_CARD = 0
                #logger.debug('Cleared last random albums card and last album card due to inactivity.')

            #command cards are only good for one use
            LAST_COMMAND_CARD = 0
            COUNT_SINCE_CARD_REMOVED = 0
        
        return
            
    if (command_card_handler(rfid) == True):
        ## you found a command card
        COUNT_SINCE_CARD_REMOVED = 0
        
        # Check if this is a music command card
        if (str(rfid) in CONFIG.COMMAND_MUSIC_CARDS):
            # this is a music command card so let's 
            # remember it so we can pick it up and put it back down.
            LAST_COMMAND_MUSIC_CARD = rfid
            #logger.debug(f'Completed random albums card: {rfid}...')
        else:
            LAST_COMMAND_CARD = rfid
            #logger.debug(f'Completed command card: {rfid}...')

    elif(music_card_handler(rfid) == True):
        # you found a music card!
        COUNT_SINCE_CARD_REMOVED = 0
        LAST_ALBUM_CARD = rfid
        # Clear command card memory when a music card is detected
        LAST_COMMAND_CARD = 0
        # Clear random albums card memory when a music card is detected
        LAST_COMMAND_MUSIC_CARD = 0
        #logger.debug(f'Completed music card: {rfid}...')
    else:
        ## you don't know this card. Treat it like a command card 
        ## so you don't keep reading it over and over.
        COUNT_SINCE_CARD_REMOVED = 0
        LAST_COMMAND_CARD = rfid


'''def rfid_matches_command_card_array(rfid, command_card_array):
  """
  This function checks if a number is present in an array.

  Args:
    number: The number to search for.
    array: The array to search in.

  Returns:
    True if the number is found in the array, False otherwise.
  """
  for element in command_card_array:
    if element == rfid:
      return True
  return False    '''   

def command_card_handler(rfid_code):
    """
    Checks to see if it recieved a command card. 
    If it did, this function will execute the command and return True
    
    Otherwise it returns false.
    """
    global DB, APP_RUNNING
    command_code = str(rfid_code)
    
    if (command_code == CONFIG.COMMAND_PLAY_ALBUM_OF_THE_DAY or command_code == CONFIG.COMMAND_PLAY_ALBUM_OF_THE_DAY_2):
        logger.debug('Playing Album of the day.')
        play_album_of_the_day()
        aareporter.log_card_tap(CONFIG.CARD_TYPE_COMMAND, "Album of the day", "COMMAND_PLAY_ALBUM_OF_THE_DAY", rfid_code)        
        return True 
    elif (command_code == CONFIG.COMMAND_PLAY_PAUSE_PLAYER):
        logger.debug('Play/Pause player.')
        aaplayer.play_pause_track()
        ##2024-05-03 Commented this out, because we don't need to report on what is effectively a button push and not a command card.
        ##aareporter.log_card_tap(CONFIG.CARD_TYPE_COMMAND, "Play/Pause Track", "COMMAND_PLAY_PAUSE_PLAYER", rfid_code)
        return True
    elif (command_code == CONFIG.COMMAND_REPEAT_ALBUM):
        ## set the current album to repeat.
        logger.debug('Setting current album to repeat.')
        aaplayer.play_feedback(CONFIG.FEEDBACK_ALBUM_REPEAT)
        aaplayer.set_repeat_album(True)
        aareporter.log_card_tap(CONFIG.CARD_TYPE_COMMAND, "Repeat Album", "COMMAND_REPEAT_ALBUM", rfid_code)
        return True        
    elif (command_code == CONFIG.COMMAND_STOP_AND_RELOAD_DB ):
        logger.debug('Executing Command Card Stop Player & Reload Database')
        
        ## stop the music so it seems like an update is happening
        
        aaplayer.pause_track()

        ## we do this because we don't want the current card remembered 
        ## after the DB load. Otherwise you expect it to start playing and it doesn't
        LAST_ALBUM_CARD = None
        
        
        ## start playing the processing feedback sound
        aaplayer.play_feedback(CONFIG.COMMAND_STOP_AND_RELOAD_DB_FEEDBACK)
        
        logger.debug('Loading DB from web.')
        ## while the sound is playing update the DB
        DB = load_database(True)
        logger.debug('DB loaded from web.')
        
        '''# removed this on 2024-05-26  as it didnt appear to do anything
        # reset the player. I'm not sure why this is here. It probably served a purpose a long time ago
        logger.debug('Restaring the player.')
        aaplayer.shutdown_player()
        aaplayer.startup()
        logger.debug('Restaring complete.')'''


        aareporter.log_card_tap(CONFIG.CARD_TYPE_COMMAND, "Reload Database", "COMMAND_STOP_AND_RELOAD_DB", rfid_code)    
        
        
        logger.debug('Waiting for 2.5 seconds for audio to complete.')
        time.sleep(2.5)
        
        return True
    elif (command_code == CONFIG.COMMAND_SHUT_DOWN_APP ):
        logger.debug('Read RFID to shutdown application')
        APP_RUNNING = False
        aareporter.log_card_tap(CONFIG.CARD_TYPE_COMMAND, "Shut Down App", "COMMAND_SHUT_DOWN_APP", rfid_code)
        return True
    elif (command_code == CONFIG.COMMAND_PLAY_RANDOM_ALBUMS ):
        logger.debug('Read RFID to play random albums')
        play_random_albums()
        aareporter.log_card_tap(CONFIG.CARD_TYPE_COMMAND, "Play Random Albums", "COMMAND_PLAY_RANDOM_ALBUMS", rfid_code)
        return True 
    elif (command_code == CONFIG.COMMAND_PLAY_AOTD_HISTORY ):
        logger.debug('Read RFID to play AOTD history')
        play_aotd_history_albums()
        aareporter.log_card_tap(CONFIG.CARD_TYPE_COMMAND, "Play AOTD History Albums", "COMMAND_PLAY_AOTD_HISTORY", rfid_code)
        return True 
    elif (command_code == CONFIG.COMMAND_PLAY_IN_ORDER_FROM_RANDOM_TRACK):
        logger.debug('Read RFID to play in order from a random track')
        aaplayer.play_in_order_from_random_track()
        aareporter.log_card_tap(CONFIG.CARD_TYPE_COMMAND, "Play in order from random track", "COMMAND_PLAY_IN_ORDER_FROM_RANDOM_TRACK", rfid_code)
        return True 
    elif (command_code == CONFIG.COMMAND_SHUFFLE_UNSHUFFLE_PLAYLIST):
        logger.debug('Read RFID to shuffle/unshuffle playlist')
        aaplayer.shuffle_unshuffle_tracks()
        aareporter.log_card_tap(CONFIG.CARD_TYPE_COMMAND, "Shuffle Playlist", "COMMAND_SHUFFLE_UNSHUFFLE_PLAYLIST", rfid_code)
        return True
    elif (command_code == CONFIG.COMMAND_SPEEK_CURRENT_TRACK_NAME):
        ## We're going to email the current track to the 
        current_track_for_email = aaplayer.get_current_track()
        if current_track_for_email != None:
                        
            ## TODO: replace the existing line with the line below it so we use the player to speak
            ## it contains all the necessary logic
            #speak_current_track()
            aaplayer.speak_current_track(CONFIG.FEEDBACK_PROCESSING)
            
            
            """ THIS IS THE WORKING EMAIL CODE. YOU"RE REPLACING IT WITH SPEACH
            ## play the feedback sound that the command card is being processed.
            aaplayer.play_feedback(CONFIG.COMMAND_EMAIL_CURRENT_TRACK_NAME_FEEDBACK)
            
            #send an email with that track
            send_email_with_current_track(current_track_for_email)
            """
            
        aareporter.log_card_tap(CONFIG.CARD_TYPE_COMMAND, "Speak Album and Track Name", "COMMAND_SPEEK_CURRENT_TRACK_NAME", rfid_code)
        return True
    elif (command_code == CONFIG.COMMAND_EMAIL_CURRENT_TRACK):
        ## We're going to email the current album to the user
        current_track = aaplayer.get_current_track()
        if current_track != None:
            
            ## Get the RFID of the current album from the player
            current_rfid = aaplayer.get_current_rfid()
            if current_rfid != None:
                ## play the feedback sound that the command card is being processed.
                aaplayer.play_feedback(CONFIG.FEEDBACK_PROCESSING)
                ## Send the album of the day email with the current album's RFID
                send_album_of_the_day_email(current_rfid, True)
                aareporter.log_card_tap(CONFIG.CARD_TYPE_COMMAND, "Email Current Album", "COMMAND_EMAIL_CURRENT_TRACK", rfid_code)
            else:
                ## play the feedback sound that the command card is being processed.
                aaplayer.play_feedback(CONFIG.FEEDBACK_RFID_NOT_FOUND)
                logger.debug("Could not get current album RFID from player")
        return True
    elif (command_code == CONFIG.COMMAND_SEND_REMOVE_REQUEST):
        ## We're going to email the current track to the 
        current_track_for_email = aaplayer.get_current_track()
        if current_track_for_email != None and aaplayer.is_playing():
                        
            ## pause the music
            aaplayer.pause_track()

            ## play the feedback sound that the command card is being processed.
            aaplayer.play_feedback(CONFIG.COMMAND_SEND_REMOVE_REQUEST_FEEDBACK)
            
            ## let the sound play partially before we play the next track
            time.sleep(1.5) 

            ## Start the next track. We're skipping the current track
            ## because the user just told us it sucks.
            aaplayer.next_track()


            # Add track to blocked list
            add_blocked_track(current_track_for_email)
            
            #send an email with the track we just skipped
            send_email_with_remove_request(current_track_for_email)
            
            
            aareporter.log_card_tap(CONFIG.CARD_TYPE_COMMAND, f"Remove Track Request {current_track_for_email}", "COMMAND_SEND_REMOVE_REQUEST", rfid_code)
        else:
            aareporter.log_card_tap(CONFIG.CARD_TYPE_COMMAND, f"Remove Track Request - No Track Provided", "COMMAND_SEND_REMOVE_REQUEST", rfid_code)    
        return True
    else:
        return False
    

def music_card_handler(rfid_code):
    """
    When you have a music card pass this fucntion the RFID and it will play it. 
    """
    global DB
    

    
    if (1 == lookup_field_by_field(DB, 'rfid', rfid_code, 'genre_card')):
        ## this card is meant to play a genre instead of a specific album
        genre = lookup_field_by_field(DB, 'rfid', rfid_code, 'genre')
        sub_genre = lookup_field_by_field(DB, 'rfid', rfid_code, 'sub_genre')
        
        #get the list of all the folders from this genre
        genre_album_folder_list = get_albums_for_genre(genre, sub_genre, is_album_shuffle(rfid_code))
        
        tracks = get_tracks(genre_album_folder_list, is_song_shuffle(rfid_code))
        
        
        if (len(tracks) > 0):
            logger.debug (f'Album folder exists. Playing Genre')
            aaplayer.play_tracks(tracks, is_album_repeat(rfid_code), is_song_shuffle(rfid_code), is_album_remember_position(rfid_code), rfid_code)   
            
        
        name = lookup_field_by_field(DB, 'rfid', rfid_code, 'Album')
        aareporter.log_card_tap(CONFIG.CARD_TYPE_GENRE, name, genre + "::" + sub_genre, rfid_code)
        return True
    
    elif (1 == lookup_field_by_field(DB, 'rfid', rfid_code, 'label_card')):
        #this card is a label card. It is intended to play all of the albums with a matching lable.
        label = lookup_field_by_field(DB, 'rfid', rfid_code, 'labels')
        label_album_folder_list = get_albums_for_label(label, is_album_shuffle(rfid_code))
        tracks = get_tracks(label_album_folder_list, is_song_shuffle(rfid_code))
        

        name = lookup_field_by_field(DB, 'rfid', rfid_code, 'Album')

        if (len(tracks) > 0):
            logger.debug (f'Album folder exists. Playing label')
            if (1 == lookup_field_by_field(DB, 'rfid', rfid_code, 'is_audiobook')):
                logger.debug (f'Audiobook has tracks. Playing Audiobook...')
                aaplayer.play_audiobook(tracks=tracks, 
                                        remember_position = is_album_remember_position(rfid_code), 
                                        rfid=rfid_code)
                aareporter.log_card_tap(CONFIG.CARD_TYPE_AUDIOBOOK, name, label, rfid_code)
            
            else:
                logger.debug (f'Folder has tracks. Playing Audiobook...')
                aaplayer.play_tracks(tracks, is_album_repeat(rfid_code), is_song_shuffle(rfid_code), is_album_remember_position(rfid_code), rfid_code)
                aareporter.log_card_tap(CONFIG.CARD_TYPE_LABEL, name, label, rfid_code)
        
        
       
        return True
    elif (1 == lookup_field_by_field(DB, 'rfid', rfid_code, 'is_stream')):
        #this card is a stream card. It is intended to play all of the albums with a matching lable.
        #label = lookup_field_by_field(DB, 'rfid', rfid_code, 'labels')
        #label_album_folder_list = get_albums_for_label(label, is_album_shuffle(rfid_code))
        #tracks = get_tracks(label_album_folder_list, is_song_shuffle(rfid_code))
        

        
        #if (len(tracks) > 0):
        #    logger.debug (f'Album folder exists. Playing Genre')
        #    aaplayer.play_tracks(tracks, is_album_repeat(rfid_code), is_song_shuffle(rfid_code), is_album_remember_position(rfid_code), rfid_code)
        #    CURRENT_ALBUM_SHUFFLED = False
        
        url = lookup_field_by_field(DB, 'rfid', rfid_code, 'url')
        name = lookup_field_by_field(DB, 'rfid', rfid_code, 'Album')
        if url != 0 and name != 0:
            aaplayer.play_stream(stream_url=url, stream_name=name)

            aareporter.log_card_tap(CONFIG.CARD_TYPE_STREAM, name, url, rfid_code)
            return True
        else:
            handle_unknown_card(rfid_code)
            return False    

    elif (1 == lookup_field_by_field(DB, 'rfid', rfid_code, 'is_podcast')):
        # this is a podcast card. run the podcast player
        url = lookup_field_by_field(DB, 'rfid', rfid_code, 'url')
        name = lookup_field_by_field(DB, 'rfid', rfid_code, 'Album')
        
        if url != 0 and name != 0:
            aaplayer.play_podcast(podcast_url=url, podcast_name=name, rfid=rfid_code)

            aareporter.log_card_tap(card_type=CONFIG.CARD_TYPE_PODCAST,
                                    card_name=name,
                                    uid=url,
                                    rfid=rfid_code)
            return True
            
        else:
            handle_unknown_card(rfid_code)
            return False
        

    elif (1 == lookup_field_by_field(DB, 'rfid', rfid_code, 'is_audiobook')):
        # this is a podcast card. run the podcast player
        #return handle_audiobook_card(rfid_code)
        
        audiobook_folder_name = lookup_field_by_field(DB, 'rfid', rfid_code, 'folder')
        logger.debug(f'Attemptting to play album: {audiobook_folder_name}...')


        if audiobook_folder_name != 0:
            ## the album folder Exists!!!
            audiobook_folder = LIBRARY_CACHE_FOLDER + audiobook_folder_name
        
            tracks = get_tracks([audiobook_folder],shuffle_tracks=False)

            if (len(tracks) > 0):
                logger.debug (f'Audiobook has tracks. Playing...')
                aaplayer.play_audiobook(tracks=tracks, 
                                        remember_position = is_album_remember_position(rfid_code), 
                                        rfid=rfid_code)
            else:
                logger.warning (f'No tracks found for folder {audiobook_folder}.')    
                
            name = lookup_field_by_field(DB, 'rfid', rfid_code, 'Album')
            aareporter.log_card_tap(card_type=CONFIG.CARD_TYPE_AUDIOBOOK,  
                                    card_name=name,  
                                    uid=audiobook_folder_name,  
                                    rfid=rfid_code)
            return True
        
        else:
            ## after all that you didn't find a card.
            handle_unknown_card(rfid_code)
            return False


        
        

    else:
        ## it must be an album card or no card at all
        

        album_folder_name = lookup_field_by_field(DB, 'rfid', rfid_code, 'folder')
        logger.debug(f'Attemptting to play album: {album_folder_name}...')


        if album_folder_name != 0:
            ## the album folder Exists!!!
            album_folder = LIBRARY_CACHE_FOLDER + album_folder_name
        
            tracks = get_tracks([album_folder], is_song_shuffle(rfid_code))


            if (len(tracks) > 0):
                logger.debug (f'Album has tracks. Playing...')
                aaplayer.play_tracks(tracks, is_album_repeat(rfid_code), is_song_shuffle(rfid_code), is_album_remember_position(rfid_code), rfid_code)
                
            
            else:
                logger.warning (f'No tracks found for folder {album_folder}.')    
        
            name = lookup_field_by_field(DB, 'rfid', rfid_code, 'Album')
            aareporter.log_card_tap(CONFIG.CARD_TYPE_ALBUM, name, album_folder_name, rfid_code)
            return True
        
        else:
            ## after all that you didn't find a card.
            handle_unknown_card(rfid_code)
            return False
            
def handle_unknown_card(rfid_code):
    aaplayer.play_feedback(CONFIG.FEEDBACK_RFID_NOT_FOUND)
    logger.debug(f'RFID {rfid_code} is unknown to the app. Consider adding it to the DB...')
    name = lookup_field_by_field(DB, 'rfid', rfid_code, 'Album')
    aareporter.log_card_tap(CONFIG.CARD_TYPE_CARD_UNKNOWN, "Unknown", "Unknown", rfid_code)


def handle_audiobook_card(rfid_code, tracks):
    
    audiobook_folder_name = lookup_field_by_field(DB, 'rfid', rfid_code, 'folder')
    logger.debug(f'Playing Audiobook: {audiobook_folder_name}...')


    if audiobook_folder_name != 0:
        ## the album folder Exists!!!
        audiobook_folder = LIBRARY_CACHE_FOLDER + audiobook_folder_name
    
    
        tracks = get_tracks([audiobook_folder],shuffle_tracks=False)

        if (len(tracks) > 0):
            logger.debug (f'Audiobook has tracks. Playing...')
            aaplayer.play_audiobook(tracks=tracks, 
                                    remember_position = is_album_remember_position(rfid_code), 
                                    rfid=rfid_code)
        else:
            logger.warning (f'No tracks found for folder {audiobook_folder}.')    
            
        name = lookup_field_by_field(DB, 'rfid', rfid_code, 'Album')
        aareporter.log_card_tap(card_type=CONFIG.CARD_TYPE_AUDIOBOOK,  
                                card_name=name,  
                                uid=audiobook_folder_name,  
                                rfid=rfid_code)
        return True
    
    else:
        ## after all that you didn't find a card.
        handle_unknown_card(rfid_code)
        return False


def start_button_controls():
 
    #Left button - previous track
    button16 = Button(CONFIG.LEFT_BUTTON_PIN)
    
    #center button - play/pause
    button15 = Button(CONFIG.CENTER_BUTTON_PIN) 

    ## right button - next track
    button13 = Button(CONFIG.RIGHT_BUTTON_PIN)

    """
    ## converted over to using config file 2025-02-17
    button16 = Button("BOARD16")
    button15 = Button("BOARD38") ## 2025-02-06 changed from BOARD7 to BOARD38
    button13 = Button("BOARD13")"""



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
        logger.debug("Previous Track Button was pushed!")
        aaplayer.back_button_short_press()


def button_callback_15(channel):
    
    # make sure to debounce partial button pushes AND
    # skip this button release if the last button push was held down.
    if (my_interrupt_handler(channel) and not last_button_held()):
        logger.debug("Play/Pause Button was pushed!")
        aaplayer.play_pause_track()

    
def button_callback_13(channel):
    
    # make sure to debounce partial button pushes AND
    # skip this button release if the last button push was held down.
    if (my_interrupt_handler(channel) and not last_button_held()):
        logger.debug("Next Track Button was pushed!")
        aaplayer.forward_button_short_press()
        
        
        
def button_forward_held_callback(channel):
    global LAST_BUTTON_HELD
    LAST_BUTTON_HELD = True
    logger.debug("Forward Button Long Press!")
    aaplayer.forward_button_long_press()
 
    
def button_backward_held_callback(channel):
    global LAST_BUTTON_HELD
    LAST_BUTTON_HELD = True
    logger.debug("Back Button Long Press!")
    aaplayer.back_button_long_press()
 
#TODO: Move this logic into the players.
def button_shuffle_current_songs(channel):
    global LAST_BUTTON_HELD
    LAST_BUTTON_HELD = True
    logger.debug("Play Long Button Press!")
    #aaplayer.shuffle_unshuffle_tracks()
    aaplayer.middle_button_long_press()


    

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
    if (interrupt_time - LAST_BUTTON_TIME > 500):
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
        logger.debug(f'The value {search_term} was not found in the column {search_column}.')
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
    
    repeat = lookup_field_by_field(DB, 'rfid', rfid_code, 'repeat')  
    if repeat == 1:
        return True
    else:
        return False


def is_album_remember_position(rfid_code):
    """
    Detremines if the album should have it's position remembered and used as the starting point.
    
    Attributes:
    - rfid_code: an RFID code for a card

    Returns:
    Boolean: True if the albums should be played from the last place it stopped or paused. False otherwise.            
    """
    
    logger.debug(f'Checking if RFID {rfid_code} should remember position.')
    remember = lookup_field_by_field(DB, 'rfid', rfid_code, 'remember_position')  
    if remember == 1:
        logger.debug(f'YES RFID {rfid_code} should remember position.')
        return True
    else:
        logger.debug(f'NO RFID {rfid_code} should not remember position.')
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

    #2024-03-09 added this code so I could add postfix numbers to the lables to force a sort order
    # Assuming 'DB' is your DataFrame and 'label' is the string you're looking for.
    matching_rows = DB[DB['labels'].astype(str).str.contains(label)].copy()

    # Extract the numeric part from the 'labels' column and fill non-numeric parts with a large number for proper sorting
    matching_rows['sort_key'] = matching_rows['labels'].str.extract(r':(\d+)$').fillna(9999).astype(int)

    # Sort by the new column 'sort_key'
    matching_rows = matching_rows.sort_values(by='sort_key')

    # Drop the 'sort_key' column if you don't want it in the final result
    matching_rows = matching_rows.drop(columns=['sort_key'])
    
    
    #2024-03-09 This was the old label matching code.
    #matching_rows = DB[DB['labels'].astype(str).str.contains(label)]
    
    
    
    #DB.query(condition)['folder']
    matching_folders = matching_rows.query("folder != '"+BLANK+"'")['folder']
    
    logger.debug(f'Printing sorted label albums')
    for folder in matching_folders:
        logger.debug(folder)
    

    #2024-05-03 moved this because it was causing an exception    
    #if(shuffle_albums):
    #    random.shuffle(matching_folders_list)
    #else:
    #    matching_folders_list.sort()


    # Convert the matching folders to a list
    matching_folders_list = matching_folders.tolist()

    if(shuffle_albums):
        random.shuffle(matching_folders_list)
    #else:
    #    matching_folders_list.sort()
    
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
        else:
            ## There is supposed to be a folder for every album 
            ## but sometimes you'll get a label or genre that gets picked up
            ## in label card or genre card. We want to ignore those
            
            ## so lets look at the child folder name 
            last_directory = os.path.basename(os.path.normpath(folder))
           
            if (last_directory.startswith("label:") or last_directory.startswith("genre:")):
                ## We should ignore this one
                logger.debug(f"Skipping folder {folder} because it's a label or genre db row.")
            else:
                ## It's not a label or genre card so it should have a folder
                ## If it doesn't exist, log the error so it's known. 
                logger.error(f'Could not find folder: {folder}')
        
        
        
    """This is now handled by the music player. 
        if(shuffle_tracks == True):
        random.shuffle(all_tracks) """ 
    
    
    #print (all_tracks)
    for mp3_file in all_tracks:
        logger.debug(f'Found Track: {mp3_file}...') 

    # Filter out blocked tracks before returning
    filtered_tracks = filter_blocked_tracks(all_tracks)
    
    return filtered_tracks   





"""
#################################################################################

            Blocked Tracks Management

#################################################################################"""

def load_blocked_tracks():
    """
    Loads blocked tracks from JSON file into memory.
    Returns the blocked tracks dictionary.
    """
    global BLOCKED_TRACKS
    
    try:
        if os.path.exists(BLOCKED_TRACKS_FILE):
            with open(BLOCKED_TRACKS_FILE, 'r') as f:
                BLOCKED_TRACKS = json.load(f)
                logger.info(f"Loaded {len(BLOCKED_TRACKS)} blocked tracks from {BLOCKED_TRACKS_FILE}")
        else:
            BLOCKED_TRACKS = {}
            logger.info("No blocked tracks file found, starting with empty blocked list")
    except Exception as e:
        logger.error(f"Error loading blocked tracks: {e}")
        BLOCKED_TRACKS = {}
    
    return BLOCKED_TRACKS

def save_blocked_tracks():
    """
    Saves the blocked tracks hashmap to JSON file.
    """
    global BLOCKED_TRACKS
    
    try:
        with open(BLOCKED_TRACKS_FILE, 'w') as f:
            json.dump(BLOCKED_TRACKS, f, indent=2)
        logger.debug(f"Saved {len(BLOCKED_TRACKS)} blocked tracks to {BLOCKED_TRACKS_FILE}")
    except Exception as e:
        logger.error(f"Error saving blocked tracks: {e}")

def add_blocked_track(track_filename):
    """
    Adds a track to the blocked tracks list.
    
    Parameters:
    - track_filename: The full path to the track file
    """
    global BLOCKED_TRACKS
    
    if track_filename and track_filename.strip():
        # Use just the filename as the key for easier matching
        filename = os.path.basename(track_filename)
        BLOCKED_TRACKS[filename] = {
            "date_blocked": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "full_path": track_filename,
            "reason": "user_request"
        }
        save_blocked_tracks()
        logger.info(f"Track blocked: {filename}")

def is_track_blocked(track_filename):
    """
    Checks if a track is in the blocked list.
    
    Parameters:
    - track_filename: The full path to the track file
    
    Returns:
    - True if the track is blocked, False otherwise
    """
    global BLOCKED_TRACKS
    
    if not track_filename:
        return False
    
    filename = os.path.basename(track_filename)
    is_blocked = filename in BLOCKED_TRACKS
    
    if is_blocked:
        logger.debug(f"Track is blocked: {filename}")
    
    return is_blocked

def filter_blocked_tracks(tracks):
    """
    Filters out blocked tracks from a list of tracks.
    
    Parameters:
    - tracks: List of track file paths
    
    Returns:
    - List of tracks with blocked tracks removed
    """
    if not tracks:
        return tracks
    
    filtered_tracks = [track for track in tracks if not is_track_blocked(track)]
    
    blocked_count = len(tracks) - len(filtered_tracks)
    if blocked_count > 0:
        logger.info(f"Filtered out {blocked_count} blocked tracks from playlist")
    
    return filtered_tracks


"""
#################################################################################

            Album of the day, Random Albums, & Email Mechanics

#################################################################################"""

def play_album_of_the_day():
    global DB, ALBUM_OF_THE_DAY_RFID
    
    #found_rfid = get_album_of_the_day_rfid()
    ## make sure we're using the latest album of the day
    set_album_of_the_day_date_and_rfid()
    
    ## pass this to the music card handler
    ## so the album of the day behaves the same as all other music.
    music_card_handler(ALBUM_OF_THE_DAY_RFID)

    

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
    global DB, ALBUM_OF_THE_DAY_DATE, ALBUM_OF_THE_DAY_RFID, FLAG_AOTD_ENABLED, IS_SYSTEM_DATE_SET
    rfid = BLANK
    
    
    ## update the system data so that you use the right date dfor the AOTD.
    if (IS_SYSTEM_DATE_SET == False):
        set_ststem_date() 
    
    
    #use today's date YYYYMMDD as the seed for pulling random albums
    # the goal is to get the same answer all day
    todays_seed = get_album_of_the_day_seed() 
    logger.debug(f'Looking up album for today: {todays_seed}...')
    
    if ALBUM_OF_THE_DAY_DATE == todays_seed:
        # the date and RFID were already set
        
        # return false so they know there's not a new album of the day.
        return False
    else:
        
        rfid = get_album_of_the_day_rfid(todays_seed)
        
        logger.debug(f'Album of the day RFID is: {rfid}...')
        
        ALBUM_OF_THE_DAY_RFID = rfid  # Store the rfid that passed the check
        ALBUM_OF_THE_DAY_DATE = todays_seed # store the current album of the day date/seed
        
        
        
        folder = replace_non_strings(lookup_field_by_field(DB, "rfid", rfid, "folder"))
        
        if check_aotd_cache_for_today(todays_seed) == None and FLAG_AOTD_ENABLED == True:
            ## We appear to have't saveded the album of the day in the cache. 
            ## I guess this is our first time doing this. 
            update_aotd_cache(todays_seed, rfid, folder)
            try:
                aareporter.log_aotd(folder, rfid)
            except Exception as e:
                    logger.error(f'Error while writing AOTD to the google sheet., an unexpected error occurred: {e}')
            
        return True
 

def get_album_of_the_day_seed():
    """
    Returns: (int) the album of the day seed in YYYYMMDD
    """
    global PARAM_COMMAND_LINE_SEED_DAY
    
    if PARAM_COMMAND_LINE_SEED_DAY != None:
        ## someone passed in a fake date use that instead
        return PARAM_COMMAND_LINE_SEED_DAY
    else:
        ## we didn't get a fake date from the command line
        ## so use the real date. 
        return datetime.today().strftime('%Y%m%d')


def get_album_of_the_day_rfid(seed_for_random_lookup=get_album_of_the_day_seed()):
    """
        pulls a random RFID out of the database making sure it's hasn't been the album of 
        the day reciently
    """
    global DB, DB_AOTD_CACHE, AOTD_REPEAT_LIMIT
    rfid = BLANK
    
    logger.debug(f'Getting Album of the day')
    
    
    ## Let's see if there already was an album of the day
    found_rfid = check_aotd_cache_for_today(seed_for_random_lookup)  # This will store the found rfid value
    
    if found_rfid != None:
        logger.debug(f'Found the album of the day in the disk cache.')
        ## We appear to have already saved the album of the day in the cache. So no need to look it up again. 
        return found_rfid
    
    ## Let's see if there's a specific album assigned for today
    found_rfid = get_assigned_aotd_for_today(seed_for_random_lookup)
    if found_rfid != None:
        logger.debug(f'AOTD Specified for todays date.')
        ## We appear to have an album of the day assigned to this day so no need to pick a random one.
        ## Let's use the one in the DB.
        return found_rfid
    
    
    ## we're going to grab all the albums that can be used as the album of the day. Then we'll see what happens. 
    potential_albums = pd.DataFrame()
    
    if is_between_thanksgiving_and_christmas_inclusive():
        """     *                                                          *
                                             *                  *        .--.
                 \/ \/  \/  \/                                        ./   /=*
                   \/     \/      *            *                ...  (_____)
                    \ ^ ^/                                       \ \_((^o^))-.     *
                    (o)(O)--)--------\.                           \   (   ) \  \._.
                    |    |  ||================((~~~~~~~~~~~~~~~~~))|   ( )   |     \
                     \__/             ,|        \. * * * * * * ./  (~~~~~~~~~~~)    \
              *        ||^||\.____./|| |          \___________/     ~||~~~~|~'\____/ *
                       || ||     || || A            ||    ||          ||    |   
                *      <> <>     <> <>          (___||____||_____)   ((~~~~~|   *
              
        ## starting on thanksgiving we play Christmas Albums as the album of the day until and including Christmas day 
        ## anything with a 1 in the christmas_random column is fair game"""
        
        """
        2023-12-30 swapping this line out. It's possible to have the list not return any results because we're counting 
        the size of the DB before checking how many albums are available. It's possible that we could have a DB so big
        but not all the albums are available for selection, so we end up at a future date with no available albums
        
        available_albums = DB[(~DB['rfid'].isin(aotd_block_list['rfid'])) & (DB['christmas_aotd'] == 1)]
        
        """
        # 2024-08-30 replaced this line with one that deals with blank RFIDs and lable/genre cards
        #potential_albums = DB[DB['christmas_aotd'] == 1]
        
        potential_albums = DB[
            (DB['christmas_aotd'] == 1) &      # Only choose Christmas Albums of the day
            (DB['rfid'].notna()) &             # No blank 'rfid' rfids
            (DB['rfid'] != '') &               # another way to say No blank 'rfid' rfids
            (DB['label_card'] != 1) &          # Don't accept 'label_card' label cards for AOTD
            (DB['genre_card'] != 1)            # Don't accept 'genre_card' genre cards for AOTD
        ]
        logger.debug(f'Christmas time! Got the list of potential Christmas albums.')
        
    else:

        ## It's not the Christmas season, so play everything but christmas music
        ## Filter the catalog DataFrame to only include rows where the album hasn't been played 
        ## reciently 
        """
        2023-12-30 swapping this line out. It's possible to have the list not return any results because we're counting 
        the size of the DB before checking how many albums are available. It's possible that we could have a DB so big
        but not all the albums are available for selection, so we end up at a future date with no available albums
        
        available_albums = DB[(~DB['rfid'].isin(aotd_block_list['rfid'])) & (DB['exclude_from_random'] != 1)]
        
        """
        
        # Get all the albums that aren't excluded dfrom the album of the day list
        #potential_albums = DB[DB['exclude_from_random'] != 1]



        potential_albums = DB[
            (DB['exclude_from_random'] != 1) &  # Only choose albums not excluded from AOTD = 'exclude_from_random' not being 1
            (DB['rfid'].notna()) &             # No blank 'rfid' rfids
            (DB['rfid'] != '') &               # another way to say No blank 'rfid' rfid
            (DB['label_card'] != 1) &          # Don't accept 'label_card' label cards for AOTD
            (DB['genre_card'] != 1)            # Don't accept 'genre_card' genre cards for AOTD
        ]

        

        logger.debug("Got the list of potential albums.")
        
      
# figure out how many possible albums there are. You need this to make sure you don't 
    # remove too many albums using the AOTD cache.    
    potential_size = len(potential_albums)
    logger.debug(f'Potential Album Count: {potential_size}')
        
    ## get the album of the day cache limited to the AOTD_REPEAT_LIMIT * the lenght of the available tracks.
    try:
        aotd_block_list = DB_AOTD_CACHE.tail(int(len(potential_albums)*AOTD_REPEAT_LIMIT))
        block_list_size = len(aotd_block_list)
        logger.debug(f'Block List Album Count: {block_list_size}')

    except (FileNotFoundError, pd.errors.EmptyDataError):
        # If the albumoftheday.csv file is not found or empty, then all albums in catalog are available
        aotd_block_list = pd.DataFrame(columns=DB_AOTD_CACHE.columns)  # Empty DataFrame with same columns
        logger.debug(f'Found no blocked albums. Created blank list')
    
    ## Remove any albums that have been the album of the day in the number of days== total potential albums times the
    ## AOTD_REPEAT_LIMIT. That makes it so that at max, 80% of the potential albums can be excluded. This way you don't
    ## get into a situation where you remove all the albums.
    available_albums = potential_albums[~potential_albums['rfid'].isin(aotd_block_list['rfid'])]
    
    
    ##This was here for agressive debugging. 
    # print_dataframe_with_line_breaks(available_albums, ['folder', 'rfid'])
    
    sample_size = len(available_albums)
    logger.debug(f'{sample_size} aotd albums in DB after removing reciently played albums.')
    
    todays_rfid_list = available_albums.sample(n=sample_size, random_state=int(seed_for_random_lookup))['rfid'].tolist()
    
    ## And just to get silly and make sure we're not following some sort of pattern
    random.shuffle(todays_rfid_list)

    #print(todays_rfid_list)
    # This was replaced by the above code.
    # found_rfid = None  # This will store the found rfid value

    for rfid in todays_rfid_list:
        #if rfid == BLANK or isinstance(rfid, float) or not str(rfid).isdigit():
        if rfid == BLANK:
            logger.debug(f'Skipping rfid "{rfid}"')
            continue
        else:
            found_rfid = rfid  # Store the rfid that passed the check
            break
    
    if found_rfid == None:
        todays_rfid_list_length = len(todays_rfid_list)
        logger.error(f'No album of the day found out of todays_rfid_list.\ntodays_rfid_list length is {todays_rfid_list_length} rfids.\nThe list is:\n{todays_rfid_list}')
    else:
        logger.debug(f'AOTD RFID = "found_rfid".')

    return found_rfid

# Updated function to print only 'folder' and 'rfid' columns with line breaks
def print_dataframe_with_line_breaks(df, columns):
    # Select only the specified columns
    df_selected = df[columns]

    # Convert the selected columns to a list for the header
    header = " | ".join(df_selected.columns)
    print(header)
    print("-" * len(header))
    
    # Iterate over the selected DataFrame rows
    for index, row in df_selected.iterrows():
        # Convert each row of the selected columns to a string
        row_string = " | ".join(str(row[col]) for col in columns)
        print(row_string)
        print()  # Blank line for separation



def thanksgiving(year):
    """
    Figures out when Thanksgiving is for the provided year.
    
    Parameters:
    - year: a 4 digit year like 2023
    
    Returns:
    Datetime: for the date of thanksgiving for the year provided
    """
    # November is represented by 11 in the month list
    weeks = calendar.monthcalendar(year, 11)
    
    # If there's a Thursday in the first week of the month
    if weeks[0][calendar.THURSDAY]:
        # Return the date of the fourth Thursday
        day = weeks[3][calendar.THURSDAY]
    else:
        # Otherwise, return the date of the fourth Thursday from the second week onward
        day = weeks[4][calendar.THURSDAY]
    
    return datetime(year, 11, day).date()


def find_nth_day(year: int, month: int, day_of_week: str, occurrence: int) -> str:
    """
    Finds the date of the nth occurrence of a specific day of the week in a given month and year.
    
    Parameters:
        year (int): The year for which the date is to be found.
        month (int): The month for which the date is to be found. (1 for January, 2 for February, etc.)
        day_of_week (str): The day of the week to find. Must be one of "Monday", "Tuesday", "Wednesday",
                           "Thursday", "Friday", "Saturday", or "Sunday".
        occurrence (int): The occurrence of the day to find. For example, 1 for the first occurrence of the day,
                          2 for the second, and so on.
    
    Returns:
        str: The date of the specified occurrence of the day in YYYYMMDD format.
    
    Raises:
        ValueError: If `day_of_week` is not a valid day name.
    """
    # Map day of the week from string to the corresponding calendar module constant
    days = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6}
    if day_of_week not in days:
        raise ValueError(f"Invalid day_of_week: {day_of_week}. Must be one of {list(days.keys())}.")
    
    day_of_week_num = days[day_of_week]

    # Use datetime to find the first day of the month
    first_day_of_month = datetime(year, month, 1)
    first_day_of_week = first_day_of_month.weekday()

    # Calculate the difference between the target day of the week and the first day of the month
    days_until_target = (day_of_week_num - first_day_of_week) % 7

    # Calculate the date of the first occurrence of the target day
    first_occurrence = first_day_of_month + timedelta(days=days_until_target)

    # Calculate the date of the nth occurrence
    nth_occurrence = first_occurrence + timedelta(weeks=occurrence-1)

    # Return the date formatted as YYYYMMDD
    return nth_occurrence.strftime('%Y%m%d')







def is_between_thanksgiving_and_christmas_inclusive():
    """
    Determines if the current date is between Thanksgiving and Christmas inclusive
    
    Returns: 
    Boolean: True if today is between Thanksgiving and Christmas inclusive. False otherwise.
    
    """
    global PARAM_COMMAND_LINE_SEED_DAY
    
    
    current_date = datetime.now().date()
    
    if PARAM_COMMAND_LINE_SEED_DAY != None:
        ## we recieved a command line date, so we're going to use that
        ## for the current date
        current_date = datetime.strptime(PARAM_COMMAND_LINE_SEED_DAY, "%Y%m%d").date()

    
    #current_date = datetime(2023, 12, 26)
    thanksgiving_date = thanksgiving(current_date.year)
    christmas_date = datetime(current_date.year, 12, 25).date()
    
    return thanksgiving_date <= current_date <= christmas_date
     
def get_assigned_aotd_for_today(date_to_check):
    """
    Given the provided date, check if there is an album assigned.
    
    Parameters:
    -date_to_check: a string in the format YYYYMMDD for the date to check or 
                    the name thanksgiving
    
    Returns: The RFID of the album of the day for that day if one is defined in the DB
            otherwise it returns None
    """                
    global DB
    
    ## first lets get the parts we need
    year = date_to_check[:4]
    month = date_to_check[4:6]
    monthday = date_to_check[4:]
    
    
    aotd_rfid = lookup_field_by_field(DB, 'aotd_date', monthday, 'rfid')
    
    ## if the date provided matches a field, then return that rfid
    if aotd_rfid != 0:
        return aotd_rfid
    elif date_to_check == thanksgiving(int(year)).strftime('%Y%m%d'): ##if it's thanksgiving
        ##checking if it's thanksgiving
        aotd_rfid = lookup_field_by_field(DB, 'aotd_date', "thanksgiving", 'rfid')
        if aotd_rfid != 0:
            return aotd_rfid
    elif date_to_check == find_nth_day(int(year), 2, "Monday", 3): ##if it's President's day
        ##checking if it's President's day
        aotd_rfid = lookup_field_by_field(DB, 'aotd_date', "presidentsday", 'rfid')
        if aotd_rfid != 0:
            return aotd_rfid
    
    return None
    

def schedule_handler_send_aotd():
    """
    This function makes sure everything is in good shape before sending the album of the day.
    """
    # make sure we really know the time.  
    set_ststem_date() 
    if not IS_SYSTEM_DATE_SET:
        logger.error(f"Skipping AOTD email because the system time hasn't been set.")
        return

    #make sure the album of the day is up to date.
    set_album_of_the_day_date_and_rfid()

    #send the email with the album of the day.
    send_album_of_the_day_email(ALBUM_OF_THE_DAY_RFID)

   
def schedule_handler_send_receint_errors():
     
    if not IS_SYSTEM_DATE_SET:
        logger.error(f"Skipping sending logs home due to time system time not being synchronized.")
        return
    aareporter.send_logs_home()




def schedule_handler_shutdown_player():
    """
    This function shuts down the player at 3:15am Eastern Time.

    This is to address times when the player is left on overnight.
    """
    logger.debug("Scheduled memory cleanup of the players.")
    aaplayer.cleanup_memory()
    time.sleep(.5)
    ## we need to restart the player after shutting it down. 
    ## so that the player doesn't impload when we call functions like play_pause_track()
    ## when the player isn't started up
    gc.collect()
    logger.debug("Garbage collection complete.")

    

def find_card_png(directory):
    """
    Searches a directory for the first .png file and returns its name.
    If no .png file is found, returns None.
    
    Args:
        directory (str): The path of the directory to search.
        
    Returns:
        str or None: The name of the first .png file found, or None if no .png file is found.
    """
    if not os.path.isdir(directory):
        return None

    for filename in os.listdir(directory):
        if filename.endswith('.png'):
            return directory + '/' + filename
    return None

def send_album_of_the_day_email(rfid, send_to_only_me=False):
    logger.debug(f'Sending an album of the day email...')

    album_name = replace_non_strings(lookup_field_by_field(DB, 'rfid', rfid, 'Album'))
    album_folder_name = replace_non_strings(lookup_field_by_field(DB, 'rfid', rfid, 'folder'))
    artist_name = replace_non_strings(lookup_field_by_field(DB, 'rfid', rfid, 'Artist'))
    album_url = replace_non_strings(lookup_field_by_field(DB, 'rfid', rfid, 'url'))
    subject = replace_non_strings(lookup_field_by_field(DB, 'rfid', rfid, 'aotd_greeting'))
    loaded_hq = replace_non_strings(lookup_field_by_field(DB, 'rfid', rfid, 'loaded_hq'))
    album_story = replace_non_strings(lookup_field_by_field(DB, 'rfid', rfid, 'album_story'))
    
    album_card_image = find_card_png(LIBRARY_CACHE_FOLDER + album_folder_name)
    if album_card_image:
        logger.debug(f"The first .png file found is: {album_card_image}")
    else:
        logger.debug(f'No .png files found in {LIBRARY_CACHE_FOLDER + album_folder_name}.')
        album_card_image = None

    

    if (subject == BLANK):
        subject = album_name
        #Add this in if you're testing 
        #subject = subject + datetime.now().strftime('%H%M%S')


    body = f"""<div style="font-size: .8em;">{"Currently playing:" if send_to_only_me else "Today's album of the day is:"}</div><br>"""
    
    if album_url != "":
        body = body + f'<a href="{album_url}">'
    
    body = body + f"""<b style="font-size: 1.6em;">{album_name}</b>"""

    if (artist_name != "" and artist_name != "Various Artists"):
        body = body + "<BR>"

        body = body + '<div style="font-size: 1em; padding-top:.5em;padding-left: 2.5em;">'
        body = body + "by "  + artist_name + "</div>"
        
    if album_url != "":
        body = body + f'</a>'

    # Check if the image file exists
    if (album_card_image):
        body = body + f"""<br>
        <img src="cid:image1" alt="album card" style="width:90%; max-width:600px; height:auto;">"""

    # Add album story if it exists
    if album_story and album_story != BLANK:
        # Check if the text contains Markdown syntax
        has_markdown = any(char in album_story for char in ['*', '#', '-', '>', '`', '['])
        
        if has_markdown:
            try:
                # Convert Markdown to HTML
                formatted_story = markdown.markdown(album_story)
            except Exception as e:
                logger.error(f"Error converting Markdown to HTML: {e}")
                # Fallback to plain text if Markdown conversion fails
                formatted_story = album_story.replace('\n', '<br>')
        else:
            # Plain text - just convert newlines to HTML breaks
            formatted_story = album_story.replace('\n', '<br>')
            
        body = body + f"""<br><br>
        <div style="font-size: 1em; line-height: 1.5; padding: 1em; background-color: #f8f8f8; border-radius: 5px;">
            {formatted_story}
        </div>"""

    body = body + f"""</b>
    <BR><BR><BR><BR>
    <BR><BR><BR><BR>
    <BR><BR><BR><BR>
    <BR><BR><BR><BR>
    """
    
    '''if loaded_hq == "y":
        body = body + f"""
        <div style="font-size: smaller; color: grey;">Best recording quality uploaded. Use the hammer to play the album.</div> 
        <BR><BR><BR><BR>       
        """
    else:
        body = body + f"""
        <div style="font-size: smaller; color: grey;">Uploaded album quality is <b>meh</b>. Use the hammer to play the album.</div>  
        <BR><BR><BR><BR>      
        """
    '''
    # Email settings
    SMTP_SERVER = 'smtp.gmail.com'
    SMTP_PORT = 587
    SENDER_EMAIL = CONFIG.EMAIL_SENDER_ADDRESS  # Change this to your Gmail
    SENDER_PASSWORD = CONFIG.EMAIL_SENDER_PASSWORD  # Change this to your password or App Password

    msg = MIMEMultipart('related')
    msg['Subject'] = subject
    msg['From'] = CONFIG.EMAIL_SENDER_NAME
    msg['To'] = CONFIG.EMAIL_SEND_TO_ONLY_ME if send_to_only_me else CONFIG.EMAIL_SEND_TO  # The receiver's email

    # Attach the HTML body to the email
    msg.attach(MIMEText(body, 'html'))

    # Open the image file and attach it to the email if it exists
    if (album_card_image):
        with open(album_card_image, 'rb') as img:
            mime_image = MIMEImage(img.read())
            # Set Content-ID for referencing the image in HTML
            mime_image.add_header('Content-ID',  '<image1>')
            #mime_image.add_header('Content-ID', f'<image1>; filename="{album_card_image}"')
            # Remove Content-Disposition header (not needed for inline images)
            mime_image.add_header('Content-Disposition', f'inline; filename="Card"')
            msg.attach(mime_image)
    



    try:
        # Send the email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.starttls()  # Upgrade the connection to secure encrypted SSL/TLS connection
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)
            logger.debug(f'Email sent successfully!')
    except Exception as e:
        print(f"Error occurred: {e}")


def play_list_of_albums_by_rfid(album_rfid_list):
    
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
        aaplayer.play_tracks(tracks, False, False, False, 0)
    else:
        logger.warning (f'No tracks found for folder {album_folder}.')

    return tracks



def play_random_albums():
    """
        Gets CONFIG.RANDOM_ALBUMS_TO_PLAY from the DB as long as they are labeled with 
        'random' and the plays them.
    """
    global DB
    
    album_rfid_list = []
    
    
    
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

    
    """  This code was replaced by the playlist of albums by RFID function boil
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
        aaplayer.play_tracks(tracks, False, False, False, 0)
    else:
        logger.warning (f'No tracks found for folder {album_folder}.')

    return tracks
    """

    return play_list_of_albums_by_rfid(album_rfid_list)

    

def play_aotd_history_albums():
    """
    Finds and plays the album of the Day for the last eight days, excluding the current day.
    Albums will pay in reverse Chronological order so that it starts with yesterday and then the 
    day before and so on until it's played the entire previous week plus one day. 


    Returns: A list of RFID values. If there aren't enough rows, it returns as many as available.
    """
    global DB_AOTD_CACHE
    
    # If there are no rows or just one row, return an empty list as we cannot exclude the last row
    if len(DB_AOTD_CACHE) <= 1:
        logger.debug("Not enough rows in the cache to retrieve RFIDs.")
        return []

    # Calculate the start index: at most, get 8 rows, but if fewer are available, get as many as possible
    start_index = max(-len(DB_AOTD_CACHE), -9)  # This dynamically adjusts if there are fewer rows available
    
    # Slice the last 9 rows and exclude the last one, then reverse the order
    album_rfid_list = DB_AOTD_CACHE['rfid'].iloc[start_index:-1][::-1].tolist()
    
    return play_list_of_albums_by_rfid(album_rfid_list)





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


def get_aotd_rfid_for_date(date_str):
    # Filter the DataFrame to find the row with the matching date
    result = DB_AOTD_CACHE[DB_AOTD_CACHE['date'] == date_str]
    
    logger.debug(f"Looking up AOTD RFID for {date_str}.")

    # Check if a matching date was found
    if not result.empty:
        logger.debug(f"Found RFID {result['rfid'].values[0]}.")
        return result['rfid'].values[0]
    else:
        logger.debug(f"No RFID Found in AOTD Cache.")
        return None

    
def get_last_aotd_cache_date():
    """
    Gets the date string for the last album of the day that was recorded.
    
    Returns: The last date an album of th day was recorded. None otherwise
    """
    global DB_AOTD_CACHE
    
    if not DB_AOTD_CACHE.empty:
        return DB_AOTD_CACHE['date'].iloc[-1]
    else:
        return None

def send_email_with_remove_request(current_track_for_email):
    """
    sends an email with current_track_for_email 
    """
    logger.debug(f'Sending request to remove email...')

    logger.debug(f'Full path: {current_track_for_email}')
    current_datetime = datetime.now()
    
    formatted_time =  current_datetime.strftime('%H:%M:%S')
    
    # Split by directory delimiter
    parts = current_track_for_email.split('/')

    # Skip the first three directories and join the rest
    album_and_track_name = '/'.join(parts[2:])
    logger.debug(f'album_and_track_name: {album_and_track_name}')
    
    
    body = f"""<br><br><div style="font-size: 1.2em; font-weight: bold;">{parts[2]}</div><br>"""
    body += f"""<div style="font-size: 1.2em; font-weight: bold; color: RED;">{parts[3]}</div><br>"""
    body += f"""<br><br>"""

    body += f"""
        <div style="font-size: smaller; color: grey;">{album_and_track_name}</div> 
        <BR><BR>     
        """
    
    # Email settings
    SMTP_SERVER = 'smtp.gmail.com'
    SMTP_PORT = 587
    SENDER_EMAIL = CONFIG.EMAIL_SENDER_ADDRESS  # Change this to your Gmail
    SENDER_PASSWORD = CONFIG.EMAIL_SENDER_PASSWORD      # Change this to your password or App Password

    
          
    msg = MIMEMultipart('related')                  
    msg['Subject'] = f'Remove Track Request {formatted_time}'
    msg['From'] = CONFIG.EMAIL_SENDER_NAME_FOR_INFO_MESSAGES
    msg['To'] = CONFIG.EMAIL_SEND_TO_FOR_INFO_MESSAGES  # The receiver's email
    # Attach the HTML body to the email
    msg.attach(MIMEText(body, 'html'))


    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.starttls()  # Upgrade the connection to secure encrypted SSL/TLS connection
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)
            logger.debug(f'Email sent successfully!')
    except Exception as e:
        print(f"Error occurred: {e}")


def speak_current_track():
    
    logger.debug(f'Attempting to speak the album and track names.')
    
    ##play audio feedback so the user knows the card tap worked
    ## it'll take a second before the audio plays back
    aaplayer.play_feedback(CONFIG.FEEDBACK_PROCESSING)
    
    try:
        current_track_for_email = aaplayer.get_current_track()
        logger.debug(f'Processing track {current_track_for_email}.')

        # Split by directory delimiter
        parts = current_track_for_email.split('/')

        # Assign album and track to separate variables
        album_name = parts[-2]
        track_name_with_extension = parts[-1]

        # Use regex to extract the disk and track number if formatted as 'disk-track'
        match = re.match(r'(\d+)-(\d+)', track_name_with_extension)
        if match:
            disk_number = str(int(match.group(1)))  # Remove leading zeros from disk number
            track_number = str(int(match.group(2)))  # Remove leading zeros from track number
        else:
            # Fallback to just track number extraction if no dash is found
            match = re.match(r'(\d+)', track_name_with_extension)
            disk_number = ''  # Default value if disk number is not applicable
            track_number = str(int(match.group(1))) if match else ''

        # Remove track/disk number, metadata in brackets, and either file extension from track name
        #file_name = re.sub(r'^\d+(-\d+)? - |\s*\[.*?\]\s*|\.webm?\.mp3$', '', track_name_with_extension)

        # Remove track/disk number and clean up the file name
        file_name = re.sub(r'^\d+(-\d+)?\s', '', track_name_with_extension)  # Remove the initial numbers and any spaces following them
        # Adjusted regex to correctly remove .mp3 and .webm.mp3
        file_name = re.sub(r'\.webm?\.mp3$', '', file_name)

        # Correctly removing .mp3 extensions
        file_name = re.sub(r'\.mp3$', '', file_name)
    
        # Remove periods from the file name, but preserve any extension handling
        file_name = re.sub(r'\.', '', file_name)
    
        # Check if the remaining file_name is just digits (and possibly spaces), clear it if so
        if re.fullmatch(r'\d+', file_name.strip()):
            file_name = ''

        # Build the description string based on available data
        description_parts = [album_name]
        if disk_number:
            description_parts.append(f"Disk {disk_number}")
        if track_number:
            description_parts.append(f"Track {track_number}")
        if file_name:
            description_parts.append(file_name)

        # Join all parts into a single string with proper formatting
        description = ". ".join(description_parts) + '.'
        
        logger.debug(f'Text to convert to speech: {description}')
        
        try:
            ## get the spoken audio from google in an mp3        
            logger.debug(f'Getting mp3 from google')
            tts = gTTS(text=description, lang='en')
            tts.save(CONFIG.TEMP_SPEECH_MP3)  # Save the audio file
        
        
            ## we need to convert to wave because pygame can't play the mp3 format outputted by google.
            logger.debug(f'Converting mp3 to wav')
            # Command to convert MP3 to WAV using ffmpeg
            #command = ['ffmpeg', '-i', CONFIG.TEMP_SPEECH_MP3, CONFIG.TEMP_SPEECH_WAV, '-y']  # -y to overwrite without asking
        
            command = [
                'ffmpeg',
                '-i', CONFIG.TEMP_SPEECH_MP3,  # Input file
                '-filter:a', 'volume=1.6',  # Increase volume by 50%
                CONFIG.TEMP_SPEECH_WAV,  # Output file
                '-y'  # Overwrite output file without asking
            ]
            subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        
            logger.debug(f'Playing the resulting audio.')
        
        
            aaplayer.play_speech(CONFIG.TEMP_SPEECH_WAV)
        except:
            logger.debug(f'Something went wrong getting or saving the audio.')
            aaplayer.play_feedback(CONFIG.FEEDBACK_AUDIO_NOT_FOUND)
        
        # Now track_number holds the digits at the beginning of track_name, if any
    
    except Exception as e:
        ## if anything goes wrong, write it to a log file.
        ## Only Errors will be logged. 
    
        logger.error(f"An exception occurred while trying to speak the album and track name: {e}")
    



"""
#################################################################################

           Command line arguments and validation

#################################################################################"""

    
def validate_seed(value):
    """Validates if the provided value matches the 8-digit format."""
    if not re.match("^[0-9]{8}$", value):
        raise argparse.ArgumentTypeError("seed must be in 8-digit format")
    return value

def main(email_flag_set, date_seed, email_now, webdb_set, debug_set, web_report):
    global FLAG_AOTD_ENABLED, PARAM_COMMAND_LINE_SEED_DAY, FLAG_AOTD_SEND_NOW, FLAG_LOAD_DB_FROM_THE_WEB, logger, ENABLE_REPORT_TO_WEB
    
    
    logger = start_logger(debug_set)
    
    
    if email_flag_set:
        print("The AOTD will be scheduled to be sent.")
        FLAG_AOTD_ENABLED = True
    else:
        print("AOTD Email Disabled")
        
        
    if email_now:
        print("Email will be sent immediately and then the app will exit.")
        FLAG_AOTD_SEND_NOW = True
    else:
        print("First AOTD email will be sent tomorrow.")
        
        
    if webdb_set:
        print("Will load the DB from the web")
        FLAG_LOAD_DB_FROM_THE_WEB = True
    else:
        print("The DB will be loaded from cache if possible.")


    if web_report:
        ENABLE_REPORT_TO_WEB = True
    else:
       ENABLE_REPORT_TO_WEB = False 
            
    if date_seed != None:
        print(f'Using provided date seed {date_seed}')
        PARAM_COMMAND_LINE_SEED_DAY = date_seed
    else:
        print(f'No seed provided. Using the real date.')
        
    try:
        ## run the app inside this try loop so that we catch 
        ## any error that kills the app
        alchemy_app_runtime()
    except Exception as e:
        ## if anything goes wrong, write it to a log file.
        ## Only Errors will be logged. 
        
        logger.error(f"An exception occurred: {e}")
        stack_trace = traceback.format_exc()
        logger.error(f"{stack_trace}")
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process some command line parameters and flags.')

    # Determines if an AOTD will be scheduled to be sent.
    parser.add_argument('--aotd_scheduled', action='store_true', help='Set this flag if you want to activate the AOTD email.')
    

    # Determines if the AUTD will be sent as soon as the application starts. 
    parser.add_argument('--aotd_send_now', action='store_true', help='Set this flag if you want to send an email at program start. Does not require --aotd-enabled')

    # Add the seed parameter with validation but make it optional
    parser.add_argument('--seed', type=validate_seed, help='A seed value in 8-digit format.')
    
    # Add the seed parameter with validation but make it optional
    parser.add_argument('--webdb', action='store_true', help='Tells the application to load the DB from the web.')
    
    parser.add_argument('--debug', action='store_true', help='Tells the application to run in debug mode.')

    parser.add_argument('--web_report', action='store_true', help='Tells the application to save to the Web google reporting sheet.')


    args = parser.parse_args()

    main(args.aotd_scheduled, args.seed, args.aotd_send_now, args.webdb, args.debug, args.web_report)

