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


## Right now the email is going to send from the above address
## to the above address. If you want to send it to a different address
## enter it here.
EMAIL_SEND_TO = EMAIL_SENDER_ADDRESS


## This is where the log file will be written. If you're running the 
## app at startup this is how you'll find out what's happening
##
## This is currently commented out in the code. You'll need
## to go into AudioAlchemy.py and uncomment the log file code.
LOG_FILE_LOCATION = '[insert your home directory here]'

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









