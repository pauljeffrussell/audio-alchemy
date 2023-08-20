""" Downloads the highest quality audio from a google sheet containing 
at least the following columns

    'Album' - This is the album name
    'url'   - This is the url to the youtube music playlist or album. 
              It must contain a parameter called list 

It starts by pulling a list of albums from a google sheet defined 
by DB_SHEET_ID and DB_SHEET_NAME below. You'll need to set those parameters to your DB

It then goes through each album and if a folder for that album doesn't already exist, 
it creates one and downloads the webm files from youtube. 
"""


import os
from urllib.parse import urlparse, parse_qs
from yt_dlp import YoutubeDL
import pandas as pd

import logging
import configfile as CONFIG

logging.basicConfig(format=' %(message)s -- %(funcName)s %(lineno)d', level=logging.INFO)



LIBRARY_CACHE_FOLDER = "./library/"
LIBRARY_SOURCE_FOLDER = "./webm/" # This is where we put the full source files.

# Use these two parameters to identify the google sheet with your album database
DB_SHEET_ID = CONFIG.DB_SHEET_ID
DB_SHEET_NAME = CONFIG.DB_SHEET_ID
BULK_DOWNLOAD = CONFIG.BULK_DOWNLOAD




DB = pd.DataFrame()

APP_RUNNING = True

TBD_DOWNLOAD = [] # the list of Downloadable Albums

TBD_NO_DOWNLOAD = [] # the list of Albums missing downloadable links



FAILED_DOWNLOADS = 0


"""
Loads the database of albums from the google sheet defined by 
DB_SHEET_ID and DB_SHEET_NAME 

"""
def load_database():
    db_url = f'https://docs.google.com/spreadsheets/d/{DB_SHEET_ID}/gviz/tq?tqx=out:csv&sheet={DB_SHEET_NAME}'

    logging.info(f'DB URL: {db_url}s')
    # Read the spreadsheet
    return pd.read_csv(db_url)

def update_failed_downloads():
    global FAILED_DOWNLOADS
    FAILED_DOWNLOADS = FAILED_DOWNLOADS +1
    logging.info(f'failed downloads updated to: {FAILED_DOWNLOADS}')
    

from downloader import update_failed_downloads

class loggerOutputs:
    
    def error(msg):
        print("Captured Error: "+msg)
        #logging.error(f'FAILED DOWNLOAD track: {TRACK_NUMBER} {TRACK_NAME}')
        update_failed_downloads()
        
    def warning(msg):
        #check = True
        print("Captured Warning: "+msg)
    
        
    def debug(msg):
        #check = True
        print("Captured debug: "+msg)
        
        
#####################################################################################
#
#   Given a youtube music URL and a folder, it downloads the contents of that URL to the folder
#  
##################################################################################### 
def download_album(url, folder):
    global FAILED_DOWNLOADS
    # Download the video
    

    FAILED_DOWNLOADS = 0
    
    logging.info(f'Downloading the album to "{folder}s"...')
    ydl_opts_old = {"outtmpl" : folder + "/%(playlist)s/%(playlist_index)s - %(title)s.%(ext)s",
                "format" : "ba"
                }
                
    ydl_opts={#'final_ext': 'mp3',
     'format': 'bestaudio/best',
     #'username': 'russelldad@gmail.com',
     'ignoreerrors': True,
     #'cookies-from-browser': 'brave',
     #'cookies': './cookies.txt',
     #'cookies-from-browser': '/Users/paul/Library/Application Support/BraveSoftware/Brave-Browser',
     #'nooverwrites': True,
     'no-abort-on-error': True,
     #"quiet": True,
     
     "logger": loggerOutputs,
     
     #'download-archive': "archive.txt" 
     #--write-info-json --no-overwrites --no-post-overwrites 
     #'postprocessors': [{'key': 'FFmpegExtractAudio',
     #                    'nopostoverwrites': False,
     #                    'preferredcodec': 'mp3',
     #                    'preferredquality': '5'}],
     #"outtmpl" : folder + "/%(playlist)s/%(playlist_index)s - %(title)s.%(ext)s",
     "outtmpl" : folder + "/%(playlist_index)s - %(title)s.%(ext)s"}
     
     #'ffmpeg_location': 'ffmpeg'}            
             
    with YoutubeDL(ydl_opts
        #{
        #    "outtmpl": "%(playlist)s/%(playlist_index)s - %(title)s.%(ext)s"
        #  
           # "outtmpl": f"{folder}/%(playlist_autonumber)_%(title)s.%(ext)s" #,
         #   "format": "bestvideo",
        #}
    ) as ydl:
        try:
            #TRACK_NUMBER = TRACK_NUMBER+1
            #info = ydl.extract_info(url)
            
            #TRACK_NAME = info['title']
            #logging.info(f"Downloaded track: {track_title}")
            ydl.download([url])
        except:
            logging.warning(f'Failed to Download Track. {url}')
    logging.info("Completed album download.")
    logging.info(f'{FAILED_DOWNLOADS} Failed File Downloads')


"""
Finds a given value in a given column of the DB and returns the value from another column in that row.

    search_column - The column header for the field to search.
    search_term - The term to search for in the search column
    result_column - The name of the column from which to return a result

returns the value from column result_column in the row where search_term was found in search_column
"""
def lookup_field_by_field(df, search_column, search_term, result_column):
    # Get the value to look up
    # Check if the value is found in the DataFrame
    search_term_string = str(search_term)
    
    if search_term_string in df[search_column].values:
        # Find the row where the value is located
        row_index = df[df[search_column] == search_term_string].index[0]
        # Get the value in the corresponding column
        result_value = df.loc[row_index, result_column]
        # Print the value
        
        logging.debug(f'Found {result_column}: {result_value}s')
        return result_value
    else:
        #didn't find that RFID in the sheet
        logging.warning(f'The value {search_term} was not found in the column {search_column}.')
        return 0




def lookup_album_url_by_field(df, field, value_to_lookup):
    # Get the value to look up
    # Check if the value is found in the DataFrame
    rfid_as_string = str(value_to_lookup)
    
    if rfid_as_string in df['folder'].values:
    #if value_to_lookup in df["rfid"]:
        # Find the row where the value is located
        row_index = df[df["folder"] == rfid_as_string].index[0]
        # Get the value in the corresponding column
        value_in_column_b = df.loc[row_index, "url"]
        # Print the value
        
        logging.debug(f'Found URL: {value_in_column_b}s')
        return value_in_column_b
    else:
        #didn't find that RFID in the sheet
        logging.warning(f'The value "{value_to_lookup}" was not found in the spreadsheet.')
        return 0
      

def list_non_downloaded_albums():
    global DB, TBD_DOWNLOAD, LIBRARY_SOURCE_FOLDER, TBD_NO_DOWNLOAD
    
    print("\n\n\n")
    print("#######  Choose an Album to Download   #######")
    print("\n")
    TBD_DOWNLOAD = []
    for album_folder_name in DB['folder'].values:
        #url = lookup_album_url_by_album_name(DB, album_name)
        
        
        
        url = str(lookup_field_by_field(DB, 'folder', album_folder_name, 'url'))
        
        
        #if (url !=0):
        #    album_id = get_album_id(url)
        if (url.startswith('https://music.youtube.com') == False and url.startswith('https://www.youtube.com') == False):
               TBD_NO_DOWNLOAD.append(album_folder_name)
               album_folder_name = 0
           
        
        if (album_folder_name != 0):
            album_folder = LIBRARY_SOURCE_FOLDER + album_folder_name

            logging.debug(f'CHECKING {album_folder}s...')
            if os.path.exists(album_folder):
                #if os.path.isdir(folder_name): 
                logging.debug (f'SKIP - album folder exists - {album_folder}s.')
                
            else:
                logging.debug (f'ADDING - album folder {album_folder}s.')
                TBD_DOWNLOAD.append(album_folder_name)

    
    #print out the list of available 
    
    if len(TBD_DOWNLOAD) == 0:
        print ('All albums with links downloaded.')
    else:
        for idx, album in enumerate(TBD_DOWNLOAD):
            print("{}  {}".format(idx, album))
    
        # This is the bulk Downloader    
        if BULK_DOWNLOAD == True:
            for idx, x in enumerate(TBD_DOWNLOAD):
                print("Downloading", idx, "  ", x)
                folder = LIBRARY_SOURCE_FOLDER + x
                url_to_download = lookup_album_url_by_field(DB, 'folder', x)
                if url_to_download == 'gdrive' or url_to_download == '':
                    print("You need to get this from google drive\n\n")
                else:
                    download_album(url_to_download,folder)
            print("\n\n#######################################")
            print("            BULK DOWNLOAD COMPLETE")
            print("#######################################\n")
    




def main():
    global DB
    
    #try:
    # Load the database of RFID tags and their matching albums
    DB = load_database()


    if BULK_DOWNLOAD == True:
        list_non_downloaded_albums()
    else:

        running = True
        while running:
            list_non_downloaded_albums()
            input_value = input('Enter a number to download the album (x to exit): ')
        
           
        
            if (input_value == 'x' or input_value == ''):
                exit()
            else:
                number = int(input_value)
                folder = LIBRARY_SOURCE_FOLDER + TBD_DOWNLOAD[number]
                url_to_download = lookup_album_url_by_field(DB, 'folder', TBD_DOWNLOAD[number])
                if url_to_download == 'gdrive' or url_to_download == '':
                    print("\n\n#######################################")
                    print("You need to get this from google drive")
                    print("#######################################\n")
                    keepgoing = input('Press any key to continue')
                else:
                    download_album(url_to_download,folder)
            

            
        


main()
    







    
#####################################################################################
#
#   
#   
#
##################################################################################### 

#####################################################################################
#
#   
#   
#
##################################################################################### 