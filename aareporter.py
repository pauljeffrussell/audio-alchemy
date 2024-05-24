import os
import datetime
import configfile as CONFIG
import gspread
import logging
import requests
import sys
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


# Use creds to create a client to interact with the Google Drive API
scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name(CONFIG.GOOGLE_SHEETS_KEY_PATH, scope)
client = None

# Find a workbook by name and open the first sheet
# Make sure you use the right name here and share the sheet with your client_email in the credentials file
spreadsheet = None
#sheet_card = spreadsheet.worksheet("card_taps")


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



def write_to_gsheet(sheet_name, row_data):
    global client, spreadsheet
    
    try:
        
        if (client == None):
            client = gspread.authorize(creds)
            
            
        if (spreadsheet == None):
            spreadsheet = client.open("audio_alchemy_logs")
            
        logger.debug(f'Attempting update the google sheet {sheet_name}')
        spreadsheet.worksheet(sheet_name).append_row(row_data)
        logging.debug(f'{sheet_name} update successful.')
    
        """ 
        ## Commented this out 2024-02-18. I was getting a lot of runtime issues with the specifc 
        ## exceptions not being imported, and I couldn't see a good reason to keep them all since the {e} should
        ## tell me everthing
        except requests.exceptions.ConnectionError:
            logger.error(f"Failed to send to {sheet_name} due to a network connection error.\nDid not write {row_data}\n\n{e}")
        
        except requests.exceptions.Timeout:
            logger.error(f'Request to log to {sheet_name} timed out.')

        except AccessTokenRefreshError:
            logger.error(f'Request to log to {sheet_name} failed. Authentication token refresh failed. Please check your credentials.')

        except gspread.exceptions.APIError as e:
            logger.error(f'Failed to log to {sheet_name} due to an API error: {e}')
        """        
    except Exception as e:
        logger.error(f"While logging to {sheet_name}. Data not written:{row_data}. Error: {e}")    













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