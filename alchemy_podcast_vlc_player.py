import vlc
import time
import feedparser
from dateutil import parser
import requests


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
        self.player_instance = vlc.Instance()
        self.media_player = self.player_instance.media_player_new()
        self.list_player = self.player_instance.media_list_player_new()
        self.media_list = self.player_instance.media_list_new()
        self.list_player.set_media_player(self.media_player)

            
        

        # Get the event manager from MediaListPlayer
        self.events = self.list_player.event_manager()

        self.events.event_attach(vlc.EventType.MediaListPlayerNextItemSet, self._on_next_item_set)
        # Attach events
        ## THIS IS THE EVENT THAT SHOULD FIRE WHEN THE PLAYLIST ENDS
        ## BUT IT DOESN'T SEEM TO BE FIRING
        self.events.event_attach(
            vlc.EventType.MediaListEndReached, self._on_media_list_end
        )

        """## This one works
        self.events.event_attach(
            vlc.EventType.MediaListPlayerNextItemSet, self._report_track
        )"""
        
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
        self.podcast_name = 'Untitled Podcast'
       
        ##TODO: This used to stop infinite repeats. I think it stopped at seven times through. It's no longer in use.
        self.count_repeats = 0


        self.db_audio_position = AudioPositionDatabase()
        

        # OLD GLOBALS I"M NOT SURE WHAT TO DO WITH
             
        
        self.initialized = False
    def _on_next_item_set(self, event):
        """
        Event handler triggered just before VLC sets the next media item.
        Resolves redirects and updates the media item with the final URL.
        """
        try:
            # Extract the new media from the event
            next_media = event.u.media
            if next_media is None:
                print("No next media set.")
                return

            print(f"Next media: {next_media}")
            original_url = next_media.get_mrl()
            print(f"Original URL: {original_url}")

            # Resolve the final URL
            final_url = self._resolve_final_url(original_url)
            self.logger.debug(f"Resolved URL: {final_url}")

            if final_url != original_url:
                # Create a new media object with the resolved URL
                new_media = self.instance.media_new(final_url)

                # Replace the media in the list at the current position
                current_index = self.media_list.index_of_item(next_media)
                if current_index != -1:
                    self.media_list.remove_index(current_index)
                    self.media_list.insert_media(new_media, current_index)
                    self.logger.debug(f"Media at index {current_index} updated with resolved URL.")
                else:
                    self.logger.debug("Could not find media in the list.")
        except Exception as e:
            self.logger.debug(f"Failed to resolve and update URL: {e}")
            self.speak_text("Failed to play the requested podcast episode.")   

    """def _on_next_item_set(self, event):
        #Event handler triggered just before VLC sets the next media item.
        #Resolves redirects and updates the media item with the final URL.
        # Get the current media item index
        current_index = self.list_player.current_media_list_index
        if current_index == -1:
            print("No media is currently playing.")
            return

        # Retrieve the media object
        media = self.media_list.item_at_index(current_index)
        if media is None:
            print(f"No media found at index {current_index}.")
            return

        # Get the original URL
        original_url = media.get_mrl()
        print(f"Original URL at index {current_index}: {original_url}")

        try:
            # Resolve the final URL
            final_url = self.resolve_final_url(original_url)
            print(f"Resolved URL: {final_url}")

            if final_url != original_url:
                # Create a new media object with the resolved URL
                new_media = self.instance.media_new(final_url)
                
                # Replace the media in the list
                self.media_list.remove_index(current_index)
                self.media_list.insert_media(new_media, current_index)

                print(f"Media at index {current_index} updated with resolved URL.")
        except Exception as e:
            print(f"Failed to resolve and update URL for media at index {current_index}: {e}")
            # Optionally, skip to the next media or handle the error as needed"""
   
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
                
    ##TODO:
    def _report_track(self, event):
        """
        Callback function triggered when a track is played.
        """
        pass
        """current_media = self.media_player.get_media()
        if current_media:
            current_index = self.media_list.index_of_item(current_media)
            folder, file_name = self._get_folder_and_file(self.track_list[current_index])  
            aareporter.log_track_play(folder, file_name)
            
            self.logger.debug('preparing to log album')
            if self.previous_folder != folder and not self.s_song_shuffle:
                self.logger.debug('logging album')
                aareporter.log_album_play(folder)

            self.previous_folder = folder
"""

    # TODO: Implement this method
    def speak_current_track(self):
        pass        

    def set_logger(self, external_logger):
        self.logger = external_logger


    def play_podcast(self, podcast_url: str, podcast_name: str):
        if not podcast_url:
            self.logger.warning("No RSS feed URL provided.")
            return

        self.podcast_name = podcast_name       
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
                self.episodes.append((episode_title, episode_url, episode_date))



        if not self.episodes:
            self.logger.warning(f"No playable episodes found in {podcast_name} ")
            return


        self.list_player.stop()
        
        

        # 2) Create a MediaList and add each track from your array
        self.media_list = self.player_instance.media_list_new()
        for episode in self.episodes:
            self.media_list.add_media(episode[1])



        # 3) Create a MediaListPlayer and set the media list
        self.list_player.set_media_list(self.media_list)

        # 4) Optionally create a specific MediaPlayer to control volume, etc.
        self.list_player.set_media_player(self.media_player)

        self.speak_text(self.get_most_recent_episode_date())

        # Play record start feedback if enabled
        #if self.media_list.count() > 0 and CONFIG.FEEDBACK_RECORD_START_ENABLED:
        #    self.play_feedback(CONFIG.FEEDBACK_RECORD_START)
        #    time.sleep(1.4)


        # 5) Start playback
        self.logger.debug(f"Playing podcast: {podcast_name}")
        self.list_player.play()


    def _resolve_final_url(self, url):
        # This method will now only return the final URL without logging intermediates
        # and will not print all redirect attempts.
        response = requests.head(url, allow_redirects=True)
        if response.status_code == 200:
            return response.url
        else:
            self.logger.debug(f"Unable to resolve final URL. Status code: {response.status_code}")
            return url
        

    ##TODO
    def set_repeat_album(self, repeat: bool):
        pass

    
    def is_playing(self) -> bool:
        """
        Return whether the player is currently playing.
        """
        return self.media_player.is_playing()


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
        self.podcast_name = 'Untitled Podcast'

       
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
        pass
        

    def jump_to_previous_album(self):
        pass


    def get_current_track(self) -> str:
        """
        Returns the path to the currently playing media.
        """
        current_media = self.media_player.get_media()
        if current_media:
            current_index = self.media_list.index_of_item(current_media)
            return self.episodes[current_index][0]
        
        return None

    def get_most_recent_episode_date(self) -> str:
        """
        Returns the path to the currently playing media.
        """
        date_str = self.episodes[0][2]
        
        formatted = parse_and_format_date_dateutil(date_str, dayfirst=False)
        if formatted:
            print(f"Original: {date_str} --> Formatted: {formatted}")
            return "Latest Episode " + formatted
        else:
            print(f"Unable to find Latest Episode pubish date")
            return "Publish Date Unknown"

    def get_whats_playing(self) -> str:
        """
        Same logic you had for describing the "current track" in a more readable format.
        """
        try:
            current_track_for_email = self.get_current_track()
            if not current_track_for_email:
                return "No track playing"


            return self.podcast_name + ". Episode: " + self.get_current_track()
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
        pass

        
    def unshuffle_current_songs(self):
        pass


    def play_in_order_from_random_track(self):
        pass

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


def get_day_suffix(day):
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

def parse_and_format_date_dateutil(date_str, dayfirst=False, desired_format="%B {day}{suffix}, %Y"):
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
        suffix = get_day_suffix(day)

        # Format the date with ordinal suffix
        formatted_date = parsed_date.strftime(desired_format).format(day=day, suffix=suffix)

        return formatted_date
    except (parser.ParserError, ValueError) as e:
        print(f"[dateutil] Error parsing date '{date_str}': {e}")
        return None

