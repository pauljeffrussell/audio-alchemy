import os
import time
import random
import datetime
import configfile as CONFIG
import gspread
import logging
import requests
import sys
import subprocess
from email.message import EmailMessage
from email.header import Header
from email.mime.text import MIMEText
import smtplib
from oauth2client.service_account import ServiceAccountCredentials
import threading

"""
These are the types of cards you can tap.
"""
ALBUM = 'ALBUM'
COMMAND = 'COMMAND'
LABEL = 'LABEL'
GENRE = 'GENRE'
AOTD = 'AOTD'

logger = None

__SHEET_LOGER_ENABLED = False

REMOTE_DB_WRITE_CACHE = {}


# Use creds to create a client to interact with the Google Drive API
scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name(CONFIG.GOOGLE_SHEETS_KEY_PATH, scope)
client = None

# Find a workbook by name and open the first sheet
# Make sure you use the right name here and share the sheet with your client_email in the credentials file
spreadsheet = None
#sheet_card = spreadsheet.worksheet("card_taps")



def enable_sheet_logger():
    global __SHEET_LOGER_ENABLED
    __SHEET_LOGER_ENABLED = True

"""
Adds a row to the card_tap table found at
https://docs.google.com/spreadsheets/d/1Pq6djcO3qk-7AsJPBvLx_s2ekjhZ1sLiwBCnyHaSw9w/edit#gid=0

Th table columns are
    date_time: the time this was called
    card_type: one of the above constnant card types
    name: the name of the card. This is an album if it's an album, label or genre card, and the command card name otherwise.
    UID: The folder name if it's an album
    rfid: The rfid of the card.

card_type	name	UID	rfid

"""
def log_card_tap(card_type, card_name, uid, rfid):
    row_data = [
        get_time(),
        card_type,
        card_name,
        uid,
        rfid
    ]
    write_to_gsheet_thread("card_taps",row_data)
    #spreadsheet.worksheet("card_taps").append_row(row_data)


"""date_time	Album	folder	track

"""
def log_track_play(folder, track):
    row_data = [
        get_time(),
        folder,
        track
    ]
    
    write_to_gsheet_thread("track_plays",row_data)
    #spreadsheet.worksheet("track_plays").append_row(row_data)


"""date_time	Album	folder	track

"""
def log_album_play(folder):
    row_data = [
        get_time(),
        folder
    ]
    
    write_to_gsheet_thread("album_plays",row_data)
    #spreadsheet.worksheet("track_plays").append_row(row_data)



def log_aotd(folder, rfid):
    row_data = [
        get_time(),
        folder,
        rfid
    ]
    write_to_gsheet_thread("aotd",row_data)
    #spreadsheet.worksheet("aotd").append_row(row_data)


def log_system_metrics():

    ## Get the temperature
    temp_output = subprocess.run(['vcgencmd', 'measure_temp'], stdout=subprocess.PIPE).stdout.decode()
    temperature = float(temp_output.split('=')[1].split("'")[0])
    

    # Calculate five-minute utilization per core
    num_cores = os.cpu_count()
    cpu_load_avg = os.getloadavg()   
    #get the 15 minute average
    average_cpu_util = (cpu_load_avg[2] / num_cores) * 100


    
    row_data = [
        get_time(),
        temperature,
        average_cpu_util
    ]
    write_to_gsheet_thread("system_metrics",row_data)




def get_past_day_error_logs():
# Get the current time
    now = datetime.datetime.now()
    # Calculate the time for 24 hours ago
    one_day_ago = now - datetime.timedelta(days=1.1)
    
    # Read the log file lines
    with open(CONFIG.LOG_FILE_LOCATION , 'r') as file:
        lines = file.readlines()
    
    # Initialize variables
    last_error_index = None
    last_in_range_index = None

    # Process lines in reverse to find the most recent "ERROR" line within the last 24 hours
    for i in range(len(lines) - 1, -1, -1):
        line = lines[i].strip()
        if line.startswith("INFO") or line.startswith("ERROR"):
            parts = line.split(' ', 2)
            timestamp_str = f"{parts[1]} {parts[2].split(',')[0]}"
            entry_time = datetime.datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            
            if entry_time > one_day_ago:
                last_in_range_index = i
                if line.startswith("ERROR"):
                    last_error_index = i
            else:
                break

    # if there's an error, collect relevant entries from the last last day 
    output = ''

    relevant_entries = []
    if last_error_index is not None:
        for i in range(last_in_range_index, len(lines)):
            output += lines[i]

    else:
        output = None

    return output

def send_logs_home():    
    
    logger.debug(f'Checking if there are logs to send...')
    
    log_output = get_past_day_error_logs()

    send_from_name = "Alchemy Errors"

    ## send an email saying you didn't find anything if you didn't find anything.
    if (log_output == None):
        logger.debug(f'No error logs to send home today...')
        #send_email(CONFIG.EMAIL_SEND_TO_FOR_INFO_MESSAGES, send_from_name, "Alchemy is Error Free!!!", '<pre>No errors found for the last 24 hours. Noice!</pre>' )
        return  
   
    logger.debug(f'Error Logs available. Sending email...')

    # Calculate yesterday's date
    yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
    # Format the date as "YYYY-MM-DD"
    formatted_date = yesterday.strftime("%Y-%m-%d")

    subject = f"Errors from {formatted_date}" 
    
    body = '<pre>' + log_output +'</pre>'

    send_email(CONFIG.EMAIL_SEND_TO_FOR_INFO_MESSAGES, send_from_name, subject, body )
    

def send_email(send_to, send_from_name, subject, body):
    # Email settings
    SMTP_SERVER = 'smtp.gmail.com'
    SMTP_PORT = 587
    SENDER_EMAIL = CONFIG.EMAIL_SENDER_ADDRESS  # Change this to your Gmail
    SENDER_PASSWORD = CONFIG.EMAIL_SENDER_PASSWORD      # Change this to your password or App Password

    # Create the message
    msg = EmailMessage()
    
    
    msg = MIMEText(body, 'html') 
              
    msg['Subject'] = subject
    msg['From'] = send_from_name
    msg['To'] = send_to # The receiver's email



    # Send the email
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.starttls()  # Upgrade the connection to secure encrypted SSL/TLS connection
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)
            logger.debug(f'Email sent successfully!')
            return True
    except Exception as e:
        logger.error(f"Error sending email. {e}")
        return False


def write_to_gsheet_thread(sheet_name, row_data):
    thread = threading.Thread(target=write_to_gsheet, args=(sheet_name, row_data,))
    thread.start()


'''
2024-07-04 Changed retries to 1 because it always seems to fail the number of retries
           and it's just going to try with the same data one hour later. 

           Technically I could take out the retry logic, but I'm leaving in case
           this one retry attempt becomes a problem in the future.
'''
def write_to_gsheet(sheet_name, row_data):
    global client, spreadsheet

    if not __SHEET_LOGER_ENABLED:
        logger.debug(f'Fake Logging: {row_data}')
        return

    ## let's remember that we're trying to add a row
    add_to_cache(sheet_name, row_data)


    if client is None:
        client = gspread.authorize(creds)

    if spreadsheet is None:
        spreadsheet = client.open("audio_alchemy_logs")

    
    try:

        ##########################################
        ##              HAPPY PATH              ##
        ##########################################
        
        logger.debug(f'Attempting to update the Google sheet {sheet_name}')
        
        rows_data = get_cached_data(sheet_name)
        
        ## write all the cached rows
        # this was for testing
        # if (row_data[1] != "Album3" and row_data[1] != "Album8"):
        #    raise Exception("Made up Exception")
        spreadsheet.worksheet(sheet_name).append_rows(rows_data)
        ## the write succeeded, so let's clear the cache so we don't try to write 
        ## this/these line in the future.
        clear_sheet_cache(sheet_name)

        logger.debug(f'{sheet_name} update successful.')
        return
    
    except Exception as e:
        """ 2024-09-28 Since June, I've had this set as a warning which was writing to disk.
            While, a lot of warnings have been written, it's never actually reached an error 
            because of the retry logic built into this package.
            So I'm going to change this from "warning" to "debug"" so that it stops writing to the 
            log file as there's no real value and having that information persisted anymore.
        logger.warning(f"While logging to {sheet_name}. Data not written:{rows_data}. Exception: {e}")
        
        Actually, never mind. There's been a lot of warnings lately and I'm not sure what's going on 
        so we're gonna monitor this some more.
        """
        logger.warning(f"While logging to {sheet_name}. Data not written:{rows_data}. Exception: {e}")
    cache_size = get_cache_length(sheet_name)
    if (cache_size >= 4):
        # If the cache has built up this much it means writing has failed for several hours.
        # or days in the case of the AOTD 
        logger.error(f"Logging to {sheet_name} has failed for the last {cache_size} hours.")





def add_to_cache(sheet_name, data_array):
    """
    Add a new data array to the cache for a specific sheet.

    Args:
    sheet_name (str): The name of the sheet to cache data for.
    data_array (list): The array of data to be cached.

    Returns:
    None
    """
    global REMOTE_DB_WRITE_CACHE
    if sheet_name not in REMOTE_DB_WRITE_CACHE:
        REMOTE_DB_WRITE_CACHE[sheet_name] = []
    REMOTE_DB_WRITE_CACHE[sheet_name].append(data_array)

def get_cached_data(sheet_name):
    """
    Retrieve all cached data for a specific sheet.

    Args:
    sheet_name (str): The name of the sheet to retrieve data for.

    Returns:
    list: A list of data arrays cached for the specified sheet.
          Returns an empty list if no data is cached for the sheet.
    """
    global REMOTE_DB_WRITE_CACHE
    return REMOTE_DB_WRITE_CACHE.get(sheet_name, [])

def clear_sheet_cache(sheet_name):
    """
    Clear all cached data for a specific sheet.

    Args:
    sheet_name (str): The name of the sheet to clear cache for.

    Returns:
    None
    """
    global REMOTE_DB_WRITE_CACHE
    if sheet_name in REMOTE_DB_WRITE_CACHE:
        del REMOTE_DB_WRITE_CACHE[sheet_name]

def get_cache_length(sheet_name):
    """
    Get the number of data arrays cached for a specific sheet.

    Args:
    sheet_name (str): The name of the sheet to check cache length for.

    Returns:
    int: The number of data arrays cached for the specified sheet.
         Returns 0 if no data is cached for the sheet.
    """
    global REMOTE_DB_WRITE_CACHE
    return len(REMOTE_DB_WRITE_CACHE.get(sheet_name, []))




#log_album_playback(album_name, artist_name, album_folder, album_rfid, card_type, genre, sub_genre)




def get_time():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def set_logger(external_logger):
    global logger
    logger = external_logger




def main():

    enable_sheet_logger()
    
    # Create the logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Create a formatter
    formatter = logging.Formatter('%(levelname)s %(asctime)s %(message)s -- %(funcName)s %(lineno)d')
    
    #formatter = logging.Formatter('%(asctime)s -- %(message)s -- %(funcName)s %(lineno)d')
    # Create a stream handler to log to STDOUT
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    
    set_logger(logger)

    # Wherever you detect an album play in your media player script:
    album_name = "Star Wars"
    artist_name = "John Williams"
    album_folder = "John Williams - Star Wars 4 - A New Hope"
    album_rfid = "12345"
    card_type = "album"
    genre = "Soundtrack"
    sub_genre = "Classical"
    track = "1-02 Main Title_Rebel Blockade Runner (Medley).mp3"

    #card_type, card_name, uid, rfid)
    #log_card_tap(ALBUM, album_name, album_folder, album_rfid)

    #log_track_play(album_folder, track)
    
    for i in range(10):
        print(f"\n\n\n\nIteration {i+1}") 
        log_track_play(f"Album{i}", f"track{i}")
        time.sleep(2)
    


# Check if this is the main entry point of the script
if __name__ == "__main__":
    main()