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
from datetime import datetime, timedelta
import smtplib
from collections import Counter, defaultdict
#from email.message import EmailMessage
#from email.header import Header
#from email.mime.text import MIMEText

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


TEST_LOOPS = 30

#LIBRARY_CACHE_FOLDER = "/home/matt/dev/library/"
LIBRARY_CACHE_FOLDER = "./library/" #CONFIG.LIBRARY_CACHE_FOLDER

FILE_AOTD_CACHE = "./dbcache/" + "albumofthedaycache.csv"

## How many day have to pass before you're allowed to repeat the album of the day.
AOTD_REPEAT_LIMIT = .7

DB_AOTD_CACHE = pd.DataFrame()


RDID_USE_TRACKER = pd.DataFrame()

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


"""def load_album_of_the_day_cache():
    global FILE_AOTD_CACHE, DB_AOTD_CACHE
    
    # Load the last 30 album names from albumoftheday.csv
    try:
        DB_AOTD_CACHE = pd.read_csv(FILE_AOTD_CACHE)
    except (FileNotFoundError, pd.errors.EmptyDataError):
        # If the albumoftheday.csv file is not found or empty, then all albums in catalog are available
        logger.error(f'Cound not read {CACHE_AOTD_FILE}') 
           
    return DB_AOTD_CACHE
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
            #logger.debug(f'Getting files for {folder}...')
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
        foo =3
        #logger.debug (f'Album has tracks. Playing...')
        #aaplayer.play_tracks(tracks, False )
    else:
        logger.warning (f'No tracks found for folder {album_folder}.')

    return tracks
    
  
    
def play_album_of_the_day(lookup_date):
    global DB
    rfid = BLANK
    
    todays_seed = lookup_date
    
    #todays_seed = int(datetime.today().strftime('%Y%m%d'))
    #print (f'Seed {todays_seed}')
   
    # Set the seed with today's date so we always get the same answer
    np.random.seed(todays_seed)
    

    
    ## don't use rows with a 1 in the 
    filtered_df = DB[DB['exclude_from_random'] != 1]
    sample_size = min(len(filtered_df), 50)
    
    todays_rfid_list = filtered_df.sample(n=sample_size, random_state=todays_seed)['rfid'].tolist()
    

    found_rfid = None  # This will store the found rfid value

    for rfid in todays_rfid_list:
        if rfid == BLANK or isinstance(rfid, float) or not str(rfid).isdigit():
            continue
        else:
            found_rfid = rfid  # Store the rfid that passed the check
            break
    
    album_folder_name = lookup_field_by_field(DB, 'rfid', found_rfid, 'folder')
    
    logger.debug(f'Album of the day:\n        {album_folder_name}...')
    #send_album_of_the_day_email(found_rfid)
    
    
    
    
    
    """album_folder = LIBRARY_CACHE_FOLDER + album_folder_name

    
    tracks = get_tracks([album_folder], False)
    if (len(tracks) > 0):
        foo = 3
        #logger.debug (f'Album has tracks. Playing...')
        #aaplayer.play_tracks(tracks, False )
    else:
        logger.warning (f'No tracks found for folder {album_folder}.')

    return tracks"""

def replace_non_strings(variable):
    if isinstance(variable, str):
       return variable
    else:
        return ""
       
def email_album_of_the_day(date_seed_string, rfid ):
    
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
    
    msg['From'] = Header(f'{CONFIG.EMAIL_SENDER_NAME}', 'utf-8')  # Set sender name here
    
                      
    msg['Subject'] = album_name
    #msg['From'] = SENDER_EMAIL
    msg['To'] = CONFIG.EMAIL_SEND_TO  # The receiver's email

    #print("Subject ", msg['Subject'])

    # Send the email
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.starttls()  # Upgrade the connection to secure encrypted SSL/TLS connection
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)
            print('Email sent successfully!')
    except Exception as e:
        print(f"Error occurred: {e}")

    

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
    
    msg['From'] = Header(f'{CONFIG.EMAIL_SENDER_NAME} <{CONFIG.EMAIL_SENDER_ADDRESS}>', 'utf-8')  # Set sender name here
    
                      
    msg['Subject'] = album_name
    #msg['From'] = SENDER_EMAIL
    msg['To'] =  CONFIG.EMAIL_SEND_TO  # The receiver's email

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


"""def update_csv(album_name, file_name='albumoftheday.csv'):
    # Create a DataFrame for the new data
    current_date = datetime.now().strftime('%Y-%m-%d')
    new_data = pd.DataFrame([[current_date, album_name]], columns=['Date', 'Album Name'])

    # Check if the file exists and append data
    try:
        existing_data = pd.read_csv(file_name)
        updated_data = existing_data.append(new_data, ignore_index=True)
    except FileNotFoundError:
        updated_data = new_data

    # Save the updated data to CSV
    updated_data.to_csv(file_name, index=False)

"""
"""def get_last_30_rows(file_name='albumoftheday.csv'):
    df = pd.read_csv(file_name)
    last_30_rows = df.tail(30)
    print(last_30_rows)

# Call the function to print the last 30 rows
"""


"""
## returns the list of albums that you can't use for the album of the day
## because they've been saved too reciently.
def get_album_of_the_day_repeat_block_list():
    global DB_AOTD_CACHE 
    
    return DB_AOTD_CACHE.tail(AOTD_REPEAT_LIMIT)
    """
"""
####################################################################################

            NEW ALBUM OF THE DAY CODE

####################################################################################
"""

## load or create and load the album of the day cache.
def load_album_of_the_day_cache():
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



def check_aotd_cache_for_today(date_to_check):
    """
    Checks the album of the day cache to see if we've already saved today's
    album of the day. 
    
    Returns: the album of the day rfid if the date matches. None otherwise
    """
    global DB_AOTD_CACHE
    
    last_date = DB_AOTD_CACHE['date'].iloc[-1]

    if last_date == date_to_check:
        logger.debug("Found album of the day in the cache.")
        return DB_AOTD_CACHE['rfid'].iloc[-1]
    else:
        return None
    


def get_album_of_the_day_seed():
    return int(datetime.today().strftime('%Y%m%d'))

"""
    pulls a random RFID out of the database making sure it's hasn't been the album of 
    the day reciently
"""
def get_album_of_the_day_rfid(seed_for_random_lookup=get_album_of_the_day_seed()):
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
    

    # THis was replaced above
    #found_rfid = None  # This will store the found rfid value

    for rfid in todays_rfid_list:
        if rfid == BLANK or isinstance(rfid, float) or not str(rfid).isdigit():
            continue
        else:
            found_rfid = rfid  # Store the rfid that passed the check
            break
    
    #print (found_rfid)
    return found_rfid


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



"""# Initialize an empty DataFrame for the cache
DB_AOTD_CACHE = pd.DataFrame(columns=['date', 'Album Name', 'RFID'])

# Try to load the existing content of albumoftheday.csv into the cache
try:
    DB_AOTD_CACHE = pd.read_csv('albumoftheday.csv')
except FileNotFoundError:
    pass
    
    try:
        # Append the new data to the existing CSV file
        DB_AOTD_CACHE.to_csv(FILE_AOTD_CACHE, mode='w', header=True, index=False)
    except:
        logger.ERROR('Unable to save the Album of the Day CACHE to disk')


def update_aotd_cache(date, rfid, album_name):
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
    
    # Append the new data to the existing CSV file
    DB_AOTD_CACHE.to_csv(FILE_AOTD_CACHE, mode='w', header=True, index=False)


# Example usage:
# append_to_albumoftheday('2023-09-02', 'Sample Album', '1234567890')
# print(DB_AOTD_CACHE)

"""









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











def main():
    global DB, DB_AOTD_CACHE, APP_RUNNING, RDID_USE_TRACKER
    
    #try:
    # Load the database of RFID tags and their matching albums
    DB = load_database(False)
    
    # Convert the column to numeric
    #DB['exclude_from_random'] = pd.to_numeric(DB['exclude_from_random'], errors='coerce')
    
    # Convert the rfid and exclude_from_random columns to numeric, setting non-numeric values to NaN
    #DB['rfid'] = pd.to_numeric(DB['rfid'], errors='coerce')
    #DB['exclude_from_random'] = pd.to_numeric(DB['exclude_from_random'], errors='coerce')
    

    #possible_albums = DB[DB['exclude_from_random'] != 1]
    # Filter the dataframe based on the given conditions and the absence of NaN values
    # Convert the rfid column to numeric, setting non-numeric values to NaN
    #DB['rfid'] = pd.to_numeric(DB['rfid'], errors='coerce')
    
    exclude = lookup_field_by_field(DB, 'rfid', 714945955662, 'exclude_from_random')
    
    print("exclude type:")
    print(type(exclude))

    # Filter the dataframe based on the given conditions
    possible_albums = DB[(DB['exclude_from_random'] != 1) & DB['rfid'].notna() ]
    #possible_albums = possible_albums[possible_albums['rfid'].apply(lambda x: not isinstance(x, str))]
    possible_albums = possible_albums[~possible_albums['rfid'].astype(str).str.contains('[a-zA-Z\s]', na=False)]
    """possible_albums = DB[ (DB['exclude_from_random'] != 1) 
                          & DB['rfid'].notna() 
                          & DB['exclude_from_random'].notna()]
    
    """
    possible_album_length = len(possible_albums)
    print (f'{possible_album_length} possible albums')
    
    RDID_USE_TRACKER = possible_albums[['rfid']].copy()
    RDID_USE_TRACKER['count'] = 0
    
    
    ## load the album of the day cache.
    ## if there isn't one, make one.
    DB_AOTD_CACHE= load_album_of_the_day_cache()
    #print(list_folders_in_order(DB))
    
    aotd_seed = get_album_of_the_day_seed()
    
    
    print("Getting Album of the day.")
    rfid1 = get_album_of_the_day_rfid(aotd_seed)
    print(f'rfid: {rfid1}')
    update_aotd_cache(aotd_seed, rfid1, "First")
    print()
    print()
    print("Getting Album of the day.")
    rfid2 = get_album_of_the_day_rfid(aotd_seed)
    print(f'rfid: {rfid2}')
    update_aotd_cache(aotd_seed, rfid2, "Second")
    
    """print (DB_AOTD_CACHE)
    print()
    print()
    print()
    
    print()
    print(f'{TEST_LOOPS} Test Loops ')
    years = TEST_LOOPS / 365
    print(f'{years:.1f} Years of albums of the day ')
    
    print (f'{possible_album_length} possible albums')
    #get an album of the day
    #run_and_analyze_function()
    #analyze_function()
    """
    
    
    
    """print("value counts")

    print(DB['exclude_from_random'].value_counts())
    
    print("data types")
    print(DB['exclude_from_random'].dtype)
    """

    #print_zero_count_rfids(RDID_USE_TRACKER)
    
    """
    print()
    display_sorted_rfids(RDID_USE_TRACKER)
    """
    
    
    
    


def analyze_function():
    global RDID_USE_TRACKER
    results = []
    last_occurrences = defaultdict(int)  # A dictionary to keep track of the last occurrence of each result.
    min_difference = float('inf')  # Start with "infinity" as the initial minimum difference.

    start_date = datetime.today() 

    for day in range(TEST_LOOPS):
        #logger.debug(f'startting loop {day}')
        # Convert the current date to the desired format
        formatted_date = start_date.strftime('%Y%m%d')
        
        # Call the load_album_of_the_day_cache function with the formatted date
        result = get_album_of_the_day_rfid(formatted_date)
        results.append(result)
        
        update_rfid_count(result, RDID_USE_TRACKER)

        folder = lookup_field_by_field(DB, 'rfid', result, 'folder')
        update_aotd_cache(formatted_date, result, folder)
        
        # Check if this result has been seen before.
        if result in last_occurrences:
            # Calculate the difference between the current day and the last occurrence.
            difference = day - last_occurrences[result]
            # Update the minimum difference if this difference is smaller.
            min_difference = min(min_difference, difference)
            #print(f"{min_difference} since last match {result}")
            

        # Update the last occurrence of this result.
        last_occurrences[result] = day
        
        
        # Increment the date by 1 day
        start_date += timedelta(days=1)
        

    duplicates = [item for item, count in Counter(results).items() if count > 1]
    
  

    #print(f"Number of duplicated values: {len(duplicates)}")
    
    if min_difference == float('inf'):
        print("No duplicates found.")
    else:
        print(f"Minimum number of days between album repeat: {min_difference}")

    return results
    
    
    
def update_rfid_count(rfid, df):
    global RDID_USE_TRACKER
    """
    Update the count of the given RFID in the DataFrame.
    
    Parameters:
    - rfid: The RFID to update.
    - df: The DataFrame containing the RFID and its count.
    """
    # If the RFID exists in the DataFrame, increment its count.
    if rfid in RDID_USE_TRACKER['rfid'].values:
        RDID_USE_TRACKER.loc[df['rfid'] == rfid, 'count'] += 1
    # If the RFID doesn't exist, append it to the DataFrame with a count of 1.
    else:
        RDID_USE_TRACKER = RDID_USE_TRACKER.append({'rfid': rfid, 'count': 1}, ignore_index=True)
    
    return RDID_USE_TRACKER



def display_sorted_rfids(df):

    """
    Display the number of RFIDs for each count.
    
    Parameter:
    - df: The DataFrame containing the RFIDs and their counts.
    """
    grouped = df.groupby('count').size().reset_index(name='number_of_rfids')
    sorted_grouped = grouped.sort_values(by='count', ascending=False)
    
    for _, row in sorted_grouped.iterrows():
        print(f"{row['number_of_rfids']} played {row['count']} times")


def print_zero_count_rfids(rfid_tracker):
    zero_count_rfids = rfid_tracker[rfid_tracker['count'] == 0]['rfid']
    
    print('#######################################################')
    print('###               NEVER PLAYED                      ###')
    print('#######################################################')
    
    for rfid in zero_count_rfids:
        print(rfid)

# Usage


"""def display_sorted_rfids(df):
    global RDID_USE_TRACKER
    
    Display the RFIDs sorted by their counts.
    
    Parameter:
    - df: The DataFrame containing the RFIDs and their counts.
    87
    sorted_df = RDID_USE_TRACKER.sort_values(by='count', ascending=False)
    print(sorted_df)
"""
    
def run_and_analyze_function():
    # List to store the return values
    results = []

    start_date = datetime.today() 
    # Call the function 100 times and store its return values
    for _ in range(365):
        
        logger.debug(f'startting loop {_}')
        # Convert the current date to the desired format
        formatted_date = start_date.strftime('%Y%m%d')
        
        # Call the load_album_of_the_day_cache function with the formatted date
        result = get_album_of_the_day_rfid(formatted_date)
        
        update_aotd_cache(formatted_date, result, "foo")
        results.append(result)
        
        # Increment the date by 1 day
        start_date += timedelta(days=1)
        

    # Use Counter to count the occurrence of each return value
    counts = Counter(results)

    # Count how many values were returned more than once
    duplicates = sum(1 for count in counts.values() if count > 1)
    
    # dupli

    # Print out the number of values that were returned more than once
    print(f"{duplicates} values were returned more than once.")




def run_load_album_of_the_day_cache():
    # Get today's date
    start_date = datetime.today()
    
    # Loop for 100 days
    for _ in range(10):
        # Convert the current date to the desired format
        formatted_date = start_date.strftime('%Y%m%d')
        
        # Call the load_album_of_the_day_cache function with the formatted date
        print(get_album_of_the_day_rfid(formatted_date))
        
        # Increment the date by 1 day
        start_date += timedelta(days=1)
    





main()
