#import RPi.GPIO as GPIO # Import Raspberry Pi GPIO library  
import time
#rom gpiozero import Button
import logging
import sys
import os
import pandas as pd
from logging.handlers import RotatingFileHandler
import sys
import random
import time
import configfile as CONFIG
import numpy as np
import math

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


#LIBRARY_CACHE_FOLDER = "/home/matt/dev/library/"
LIBRARY_CACHE_FOLDER = "./library/" #CONFIG.LIBRARY_CACHE_FOLDER

DB_SHEET_ID = CONFIG.DB_SHEET_ID
DB_SHEET_NAME = CONFIG.DB_SHEET_ID
DB = pd.DataFrame()

APP_RUNNING = True

DB_CACHE_FOLDER = "./dbcache/"

DB_CACHE = DB_CACHE_FOLDER + "dbcache.csv"

#### THESE ARE NEW
BLANK = 'BLANK'

SUPPORTED_EXTENSIONS = ['.mp3', '.MP3', '.wav', '.WAV', '.ogg', '.OGG']


RANDOM_ALBUMS_TO_PLAY = CONFIG.RANDOM_ALBUMS_TO_PLAY

"""
This is used to deal with hardware duplicate button pushes and RF bleed between GPIO pins.
"""
LAST_BUTTON_TIME = 0;


"""
Track if the last button push was to skip to the next album
"""
LAST_BUTTON_HELD = False;

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



"""
Returns True if the last button action was a held button.      
"""
def last_button_held():
    global LAST_BUTTON_HELD
    
    current_value = LAST_BUTTON_HELD
    LAST_BUTTON_HELD = False
    return current_value
    
    




def button_callback_16(channel):
    logger.info("16")
    
    if (my_interrupt_handler(channel) and not last_button_held()):
        logger.info("Previous Track Button was pushed!")
        #aaplayer.prev_track()

def button_callback_15(channel):
    logger.info("15")
    if (my_interrupt_handler(channel) and not last_button_held()):
        logger.info("Play/Pause Button was pushed!")
        #aaplayer.play_pause_track()
    
def button_callback_13(channel):
    logger.info("13")
    if (my_interrupt_handler(channel) and not last_button_held()):
        logger.info("Next Track Button was pushed!")
        #aaplayer.next_track()


def button_forward_held_callback(channel):
    global LAST_BUTTON_HELD
    LAST_BUTTON_HELD = True
    logger.info("SKIP TO NEXT ALBUM!")


def start_button_controls():
 
    button16 = Button("BOARD16")
    button15 = Button("BOARD15")
    button13 = Button("BOARD13")


    ## Previous button
    button16.when_released = button_callback_16
    
    ## Play Pause Button
    button15.when_released = button_callback_15
    
    ## Next Button
    button13.when_released = button_callback_13
    button13.hold_time = 2
    button13.when_held = button_forward_held_callback


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
            #set_ststem_date()
            
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
            

            
            backup_cache()
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


def backup_cache():
    logging.debug('Starting backup_cache().')
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
    


def get_albums_for_label(label, shuffle_albums):

    
    logger.debug(f'Looking up albums with label: {label}...')

    
    #matching_rows = DB[DB['labels'].apply(lambda x: label in x)]
    matching_rows = DB[DB['labels'].astype(str).str.contains(label)]
    #DB.query(condition)['folder']
    matching_folders = matching_rows.query("folder != '"+BLANK+"'")['folder']
    

    # Convert the matching folders to a list
    matching_folders_list = matching_folders.tolist()

        
    matching_folders_list = [LIBRARY_CACHE_FOLDER + folder for folder in matching_folders_list]
    
    if(shuffle_albums):
        random.shuffle(matching_folders_list)
    else:
        matching_folders_list.sort() 
    
    return matching_folders_list
      
      


"""
Returns a list of the full path to tracks for a list of folders. If  shuffle_tracks == True, the resulting
    list of tracks will be randomly shuffled.
"""
def get_tracks(folders, shuffle_tracks):
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
    #for mp3_file in all_tracks:
    #    logger.debug(f'Found Track: {mp3_file}...') 

    return all_tracks   

    
def next_different_directory(file_paths, index):
    current_directory = os.path.dirname(file_paths[index])
    next_index = index + 1

    while next_index < len(file_paths):
        next_directory = os.path.dirname(file_paths[next_index])
        if next_directory != current_directory:
            logger.debug(f'New Index Found {next_index}...')
            return next_index      
        next_index += 1
    logger.debug(f'Returning to Index 0...')  
    return 0  # No different directory found after the given index


"""
    pulls a random RFID out of the database
"""
def get_random_rfid_value():
    global DB
    rfid = BLANK
    
    
    
    while rfid == BLANK or isinstance(rfid, float) or not str(rfid).isdigit():
        random_index = np.random.choice(DB.index)
        rfid = DB.loc[random_index, 'rfid']
        print(f'Found rfid: {rfid}')
    return rfid




def list_folders_in_order(dataframe):
    return dataframe['rfid'].sort_values().tolist()


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




def play_random_albums():
    global DB, RANDOM_ALBUMS_TO_PLAY
    
    
    logger.debug(f'Starting play_random_albums()')
    album_rfid_list = []
    
    
    while len(album_rfid_list) <= RANDOM_ALBUMS_TO_PLAY -1:
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
        #aaplayer.play_tracks(tracks, False )
    else:
        logger.warning (f'No tracks found for folder {album_folder}.')

    return tracks
    

def main():
    global DB, APP_RUNNING
    
    #try:
    # Load the database of RFID tags and their matching albums
    DB = load_database(False)
    
    #print(list_folders_in_order(DB))
    
    for item in play_random_albums():
        print(item)
    #print (play_random_albums())
    
    #i=0
    #while i < 100: 
        
    #    get_random_folder_value(DB)
    #    i = i+1
    
    exit()
 
""" 
    
    label_album_folder_list = get_albums_for_label("liverock", False)
    
    for album in label_album_folder_list:
        print("album: " + album)

    tracks = get_tracks(label_album_folder_list, False)

    for song in tracks:
        print("song: " + song)

 logger.info("Starting button monitor!")
"""   


#    for song in tracks:
#        print(song)
        
        
        
    
    #CURRENT_INDEX = 16
    #print()
    #print("Current Song: " + tracks[CURRENT_INDEX])
    
    #print("Next Song: " + tracks[next_different_directory(tracks,CURRENT_INDEX)])

    #print("\n\n")
    

    #start_button_controls()
    #exit()

"""
    while True:
        try: 
            time.sleep(5)
        except KeyboardInterrupt: 
            break

    logger.info("Cleaning up!")

   #    button16.close()
#    button15.close()
#    button13.close()

    logger.info("exiting!")

"""    
main()
