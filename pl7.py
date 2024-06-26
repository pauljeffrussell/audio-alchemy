import pygame
import os
import logging
import time
import random
import os
import time
import configfile as CONFIG
import aareporter
import traceback
from audio_position_database import AudioPositionDatabase

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


S_ALBUM_REPEAT = False

S_SONG_SHUFFLE = False

SONG_SHUFFLE_ORIGINAL_SETTING = False

S_REMEMBER_POSITION = False

S_ALBUM_RFID = None

S_LAST_TRACK = 0

S_LAST_POSITION = 0

## the number of times the current album has repeated
COUNT_REPEATS = 0


SUPPORTED_EXTENSIONS = ['.mp3', '.MP3', '.wav', '.WAV', '.ogg', '.OGG']

DEVICE_NAME = 'Audio Adapter (Unitek Y-247A) Mono'

PREVIOUS_FOLDER = None

DB_AUDIO_POSITION = None

## keeps track of weather or not the tracks have all been played.
## This is True after the tracks have played, until someone starts playing them again.
#TRACKS_COMPLETE = False

logger = None

# Initialize the current index and current track variables
current_index = 0

MUSIC_STOPPED = 0


def startup():
    global ALBUM_LOADED, MUSIC_PAUSED, END_TRACK_INDEX, MUSIC_STOPPED, DB_AUDIO_POSITION
    global S_ALBUM_REPEAT, S_SONG_SHUFFLE, S_REMEMBER_POSITION, S_ALBUM_RFID, S_LAST_TRACK, S_LAST_POSITION
    
    #reset the state back to the beginning state so we don't get weirdness
    END_TRACK_INDEX = 0
    MUSIC_PAUSED = 1
    ALBUM_LOADED = False 
    #PLAYER_RUNNING = False
    S_ALBUM_REPEAT = False
    S_SONG_SHUFFLE = False
    SONG_SHUFFLE_ORIGINAL_SETTING = False
    
    S_REMEMBER_POSITION = False
    
    S_ALBUM_RFID = ''
    S_LAST_TRACK = 0
    S_LAST_POSITION = 0
    
    MIXER_LOADED = False
    MUSIC_STOPPED = 0
    
    DB_AUDIO_POSITION = AudioPositionDatabase()
    
    ## It's possible for the audio drivers not to be loaded at the point this is called
    ## So we try and if it doesn't work, we wait 5 seconds and try again.
    ## Rinse and repeat until it works.
    while not MIXER_LOADED:
        try:
            logger.debug("Attempting to load the mixer.")
            pygame.mixer.pre_init(48000, -16, 2, 2048)
            pygame.init()
            pygame.mixer.init()
            pygame.mixer.music.set_volume(1)
            logger.debug("SUCCESS! The mixer loaded.")
            MIXER_LOADED = True
        except:
            logger.debug("Mixer load failed. Retrying in 5 seconds.")
            time.sleep(5)

def set_logger(external_logger):
    global logger
    logger = external_logger


def set_repeat_album(repeat):
    """ Tells the current album to repeat. """
    global S_ALBUM_REPEAT
    
    S_ALBUM_REPEAT = repeat



def is_playing():
    if (MUSIC_PAUSED == 1):
        return False
    else:
        return True
     
    
def keep_playing():
    global MUSIC_PAUSED
    #Check if the current track has finished
    
    #busy = pygame.mixer.music.get_busy()
    
    #logger.debug(f'Next Song? Album in progress: {ALBUM_IN_PROGRESS}    Paused: {MUSIC_PAUSED}  Music Player Busy: {busy}' )
    
    
    if (MUSIC_PAUSED ==0 and pygame.mixer.music.get_busy() == False):
        """
        The music isn't paused and the player isn't busy. So we should 
        try to play the next track
        """        
        # Play the next track
        logger.debug(f'Track Ended. Playing Next Track.')
        next_track()

    
    
def play_tracks(tracks, repeat, shuffle, remember_position, rfid_code):
    global TRACK_LIST, END_TRACK_INDEX, current_index, ALBUM_LOADED, MUSIC_PAUSED, TRACK_LIST_ORIGINAL_ORDER, COUNT_REPEATS 
    global S_ALBUM_REPEAT, S_SONG_SHUFFLE, S_REMEMBER_POSITION, S_ALBUM_RFID, S_LAST_TRACK, S_LAST_POSITION


    if ALBUM_LOADED:
        shutdown_player()


    
    # Initialize Pygame    
    logger.debug("Initiallizing pygame...")
    startup()
    logger.debug("Completed initializing pygame")

    current_index = 0
    
    # make the list of tracks available to the entire player
    TRACK_LIST = tracks
    TRACK_LIST_ORIGINAL_ORDER = tracks.copy()
    END_TRACK_INDEX = len(TRACK_LIST)
    logger.debug(f'Total Tracks to play: {END_TRACK_INDEX}')
    
    # set this global so the keep playing and next functions know if they should repeat at album end.
    S_ALBUM_REPEAT = repeat
    
    # set this global so we know if the album songs are shuffled. If they are only record the 0 index and not every
    ## change in folder. see play_cuurrent_track
    S_SONG_SHUFFLE = shuffle
    SONG_SHUFFLE_ORIGINAL_SETTING = S_SONG_SHUFFLE
    COUNT_REPEATS = 0
    
    
    S_REMEMBER_POSITION = remember_position
    S_ALBUM_RFID = rfid_code
    
    if S_REMEMBER_POSITION:
        ## we're supposed to remember the position of this album when it stops.
        ## and play from there when we restart
        
        logger.debug(f"Looking up position info for RFID: {S_ALBUM_RFID}")
        position_info = DB_AUDIO_POSITION.get_position_info(S_ALBUM_RFID)
        if position_info:
            ## the DB has some position info
            
            S_LAST_TRACK = position_info[0]
            S_LAST_POSITION = position_info[1]
            logger.debug(f"Found saved position info for RFID: {S_ALBUM_RFID}, Track: {position_info[0]}, Time in Seconds: {position_info[1]}")
        else:
            logger.debug(f"No saved position info found in the DB for RFID: {S_ALBUM_RFID}")
    else:
        S_LAST_TRACK = 0
        S_LAST_POSITION = 0
    
    
    ## this should really be done by passing the CONFIG variables into the play tracks
    ## method, but 
    if (END_TRACK_INDEX != 0 and CONFIG.FEEDBACK_RECORD_START_ENABLED):
        ## play the record scratch sound
        play_feedback(CONFIG.FEEDBACK_RECORD_START)
        ## now we wait for a bit before starting the album so it sounds like a real record.
        time.sleep(1.4)
    
    # Play the first track
    #current_track = TRACK_LIST[current_index]
    
    ## this is the only time we tell this function to honor 
    ## remembering the track position. Otherwise, we could never leave the track.
    play_current_track(True)

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
            logger.debug(f'New Index Found {next_index}...')
            jump_to_track(next_index)
            return 1     
        next_index += 1
    logger.debug(f'Returning to Index 0...')  
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
            
            logger.debug(f'New Index Found {album_first_track}...')
            jump_to_track(album_first_track)
            return 1     
        prev_index -= 1
    logger.debug(f'Returning to Index 0...')  
    jump_to_track(0)   # No different directory found after the given index



def shuffle_current_songs():
    global TRACK_LIST, current_index, S_SONG_SHUFFLE
    
    pygame.mixer.music.stop()
    
    S_SONG_SHUFFLE = True
    
    random.shuffle(TRACK_LIST)
    
    current_index = 0
    play_current_track()

def unshuffle_current_songs():
    global TRACK_LIST, current_index, TRACK_LIST_ORIGINAL_ORDER, S_SONG_SHUFFLE, SONG_SHUFFLE_ORIGINAL_SETTING
    
    pygame.mixer.music.stop()
    
    ## we put back the original order. Some playlists are not alphabetically ordered.
    ## for example the play 5 random albums are in order per album, but the albums aren't in a specific order
    ## moreover, of you sort that list, you're going to get albums overlapping each other.
    TRACK_LIST = TRACK_LIST_ORIGINAL_ORDER.copy()
    
    ## we don't put S_SONG_SHUFFLE back at this point because we 
    S_SONG_SHUFFLE = SONG_SHUFFLE_ORIGINAL_SETTING
    
    
    current_index = 0
    play_current_track()


## picks a random track in the album and plays the track in order from there. 
def play_in_order_from_random_track():
    
    try:
        new_track_index = random.randint(0, len(TRACK_LIST) - 1)
        logger.debug(f'Jumping to track: {new_track_index} and continuing to play in order...')
        jump_to_track(new_track_index)
        S_ALBUM_REPEAT = True
    except:
        logger.error("Unable to jump to a random track. There was a problem picking a random index.")
        


def get_index_of_first_track(album_directory):
    global TRACK_LIST
    
    for index in range(len(TRACK_LIST)):
        if os.path.dirname(TRACK_LIST[index]) == album_directory:
            return index
    
    return 0
    
    


def play_pause_track():
    global MUSIC_PAUSED, MUSIC_STOPPED
    
    if (MUSIC_STOPPED == 1):
        ## the music was stopped. This is likely
        ## because you reached the end of the album
        ## It's looped back around to the beginning 
        ## but the player is stopped instead of paused. Since pygame.mixer.music.unpause()
        ## doesn't work on stopped music, we need to call play.
        play_current_track()
        
    elif (MUSIC_PAUSED == 1):
        unpause_track()
    else:
        pause_track()
        

# Define the menu functions
def unpause_track():
    global MUSIC_PAUSED
    MUSIC_PAUSED = 0
    pygame.mixer.music.unpause()
    logger.debug('Unpaused album.')

def pause_track():
    global MUSIC_PAUSED
    MUSIC_PAUSED = 1
    pygame.mixer.music.pause()
    logger.debug('Paused album.')
    save_position()
    

def save_position():
    
    if S_REMEMBER_POSITION:
        
        if (current_index == S_LAST_TRACK):
            position = pygame.mixer.music.get_pos() + S_LAST_POSITION
        else:
            position = pygame.mixer.music.get_pos()
            
            
        if (position > 10):
            position = position - 10
        else:
            position = 0
        
        DB_AUDIO_POSITION.add_or_update_entry(S_ALBUM_RFID, current_index, position)
        logger.debug(f'Saved Track and position. track {current_index}, position: {position}')




def play_current_track(check_remember=False):
    global TRACK_LIST, current_index, MUSIC_PAUSED, PREVIOUS_FOLDER, MUSIC_STOPPED
    
    current_track = None
    try:

        if (check_remember and S_REMEMBER_POSITION):
            current_index = S_LAST_TRACK 
            current_track = TRACK_LIST[current_index]
            logger.debug(f'Starting: {current_track}')
            pygame.mixer.music.load(current_track)
            pygame.mixer.music.rewind()
            position = S_LAST_POSITION/1000
            pygame.mixer.music.play(start=position)
        else:
            current_track = TRACK_LIST[current_index]
            logger.debug(f'Starting: {current_track}')
            pygame.mixer.music.load(current_track)
            pygame.mixer.music.play() 
            
        MUSIC_PAUSED = 0
        MUSIC_STOPPED = 0
                
        if (current_index == 0):
            #we've started or restarted an album. So reset the album name so we count it again
            PREVIOUS_FOLDER = None
            
        report_track(current_track)
    except Exception as e:
        if (current_track == None):
            stack_trace = traceback.format_exc()
            #print(f"An exception occurred: {e}\nStack trace:\n{stack_trace}")
            logger.error(f"No track to play. An exception occurred: {e}\nStack trace:\n{stack_trace}")
            #logger.error(f'Unable to play track at index "{current_index}" {e} ')
        else:
            logger.error(f'Unable to play track "{current_track}" {e} ')
            stack_trace = traceback.format_exc()
            #print(f"An exception occurred: {e}\nStack trace:\n{stack_trace}")
            logger.error(f"Unable to play track. An exception occurred: {e}\nStack trace:\n{stack_trace}")
            #logger.error(f'Unable to play track "{current_track}" {e} ')
        
    

def get_current_track():
    """
    gets the current track that is playing
    
    """
    global TRACK_LIST
    if is_playing():
        return TRACK_LIST[current_index]
    else:
        return None
    


def jump_to_track(track_index):
    global current_index, TRACK_LIST, MUSIC_PAUSED
  
    MUSIC_PAUSED = 0
    # Stop the mixer
    pygame.mixer.music.stop()
    
    # Get the next index
    current_index = track_index
    play_current_track()
    
  


def next_track(button_press=True):
    global current_index, TRACK_LIST, MUSIC_PAUSED, MUSIC_STOPPED, COUNT_REPEATS
  
    
    """ Started writing this code to enable skip ahead 15 seconds 
        when listening to podcasts / things where you'd remember the position.
    
    if (button_press==True and S_REMEMBER_POSITION == True):
        ## we're listening to something where it's going to stop and start
        ## and we might want to jump around a bit
        fast_forward()
        return"""
  
    if is_playing():
        ## The track is playing. Let's go to the next   
        MUSIC_PAUSED = 0
        # Stop the mixer
        pygame.mixer.music.stop()
    
    
        # Get the next index
        current_index += 1
        if (S_ALBUM_REPEAT == False and current_index >= len(TRACK_LIST)):
            current_index = 0
            # 2024-02-05 removed these two lines. Since I added logging 
            # to the play_current_track function it's become obvious that 
            # I'm playing these tracks for no reason
            # play_current_track()
            # pause_track()
            MUSIC_STOPPED = 1
            MUSIC_PAUSED = 1
            logger.debug(f'Reached end of album. Press play to restart album.')
        elif (S_ALBUM_REPEAT == True and current_index >= len(TRACK_LIST)):
            ## The album reached it's end and should now restart

            current_index = 0
            
            ## This is here to make sure we don't just keep playing an album forever.
            ## This can happen if someone turns off the amplifier without hitting pause. 
            if (COUNT_REPEATS < CONFIG.MAX_REPLAY_COUNT):
                COUNT_REPEATS = COUNT_REPEATS + 1
                play_current_track()
                MUSIC_STOPPED = 0
                logger.debug(f'Reached end of album. Album set to repeat. Restarting at the album beginning.')
            else:
                logger.debug(f'Completed max allowed repeats of album. Player stopped automatically.')
            
        else:
            # Load and play the next track
            play_current_track()
            MUSIC_STOPPED = 0
            
    else:
        ## the music wasn't playing. Don't index the track, just start playing again where ever it stopped.
        play_pause_track()
        


def prev_track():
    """
    If the current track has been playing for more than 10 seconds this brings the user back 
    to the beginning of the currently playing track
    
    If the current track has been playing for less than 10 seconds it brings you to the previous 
    track.
    """
    global current_index, TRACK_LIST, MUSIC_PAUSED
  
    position = pygame.mixer.music.get_pos()
      
  
    MUSIC_PAUSED = 0
    # Stop the mixer
    
    pygame.mixer.music.stop()
    
    
    ## this checks how many miliseconds into the song
    
    logger.debug(f'Music Position: {position}')
    
    ## the player has reached.
    if (position < 6000):
        ## if the track has been playing for less than 6 seconds
        ## Go to the previous track
        current_index -= 1
        if current_index < 0:
            current_index = len(TRACK_LIST) - 1
        
        ## Otherwise we'll just go back to the beginning of the current 
        ## track and start playing it again.
    
    # Load and play the previous track
    current_track = TRACK_LIST[current_index]
    play_current_track()
 


def play_feedback(feedback_file):
    
    try:
        feedback_audio = pygame.mixer.Sound(feedback_file)
        feedback_audio.play()
    except Exception as e:
        logger.error(f'Unable to play feedback sound "{feedback_file}" {e} ')
        
        
    
def play_speech(speech_file):
    
    
    # turn down the music so we can hear the speaking
    pygame.mixer.music.set_volume(0.3)
    time.sleep(0.2)
    
    # Load the short sound effect
    speech = pygame.mixer.Sound(speech_file)
    speech.set_volume(1.0)  # Set volume for the short sound
    
    speech.play()
    
    #Wait for the short sound to finish (simplistic timing control)
    pygame.time.wait(int(speech.get_length() * 1000))
    
    time.sleep(0.2)
    
    ## return the music audio back to normal
    pygame.mixer.music.set_volume(1)
    
        
def report_track(current_track):
    global PREVIOUS_FOLDER, S_SONG_SHUFFLE
    folder, file_name = get_folder_and_file(current_track)
    logger.debug(f'folder: {folder}')
    logger.debug(f'file: {file_name}')
    aareporter.log_track_play(folder, file_name)
    
    logger.debug(f'preparing to log album')
    if (PREVIOUS_FOLDER != folder and S_SONG_SHUFFLE == False ):
        # we're playing a new album. We ignore song shuffled albums because
        # they will create lots of album plays as they jump thorugh albums
        logger.debug(f'logging album')
        aareporter.log_album_play(folder)

    PREVIOUS_FOLDER = folder
    
    
def get_folder_and_file(path):
    # Get the full path of the directory
    folder_path = os.path.dirname(path)
    # Extract the folder name from the full path
    folder_name = os.path.basename(folder_path)
    # Extract the file name from the full path
    file_name = os.path.basename(path)
    return folder_name, file_name
    

        
def shutdown_player():
    #global PLAYER_RUNNING
    #PLAYER_RUNNING = False
    logger.debug('Starting Player Shutdown')
    
    # Define custom event constant
    #MY_CUSTOM_EVENT = pygame.USEREVENT + 1
    #pygame.event.post(pygame.event.Event(MY_CUSTOM_EVENT))
    #time.sleep(3)
    
    pause_track()
    pygame.mixer.music.stop()
    pygame.quit()
    logger.debug('Completed Player Shutdown')
    


