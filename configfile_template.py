"""
This is the configuration file for the AudioAlchemy application. You'll need to configure these settings
specific to your application.

IMPORTANT: Once you have updated this file, rename it to configfile.py for your local installation
"""

"""


The audio alchemy app uses a public google sheet to store it's database of albums. 

You'll need to create a copy of the public one and replace the settings below to point to it.

To get started copy the example google sheet linked below and update the variables below accordingly.
https://docs.google.com/spreadsheets/d/12c_d4NEUgpyRVUnB2qEZUqPCcaywmd_KYo9E6x15Z5M

"""
DB_SHEET_ID = '12c_d4NEUgpyRVUnB2qEZUqPCcaywmd_KYo9E6x15Z5M'   ## This is the UID of the sheet. 
                                                                ## You can get it from the google sheet URL.
                                                                ## It's the unique string at the end of the URL


DB_SHEET_NAME = 'Sheet 1'    ## this is the name of the individual sheet. by default google sheets start 
                                ## with "Sheet 1" but if you've renamed it, you'll need to update this field 
                                ## to match what you've named the sheet



## This is where you've saved your MP3s that will be read by the app
LIBRARY_CACHE_FOLDER = "/media/audioalchemy/library/"

## This is where the system will save caches of the album library
DB_CACHE_LOCATION = "/media/audioalchemy/dbcache/"


DB_AUDIO_POSITION = DB_CACHE_LOCATION + 'audio_position_data.csv'
#DB_AUDIO_POSITION = 'dbcache/audio_position_data.csv'


## This is the RFID ID for the object that stops and reinitializes the player
## You'll want to replace this with whatever RFID you use.
COMMAND_STOP_AND_RELOAD_DB = "750150895668" 


## This is the RFID ID for the object that stops the entire application.
## When this code is read, the application will exit
## You'll want to replace this with whatever RFID you use to kill the app.
COMMAND_SHUT_DOWN_APP = "344226340374"


## This is an RFID for the object that tells the player to select random albums 
## labeled with 'random' and play them.
COMMAND_PLAY_RANDOM_ALBUMS = "824276459135" #skylander D20 in glass tube
                      
## Command code for the album of the day
COMMAND_PLAY_ALBUM_OF_THE_DAY = "223595766210" #skylander hammer



## This is a command card that tells the app to shuffle the current tracks
COMMAND_PLAY_IN_ORDER_FROM_RANDOM_TRACK = "578541694301" #skylander shoe with wings

## This command tells the player to email the current playing track 
## to EMAIL_FOR_INFO_MESSAGES
COMMAND_EMAIL_CURRENT_TRACK_NAME = "847585307635"

## This command tells the player to speek the current playing track 
## It replaces the email the track name function
COMMAND_SPEEK_CURRENT_TRACK_NAME = "847585307635"


## This command tells the player to put the current album on repeat.
COMMAND_REPEAT_ALBUM = "584189322831"

## this command tells the play to stop playing if it's playing
COMMAND_PLAY_PAUSE_PLAYER = "584189313643"

CARD_TYPE_COMMAND = 'command'

CARD_TYPE_ALBUM = 'album'

CARD_TYPE_CARD_UNKNOWN = 'unknown'

CARD_TYPE_GENRE = 'genre'

CARD_TYPE_LABEL = 'label'

## this tells the player the max number of times to play a 
## repeat album so we don't play forever if someone forgets to hit stop.
MAX_REPLAY_COUNT = 7


"""--------------------------------------------------------------"""
"""                     FEEDBACK AUDIO                           """
"""--------------------------------------------------------------"""

## Found this sound at https://pixabay.com/sound-effects/success-1-6297/
COMMAND_STOP_AND_RELOAD_DB_FEEDBACK = LIBRARY_CACHE_FOLDER + "_FEEDBACK_AUDIO/feedback_db_load_complete_100.mp3"


COMMAND_EMAIL_CURRENT_TRACK_NAME_FEEDBACK = LIBRARY_CACHE_FOLDER + "_FEEDBACK_AUDIO/feedback_logs_accessed_80.wav"

## when set to True, a it sounds like you're starting a record when you start an album
FEEDBACK_RECORD_START_ENABLED = True


## the sound that plays at the beginning of an album
FEEDBACK_RECORD_START = LIBRARY_CACHE_FOLDER + "_FEEDBACK_AUDIO/feedback_record_start_amplified.wav"

## the sound that plays when you use the repeat album command card
FEEDBACK_ALBUM_REPEAT = LIBRARY_CACHE_FOLDER + "_FEEDBACK_AUDIO/feedback_repeat album_force_field_on2.mp3"


##the sound that plays when you use an RFID card that is not recognized.
FEEDBACK_RFID_NOT_FOUND = LIBRARY_CACHE_FOLDER + "_FEEDBACK_AUDIO/feedback_no_match_RFID_denybeep1.mp3"

## the sound that plays when you are unable to generate and play TTS audio of the album and track name
FEEDBACK_AUDIO_NOT_FOUND = LIBRARY_CACHE_FOLDER + "_FEEDBACK_AUDIO/feedback_no_match_RFID_denybeep1.mp3"

FEEDBACK_PROCESSING = LIBRARY_CACHE_FOLDER + "_FEEDBACK_AUDIO/feedback_processing-R2D2.wav"


TEMP_SPEECH_MP3 = '/tmp/current_folder_and_track_spoken.mp3'

TEMP_SPEECH_WAV = '/tmp/current_folder_and_track_spoken.wav'


"""--------------------------------------------------------------"""
"""                     EMAIL CONFIG                             """
"""--------------------------------------------------------------"""


## The email address to send system emails to 
EMAIL_SEND_TO_FOR_INFO_MESSAGES = "INSERT YOUR EMAIL ADDRESS"

## The email from name for system emails
EMAIL_SENDER_NAME_FOR_INFO_MESSAGES = "Audio Alchemy"

## this is the number of random albums to play when the PLAY_RANDOM_ALBUMS 
## command card is used
RANDOM_ALBUMS_TO_PLAY = 5



EMAIL_SENDER_NAME = "Album Of The Day"


#The system will send an email from this address 
# each day with the album of the day
EMAIL_SENDER_ADDRESS  = 'INSERT YOUR EMAIL ADDRESS'


## This is the app password for the above address. EMAIL_SENDER_ADDRESS
## https://support.google.com/accounts/answer/185833?hl=en
## DO NOT MAKE THIS AVAILABLE PUBLICALLY 
## Don't give anyone else access to this file once you put the PW in here
EMAIL_SENDER_PASSWORD = 'INSERT YOUR APP PASSWORD' 
GOOGLE_SHEETS_KEY_PATH = '/media/audioalchemy/keys/YOUR_JSON_KEY_FOR_API_CALLS_TOGSHEETS.json'


## Right now the email is going to send from the above address
## to the above address. If you want to send it to a different address
## enter it here.
EMAIL_SEND_TO = 'INSERT YOUR EMAIL ADDRESS'


## This is where the log file will be written. If you're running the 
## app at startup this is how you'll find out what's happening
##
## This is currently commented out in the code. You'll need
## to go into AudioAlchemy.py and uncomment the log file code.
LOG_FILE_LOCATION = "/media/audioalchemy/logs/errors.log"

## This is the time in seconds you have to hold a button for the 
## app to consider the button being held. It is used for things like
## skipping to the next album in a playlist of albums or to go back to the
## beginning of an album in the case of a single album.
BUTTON_HOLD_DURATION = 1.5

## Use bulk downloading to keep from pinging youtube music every time.
## no reason to clobber their bandwith with repeated requests for the same thing.
##
## when set to true, the downloader will attempt to get every album in your db sheet.
## when set to false it will list the albums that don't yet have a folder in ./webm
BULK_DOWNLOAD = False

BUTTON_HIGH = False









