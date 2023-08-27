import pygame
import os
import logging
import time
import random
import os
import time
#os.environ['SDL_AUDIODRIVER'] = 'dsp'




# Define the directory containing the MP3 files
#mp3_dir = "testshort"

# Get a list of all the MP3 files in the directory
TRACK_LIST = []#[os.path.join(mp3_dir, f) for f in os.listdir(mp3_dir) if f.endswith('.mp3')]
# Sort the list of MP3 files alphabetically

## This is the same as TRACK_LIST when the album is first loaded
## but you can shuffle the album which reoders TRACK_LIST
## We keep this list so we can go back to the unshuffled list
TRACK_LIST_ORIGINAL_ORDER = []


END_TRACK_INDEX = 0

## Determines the state of the player. 
## when 1 the player is paused
## when 0 the player is playing
MUSIC_PAUSED = 1

ALBUM_LOADED = False # used to determine if I should cleanup pygame before starting the next track

## appears to be the same as ALBUM LOADED. Can probably be combined into one variable 
#PLAYER_RUNNING = False
#ALBUM_IN_PROGRESS = False

# should the current album be shuffled
#ALBUM_SHUFFLE = False


ALBUM_REPEAT = False

SUPPORTED_EXTENSIONS = ['.mp3', '.MP3', '.wav', '.WAV', '.ogg', '.OGG']

DEVICE_NAME = 'Audio Adapter (Unitek Y-247A) Mono'


## keeps track of weather or not the tracks have all been played.
## This is True after the tracks have played, until someone starts playing them again.
#TRACKS_COMPLETE = False


# Initialize the current index and current track variables
current_index = 0


def startup():
    global ALBUM_REPEAT, ALBUM_LOADED, MUSIC_PAUSED, END_TRACK_INDEX
    
    
    #reset the state back to the beginning state so we don't get weirdness
    END_TRACK_INDEX = 0
    MUSIC_PAUSED = 1
    ALBUM_LOADED = False 
    #PLAYER_RUNNING = False
    ALBUM_REPEAT = False
    
    MIXER_LOADED = False
    
    
    ## It's possible for the audio drivers not to be loaded at the point this is called
    ## So we try and if it doesn't work, we wait 5 seconds and try again.
    ## Rinse and repeat until it works.
    while not MIXER_LOADED:
        try:
            logging.debug("Attempting to load the mixer.")
            pygame.mixer.pre_init(48000, -16, 2, 2048)
            pygame.init()
            pygame.mixer.init()
            pygame.mixer.music.set_volume(1)
            logging.debug("SUCCESS! The mixer loaded.")
            MIXER_LOADED = True
        except:
            logging.debug("Mixer load failed. Retrying in 5 seconds.")
            time.sleep(5)


def is_playing():
    if (MUSIC_PAUSED == 1):
        return False
    else:
        return True
     
    
def keep_playing():
    global MUSIC_PAUSED
    #Check if the current track has finished
    
    busy = pygame.mixer.music.get_busy()
    
    #logging.debug(f'Next Song? Album in progress: {ALBUM_IN_PROGRESS}    Paused: {MUSIC_PAUSED}  Music Player Busy: {busy}' )
    
    
    if (MUSIC_PAUSED ==0 and pygame.mixer.music.get_busy() == False):
    #if (ALBUM_IN_PROGRESS == True and MUSIC_PAUSED ==0 and pygame.mixer.music.get_busy() == False):
        # Play the next track
        logging.debug(f'Track Ended. Playing Next Track.')
        next_track()
    

""" removed 2023-08-25. Looks like this was replaced by play_tracks a while back.
    def play_folder(folder_path, shuffle, repeat):
    global TRACK_LIST, END_TRACK_INDEX, current_index, current_track, mp3_dir, ALBUM_LOADED, MUSIC_PAUSED, SUPPORTED_EXTENSIONS, ALBUM_REPEAT

    

    if ALBUM_LOADED:
        shutdown_player()

    #logging.debug('Setting Player Running to true')
    #PLAYER_RUNNING = True
    #logging.debug(f'Player Running to {PLAYER_RUNNING}')
    #ALBUM_SHUFFLE = shuffle
    
    # set this global so the keep playing and next functions know if they should repeat at album end.
    ALBUM_REPEAT = repeat
    
    
    logging.debug("Initiallizing pygame...")
    # Initialize Pygame
    startup()
    #pygame.mixer.pre_init(48000, -16, 2, 2048, DEVICE_NAME)
    #pygame.init()
    #pygame.mixer.init(48000, -16, 1, 1024)
    
    logging.debug("Completed initializing pygame")

    current_index = 0
    print("folder path: ", folder_path )

    # Get a list of all the MP3 files in the directory
    #valid_extensions = ['.mp3', '.wav', '.ogg']
    TRACK_LIST = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if os.path.splitext(f)[1] in SUPPORTED_EXTENSIONS]
    
    
    # this line ysed to implode because of .DS_local files appearing in directories.
    #TRACK_LIST = [os.path.join(folder_path, f) for f in os.listdir(folder_path) ]

    # TRACK_LIST = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith('.ogg')]
    
    if shuffle == True:
        random.shuffle(TRACK_LIST)
    else:
        # Sort the list of MP3 files alphabetically
        TRACK_LIST.sort()

    END_TRACK_INDEX = len(TRACK_LIST)
    
    print("total tracks ", END_TRACK_INDEX)
    
    # Play the first track
    #current_index += 1
    current_track = TRACK_LIST[current_index]
    # Load the current track
    
    play_current_track()
    #logging.info(f'Loading track {current_track}')
    #pygame.mixer.music.load(current_track)
    #pygame.mixer.music.play()
    MUSIC_PAUSED = 0
    ALBUM_LOADED = True
    #ALBUM_IN_PROGRESS = True
    print ("End track index", END_TRACK_INDEX)
"""
    
    
def play_tracks(tracks, repeat):
    global TRACK_LIST, END_TRACK_INDEX, current_index, ALBUM_LOADED, MUSIC_PAUSED, ALBUM_REPEAT


    if ALBUM_LOADED:
        shutdown_player()

    # set this global so the keep playing and next functions know if they should repeat at album end.
    ALBUM_REPEAT = repeat
    
    # Initialize Pygame    
    logging.debug("Initiallizing pygame...")
    startup()
    logging.debug("Completed initializing pygame")

    current_index = 0
    
    # make the list of tracks available to the entire player
    TRACK_LIST = tracks
    TRACKS_ORIGINAL_ORDER = tracks
    END_TRACK_INDEX = len(TRACK_LIST)
    logging.debug(f'Total Tracks to play: {END_TRACK_INDEX}')
    
    # Play the first track
    #current_track = TRACK_LIST[current_index]
    play_current_track()

    MUSIC_PAUSED = 0
    ALBUM_LOADED = True
    
    
def jump_to_next_album():
    global TRACK_LIST, current_index
    
    index = current_index
    file_paths = TRACK_LIST
    
    current_directory = os.path.dirname(file_paths[index])
    next_index = index + 1

    while next_index < len(file_paths):
        next_directory = os.path.dirname(file_paths[next_index])
        if next_directory != current_directory:
            logging.debug(f'New Index Found {next_index}...')
            jump_to_track(next_index)
            return 1     
        next_index += 1
    logging.debug(f'Returning to Index 0...')  
    jump_to_track(0)   # No different directory found after the given index


def jump_to_previous_album():
    global TRACK_LIST, current_index
    
    index = current_index
    file_paths = TRACK_LIST
    
    current_directory = os.path.dirname(file_paths[index])
    
    ## first check if you're on the first track of the album.
    ## if not, go to that first track
    first_track_of_current_album = get_index_of_first_track(current_directory)
    if first_track_of_current_album != index:
        jump_to_track(first_track_of_current_album)    
        return 1
        
    ## if you got here, you were already on the first track of the album
    ## so now we want to find the first track of the previous album
    prev_index = index -1
    
    if prev_index < 0:
        prev_index = len(file_paths) - 1

    while prev_index > 0:
        prev_directory = os.path.dirname(file_paths[prev_index])
        if prev_directory != current_directory:
            # you've found the last track of the previous album
            
            # now find the first track of that previous album
            album_first_track = get_index_of_first_track(prev_directory)
            
            logging.debug(f'New Index Found {album_first_track}...')
            jump_to_track(album_first_track)
            return 1     
        prev_index -= 1
    logging.debug(f'Returning to Index 0...')  
    jump_to_track(0)   # No different directory found after the given index



def shuffle_current_songs():
    global TRACK_LIST, current_index
    
    pygame.mixer.music.stop()
    
    random.shuffle(TRACK_LIST)
    
    current_index = 0
    play_current_track()

def unshuffle_current_songs():
    global TRACK_LIST, current_index, TRACK_LIST_ORIGINAL_ORDER
    
    pygame.mixer.music.stop()
    
    ## we put back the original order. Some playlists are not alphabetically ordered.
    ## for example the play 5 random albums are in order per album, but the albums aren't in a specific order
    ## moreover, of you sort that list, you're going to get albums overlapping each other.
    TRACK_LIST = TRACK_LIST_ORIGINAL_ORDER
    
    current_index = 0
    play_current_track()


## picks a random track in the album and plays the track in order from there. 
def play_in_order_from_random_track():
    
    try:
        new_track_index = random.randint(0, len(TRACK_LIST) - 1)
        logging.debug(f'Jumping to track: {new_track_index} and continuing to play in order...')
        jump_to_track(new_track_index)
        ALBUM_REPEAT = True
    except:
        logging.error("Unable to jump to a random track. There was a problem picking a random index.")
        


def get_index_of_first_track(album_directory):
    global TRACK_LIST
    
    for index in range(len(TRACK_LIST)):
        if os.path.dirname(TRACK_LIST[index]) == album_directory:
            return index
    
    return 0
    
    


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
    global TRACK_LIST, current_index, MUSIC_PAUSED
    
    MUSIC_PAUSED = 0
    current_track = TRACK_LIST[current_index]
    logging.info(f'Starting: {current_track}')
    pygame.mixer.music.load(current_track)
    pygame.mixer.music.play()
    

def jump_to_track(track_index):
    global current_index, TRACK_LIST, MUSIC_PAUSED
  
    MUSIC_PAUSED = 0
    # Stop the mixer
    pygame.mixer.music.stop()
    
    # Get the next index
    current_index = track_index
    play_current_track()
    
  


def next_track():
    global current_index, TRACK_LIST, MUSIC_PAUSED, ALBUM_REPEAT
  
    MUSIC_PAUSED = 0
    # Stop the mixer
    pygame.mixer.music.stop()
    
    # Get the next index
    current_index += 1
    if (ALBUM_REPEAT == False and current_index >= len(TRACK_LIST)):
        current_index = 0
        play_current_track()
        pause_track()
        logging.info(f'Reached end of album. Press play to restart album.')
    else:
        # Load and play the next track
        play_current_track()


def prev_track():
    global current_index, TRACK_LIST, MUSIC_PAUSED
  
    MUSIC_PAUSED = 0
    # Stop the mixer
    pygame.mixer.music.stop()
    
    # Get the previous index
    current_index -= 1
    if current_index < 0:
        current_index = len(TRACK_LIST) - 1
    
    # Load and play the previous track
    current_track = TRACK_LIST[current_index]
    play_current_track()
 



def shutdown_player():
    #global PLAYER_RUNNING
    #PLAYER_RUNNING = False
    logging.debug('Starting Player Shutdown')
    
    # Define custom event constant
    #MY_CUSTOM_EVENT = pygame.USEREVENT + 1
    #pygame.event.post(pygame.event.Event(MY_CUSTOM_EVENT))
    #time.sleep(3)
    pygame.mixer.music.stop()
    pygame.quit()
    logging.debug('Completed Player Shutdown')
    


