""" convert_audio.py takes any folder This is a helper script intended for one time use

I wrote it to help migrate to using the folder field in the DB
as the field to save the music into.

Previs versions used the Album name or youtube UID which was
both hard to read, and could be changed by the end user causing issues.
"""


import os
from urllib.parse import urlparse, parse_qs
import pandas as pd

import threading
import logging
import subprocess
import configfile as CONFIG


logging.basicConfig(format=' %(message)s -- %(funcName)s %(lineno)d', level=logging.INFO)





LIBRARY_CACHE_FOLDER = "./library/"
LIBRARY_SOURCE_FOLDER = "./webm/" # This is where we put the full source files.

# Use these two parameters to identify the google sheet with your album database
DB_SHEET_ID = CONFIG.DB_SHEET_ID
DB_SHEET_NAME = CONFIG.DB_SHEET_ID



DB = pd.DataFrame()

APP_RUNNING = True

TBD_DOWNLOAD = [] # the list of Downloadable Albums





def load_database():
    db_url = f'https://docs.google.com/spreadsheets/d/{DB_SHEET_ID}/gviz/tq?tqx=out:csv&sheet={DB_SHEET_NAME}'

    logging.info(f'DB URL: {db_url}s')
    # Read the spreadsheet
    return pd.read_csv(db_url)



def lookup_album_url_by_field(df, field, value_to_lookup):
    # Get the value to look up
    #value_to_lookup = 2
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
        



def list_non_converted_albums():
    global DB, TBD_DOWNLOAD, LIBRARY_SOURCE_FOLDER, LIBRARY_CACHE_FOLDER
    
    print("\n\n\n")
    print("#######  Choose an Album to Convert   #######")
    print("\n")
    TBD_DOWNLOAD = []
    for album_name in DB['folder'].values:

        
        if (album_name != 0):
            album_folder = LIBRARY_CACHE_FOLDER + album_name

            logging.debug(f'checking {album_folder}s...')
            if os.path.exists(album_folder):
                #if os.path.isdir(folder_name): 
                logging.debug (f'Album folder {album_folder}s exists.')
                

            else:
                logging.debug (f'Album {album_folder}s needs conersion.')
                TBD_DOWNLOAD.append(album_name)

    #print out the list of available 
    for idx, album in enumerate(TBD_DOWNLOAD):
        print("{}  {}".format(idx, album))
    
   
  
    

def convert_audio(source_file, source_folder, destination_folder):
    
    logging.debug(f'File conversion {source_file}' )
    # make the destination directory if it doesn't exist.
    if os.path.exists(destination_folder):
        #do nothing
        logging.debug(f'  Destination folder exists {destination_folder}' )

        print("Directory exists.")
    else:
        logging.info(f'  Creating director {destination_folder}' )
        os.mkdir(destination_folder)
    


    #path = '[yourmp4fileaddress]'
    logging.info(f'Converting {source_file} >>> {destination_folder}')
    source_file_location = source_folder + '/' + source_file
    destination_file_location = destination_folder +  '/' + source_file
    subprocess.run(f'ffmpeg -i "{source_file_location}" -vn -ab 320k -ar 48000 "{destination_file_location}".mp3',shell=True)
        




def main():
    global DB
    
    #try:
    # Load the database of RFID tags and their matching albums
    DB = load_database()

    #list_non_downloaded_albums()
    #list_non_downloaded_albums()

    list_non_converted_albums()

    BULK_RUN = True
    if BULK_RUN:
        for idx, source_folder_name in enumerate(TBD_DOWNLOAD):
            source_folder = LIBRARY_SOURCE_FOLDER + source_folder_name
            destination_folder = LIBRARY_CACHE_FOLDER + source_folder_name
            
            #source_files = [os.path.join(source_folder, f) for f in os.listdir(source_folder) ]
            if os.path.exists(source_folder):
                #if os.path.isdir(folder_name): 
                logging.debug (f'Album folder {source_folder} exists. Starting conversion')
                for source_file in os.listdir(source_folder): 
                    convert_audio(source_file, source_folder, destination_folder)
                else:
                   logging.debug (f'Did not find folder {source_folder} . Skipping conversion') 
    else:        
        running = True
        while running:
            
            number = int(input('Enter a number to convert the album audio: '))
        
           
        
            if number < 0:
                exit()
            else:
            
            
                source_folder = LIBRARY_SOURCE_FOLDER + TBD_DOWNLOAD[number]
                destination_folder = LIBRARY_CACHE_FOLDER + TBD_DOWNLOAD[number]
            
              
                for source_file in os.listdir(source_folder): 
                    convert_audio(source_file, source_folder, destination_folder)
                
            
              
            keep_going = input("\n\nEnter to continue. 'X' to quit\n\n")
            if keep_going == 'x':
                exit()
            else:
                list_non_converted_albums()
            
        


main()
    




