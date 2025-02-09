import vlc
import time
import feedparser
from dateutil import parser
import requests
import threading
import os
import traceback



from audio_position_database import AudioPositionDatabase
import configfile as CONFIG
import aareporter
from abstract_audio_player import AbstractAudioPlayer  # Adjust import as needed





class AlchemyPodcastPlayer(AbstractAudioPlayer):
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
        self.player_instance = vlc.Instance("--aout=alsa")
        

        if self.player_instance is None:
            self.logger.error("Failed to create VLC instance.")
            return
        self.player = self.player_instance.media_player_new()

        # Get the event manager from MediaListPlayer
        self.events = self.player.event_manager()
        self.events.event_attach(
            vlc.EventType.MediaPlayerEndReached, self._on_media_player_end
        )
        
        self.feedback_instance = vlc.Instance("--aout=alsa")
        self.feedback_player = self.feedback_instance.media_player_new()

        self.s_album_repeat = False
        self.s_song_shuffle = False
        self.album_loaded = False
        self.s_remember_position = False
        self.s_album_rfid = None
        self.previous_folder = None
        self.current_loop = 0
        self.current_episode_index = 0
        self.podcast_name = 'Untitled Podcast'
        self.is_audiobook = False
        #self.s_last_position = 0

        self.EPISODE_TITLE = "title"
        self.EPISODE_DATE = "date"
        self.EPISODE_URL = "url"
        self.EPISODE_URL_RESOLVED = "url_resolved"   


        self.min_volume = 50
        self.max_volume = 100
        self.feexback_volume = 100

        ##TODO: This used to stop infinite repeats. I think it stopped at seven times through. It's no longer in use.
        self.count_repeats = 0


        self.db_audio_position = AudioPositionDatabase()
        

        # OLD GLOBALS I"M NOT SURE WHAT TO DO WITH
        self.initialized = False

       



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
        self.count_repeats = 0
        self.current_loop = 0
        self.current_episode_index = 0
        self.podcast_name = 'Untitled Podcast'
        #self.s_last_position = 0


    def speak_text(self, text: str):
        pass

    def speak_current_track(self, intro_sound_file: str = None):
        # Speak the name of the stream

        self.logger.debug("Starting speak_current_track")
        ###########       you stopped Here
        try:
            if self.player.is_playing():
                self.player.audio_set_volume(self.min_volume)
                time.sleep(0.2)


            current_volume = self.player.audio_get_volume()
            print(f"The current player volume is: {current_volume}")
            current_volume = self.feedback_player.audio_get_volume()
            print(f"The current feedback_player volume is: {current_volume}")

            if intro_sound_file:
                self.play_feedback(intro_sound_file, wait=True)
                time.sleep(0.3)
            
            if self.prepare_speech_file(self.get_current_podcast_and_track_name()):
                self.play_feedback(CONFIG.TEMP_SPEECH_WAV, wait=True)
            else:
                self.play_feedback(CONFIG.FEEDBACK_AUDIO_NOT_FOUND, wait=True)

            self.increase_player_to_max_volume()

        except Exception as e:
            self.logger.error(f'Error speaking track: {e}')     

    def play_feedback(self, feedback_file: str, wait: bool = False):
        # For streaming, this might just be a print or a no-op
        print(f"Playing feedback: {feedback_file}")
        try:
            self.feedback_player.set_media(self.feedback_instance.media_new(feedback_file))
            self.feedback_player.play()
            
            ## If the caller wants to wait for the feedback to finish, do so.
            if wait:
                ## Give the player a few seconds to get started before anything might do something with it.
                ## Without this Here, people can check if the player is playing before it actually gets started.
                time.sleep(0.2)

                ## Wait for the feedback to finish (blocking approach)
                while self.feedback_player.is_playing():
                    time.sleep(0.1)
            
        except Exception as e:
            self.logger.error(f'Unable to play feedback sound "{feedback_file}": {e}')

    def increase_player_to_max_volume(self):
        
        current_volume = self.player.audio_get_volume()
        self.logger.debug(f"Increasing volume to {self.max_volume} from: {current_volume}")
        
        for i in range(current_volume, self.max_volume + 1, 5):  # Start at 50, go up to 100, increment by 5
                self.player.audio_set_volume(i)
                time.sleep(0.1)

        current_volume = self.player.audio_get_volume()
        self.logger.debug(f"Volume increased to: {current_volume}")

    ##TODO:
    def _report_track(self, event):
        """
        Callback function triggered when a track is played.
        """
        pass
        """current_media = self.media_player.get_media()
        if current_media:
            current_episode_index = self.media_list.index_of_item(current_media)
            folder, file_name = self._get_folder_and_file(self.track_list[current_episode_index])  
            aareporter.log_track_play(folder, file_name)
            
            self.logger.debug('preparing to log album')
            if self.previous_folder != folder and not self.s_song_shuffle:
                self.logger.debug('logging album')
                aareporter.log_album_play(folder)

            self.previous_folder = folder
"""

       

    def set_logger(self, external_logger):
        self.logger = external_logger

    def play_audiobook(self,  tracks: list, remember_position=False, rfid=int):

        self.logger.debug(f"Playing audiobook with {len(tracks)} tracks.")
        ## get podcast name
        #  
        self.podcast_name = self._get_folder_name(tracks[0])
        self.is_audiobook = True
        self.s_remember_position = remember_position
        self.s_album_rfid = rfid
        ## load episodes
        self.episodes = []
        for track in tracks:
            #self.episodes.append((episode_title, episode_url, episode_date))
            self.episodes.append({
                self.EPISODE_TITLE: self._get_track_name(track),
                self.EPISODE_URL: track,
                self.EPISODE_URL_RESOLVED: track,
                self.EPISODE_DATE: None
            })



        if not self.episodes:
            self.logger.warning(f"No playable episodes found in {self.podcast_name} ")
            return


        if self.s_remember_position:
            self.logger.debug(f"Looking up position info for RFID: {self.s_album_rfid}")
            position_info = self.db_audio_position.get_position_info(self.s_album_rfid)
            if position_info:
                self.current_episode_index = position_info[0]
                s_last_position = position_info[1]
                self.logger.debug(f"Found saved position info for RFID: {self.s_album_rfid}, "
                                    f"Track: {position_info[0]}, Time: {position_info[1]}")
            else:
                self.logger.debug(f"No saved position info found for RFID: {self.s_album_rfid}")
        else:
            self.current_episode_index = 0
            s_last_position = 0

        
        self._play_current_episode(starting_time=s_last_position)


    def _get_folder_name(self, path):
        folder_path = os.path.dirname(path)
        folder_name = os.path.basename(folder_path)
       
        return folder_name

    def _get_track_name(self, path):
        file_name = os.path.basename(path)
        name_without_ext, _ = os.path.splitext(file_name)
        return name_without_ext



    def play_podcast(self, podcast_url: str, podcast_name: str, rfid:int):
        if not podcast_url:
            self.logger.warning("No RSS feed URL provided.")
            self.play_feedback(CONFIG.FEEDBACK_AUDIO_NOT_FOUND)
            return

        self.play_feedback(CONFIG.FEEDBACK_PODCAST_START, wait=False)

        self.is_audiobook = False
        self.podcast_name = podcast_name 
        self.s_album_rfid = rfid      
        self.s_remember_position = True
        self.logger.debug(f"Fetching podcast RSS feed from {podcast_url}...")
        feed = feedparser.parse(podcast_url)
        if not feed.entries:
            self.logger.warning("No episodes found in RSS feed.")
            return

        # Extract episode URLs and titles.
        # First entry is assumed to be the latest episode.
        self.episodes = []
        for entry in feed.entries:
            #print (entry)
            if entry.enclosures and entry.enclosures[0].href:
                #print(entry.enclosures)

                episode_url = entry.enclosures[0].href
                episode_title = entry.title if hasattr(entry, 'title') else 'Untitled Episode'
                episode_date = entry.published if hasattr(entry, 'published') else 'Unknown Date'
                # Store a tuple (title, url)
                #self.episodes.append((episode_title, episode_url, episode_date))
                self.episodes.append({
                    self.EPISODE_TITLE: episode_title,
                    self.EPISODE_URL: episode_url,
                    self.EPISODE_DATE: episode_date
                })



        if not self.episodes:
            self.logger.warning(f"No playable episodes found in {podcast_name} ")
            return


        """if self.s_remember_position:
            self.logger.debug(f"Looking up position info for RFID: {self.s_album_rfid}")
            position_info = self.db_audio_position.get_position_info(self.s_album_rfid)
            if position_info:
                self.current_episode_index = position_info[0]
                self.s_last_position = position_info[1]
                self.logger.debug(f"Found saved position info for RFID: {self.s_album_rfid}, "
                                    f"Track: {position_info[0]}, Time: {position_info[1]}")
            else:
                self.logger.debug(f"No saved position info found for RFID: {self.s_album_rfid}")
        else:
            self.current_episode_index = 0
            self.s_last_position = 0"""
        
        # position is remembered on a per episode basis and handled 
        # when you play the episode. So the code above has been commented out because it doesn't do anything.
        self.current_episode_index = 0

        self._play_current_episode()
        


    def _play_current_episode(self, starting_time=0):
        """
        Play the current episode in the list.
        """
        try:
               
            if self.is_audiobook == False:
                ## Every podcast episode can remember its own position
                starting_time = self._get_podcast_episode_postition()

            self.logger.debug(f'playing track {self.current_episode_index}  time: {starting_time}')   
            self.player.stop()

            # Access the first episode in the list
            url = self.get_current_track_resolved_url()
            if url == None:
                ## The URL has not been resolved, and VLC will choke on The redirect, so let's give it a resolved URL first.
                url = self._resolve_final_url(self.get_current_track_url())
                self.set_current_track_resolved_url(url)

            episode_media = vlc.Media(url)
            self.player.set_media(episode_media)

            self.logger.debug(f"About to speak name of episode at index {self.current_episode_index}")
            if self.is_audiobook == False:
                self.speak_current_track()

            # 5) Start playback
            self.logger.debug(f"Playing Track: {self.get_current_podcast_and_track_name()}")
            self.logger.debug(f'starting at {starting_time}')
            
            
            self.player.play()
            time.sleep(0.1)
            self.player.set_time(int(starting_time))
            

        except Exception as e:
            self.logger.error(f"An exception occurred while attempting to play track {self.current_episode_index}. {e}")
            return None
    



    def _on_media_player_end(self, event):
        self.logger.debug("Jumping to the next episode...")

        if self.is_audiobook == False:
            ## pass True so it resets the Podcast track to go 
            # back to the beginning next time it's played
            self._save_position(True)
        threading.Thread(target=self.next_track, daemon=True).start()
                

       

    def _resolve_final_url(self, url):
        # This method will now only return the final URL without logging intermediates
        # and will not print all redirect attempts.
        response = requests.head(url, allow_redirects=True)
        if response.status_code == 200:
            return response.url
        else:
            self.logger.debug(f"Unable to resolve final URL. Status code: {response.status_code}")
            return url
        
    def _restart(self):
        self._play_current_episode()
    
    def is_playing(self) -> bool:
        """
        Return whether the player is currently playing.
        """
        return self.player.is_playing()


    
       
    def shutdown_player(self):
        """
        Shutdown the audio player
        """
        self.logger.debug('Starting Player Shutdown')
        self.pause_track()
        self.logger.debug('Completed Player Shutdown')


    """def next_track(self):
        
        #Advance to the next track in self.media_list.
        #If already at the last track, wrap around to the first track.
        try:
            # Make sure we actually have a media list
            if not self.episodes or len(self.episodes) == 0:
                return  # No tracks, nothing to do

            # Decide whether to go to the next item or wrap
            if self.current_episode_index < (len(self.episodes) - 1):
                # Just go to the next item
                self.current_episode_index += 1
            else:
                # We're on the last item, so wrap around to index 0
                self.current_episode_index = 0

            self._play_current_episode()
        except Exception as e:
            self.logger.error(f"Error while going to next track: index {self.current_episode_index}. {e}")
            return None"""

    
    def forward_button_short_press(self):
        """
        Go forward 30 seconds on the current track
        """
        if self.skip_forward() == False:
            self.next_track()

    def skip_forward(self):
        """
        Go forward 30 seconds on the current track
        """
        try:
            position_ms = self.player.get_time()
            new_position_ms = position_ms + (CONFIG.FAST_FORWARD_MILLISECONDS) # go back 10 seconds
            if new_position_ms > self.player.get_length():
                # TODO: change this to jump to the next track
                return False
            else:
                self.player.set_time(int(new_position_ms))
                return True

        except Exception as e:
            self.logger.error(f"Error going forward 30 seconds. {e}")
            return None

    def next_track(self):

        #self.logger.debug(f'current_episode_index:{self.current_episode_index}, len(self.episodes):{len(self.episodes)}')
        if self.current_episode_index < len(self.episodes)-1:
            """we haven't reached the end of the episodes yet"""
            self.current_episode_index += 1
            self._play_current_episode()
        else:
            """ We reached the end of the episodes, so set the index back 
            to the beginning in case someone hits play again and wants to 
            start over. But we're not going to start for them."""
            self.current_episode_index = 0
            self.logger.debug(f'Reached end of audio content. Resetting to the beginning and stoping playback.')
        
        
    def back_button_short_press(self):
        """
        Go back 10 seconds on the current track
        """
        self.skip_back()


    def skip_back(self):
        """
        Go back 10 seconds on the current track
        """
        try:
            position_ms = self.player.get_time()
            new_position_ms = position_ms - (CONFIG.REWIND_MILLISECONDS) # go back 10 seconds
            
            self.logger.debug(f"at: {position_ms} going to: {new_position_ms}")

            if new_position_ms < 0:
                self.player.set_time(0)
            else:
                self.player.set_time(int(new_position_ms))

        except Exception as e:
            self.logger.error(f"Error going back 10 seconds. {e}")
            return None




    def get_current_podcast_and_track_name(self) -> str:
        """
        Returns the path to the currently playing media.
        """
        #current_track_title = self.episodes[self.current_episode_index][self.EPISODE_TITLE]

        return self.podcast_name + ". " + self.get_current_track_date_formatted() + ". " + self.get_current_track_title() + "." 
            
    def get_current_track_title(self):
        return self.episodes[self.current_episode_index][self.EPISODE_TITLE]
    
    def get_current_track(self):
        return self.get_current_podcast_and_track_name()
        
    def get_current_track_url(self):
        return self.episodes[self.current_episode_index][self.EPISODE_URL]
    
    def get_current_track_resolved_url(self):
        return self.episodes[self.current_episode_index].get(self.EPISODE_URL_RESOLVED)
    
    def set_current_track_resolved_url(self, url):
        self.episodes[self.current_episode_index][self.EPISODE_URL_RESOLVED] = url
        
    
    def get_current_track_date(self):
        return self.episodes[self.current_episode_index][self.EPISODE_DATE]
    
    def get_current_track_date_formatted(self):

        date = self.episodes[self.current_episode_index][self.EPISODE_DATE]
        if date == None:
            return ''
        else:
            return self.parse_and_format_date_dateutil(date)

    def get_most_recent_episode_date(self) -> str:
        """
        Returns the path to the currently playing media.
        """
        date_str = self.episodes[0][self.EPISODE_DATE]
        
        formatted = self.parse_and_format_date_dateutil(date_str)
        if formatted:
            print(f"Original: {date_str} --> Formatted: {formatted}")
            return "Latest Episode " + formatted
        else:
            print(f"Unable to find Latest Episode pubish date")
            return "Publish Date Unknown"



    def get_whats_playing(self) -> str:
        """
        Return the name of the track that is playing
        """
        try:
            whats_playing = self.get_current_podcast_and_track_name()
            if not whats_playing:
                return "No track playing."


            return self.podcast_name + ". Episode: " + self.get_current_track()
        except Exception as e:
            self.logger.error(f"An exception occurred while describing the track name: {e}")
            return "Error describing track."
    
    def play_pause_track(self):
        
        
        state = self.player.get_state()
        #self.logger.debug(f"player state: {state}")

        if state == vlc.State.Paused:
            self.player.play()
        elif state == vlc.State.Playing:
            self.player.pause()
            self.logger.debug('Paused audio.')
            self._save_position(restart_album=False)
        elif state == vlc.State.Ended:
            self._restart()

    def pause_track(self):
        """
        Pause the current track.
        """
        if self.player.get_state() == vlc.State.Playing:
            self.player.pause()
            self.logger.debug('Paused album.')
            self._save_position(restart_album=False)   

    

    ##TODO
    def _save_position(self, restart_album):
        self.logger.debug('Checking to save position')
        if self.s_remember_position:
            if self.is_audiobook:
                self.logger.debug('Saving audiobook position')
                self._save_position_audiobook(restart_album)
            else:
                self.logger.debug('Saving podcast spisode position')
                self._save_position_podcast_episode(restart_album)  
       
    def _save_position_audiobook(self, restart_album):
        """
        Save track position in the DB if 'remember_position' is enabled.
        """
        ## if we reached the end we're going to be told to go back to the beginning
        if self.s_remember_position and restart_album:
            self.db_audio_position.remove_entry(self.s_album_rfid)
            self.logger.debug('Album complete. Reset track position to beginning.')


        if self.s_remember_position:
            position_ms = self.player.get_time()  # get_time() returns ms

            ## Rewind a little bit, so we have some context when we start replaying
            position_ms = max(position_ms - CONFIG.REWIND_SAVE_POSITION_MILLISECONDS, 0)
            

            self.db_audio_position.add_or_update_entry(self.s_album_rfid, self.current_episode_index, position_ms)
            self.logger.debug(f'Saved track & position: track {self.current_episode_index}, position: {position_ms}')


    def _save_position_podcast_episode(self, restart_eposide_next_time):

        if restart_eposide_next_time:
            self.db_audio_position.remove_entry(self._get_podcast_episode_id())
        else:
            position_ms = self.player.get_time()  # get_time() returns ms
            ## Rewind a little bit, so we have some context when we start replaying
            position_ms = max(position_ms - CONFIG.REWIND_SAVE_POSITION_MILLISECONDS, 0)
            self.db_audio_position.add_or_update_entry(self._get_podcast_episode_id(), 0, position_ms)
            self.logger.debug(f'Saved track & position: track {self._get_podcast_episode_id()}, position: {position_ms}')


    def _get_podcast_episode_postition(self):
        """
        Get the saved position for the current podcast episode.
        """
        position = self.db_audio_position.get_position_info(self._get_podcast_episode_id())       
        if position:
            return position[1]
        else:
            return 0




    def _get_podcast_episode_id(self):
        ## This is the UID we'll use to store the position of the track
        ## in the position DB
        return str(self.s_album_rfid) + "_" + self.get_current_track_url()    
    



    def get_day_suffix(self, day):
        """
        Returns the ordinal suffix for a given day of the month.

        :param day: Integer representing the day of the month.
        :return: String suffix ('st', 'nd', 'rd', 'th').
        """
        if 11 <= day <= 13:
            return 'th'
        last_digit = day % 10
        if last_digit == 1:
            return 'st'
        elif last_digit == 2:
            return 'nd'
        elif last_digit == 3:
            return 'rd'
        else:
            return 'th'

    def parse_and_format_date_dateutil(self, date_str, dayfirst=False, desired_format="%B {day}{suffix}, %Y"):
        """
        Parses an arbitrary date string using dateutil and formats it into "Month Dayth, Year".

        :param date_str: The date string to parse.
        :param dayfirst: Whether to interpret the first value as the day.
        :param desired_format: The desired output format with placeholders for day and suffix.
        :return: Formatted date string or None if parsing fails.
        """
        try:
            # Parse the date string into a datetime object
            parsed_date = parser.parse(date_str, dayfirst=dayfirst)

            day = parsed_date.day
            suffix = self.get_day_suffix(day)

            # Format the date with ordinal suffix
            formatted_date = parsed_date.strftime(desired_format).format(day=day, suffix=suffix)

            return formatted_date
        except (parser.ParserError, ValueError) as e:
            print(f"[dateutil] Error parsing date '{date_str}': {e}")
            return None

    def set_repeat_album(self, repeat: bool):
        pass

    def forward_button_long_press(self):
        """ jump to the next episode """
        self.next_track()
        

    
    def back_button_long_press(self):
        """
        Jump to the previous episode in the list.
        """
        try:
            if not self.episodes or len(self.episodes) == 0:
                return  # No episodes, nothing to do

            if self.current_episode_index == 0:
                self.current_episode_index = len(self.episodes) - 1  # Wrap around to the last episode
            else:
                self.current_episode_index -= 1  # Go to the previous episode

            self._play_current_episode()
        except Exception as e:
            self.logger.error(f"Error while jumping to previous episode: index {self.current_episode_index}. {e}")
            return None
    


    def shuffle_unshuffle_tracks(self):
        pass
    


    def play_in_order_from_random_track(self):
        pass



 