import pygame
import os
import logging
import time
import random





# Define the directory containing the MP3 files
#mp3_dir = "testshort"

# Get a list of all the MP3 files in the directory
mp3_files = []#[os.path.join(mp3_dir, f) for f in os.listdir(mp3_dir) if f.endswith('.mp3')]
# Sort the list of MP3 files alphabetically


END_TRACK_INDEX = 0

## Determines the state of the player. 
## when 1 the player is paused
## when 0 the player is playing
MUSIC_PAUSED = 1

ALBUM_LOADED = False # used to determine if I should cleanup pygame before starting the next track

## appears to be the same as ALBUM LOADED. Can probably be combined into one variable 
PLAYER_RUNNING = False


# should the current album be shuffled
#ALBUM_SHUFFLE = False


ALBUM_REPEAT = False



# Initialize the current index and current track variables
current_index = 0


def startup():
    pygame.mixer.pre_init(48000, -16, 2, 2048)
    pygame.init()
    

    
def keep_playing():
    global PLAYER_RUNNING, MUSIC_PAUSED
    #Check if the current track has finished
    #logging.debug(f'Next Song? Player Running: {PLAYER_RUNNING}.  Paused: {MUSIC_PAUSED}')
    
    
    
    if (PLAYER_RUNNING == True and MUSIC_PAUSED ==0 and pygame.mixer.music.get_busy() == False):
        # Play the next track
        logging.debug(f'Track Ended. Playing Next Track.')
        next_track()
    

def play_folder(folder_path, shuffle, repeat):
    global mp3_files, END_TRACK_INDEX, current_index, current_track, mp3_dir, ALBUM_LOADED, MUSIC_PAUSED, PLAYER_RUNNING

    

    if ALBUM_LOADED:
        shutdown_player()

    PLAYER_RUNNING = True
    #ALBUM_SHUFFLE = shuffle
    
    # set this global so the keep playing and next functions know if they should repeat at album end.
    ALBUM_REPEAT = repeat
    
    
    logging.debug("Initiallizing pygame...")
    # Initialize Pygame
    pygame.mixer.pre_init(48000, -16, 2, 2048)
    pygame.init()
    #pygame.mixer.init(48000, -16, 1, 1024)
    pygame.mixer.music.set_volume(1)
    logging.debug("Completed initializing pygame")

    current_index = 0
    print("folder path: ", folder_path )

    # Get a list of all the MP3 files in the directory
    mp3_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) ]

    # mp3_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith('.ogg')]
    
    if shuffle == True:
        random.shuffle(mp3_files)
    else:
        # Sort the list of MP3 files alphabetically
        mp3_files.sort()

    END_TRACK_INDEX = len(mp3_files)
    
    print("total tracks ", END_TRACK_INDEX)
    
    # Play the first track
    #current_index += 1
    current_track = mp3_files[current_index]
    # Load the current track
    
    play_current_track()
    #logging.info(f'Loading track {current_track}')
    #pygame.mixer.music.load(current_track)
    #pygame.mixer.music.play()
    MUSIC_PAUSED = 0
    ALBUM_LOADED = True
    print ("End track index", END_TRACK_INDEX)

def play_pause_track():
    global MUSIC_PAUSED
    if (MUSIC_PAUSED == 1):
        unpause_track()
    else:
        pause_track()
        

# Define the menu functions
def unpause_track():
    global MUSIC_PAUSED
    MUSIC_PAUSED = 0
    pygame.mixer.music.unpause()

def pause_track():
    global MUSIC_PAUSED
    MUSIC_PAUSED = 1
    pygame.mixer.music.pause()
    logging.info('Pausing album.')

def play_current_track():
    global mp3_files, current_index
    
    current_track = mp3_files[current_index]
    logging.info(f'Starting: {current_track}')
    pygame.mixer.music.load(current_track)
    pygame.mixer.music.play()
    


def next_track():
    global current_index, mp3_files, MUSIC_PAUSED
  
    MUSIC_PAUSED = 0
    # Stop the mixer
    pygame.mixer.music.stop()
    
    # Get the next index
    current_index += 1
    if (ALBUM_REPEAT == False and current_index >= len(mp3_files)):
        current_index = 0
        play_current_track()
        pause_track()
        logging.info(f'Reached end of album. Press play to restart album.')
    else:
        # Load and play the next track
        play_current_track()


def prev_track():
    global current_index, mp3_files, MUSIC_PAUSED
  
    MUSIC_PAUSED = 0
    # Stop the mixer
    pygame.mixer.music.stop()
    
    # Get the previous index
    current_index -= 1
    if current_index < 0:
        current_index = len(mp3_files) - 1
    
    # Load and play the previous track
    current_track = mp3_files[current_index]
    play_current_track()
 



def shutdown_player():
    global PLAYER_RUNNING
    PLAYER_RUNNING = False
    logging.debug('Starting Player Shutdown')
    
    # Define custom event constant
    MY_CUSTOM_EVENT = pygame.USEREVENT + 1
    #pygame.event.post(pygame.event.Event(MY_CUSTOM_EVENT))
    #time.sleep(3)
    pygame.mixer.music.stop()
    pygame.quit()
    logging.debug('Completed Player Shutdown')
    


