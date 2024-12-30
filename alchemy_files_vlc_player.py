import vlc
import time
import os
import random
import re
from threading import Event


from audio_position_database import AudioPositionDatabase
import configfile as CONFIG
import aareporter
from abstract_audio_player import AbstractAudioPlayer  # Adjust import as needed




class AlchemyFilesPlayer(AbstractAudioPlayer):
    """
    A VLC-based implementation of AbstractAudioPlayer for playing local files (MP3s, WAVs, etc.).
    Preserves logic from the original Pygame version but uses python-vlc.
    """

    def __init__(self):
        super().__init__()

        self.track_list = []
        self.track_list_original_order = []
        self.logger = None

        # VLC-related objects
        self.player_instance = vlc.Instance()
        self.media_player = self.player_instance.media_player_new()
        self.list_player = self.player_instance.media_list_player_new()
        self.media_list = self.player_instance.media_list_new()
        
        

        # Get the event manager from MediaListPlayer
        self.events = self.list_player.event_manager()

        # Attach events
        ## THIS IS THE EVENT THAT SHOULD FIRE WHEN THE PLAYLIST ENDS
        ## BUT IT DOESN'T SEEM TO BE FIRING
        self.events.event_attach(
            vlc.EventType.MediaListEndReached, self._on_media_list_end
        )

        ## This one works
        self.events.event_attach(
            vlc.EventType.MediaListPlayerNextItemSet, self._report_track
        )
        
        self.feedback_instance = vlc.Instance()
        self.feedback_player = self.feedback_instance.media_player_new()

        self.s_album_repeat = False
        self.s_song_shuffle = False
        self.album_loaded = False
        self.s_remember_position = False
        self.s_album_rfid = None
        self.s_album_rfid = ''
        self.previous_folder = None
        self.current_loop = 0
       
        ##TODO: This used to stop infinite repeats. I think it stopped at seven times through. It's no longer in use.
        self.count_repeats = 0


        self.db_audio_position = AudioPositionDatabase()
        

        # OLD GLOBALS I"M NOT SURE WHAT TO DO WITH
             
        
        self.initialized = False
       
   
    def _on_media_list_end(self, event):
        """
        Callback function triggered when the playlist ends.

        :param event: VLC event.
        """
        print ("_on_media_list_end")
        if self.s_album_repeat:
            self.current_loop += 1
            self.logger.debug(f"Loop {self.current_loop} of {CONFIG.MAX_REPLAY_COUNT} completed.")
            if self.current_loop < CONFIG.MAX_REPLAY_COUNT:
                self.logger.debug("Restarting playlist...")
                time.sleep(0.3)
                
                self.play_tracks(tracks=self.track_list, repeat=self.s_album_repeat, shuffle=self.s_song_shuffle, 
                         remember_position=self.s_remember_position, rfid=self.s_album_rfid)
                
            else:
                self.logger.debug("Desired loop count reached. Stopping playback.")
                self.list_player.stop()
                

    def _report_track(self, event):
        """
        Callback function triggered when a track is played.
        """

        current_media = self.media_player.get_media()
        if current_media:
            current_index = self.media_list.index_of_item(current_media)
            folder, file_name = self._get_folder_and_file(self.track_list[current_index])  
            aareporter.log_track_play(folder, file_name)
            
            self.logger.debug('preparing to log album')
            if self.previous_folder != folder and not self.s_song_shuffle:
                self.logger.debug('logging album')
                aareporter.log_album_play(folder)

            self.previous_folder = folder

            

    def set_logger(self, external_logger):
        self.logger = external_logger

    ##TODO
    def set_repeat_album(self, repeat: bool):
        """
        Tells the current album to repeat.
        """
        CONFIG.MAX_REPLAY_COUNT
        self.s_album_repeat = repeat

    ##TODO
    def is_playing(self) -> bool:
        """
        Return whether the player is currently playing.
        """
        return not self.music_paused


    ##TODO
    def startup(self):
        """
        Initialize the VLC-based audio player. 
        This replaces the old Pygame mixer logic.
        """
        self.track_list = []
        self.track_list_original_order = []
        self.s_album_repeat = False
        self.s_song_shuffle = False
        self.album_loaded = False
        self.s_remember_position = False
        self.s_album_rfid = None
        self.s_album_rfid = ''
        self.count_repeats = 0
        self.current_loop = 0

       
    def shutdown_player(self):
        """
        Shutdown the audio player
        """
        self.logger.debug('Starting Player Shutdown')
        self.pause_track()
        self.logger.debug('Completed Player Shutdown')

    def play_feedback(self, feedback_file: str):
        # For streaming, this might just be a print or a no-op
        print(f"Playing feedback: {feedback_file}")
        try:
            self.feedback_player.set_media(self.feedback_instance.media_new(feedback_file))
            self.feedback_player.play()
        except Exception as e:
            self.logger.error(f'Unable to play feedback sound "{feedback_file}": {e}')


    def play_tracks(self, tracks: list, repeat: bool, shuffle: bool, remember_position: bool, rfid: int):
    
        """
        Play a list of tracks (file paths) back-to-back using python-vlc.
        """
        
        self.list_player.stop()

        
        self.track_list = tracks
        self.track_list_original_order = tracks.copy()
        self.s_album_repeat = repeat

        if shuffle:
            random.shuffle(self.track_list)

        # 2) Create a MediaList and add each track from your array
        self.media_list = self.player_instance.media_list_new()
        for track in tracks:
            self.media_list.add_media(track)

        # 3) Create a MediaListPlayer and set the media list
        self.list_player.set_media_list(self.media_list)

        # 4) Optionally create a specific MediaPlayer to control volume, etc.
        self.list_player.set_media_player(self.media_player)

        # Play record start feedback if enabled
        if self.media_list.count() > 0 and CONFIG.FEEDBACK_RECORD_START_ENABLED:
            self.play_feedback(CONFIG.FEEDBACK_RECORD_START)
            time.sleep(1.4)


        # 5) Start playback
        self.list_player.play()


    def next_track(self):
        """
        Advance to the next track in self.media_list.
        If already at the last track, wrap around to the first track.
        """
        # Make sure we actually have a media list
        if not self.media_list or self.media_list.count() == 0:
            return  # No tracks, nothing to do

        # Identify the currently playing media
        current_media = self.media_player.get_media()
        if current_media is None:
            # If there's no current media, just move to the first track
            self.list_player.play_item_at_index(0)
            return

        # Find out which index we're on in the media_list
        current_index = self.media_list.index_of_item(current_media)
        total_tracks = self.media_list.count()

        # Decide whether to go to the next item or wrap
        if current_index < (total_tracks - 1):
            # Just go to the next item
            self.list_player.next()
        else:
            # We're on the last item, so wrap around to index 0
            self.list_player.play_item_at_index(0)
        
    def prev_track(self):
        """
        If the current track has been playing for less than 6 seconds, go to prev track;
        else restart current track. (Matching old pygame logic.)
        """
        
        # We'll approximate "time into track" via get_time()
        if self.media_player:
            position_ms = self.media_player.get_time()  # milliseconds
        else:
            position_ms = 0

        if position_ms < 6000:
            # Find out which index we're on in the media_list
            current_media = self.media_player.get_media()
            current_index = self.media_list.index_of_item(current_media)
            total_tracks = self.media_list.count()
            
            # Decide whether to go to the next item or wrap
            if current_index == 0:
                # We're on the first track. Loop around to the end.
                self.list_player.play_item_at_index(total_tracks -1)    
            else:
                # We're on the last item, so wrap around to index 0
                self.list_player.previous()
        else:
            state = self.media_player.get_state()
            if state in (vlc.State.Playing, vlc.State.Paused):
                self.logger.debug("Restarting the current track by seeking to the beginning.")
                self.media_player.set_time(0)  # Seek to the start (milliseconds)
            else:
                self.logger.debug("No track is currently playing or it's not in a playable state.")



    def play_pause_track(self):
        """
        Toggle play/pause
        """
        state = self.media_player.get_state()
        if state == vlc.State.Playing:
            self.media_player.pause()
        elif state == vlc.State.Paused:
            self.media_player.play()
        elif state in (vlc.State.Stopped, vlc.State.Ended):
            self.list_player.play_item_at_index(0)
       
    
    def jump_to_next_album(self):
        
        current_media = self.media_player.get_media()
        if current_media:
            mrl = current_media.get_mrl()
            current_index = self.media_list.index_of_item(current_media)
            last_index = self.media_list.count() - 1
            print(f"Current MRL: {mrl}")
        else:
            print("No media is currently playing.")
            return
        
        current_directory = os.path.basename(os.path.dirname(mrl))
        
        print (f'current_directory: {current_directory}')

        for i in range(current_index, last_index):
            next_media = self.media_list.item_at_index(i)
            next_mrl = next_media.get_mrl()
            next_directory = os.path.basename(os.path.dirname(next_mrl))
            print(f'next_directory: {next_directory}')
            if next_directory != current_directory:
                print(f'Jumping to track {i}...')
                self.list_player.play_item_at_index(i)
                return
            
        ## you made it to the end of all the albums. Go back to the first one.
        self.list_player.play_item_at_index(0)

    def jump_to_previous_album(self):
        """
        Jumps to the first track of the previous album in the track list.
        If at the beginning of the list, wraps around to the last track.
        """
        current_media = self.media_player.get_media()
        if current_media:
            mrl = current_media.get_mrl()
            current_index = self.media_list.index_of_item(current_media)
            current_directory =  os.path.basename(os.path.dirname(self.track_list[current_index]))
        else:
            print("No media is currently playing.")
            return

        print(f'current_directory: {current_directory}')



        # Iterate backwards from current_index - 1 to 0
        for i in range(current_index - 1, -1, -1):
            prev_directory = os.path.basename(os.path.dirname(self.track_list[i]))
            print(f'prev_directory: {prev_directory}')
            
            # Check if the previous media is in a different directory (album)
            if prev_directory != current_directory:
                previous_album_start = self._get_index_of_first_track(prev_directory)
                print(f'Jumping to track {previous_album_start}...')
                self.list_player.play_item_at_index(previous_album_start)
                return
            
            
        print("No previous album found. Wrapping around to the last album.")
        target_album_directory =  os.path.basename(os.path.dirname(self.track_list[-1]))
        previous_album_start = self._get_index_of_first_track(target_album_directory)
        self.list_player.play_item_at_index(previous_album_start)
            


    def get_current_track(self) -> str:
        """
        Returns the path to the currently playing media.
        """
        current_media = self.media_player.get_media()
        if current_media:
            current_index = self.media_list.index_of_item(current_media)
            return self.track_list[current_index]
        
        return None


    def get_whats_playing(self) -> str:
        """
        Same logic you had for describing the "current track" in a more readable format.
        """
        try:
            current_track_for_email = self.get_current_track()
            if not current_track_for_email:
                return "No track playing"

            self.logger.debug(f'Processing track {current_track_for_email}.')
            parts = current_track_for_email.split('/')
            if len(parts) < 2:
                return current_track_for_email

            album_name = parts[-2]
            track_name_with_extension = parts[-1]

            # Extract disk number, track number, etc.
            match = re.match(r'(\d+)-(\d+)', track_name_with_extension)
            if match:
                disk_number = str(int(match.group(1)))
                track_number = str(int(match.group(2)))
            else:
                match = re.match(r'(\d+)', track_name_with_extension)
                disk_number = ''
                track_number = str(int(match.group(1))) if match else ''

            file_name = re.sub(r'^\d+(-\d+)?\s', '', track_name_with_extension)
            file_name = re.sub(r'\.webm?\.mp3$', '', file_name)
            file_name = re.sub(r'\.mp3$', '', file_name)
            file_name = re.sub(r'\.', '', file_name)
            if re.fullmatch(r'\d+', file_name.strip()):
                file_name = ''

            description_parts = [album_name]
            if disk_number:
                description_parts.append(f"Disk {disk_number}")
            if track_number:
                description_parts.append(f"Track {track_number}")
            if file_name:
                description_parts.append(file_name)

            return ". ".join(description_parts) + '.'
        except Exception as e:
            self.logger.error(f"An exception occurred while describing the track name: {e}")
            return "Error describing track"

    def play_speech(self, speech_file: str):
        """Stub for playing a short speech file."""

        
        # 2) Lower the volume of your main player
        self.logger.debug(f"reducing stream audio.")
        self.media_player.audio_set_volume(70)
        time.sleep(0.2)

        
        self.feedback_player.set_media(self.feedback_instance.media_new(speech_file))
        self.feedback_player.audio_set_volume(100)  # or whatever volume you want
        
        
        self.logger.debug(f"feedback_player.play()")
        self.feedback_player.play()
        time.sleep(0.2)
        # 4) Wait for the speech to finish (blocking approach)
        while self.feedback_player.is_playing():
            self.logger.debug(f"waiting for speech to finish.")
            time.sleep(0.1)
        self.feedback_player.stop()
        time.sleep(0.2)


        # 5) Raise the volume on the main player again
        self.media_player.audio_set_volume(100)

  

    def shuffle_current_songs(self):
        self.s_song_shuffle = True
        self.play_tracks(tracks=self.track_list, repeat=self.s_album_repeat, shuffle=self.s_song_shuffle, 
                         remember_position=self.s_remember_position, rfid=self.s_album_rfid)

        
    def unshuffle_current_songs(self):
        self.s_song_shuffle = False
        self.play_tracks(tracks=self.track_list_original_order, repeat=self.s_album_repeat, shuffle=self.s_song_shuffle, 
                         remember_position=self.s_remember_position, rfid=self.s_album_rfid)


    def play_in_order_from_random_track(self):
        try:
            new_track_index = random.randint(0, len(self.track_list) - 1)
            self.logger.debug(f'Jumping to track: {new_track_index} and continuing in order...')
            self.list_player.self.list_player.play_item_at_index(new_track_index)
            self.s_album_repeat = True
        except Exception as e:
            self.logger.error(f"Unable to jump to a random track: {e}")

    def pause_track(self):
        """
        Pause the current track.
        """
        if self.media_player.get_state() == vlc.State.Playing:
            self.media_player.pause()
            self.logger.debug('Paused album.')
            self._save_position(restart_album=False)

 

    ##TODO
    def _save_position(self, restart_album):
        """
        Save track position in the DB if 'remember_position' is enabled.
        """
        if self.s_remember_position and restart_album:
            self.db_audio_position.add_or_update_entry(self.s_album_rfid, 0, 0)
            self.logger.debug('Album complete. Reset track position to beginning.')

        if self.s_remember_position:
            position_sec = 0.0
            if self.player:
                position_sec = self.player.get_time() / 1000.0  # get_time() returns ms

            if self.current_index == self.s_last_track:
                position_sec += self.s_last_position

            if position_sec > 10:
                position_sec -= 10
            else:
                position_sec = 0

            self.db_audio_position.add_or_update_entry(self.s_album_rfid, self.current_index, position_sec)
            self.logger.debug(f'Saved track & position: track {self.current_index}, position: {position_sec}')



    def _get_index_of_first_track(self, album_directory):
        """
        Given a directory, this will find the first instance of it. 
        It's only used when moving backwards through albums in a long list.
        """
        for index, track in enumerate(self.track_list):
            index_dir = os.path.basename(os.path.dirname(track))

            print (f'index_dir: {index_dir}')
            print (f'album_directory: {album_directory}')    

            if os.path.basename(os.path.dirname(track)) == album_directory:
                return index
        return 0

    ##TODO
    """ def _report_track(self, current_track):
        folder, file_name = self._get_folder_and_file(current_track)
        self.logger.debug(f'folder: {folder}, file: {file_name}')
        aareporter.log_track_play(folder, file_name)

        self.logger.debug('preparing to log album')
        if self.previous_folder != folder and not self.s_song_shuffle:
            self.logger.debug('logging album')
            aareporter.log_album_play(folder)

        self.previous_folder = folder
    """
    ##TODO
    def _get_folder_and_file(self, path):
        folder_path = os.path.dirname(path)
        folder_name = os.path.basename(folder_path)
        file_name = os.path.basename(path)
        return folder_name, file_name

   