import os
from urllib.parse import urlparse, parse_qs
#from yt_dlp import YoutubeDL
import pandas as pd
#import pl7 as aaplayer
#import RPi.GPIO as GPIO # Import Raspberry Pi GPIO library  
#from gpiozero import Button
#from mfrc522 import SimpleMFRC522
#import threading
import logging
from logging.handlers import RotatingFileHandler
import sys
import time
import configfile as CONFIG
import requests
import requests
import subprocess
from dateutil.parser import parse
import random


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
LIBRARY_CACHE_FOLDER = './library/' #CONFIG.LIBRARY_CACHE_FOLDER

DB_SHEET_ID = CONFIG.DB_SHEET_ID
DB_SHEET_NAME = CONFIG.DB_SHEET_ID
DB = pd.DataFrame()

APP_RUNNING = True

DB_CACHE_FOLDER = CONFIG.DB_CACHE_LOCATION

DB_CACHE = "./dbcache.csv"



#### THESE ARE NEW
BLANK = 'BLANK'

SUPPORTED_EXTENSIONS = ['.mp3', '.MP3', '.wav', '.WAV', '.ogg', '.OGG']

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
            loaded_db = pd.read_csv(db_url)
            logging.debug("SUCCESS! The DB loaded from the web.")
            
            backup_cache()
            loaded_db.to_csv(DB_CACHE, index=False)
                
            DB_LOADED = True
            return loaded_db
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
Returns a list of the paths to the library folders that match the provided genre and sub_genre
"""
def get_albums_for_genre(genre, sub_genre):
          
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
        
        condition = condition + " and folder != '" +  BLANK + "'"
        
    logger.debug(f'Attemptting to play: {condition}...')

    # Use the query method to filter the DataFrame and extract the 'folder' column
    matching_folders = DB.query(condition)['folder']

    # Convert the matching folders to a list
    matching_folders_list = matching_folders.tolist()
    matching_folders_list = [LIBRARY_CACHE_FOLDER + folder for folder in matching_folders_list]

    return matching_folders_list
    

def get_albums_for_label(label):
    logger.debug(f'Looking up albums with label: {label}...')

    
    matching_rows = DB[DB['labels'].apply(lambda x: label in x)]
    matching_folders = matching_rows.query("folder != '"+BLANK+"'")['folder']
    
    # Convert the matching folders to a list
    matching_folders_list = matching_folders.tolist()
        
    matching_folders_list = [LIBRARY_CACHE_FOLDER + folder for folder in matching_folders_list]

    return matching_folders_list
      

"""
    logger.debug(f'Looking up albums with label: {label}...')

    # Use the query method to filter the DataFrame and extract the 'folder' column
    #matching_rows = df.filter(like='foo', axis=1)
    
    #matching_folders_list = matching_folders['folder'].tolist()
    # Convert the matching folders to a list
    
    #matching_rows = DB[(DB['folder'] != 'BLANK') & DB['labels'].str.contains(label)]
    #matching_rows_list = matching_rows.values.tolist()
    
    #matching_rows = DB.query("folder != 'BLANK' and labels.str.contains('"+ label+"')")['folder']
    
    # Assuming you have a DataFrame called 'df'
    #matching_rows = DB.query("labels.str.contains('"+label+"')")
    
    matching_rows = DB[DB['labels'].apply(lambda x: label in x)]
    matching_folders = matching_rows.query("folder != '"+BLANK+"'")['folder']
    #matching_rows = DB[(DB['labels'].apply(lambda x: 'foo' in x)) & (DB['folder'] != 'BLANK')]
    
    #matching_rows = DB.query("folder != 'BLANK' and `labels`.str.contains('"+label+"')")
    
    logger.debug(f'GOT MATCHING ROWS...')

    
    # Convert the matching folders to a list
    matching_folders_list = matching_folders.tolist()
        
    matching_folders_list = [LIBRARY_CACHE_FOLDER + folder for folder in matching_folders_list]

    return matching_folders_list
   """   
    
    
    
    

"""
Returns a list of the full path to tracks for a list of folders. If  shuffle_tracks == True, the resulting
    list of tracks will be randomly shuffled.
"""
def get_tracks(folders, shuffle_tracks):
    global SUPPORTED_EXTENSIONS
    
    all_tracks = []
    
    #shuffle the albums so we don't always start with the same album
    random.shuffle(folders)
    
    for folder in folders:
        #folder_path = os.path.join(base_folder_path, folder)  # Assuming a base folder path
        logger.debug(f'Getting files for {folder}...')
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
    
        # Process the mp3_files for the current folder
     
       #     # Additional code specific to processing each file
    
    
    
    # Get a list of all the MP3 files in the directory
    #valid_extensions = ['.mp3', '.wav', '.ogg']
    #mp3_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if os.path.splitext(f)[1] in SUPPORTED_EXTENSIONS]
    
    
    # this line ysed to implode because of .DS_local files appearing in directories.
    #mp3_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) ]

    # mp3_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith('.ogg')]
    
    #if shuffle == True:
    #    random.shuffle(mp3_files)
    ##else:
        # Sort the list of MP3 files alphabetically
     #   mp3_files.sort()
    
    
    

def lets_do_this():
    global DB, APP_RUNNING
    
    #try:
    # Load the database of RFID tags and their matching albums
    DB = load_database(False)
    DB['sub_genre'] = DB['sub_genre'].fillna(BLANK)
    DB['genre'] = DB['genre'].fillna(BLANK)
    DB['folder'] = DB['folder'].fillna(BLANK)
    DB['labels'] = DB['labels'].fillna(BLANK)
    columns_to_print = ['folder', 'genre', 'sub_genre']
    print(DB[columns_to_print])
    
    genre_card = 0
    
    label_card = 1
    
    if (genre_card == 1):
        ## this card is meant to play a genre instead of a specific album
        genre = 'Soundtrack'
        sub_genre = 'Classical' #lookup_field_by_field(DB, 'rfid', rfid_code, 'sub_genre')
        """ if (len(sub_genre) == 0):
            logger.debug(f'Looking up tracks for genre: {genre}...')
        else:
            logger.debug(f'Looking up tracks for genre: {genre}:{sub_genre}...') 
        """
        #get the list of all the folders from this genre
        genre_album_folder_list = get_albums_for_genre(genre, sub_genre)
        
        tracks = get_tracks(genre_album_folder_list, False)
        
        if (len(tracks) > 0):
            logger.debug (f'Album folder exists. Playing Genre')
            #aaplayer.play_tracks(tracks, is_album_repeat(rfid_code) )
    elif (label_card == 1):
        label = 'test'
        label_album_folder_list = get_albums_for_label(label)
        tracks = get_tracks(label_album_folder_list, False)
        
        if (len(tracks) > 0):
            logger.debug (f'Album folder exists. Playing Genre')
            #aaplayer.play_tracks(tracks, is_album_repeat(rfid_code) )
        
        
        
    else:
        ###########################################################################
        ###########################################################################
        #                   REMOVE THIS LINE
        rfid_code = 332068452025
        ###########################################################################
        ###########################################################################        
        
        album_folder_name = lookup_field_by_field(DB, 'rfid', rfid_code, 'folder')
        logger.debug(f'Attemptting to play album: {album_folder_name}...')

 

        #aaplayer.play_tracks(tracks, is_album_repeat(rfid_code) )
        album_folder = LIBRARY_CACHE_FOLDER + album_folder_name
            
        tracks = get_tracks([album_folder], False)

        if (len(tracks) > 0):
            logger.debug (f'Album folder exists. Playing Genre')
            ###########################################################################
            ###########################################################################
            #                   ADD THE NEXT LINE
            ###########################################################################
            ###########################################################################
            #aaplayer.play_tracks(tracks, is_album_repeat(rfid_code) )
        else:
            logger.warning (f'No tracks found for folder {album_folder}.')    

      
    
     
        ##REPLACE THE ABOVE WITH THIS LINE
        #get_tracks(genre_album_folder_list, is_album_shuffle(rfid_code)), 
       
        #for string in genre_album_folder_list:
        #    print(string)
        
        ## play all 
        #aaplayer.play_genre(genre_album_list, is_album_shuffle(rfid_code), is_album_repeat(rfid_code))
    
lets_do_this()
    