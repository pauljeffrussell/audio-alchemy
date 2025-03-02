import pygame
import os
import logging
import time
import random
import traceback
import threading
import re


from audio_position_database import AudioPositionDatabase
import configfile as CONFIG
import aareporter
from abstract_audio_player import AbstractAudioPlayer  # Adjust import as needed


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
            print("\n##################")
            print("THREAD -- START")
            print("##################")
            self._stop_event.clear()
            self.thread = threading.Thread(target=self._run)
            self.thread.start()

    def stop(self):
        """
        Stops the thread if it is running. This method sets the stop event and waits
        for the thread to finish.
        """
        self._stop_event.set()
        print("\n##################")
        print("THREAD -- STOP")
        print("##################")
        if self.thread and self.thread.is_alive() and threading.current_thread() != self.thread:
            self.thread.join()
        self.thread = None


class AlchemyFilesPlayer(AbstractAudioPlayer):
    """
    A concrete implementation of AbstractAudioPlayer that uses pygame.mixer for audio playback.
    Incorporates all previously existing functionality.
    """

    def __init__(self):
        super().__init__()

        # State variables previously global
        self.track_list = []
        self.track_list_original_order = []
        self.end_track_index = 0
        self.music_paused = True
        self.music_stopped = True
        self.album_loaded = False
        self.is_shuffled = False

        self.s_album_repeat = False
        self.s_remember_position = False
        self.s_album_rfid = None
        self.s_last_track = 0
        self.s_last_position = 0
        self.count_repeats = 0

        self.max_volume = 100
        self.min_volume = 30

        self.previous_folder = None
        self.db_audio_position = None
        self.current_index = 0

        self.sleep_duration_keep_playing = 0.1
        self.logger = logging.getLogger(__name__)
        self.mixer_loaded = False

        # Initialize DB
        self.db_audio_position = AudioPositionDatabase()

        # Initialize PlaybackManager
        self.playback_manager = PlaybackManager(self._keep_playing, self.sleep_duration_keep_playing)

    def set_logger(self, external_logger):
        self.logger = external_logger





    def set_repeat_album(self, repeat: bool):
        """
        Tells the current album to repeat.
        """
        with self.playback_manager._lock:
            self.s_album_repeat = repeat

    def is_playing(self) -> bool:
        with self.playback_manager._lock:
            return not self.music_paused

    def startup(self):
        # Initialize the audio player
        self.end_track_index = 0
        self.music_paused = True
        self.music_stopped = True
        self.album_loaded = False
        self.is_shuffled = False
        self.s_album_repeat = False
        self.s_remember_position = False
        self.s_album_rfid = ''
        self.s_last_track = 0
        self.s_last_position = 0
        self.count_repeats = 0

        self.db_audio_position = AudioPositionDatabase()

        # Try loading the mixer until successful
        while not self.mixer_loaded:
            try:
                self.logger.debug("Attempting to load the mixer.")
                pygame.mixer.pre_init(48000, -16, 2, 2048)
                pygame.init()
                pygame.mixer.init()
                pygame.mixer.music.set_volume(1)
                self.logger.debug("SUCCESS! The mixer loaded.")
                self.mixer_loaded = True
            except:
                self.logger.debug("Mixer load failed. Retrying in 5 seconds.")
                time.sleep(5)

    def shutdown_player(self):
        # Shutdown the audio player
        self.logger.debug('Starting Player Shutdown')
        self.pause_track()
        pygame.mixer.music.stop()
        pygame.quit()
        self.mixer_loaded = False
        self.logger.debug('Completed Player Shutdown')

    def play_feedback(self, feedback_file: str, wait: bool = False):
        # Play a feedback sound based on the given type (here we treat feedback_type as a file)
        try:
            feedback_audio = pygame.mixer.Sound(feedback_file)
            feedback_audio.set_volume(1.0)
            feedback_audio.play()
            if wait:
                pygame.time.wait(int(feedback_audio.get_length() * 1000))
        except Exception as e:
            self.logger.error(f'Unable to play feedback sound "{feedback_file}": {e}')

    def speak_current_track(self, intro_sound_file: str = None):
    # Speak the name of the stream
        
        with self.playback_manager._lock:
            try:
                # turn down the music so we can hear the speaking
                pygame.mixer.music.set_volume(0.3)
                time.sleep(0.2)

                self.play_feedback(intro_sound_file, wait=True)

                self.prepare_speech_file(f"{self.get_whats_playing()}")

                self.play_feedback(CONFIG.TEMP_SPEECH_WAV, wait=True)
                
                time.sleep(0.2)
                
                # return the music volume back to normal
                self._increase_player_to_max_volume()
            except Exception as e:
                self.logger.error(f'Error speaking track: {e}') 
                stack_trace = traceback.format_exc()
            
                logging.debug("Here is the stack trace:")
                logging.debug(stack_trace)

    def _increase_player_to_max_volume(self):

        current_volume = pygame.mixer.music.get_volume()
        self.logger.debug(f"Increasing volume to {self.max_volume} from: {current_volume}")
        
        for i in range(self.min_volume, self.max_volume + 1, 5):  # Start at 50, go up to 100, increment by 5
                pygame.mixer.music.set_volume(i/100)
                time.sleep(0.1)

        current_volume = pygame.mixer.music.get_volume()
        self.logger.debug(f"Volume increased to: {current_volume}")


    def play_tracks(self, tracks: list, repeat: bool, shuffle: bool, remember_position: bool, rfid: int):
        
        self.logger.debug("Starting Music Player...")
        with self.playback_manager._lock:
            if self.album_loaded:
                self.shutdown_player()

            self.logger.debug("Initializing pygame for album playback...")
            self.startup()
            self.logger.debug("Completed initializing pygame")

            self.current_index = 0
            self.track_list = tracks
            self.track_list_original_order = tracks.copy()
            self.end_track_index = len(self.track_list)
            self.logger.debug(f'Total tracks to play: {self.end_track_index}')

            self.s_album_repeat = repeat
            self.count_repeats = 0

            self.s_remember_position = remember_position
            self.s_album_rfid = rfid

            if self.s_remember_position:
                self.logger.debug(f"Looking up position info for RFID: {self.s_album_rfid}")
                position_info = self.db_audio_position.get_position_info(self.s_album_rfid)
                if position_info:
                    self.s_last_track = position_info[0]
                    self.s_last_position = position_info[1]
                    self.logger.debug(f"Found saved position info for RFID: {self.s_album_rfid}, "
                                      f"Track: {position_info[0]}, Time: {position_info[1]}")
                else:
                    self.logger.debug(f"No saved position info found for RFID: {self.s_album_rfid}")
            else:
                self.s_last_track = 0
                self.s_last_position = 0

            # Play record start feedback if enabled
            if self.end_track_index != 0 and CONFIG.FEEDBACK_RECORD_START_ENABLED:
                self.play_feedback(CONFIG.FEEDBACK_RECORD_START)
                time.sleep(1.4)

            if shuffle == True:
                ## shuffle the trackw and play
                self.shuffle_unshuffle_tracks()
            else:
                # Play the first track, honoring remembered position if set
                self._play_current_track(check_remember=True)

            self.album_loaded = True

    def play_pause_track(self):
        with self.playback_manager._lock:
            if self.music_stopped:
                # music was stopped (e.g., end of album), just restart current track
                self._play_current_track()
            elif self.music_paused:
                self._unpause_track()
            else:
                self.pause_track()

    def forward_button_short_press(self):
        with self.playback_manager._lock:
            self.next_track()

    def next_track(self, button_press=True):
        with self.playback_manager._lock:


            """
            If this is a track that stores it's position, then skip forward
            in the track like we're jumping ahead in an audio book instead 
            of switching tracks. 
            
            2025-01 I commented this out because there should be no music tracks 
            that have this feature And it was causing an issue with tracks
            not going to the next track.
            
            """
            #if self.s_remember_position == True:
            #    # we want to skip forward because this is an audiobook
            #    self.skip_forward() 
            #    return

            """
            Advance to the next track in self.media_list.
            If already at the last track, wrap around to the first track.
            """
            self.current_index += 1
            album_length = len(self.track_list)

            if self.current_index < album_length:
                self._play_current_track()
            elif button_press and self.current_index >= album_length:
                # Button pushed at end of album: wrap around
                self.current_index = 0
                self._play_current_track()
            elif not self.s_album_repeat and self.current_index >= album_length:
                # End of album, no repeat
                self.current_index = 0
                self._stop_player()
                self.logger.debug('Reached end of album. Stopping playback.')
            elif self.s_album_repeat and self.current_index >= album_length:
                # Repeat the album
                self.current_index = 0
                if self.count_repeats < CONFIG.MAX_REPLAY_COUNT:
                    self.count_repeats += 1
                    self._play_current_track()
                    self.logger.debug('Reached end of album. Album set to repeat. Restarting.')
                else:
                    self._stop_player()
                    self.logger.debug('Reached end of album & completed allowed repeats. Stopping playback.')

    def back_button_short_press(self):
        with self.playback_manager._lock:
            self.prev_track()

    def prev_track(self):
        with self.playback_manager._lock:

            """
            If this is a track that stores it's position, then go back
            10 seconds in the track like we're back 10 seconds in an 
            audio book instead of switching tracks. 
            
            if self.s_remember_position == True:
                # we want to skip forward because this is an audiobook
                self.skip_back() 
                return
            """
            
            """
            Looks like we need to go to the next track since we're not in 
            audiobook mode
            """
            position = pygame.mixer.music.get_pos()
            self.music_paused = False

            # If track played less than 6 seconds, go to previous track, else restart current track
            if position < 6000:
                self.current_index -= 1
                if self.current_index < 0:
                    self.current_index = len(self.track_list) - 1

            self._play_current_track()

    def skip_forward(self):
        """
        Go forward 30 seconds on the current track
        """
        with self.playback_manager._lock:
            try:
                position_ms = pygame.mixer.music.get_pos()
                new_position_ms = (position_ms + (CONFIG.FAST_FORWARD_MILLISECONDS) ) 
                # Convert milliseconds to seconds for pygame.mixer.music.set_pos()
                new_position_seconds = new_position_ms / 1000.0

                self.logger.debug(f"at: {position_ms} going to: {new_position_ms} (seconds: {new_position_seconds})")

                ## We need to convert two seconds because the pygame player
                ## expects seconds When adjusting playback but we save 
                ## position as milliseconds
                pygame.mixer.music.set_pos(new_position_ms)
                return True
            except Exception as e:
                self.logger.error(f"Error going forward 30 seconds. {e}")
                return None


    def skip_back(self):
        """
        Go back 10 seconds on the current track
        """
        with self.playback_manager._lock:
            try:
                current_pos = pygame.mixer.music.get_pos()   # Convert to seconds
                new_pos = max(current_pos - CONFIG.REWIND_MILLISECONDS, 0)   # Ensure it doesn't go below 0
                ## we need to Convert from milliseconds to seconds 
                # because the pygame player said position works in seconds.
                pygame.mixer.music.set_pos(new_pos / 1000)
                
            except Exception as e:
                self.logger.error(f"Error going back 10 seconds. {e}")
                return None

    def play_stream(self, stream_url: str, stream_name: str):
        """Play a streaming audio source."""
        pass

    def middle_button_long_press(self):
        self.shuffle_unshuffle_tracks()

    def forward_button_long_press(self):
        """
        This will jump to the next album.
        """
        with self.playback_manager._lock:
            index = self.current_index
            file_paths = self.track_list
            current_directory = os.path.dirname(file_paths[index])
            next_index = index + 1

            while next_index < len(file_paths):
                next_directory = os.path.dirname(file_paths[next_index])
                if next_directory != current_directory:
                    self.logger.debug(f'New album at index {next_index}...')
                    self._jump_to_track(next_index)
                    return
                next_index += 1
            self.logger.debug('No next album found, returning to index 0.')
            self._jump_to_track(0)

    def back_button_long_press(self):
        """
        this will jump to the previous album
        """
        with self.playback_manager._lock:
            index = self.current_index
            file_paths = self.track_list

            current_directory = os.path.dirname(file_paths[index])
            first_track_of_current_album = self._get_index_of_first_track(current_directory)

            if first_track_of_current_album != index:
                # Jump to the first track of the current album
                self._jump_to_track(first_track_of_current_album)
                return

            # Already on the first track of current album, find previous album
            prev_index = index - 1
            if prev_index < 0:
                prev_index = len(file_paths) - 1

            while prev_index > 0:
                prev_directory = os.path.dirname(file_paths[prev_index])
                if prev_directory != current_directory:
                    album_first_track = self._get_index_of_first_track(prev_directory)
                    self.logger.debug(f'Previous album found at index {album_first_track}...')
                    self._jump_to_track(album_first_track)
                    return
                prev_index -= 1

            self.logger.debug('No previous album found, returning to index 0.')
            self._jump_to_track(0)

    def get_current_track(self) -> str:
        # Return the current track name
        with self.playback_manager._lock:
            if not self.track_list:
                return None
            if self.is_playing():
                return self.track_list[self.current_index]
            else:
                return None
            

    def get_whats_playing(self) -> str:
        try:
            current_track_for_email = self.get_current_track()
            self.logger.debug(f'Processing track {current_track_for_email}.')

            # Split by directory delimiter
            parts = current_track_for_email.split('/')

            # Assign album and track to separate variables
            album_name = parts[-2]
            track_name_with_extension = parts[-1]

            # Use regex to extract the disk and track number if formatted as 'disk-track'
            match = re.match(r'(\d+)-(\d+)', track_name_with_extension)
            if match:
                disk_number = str(int(match.group(1)))  # Remove leading zeros from disk number
                track_number = str(int(match.group(2)))  # Remove leading zeros from track number
            else:
                # Fallback to just track number extraction if no dash is found
                match = re.match(r'(\d+)', track_name_with_extension)
                disk_number = ''  # Default value if disk number is not applicable
                track_number = str(int(match.group(1))) if match else ''

            # Remove track/disk number, metadata in brackets, and either file extension from track name
            #file_name = re.sub(r'^\d+(-\d+)? - |\s*\[.*?\]\s*|\.webm?\.mp3$', '', track_name_with_extension)

            # Remove track/disk number and clean up the file name
            file_name = re.sub(r'^\d+(-\d+)?\s', '', track_name_with_extension)  # Remove the initial numbers and any spaces following them
            # Adjusted regex to correctly remove .mp3 and .webm.mp3
            file_name = re.sub(r'\.webm?\.mp3$', '', file_name)

            # Correctly removing .mp3 extensions
            file_name = re.sub(r'\.mp3$', '', file_name)
        
            # Remove periods from the file name, but preserve any extension handling
            file_name = re.sub(r'\.', '', file_name)
        
            # Check if the remaining file_name is just digits (and possibly spaces), clear it if so
            if re.fullmatch(r'\d+', file_name.strip()):
                file_name = ''

            # Build the description string based on available data
            description_parts = [album_name]
            if disk_number:
                description_parts.append(f"Disk {disk_number}")
            if track_number:
                description_parts.append(f"Track {track_number}")
            if file_name:
                description_parts.append(file_name)

            # Join all parts into a single string with proper formatting
            description = ". ".join(description_parts) + '.'
            
            return description
           
            
            # Now track_number holds the digits at the beginning of track_name, if any
        
        except Exception as e:
            ## if anything goes wrong, write it to a log file.
            ## Only Errors will be logged. 
        
            self.logger.error(f"An exception occurred while trying to speak the album and track name: {e}")

    def play_speech(self, speech_file):
        """
        Plays a speech audio file by temporarily reducing the volume of background music.
        """
        with self.playback_manager._lock:
            # turn down the music so we can hear the speaking
            pygame.mixer.music.set_volume(0.3)
            time.sleep(0.2)

            try:
                speech = pygame.mixer.Sound(speech_file)
                speech.set_volume(1.0)
                speech.play()

                # Wait for the speech to finish
                pygame.time.wait(int(speech.get_length() * 1000))
                time.sleep(0.2)
            except Exception as e:
                self.logger.error(f'Unable to play speech "{speech_file}": {e}')

            # return the music volume back to normal
            pygame.mixer.music.set_volume(1)

    def shuffle_unshuffle_tracks(self):
        with self.playback_manager._lock:
            if self.is_shuffled == True:
                self.logger.debug("Unsuffle Current tracks!")
                pygame.mixer.music.stop()
                # revert to original order
                self.track_list = self.track_list_original_order.copy()
                self.is_shuffled = False
                self.current_index = 0
                self._play_current_track()
            else:
                self.logger.debug("Suffle Current tracks!")
                pygame.mixer.music.stop()
                self.is_shuffled = True
                random.shuffle(self.track_list)
                self.current_index = 0
                self._play_current_track()    



    def play_in_order_from_random_track(self):
        with self.playback_manager._lock:
            try:
                new_track_index = random.randint(0, len(self.track_list) - 1)
                self.logger.debug(f'Jumping to track: {new_track_index} and continuing to play in order...')
                self._jump_to_track(new_track_index)
                self.s_album_repeat = True
            except Exception as e:
                self.logger.error(f"Unable to jump to a random track: {e}")

    def pause_track(self):
        with self.playback_manager._lock:
            self.music_paused = True
            pygame.mixer.music.pause()
            self.playback_manager.stop()
            self.logger.debug('Paused album.')
            self._save_position(restart_album=False)

    def _unpause_track(self):
        with self.playback_manager._lock:
            self.music_paused = False
            pygame.mixer.music.unpause()
            self.playback_manager.start()
            self.logger.debug('Unpaused album.')

    def _stop_player(self):
        with self.playback_manager._lock:
            self.music_paused = True
            self.music_stopped = True
            pygame.mixer.music.pause()
            self.playback_manager.stop()
            self.logger.debug('Stopped album.')
            self._save_position(restart_album=True)

    def _save_position(self, restart_album):
        if self.s_remember_position and restart_album:
            self.db_audio_position.add_or_update_entry(self.s_album_rfid, 0, 0)
            self.logger.debug('Album complete. Reset track position to beginning.')

        if self.s_remember_position:
            position = pygame.mixer.music.get_pos()
            if self.current_index == self.s_last_track:
                position += self.s_last_position

            
            # Adjust position slightly backward if possible
            if position > 10:
                position -= 10
            else:
                position = 0

            self.s_last_position = position

            self.db_audio_position.add_or_update_entry(self.s_album_rfid, self.current_index, position)
            self.logger.debug(f'Saved track & position: track {self.current_index}, position: {position}')

    def _play_current_track(self, check_remember=False):
        with self.playback_manager._lock:
            current_track = None
            try:
                if check_remember and self.s_remember_position:
                    self.current_index = self.s_last_track
                    current_track = self.track_list[self.current_index]
                    self.logger.debug(f'Starting: {current_track} with remembered position.')
                    pygame.mixer.music.load(current_track)
                    pygame.mixer.music.rewind()
                    position = self.s_last_position / 1000
                    ## we save the track time in ms, but pygame expects
                    ## seconds when playing 
                    pygame.mixer.music.play(start=position)
                    self.playback_manager.start()
                else:
                    current_track = self.track_list[self.current_index]
                    self.logger.debug(f'Starting: {current_track}')
                    pygame.mixer.music.load(current_track)
                    pygame.mixer.music.play()
                    self.playback_manager.start()

                self.music_paused = False
                self.music_stopped = False

                if self.current_index == 0:
                    self.previous_folder = None

                self._report_track(current_track)
            except Exception as e:
                stack_trace = traceback.format_exc()
                if current_track is None:
                    self.logger.error(f"No track to play. Exception: {e}\n{stack_trace}")
                    self.playback_manager.stop()
                else:
                    self.logger.error(f'Unable to play track "{current_track}": {e}\n{stack_trace}')
                    self.playback_manager.stop()

    def _jump_to_track(self, track_index):
        with self.playback_manager._lock:
            self.music_paused = False
            self.current_index = track_index
            self._play_current_track()

    def _get_index_of_first_track(self, album_directory):
        for index, track in enumerate(self.track_list):
            if os.path.dirname(track) == album_directory:
                return index
        return 0

    def _report_track(self, current_track):
        folder, file_name = self._get_folder_and_file(current_track)
        self.logger.debug(f'logging trackfolder: {folder}, file: {file_name}')
        aareporter.log_track_play(folder, file_name)

        #self.logger.debug('preparing to log album')
        # Only log album if not shuffled
        if self.previous_folder != folder and not self.is_shuffled:
            self.logger.debug('logging album')
            aareporter.log_album_play(folder)

        self.previous_folder = folder

    def _get_folder_and_file(self, path):
        folder_path = os.path.dirname(path)
        folder_name = os.path.basename(folder_path)
        file_name = os.path.basename(path)
        return folder_name, file_name

    def _keep_playing(self):
        # Called periodically by PlaybackManager
        if (self.music_paused == False and not pygame.mixer.music.get_busy()):
            # Play the next track
            self.logger.debug('Track ended. Playing next track.')
            self.next_track(False)

    def _restart(self):
        pass