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
import threading

###########################################################
### PLAYBACK_MANAGER is defined at the bottom of this file.
###########################################################

# Get a list of all the MP3 files in the directory
TRACK_LIST = []

## This is the same as TRACK_LIST when the album is first loaded
## but you can shuffle the album which reoders TRACK_LIST
## We keep this list so we can go back to the unshuffled list
TRACK_LIST_ORIGINAL_ORDER = []


END_TRACK_INDEX = 0

## Determines the state of the player. 
## when 1 the player is paused
## when 0 the player is playing
MUSIC_PAUSED = True

MUSIC_STOPPED = True

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



SLEEP_DURATION_KEEP_PLAYING = 0.1

import threading
import time

class PlaybackManager:
    """
    Controls the playback of music tracks by periodically calling the keep_playing method
    in a separate thread. The thread can be started and stopped as needed.
    """
    def __init__(self, keep_playing_function, sleep_duration):
        """
        Initializes the PlaybackManager with the given keep_playing_function and sleep duration.
        
        Args:
            keep_playing_function: The function that controls the playback of music.
            sleep_duration: The duration to sleep between calls to keep_playing_function.
        """
        self.keep_playing = keep_playing_function
        self.sleep_duration = sleep_duration
        self._stop_event = threading.Event()
        self._lock = threading.RLock()
        self.thread = None

    def _run(self):
        """
        The target method for the thread. Calls the keep_playing_function method
        every sleep_duration seconds, unless the stop event is set.
        """
        while not self._stop_event.is_set():
            with self._lock:
                self.keep_playing()
            time.sleep(self.sleep_duration)

    def start(self):
        """
        Starts the thread if it is not already running.
        """
        if not self.thread or not self.thread.is_alive():
            print ("\n##################")
            print ("THREAD -- START")
            print ("##################")
            self._stop_event.clear()
            self.thread = threading.Thread(target=self._run)
            self.thread.start()
        

    def stop(self):
        """
        Stops the thread if it is running. This method sets the stop event and waits
        for the thread to finish.
        """
        self._stop_event.set()
        print ("\n##################")
        print("THREAD -- STOP")
        print ("##################")
        if self.thread and self.thread.is_alive() and threading.current_thread() != self.thread:
            self.thread.join()
        self.thread = None

    def lock_decorator(self, func):
        """
        Decorator that ensures the decorated function executes within a thread-safe lock.

        Args:
            func: The function to be decorated.

        Returns:
            A wrapper function that executes the original function with a lock.
        """
        def wrapper(*args, **kwargs):
            with self._lock:
                return func(*args, **kwargs)
        return wrapper


'''class PlaybackManager:
    """
    Controls the playback of music tracks by periodically calling the keep_playing method
    in a separate thread. The thread can be started and stopped as needed.
    """
    def __init__(self, keep_playing_function, sleep_duration):
        """
        Initializes the PlaybackManager with the given keep_playing_function and sleep duration.
        
        Args:
            keep_playing_function: The function that controls the playback of music.
            sleep_duration: The duration to sleep between calls to keep_playing_function.
        """
        self.keep_playing = keep_playing_function
        self.sleep_duration = sleep_duration
        self._stop_event = threading.Event()
        self._lock = threading.RLock()
        self.thread = None

    def _run(self):
        """
        The target method for the thread. Calls the keep_playing_function method
        every sleep_duration seconds, unless the stop event is set.
        """
        while not self._stop_event.is_set():
            with self._lock:
                self.keep_playing()
            time.sleep(self.sleep_duration)

    def start(self):
        """
        Starts the thread if it is not already running.
        """
        if not self.thread or not self.thread.is_alive():
            self._stop_event.clear()
            self.thread = threading.Thread(target=self._run)
            self.thread.start()
        

    def stop(self):
        """
        Stops the thread if it is running. This method sets the stop event and waits
        for the thread to finish.
        """
        self._stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join()
        self.thread = None

    def lock_decorator(self, func):
        """
        Decorator that ensures the decorated function executes within a thread-safe lock.

        Args:
            func: The function to be decorated.

        Returns:
            A wrapper function that executes the original function with a lock.
        """
        def wrapper(*args, **kwargs):
            with self._lock:
                return func(*args, **kwargs)
        return wrapper'''

def _keep_playing():
    global MUSIC_PAUSED
    #Check if the current track has finished
    
    #busy = pygame.mixer.music.get_busy()
    #logger.debug("_keep_playing called.")
    #logger.debug(f'Next Song? Album in progress: {ALBUM_IN_PROGRESS}    Paused: {MUSIC_PAUSED}  Music Player Busy: {busy}' )
    
    
    if (MUSIC_PAUSED == False and pygame.mixer.music.get_busy() == False):
        """
        The music isn't paused and the player isn't busy. So we should 
        try to play the next track
        """        
        # Play the next track
        logger.debug(f'Track Ended. Playing Next Track.')
        next_track(False)

# Initialize the music controller with the player functions
PLAYBACK_MANAGER = PlaybackManager(_keep_playing, SLEEP_DURATION_KEEP_PLAYING)


def startup():
    global ALBUM_LOADED, MUSIC_PAUSED, END_TRACK_INDEX, MUSIC_STOPPED, DB_AUDIO_POSITION
    global S_ALBUM_REPEAT, S_SONG_SHUFFLE, S_REMEMBER_POSITION, S_ALBUM_RFID, S_LAST_TRACK, S_LAST_POSITION, PLAYBACK_MANAGER
    
    #reset the state back to the beginning state so we don't get weirdness
    END_TRACK_INDEX = 0
    MUSIC_PAUSED = True
    MUSIC_STOPPED = True
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


@PLAYBACK_MANAGER.lock_decorator 
def is_playing():
    if (MUSIC_PAUSED == True):
        return False
    else:
        return True
     
    

    
@PLAYBACK_MANAGER.lock_decorator    
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
    _play_current_track(True)

    MUSIC_PAUSED = False
    ALBUM_LOADED = True
    
@PLAYBACK_MANAGER.lock_decorator
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
            _jump_to_track(next_index)
            return 1     
        next_index += 1
    logger.debug(f'Returning to Index 0...')  
    _jump_to_track(0)   # No different directory found after the given index

@PLAYBACK_MANAGER.lock_decorator
def jump_to_previous_album():
    global TRACK_LIST, current_index
    
    index = current_index
    file_paths = TRACK_LIST
    
    current_directory = os.path.dirname(file_paths[index])
    
    ## first check if you're on the first track of the album.
    ## if not, go to that first track
    first_track_of_current_album = _get_index_of_first_track(current_directory)
    if first_track_of_current_album != index:
        _jump_to_track(first_track_of_current_album)    
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
            album_first_track = _get_index_of_first_track(prev_directory)
            
            logger.debug(f'New Index Found {album_first_track}...')
            _jump_to_track(album_first_track)
            return 1     
        prev_index -= 1
    logger.debug(f'Returning to Index 0...')  
    _jump_to_track(0)   # No different directory found after the given index


@PLAYBACK_MANAGER.lock_decorator
def shuffle_current_songs():
    global TRACK_LIST, current_index, S_SONG_SHUFFLE
    
    pygame.mixer.music.stop()
    
    S_SONG_SHUFFLE = True
    
    random.shuffle(TRACK_LIST)
    
    current_index = 0
    _play_current_track()

@PLAYBACK_MANAGER.lock_decorator
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
    _play_current_track()


## picks a random track in the album and plays the track in order from there. 
@PLAYBACK_MANAGER.lock_decorator
def play_in_order_from_random_track():
    
    try:
        new_track_index = random.randint(0, len(TRACK_LIST) - 1)
        logger.debug(f'Jumping to track: {new_track_index} and continuing to play in order...')
        _jump_to_track(new_track_index)
        S_ALBUM_REPEAT = True
    except:
        logger.error("Unable to jump to a random track. There was a problem picking a random index.")
        

@PLAYBACK_MANAGER.lock_decorator
def _get_index_of_first_track(album_directory):
    global TRACK_LIST
    
    for index in range(len(TRACK_LIST)):
        if os.path.dirname(TRACK_LIST[index]) == album_directory:
            return index
    
    return 0
    
    

@PLAYBACK_MANAGER.lock_decorator
def play_pause_track():
    global MUSIC_PAUSED, MUSIC_STOPPED
    
    if (MUSIC_STOPPED == True):
        ## the music was stopped. This is likely
        ## because you reached the end of the album
        ## It's looped back around to the beginning 
        ## but the player is stopped instead of paused. Since pygame.mixer.music.unpause()
        ## doesn't work on stopped music, we need to call play.
        _play_current_track()
        
    elif (MUSIC_PAUSED == True):
        _unpause_track()
    else:
        _pause_track()
        

@PLAYBACK_MANAGER.lock_decorator
def _unpause_track():
    global MUSIC_PAUSED
    MUSIC_PAUSED = False
    pygame.mixer.music.unpause()
    PLAYBACK_MANAGER.start()
    logger.debug('Unpaused album.')

@PLAYBACK_MANAGER.lock_decorator
def _pause_track():
    global MUSIC_PAUSED
    MUSIC_PAUSED = True
    pygame.mixer.music.pause()
    PLAYBACK_MANAGER.stop()
    logger.debug('Paused album.')
    _save_position(restart_album=False)

@PLAYBACK_MANAGER.lock_decorator
def _stop_player():
    global MUSIC_PAUSED, MUSIC_STOPPED
    MUSIC_PAUSED = True
    MUSIC_STOPPED = True
    pygame.mixer.music.pause()
    PLAYBACK_MANAGER.stop()
    logger.debug('Paused album.')
    _save_position(restart_album=True)

    
@PLAYBACK_MANAGER.lock_decorator
def _save_position(restart_album):
    
    if S_REMEMBER_POSITION and restart_album:
        DB_AUDIO_POSITION.add_or_update_entry(S_ALBUM_RFID, 0, 0)
        logger.debug(f'Album complete. Reset Track Position to beginnging.')
 

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



@PLAYBACK_MANAGER.lock_decorator
def _play_current_track(check_remember=False):
    global TRACK_LIST, current_index, MUSIC_PAUSED, PREVIOUS_FOLDER, MUSIC_STOPPED
    
    current_track = None
    try:

        if (check_remember and S_REMEMBER_POSITION):
            ## this track requires we recall it's playback position
            current_index = S_LAST_TRACK 
            current_track = TRACK_LIST[current_index]
            logger.debug(f'Starting: {current_track}')
            pygame.mixer.music.load(current_track)
            pygame.mixer.music.rewind()
            position = S_LAST_POSITION/1000
            pygame.mixer.music.play(start=position)
            ## make sure we've got a thread going to play the next track
            PLAYBACK_MANAGER.start()
        else:
            ## this is a normal trac that doesn't need us to remember position
            current_track = TRACK_LIST[current_index]
            logger.debug(f'Starting: {current_track}')
            pygame.mixer.music.load(current_track)
            pygame.mixer.music.play() 
            ## make sure we've got a thread going to play the next track
            PLAYBACK_MANAGER.start()
            
        MUSIC_PAUSED = False
        MUSIC_STOPPED = False
                
        if (current_index == 0):
            #we've started or restarted an album. So reset the album name so we count it again
            PREVIOUS_FOLDER = None
            
        report_track(current_track)
    except Exception as e:
        if (current_track == None):
            stack_trace = traceback.format_exc()
            logger.error(f"No track to play. An exception occurred: {e}\nStack trace:\n{stack_trace}")
            PLAYBACK_MANAGER.stop()
        else:
            logger.error(f'Unable to play track "{current_track}" {e} ')
            stack_trace = traceback.format_exc()
            logger.error(f"Unable to play track. An exception occurred: {e}\nStack trace:\n{stack_trace}")
            PLAYBACK_MANAGER.stop()
        
    

def get_current_track():
    """
    returns the current track that is playing
    """
    global TRACK_LIST
    if is_playing():
        return TRACK_LIST[current_index]
    else:
        return None
    

@PLAYBACK_MANAGER.lock_decorator
def _jump_to_track(track_index):
    global current_index, TRACK_LIST, MUSIC_PAUSED
  
    ## Set this so it starts playing when we hit the next button if it wasn't already playing
    MUSIC_PAUSED = False
    # Stop the mixer
    #pygame.mixer.music.stop()
    #PLAYBACK_MANAGER.stop()
    
    # Get the next index
    current_index = track_index
    _play_current_track()
    
  

@PLAYBACK_MANAGER.lock_decorator
def next_track(button_press=True):
    global current_index, TRACK_LIST, MUSIC_PAUSED, MUSIC_STOPPED, COUNT_REPEATS
  
    if is_playing():
    
        # Get the next index
        current_index += 1
        album_length = len(TRACK_LIST)


        if (current_index < album_length ):
            _play_current_track()
        elif(button_press and current_index >= album_length):
            ## Because this was a button push, And we're at the end of the album,
            ## we should we start playing at the beginning of the album.
            current_index = 0
            _play_current_track()
        elif(S_ALBUM_REPEAT == False and current_index >= album_length):
            ## you reached the end of the album and it's not supposed to repeat.
            current_index = 0
            _stop_player()
            logger.debug(f'Reached end of album. Stopping playback.')
            
        elif (S_ALBUM_REPEAT == True and current_index >= len(TRACK_LIST)):
            ## The album reached it's end and should now restart
            current_index = 0
            
            ## This is here to make sure we don't just keep playing an album forever.
            ## This can happen if someone turns off the amplifier without hitting pause. 
            if (COUNT_REPEATS < CONFIG.MAX_REPLAY_COUNT):
                COUNT_REPEATS = COUNT_REPEATS + 1
                _play_current_track()
                logger.debug(f'Reached end of album. Album set to repeat. Restarting at the album beginning.')
            else:
                _stop_player()
                logger.debug(f'Reached end of album & completed allowed repeats. Stopping playback.')                
        else:
            # Load and play the next track
            _play_current_track()
            MUSIC_STOPPED = False
            
    else:
        ## the music wasn't playing. Don't index the track, 
        #just start playing again where ever it stopped.
        play_pause_track()
        

@PLAYBACK_MANAGER.lock_decorator
def prev_track():
    """
    If the current track has been playing for more than 10 seconds this brings the user back 
    to the beginning of the currently playing track
    
    If the current track has been playing for less than 10 seconds it brings you to the previous 
    track.
    """
    global current_index, TRACK_LIST, MUSIC_PAUSED
  
    position = pygame.mixer.music.get_pos()
      
  
    MUSIC_PAUSED = False
    # Stop the mixer
    
    #pygame.mixer.music.stop()
    
    
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
    #current_track = TRACK_LIST[current_index]
    _play_current_track()
 


def play_feedback(feedback_file):
    """
    Plays the sound file oer anything else that's playing.
    """
    try:
        feedback_audio = pygame.mixer.Sound(feedback_file)
        feedback_audio.play()
    except Exception as e:
        logger.error(f'Unable to play feedback sound "{feedback_file}" {e} ')
        
        
    
def play_speech(speech_file):
    """
    Plays a speech audio file by temporarily reducing the 
    volume of background music.

    Args:
        speech_file (str): The file path of the speech audio to be played.
    """
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
    return
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
    
    
    _pause_track()
    pygame.mixer.music.stop()
    pygame.quit()
    logger.debug('Completed Player Shutdown')
    



