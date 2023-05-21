"""
This is the configuration file for the AudioAlchemy application. You'll need to configure these settings
specific to your application.
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


## This is the RFID ID for the object that stops and reinitializes the player
## You'll want to replace this with whatever RFID you use.
STOP_AND_RELOAD_DB = "750150895668" 




LOG_FILE_LOCATION = '[insert your home directory here]'



BULK_DOWNLOAD = False











