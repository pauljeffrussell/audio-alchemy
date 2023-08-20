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

#### THESE ARE NEW
BLANK = 'BLANK'

SUPPORTED_EXTENSIONS = ['.mp3', '.MP3', '.wav', '.WAV', '.ogg', '.OGG']

BUTTON_HOLD_DURATION = CONFIG.BUTTON_HOLD_DURATION

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
Command card for playing random albums
"""
PLAY_RANDOM_ALBUMS = CONFIG.PLAY_RANDOM_ALBUMS


"""
The number of albums to play with the PLAY_RANDOM_ALBUMS command card
"""
RANDOM_ALBUMS_TO_PLAY = CONFIG.RANDOM_ALBUMS_TO_PLAY

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
LAST_BUTTON_TIME = 0

"""
Track if the last button push was to skip to the next album
"""
LAST_BUTTON_HELD = False


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



"""
    def set_ststem_date():
  
    because the system is read only, every time you reboot the system thinks the date is 
            June 17 2023 which is when OS was set to read only.
            
            intenet requests to google fail if the system date is off too much because the system
"""      
def set_ststem_date():

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
    elif (command_code == PLAY_RANDOM_ALBUMS ):
        logger.debug('Read RFID to play random albums')
        play_random_albums()
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
Return true if the song is set to shuffle
    false otherwise            
"""                 
def is_song_shuffle(rfid_code):
    global DB
    
    suffle_songs = lookup_field_by_field(DB, 'rfid', rfid_code, 'shuffle_songs')  
    if suffle_songs == 1:
        return True
    else:
        return False
        
"""
Return true if the album is set to shuffle
   false otherwise            
"""       
def is_album_shuffle(rfid_code):
    global DB
    
    suffle_album = lookup_field_by_field(DB, 'rfid', rfid_code, 'shuffle_albums')  
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



"""
Returns a list of the paths to the library folders that match the provided genre and sub_genre
"""
def get_albums_for_genre(genre, sub_genre, shuffle_albums):
          
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
    for mp3_file in all_tracks:
        logger.debug(f'Found Track: {mp3_file}...') 

    return all_tracks   


"""
    Gets CONFIG.RANDOM_ALBUMS_TO_PLAY from the DB as long as they are labeled with 
    'random' and the plays them.
"""
def play_random_albums():
    global DB, RANDOM_ALBUMS_TO_PLAY
    
    album_rfid_list = []
    
    
    while len(album_rfid_list) <= RANDOM_ALBUMS_TO_PLAY -1:
        ## get another album
        rfid = get_random_rfid_value()
        labels = lookup_field_by_field(DB, 'rfid', rfid, 'labels')
        if 'random' in labels and rfid not in album_rfid_list:
            album_rfid_list.append(rfid)
        else:
            print("Found a non random album.")

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

"""
    pulls a random RFID out of the database
"""
def get_random_rfid_value():
    global DB
    rfid = BLANK
    
    while rfid == BLANK or isinstance(rfid, float) or not str(rfid).isdigit():
        random_index = np.random.choice(DB.index)
        rfid = DB.loc[random_index, 'rfid']
    
    #print(f'Found rfid: {rfid}')
    return rfid





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
    
    elif (label_card == 1):
        #this card is a label card. It is intended to play all of the albums with a matching lable.
        label = lookup_field_by_field(DB, 'rfid', rfid_code, 'labels')
        label_album_folder_list = get_albums_for_label(label, is_album_shuffle(rfid_code))
        tracks = get_tracks(label_album_folder_list, is_song_shuffle(rfid_code))
        
        if (len(tracks) > 0):
            logger.debug (f'Album folder exists. Playing Genre')
            aaplayer.play_tracks(tracks, is_album_repeat(rfid_code) )
    
    else:
        album_folder_name = lookup_field_by_field(DB, 'rfid', rfid_code, 'folder')
        logger.debug(f'Attemptting to play album: {album_folder_name}...')


        if album_folder_name != 0:

            album_folder = LIBRARY_CACHE_FOLDER + album_folder_name
        
        
            tracks = get_tracks([album_folder], is_song_shuffle(rfid_code))

            if (len(tracks) > 0):
                logger.debug (f'Album has tracks. Playing...')
                aaplayer.play_tracks(tracks, is_album_repeat(rfid_code) )
            else:
                logger.warning (f'No tracks found for folder {album_folder}.')    
        else:
            logger.warning(f'RFID {rfid_code} is unknown to the app. Consider adding it to the DB...')
            
      
        
        
        
        

          
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
                
             
"""def handle_rfid_read(rfid_code):
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

"""
Returns True if the last button action was a held button.      
"""
def last_button_held():
    global LAST_BUTTON_HELD
    
    current_value = LAST_BUTTON_HELD
    LAST_BUTTON_HELD = False
    return current_value
    
    
          
         
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
    
    ## Next Button
    button13.when_released = button_callback_13
    button13.hold_time = BUTTON_HOLD_DURATION
    button13.when_held = button_forward_held_callback




def main():
    global DB, APP_RUNNING
    
    #try:
    # Load the database of RFID tags and their matching albums
    DB = load_database(False)
    
    #DB['sub_genre'] = DB['sub_genre'].fillna(BLANK)
    #DB['genre'] = DB['genre'].fillna(BLANK)
    #DB['folder'] = DB['folder'].fillna(BLANK)
    #DB['labels'] = DB['labels'].fillna(BLANK)
    
    columns_to_print = ['folder', 'genre', 'sub_genre']
    print(DB[columns_to_print])
    #except:
    #    logger.warning('Failed to update blank columns.')
    
   
    
    #with pd.option_context('display.max_rows', None, 'display.max_columns', None):  # more options can be specified also
    #print(DB)

    

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
    



