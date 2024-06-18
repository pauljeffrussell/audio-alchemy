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
    write_to_gsheet("card_taps",row_data)
    #spreadsheet.worksheet("card_taps").append_row(row_data)


"""date_time	Album	folder	track

"""
def log_track_play(folder, track):
    row_data = [
        get_time(),
        folder,
        track
    ]
    
    write_to_gsheet("track_plays",row_data)
    #spreadsheet.worksheet("track_plays").append_row(row_data)


"""date_time	Album	folder	track

"""
def log_album_play(folder):
    row_data = [
        get_time(),
        folder
    ]
    
    write_to_gsheet("album_plays",row_data)
    #spreadsheet.worksheet("track_plays").append_row(row_data)



def log_aotd(folder, rfid):
    row_data = [
        get_time(),
        folder,
        rfid
    ]
    write_to_gsheet("aotd",row_data)
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
    write_to_gsheet("system_metrics",row_data)



'''def get_past_day_error_logs():
# Get the current time
    now = datetime.datetime.now()
    # Calculate the time for 24 hours ago
    one_day_ago = now - datetime.timedelta(days=1.1)
    
    # Read the log file lines
    with open(CONFIG.LOG_FILE_LOCATION , 'r') as file:
        lines = file.readlines()
    
    # Identify the starting point to check entries
    start_index = len(lines)
    entry_found = False
    
    for i in range(len(lines) - 1, -1, -1):
        line = lines[i]
        #if line.startswith("INFO") or line.startswith("ERROR"):
        if line.startswith("INFO") or line.startswith("ERROR"):
            parts = line.split(' ', 2)
            timestamp_str = f"{parts[1]} {parts[2].split(',')[0]}"
            entry_time = datetime.datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            
            if entry_time <= one_day_ago:
                start_index = i + 1
                entry_found = True
                break
    
    # If no entries found, print nothing to report
    if not entry_found:
        return None
    
    # List to hold entries from the last day
    recent_entries = []
    current_entry = []
    
    # Collect entries from the start index
    for line in lines[start_index:]:
        if line.startswith("INFO") or line.startswith("ERROR"):
            if current_entry:
                recent_entries.append("".join(current_entry))
                current_entry = []
        current_entry.append(line)
    
    # Add the last entry
    if current_entry:
        recent_entries.append("".join(current_entry))
    
    output = ''
    # Print the recent entries if found
    if recent_entries:
        for entry in recent_entries:
            output += entry
    else:
        return None
    
    return output'''


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
        send_email(CONFIG.EMAIL_SEND_TO_FOR_INFO_MESSAGES, send_from_name, "Alchemy is Error Free!!!", '<pre>No errors found for the last 24 hours. Noice!</pre>' )
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


'''def write_to_gsheet(sheet_name, row_data):
    global client, spreadsheet

    if not __SHEET_LOGER_ENABLED:
        return
    
    try:
        
        if (client == None):
            client = gspread.authorize(creds)
            
            
        if (spreadsheet == None):
            spreadsheet = client.open("audio_alchemy_logs")
            
        logger.debug(f'Attempting update the google sheet {sheet_name}')
        spreadsheet.worksheet(sheet_name).append_row(row_data)
        logging.debug(f'{sheet_name} update successful.')
    
       
    except Exception as e:
        logger.error(f"While logging to {sheet_name}. Data not written:{row_data}. Error: {e}")    
'''



def write_to_gsheet(sheet_name, row_data, retries=3):
    global client, spreadsheet

    if not __SHEET_LOGER_ENABLED:
        return

    if client is None:
        client = gspread.authorize(creds)

    if spreadsheet is None:
        spreadsheet = client.open("audio_alchemy_logs")

    for i in range(retries):
        try:
            logger.debug(f'Attempting to update the Google sheet {sheet_name}')
            spreadsheet.worksheet(sheet_name).append_row(row_data)
            logger.debug(f'{sheet_name} update successful.')
            return
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Failed to send to {sheet_name} due to a network connection error. Did not write {row_data}\n\n{e}")
            wait_time = (2 ** i) + random.uniform(0, 1)
            logger.debug(f"Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
        except requests.exceptions.Timeout as e:
            logger.warning(f'Request to log to {sheet_name} timed out. Did not write {row_data}\n\n{e}')
            wait_time = (2 ** i) + random.uniform(0, 1)
            logger.debug(f"Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
        except gspread.exceptions.APIError as e:
            if e.response.status_code == 500:
                logger.warning(f'Failed to log to {sheet_name} due to an API error: {e}')
                wait_time = (2 ** i) + random.uniform(0, 1)
                logger.debug(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                raise e
        except Exception as e:
            logger.error(f"While logging to {sheet_name}. Data not written:{row_data}. Error: {e}")
            break

    logger.error(f"Failed to log to {sheet_name} after {retries} retries. Data not written: {row_data}")









#log_album_playback(album_name, artist_name, album_folder, album_rfid, card_type, genre, sub_genre)




def get_time():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def set_logger(external_logger):
    global logger
    logger = external_logger




def main():

    
    
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
    log_card_tap(ALBUM, album_name, album_folder, album_rfid)

    log_track_play(album_folder, track)
    
    


# Check if this is the main entry point of the script
if __name__ == "__main__":
    main()