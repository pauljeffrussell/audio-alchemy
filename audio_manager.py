# audio_manager.py
from abstract_audio_player import AbstractAudioPlayer
#from alchemy_files_vlc_player import AlchemyFilesPlayer
from alchemy_files_player import AlchemyFilesPlayer
from alchemy_stream_player import AlchemyStreamPlayer
from alchemy_podcast_player import AlchemyPodcastPlayer


class AudioManager(AbstractAudioPlayer):
    """
    A manager that holds multiple concrete players in memory and can swap
    between them at runtime. Inherits from AbstractAudioPlayer so it can
    be used wherever an AbstractAudioPlayer is expected.
    """

    def __init__(self):
        # Create both players immediately 
        self.file_player = AlchemyFilesPlayer()
        self.stream_player = AlchemyStreamPlayer()
        self.podcast_player = AlchemyPodcastPlayer()

        # Pick one as the current (default) player
        self.current_player = self.file_player

        # Optional: you could store the logger if you want to reuse it locally
        self.logger = None

    def cleanup_memory(self):
        self.logger.debug(f"Cleaning up audio manager memory.")
        
        self.file_player.cleanup_memory()
        
        self.stream_player.cleanup_memory()
        
        self.podcast_player.cleanup_memory()
        
        
        
        
    def set_player(self, player_type: str):
        """
        Swap out the current player for another. For example:
          - set_player("file")   -> use self.file_player
          - set_player("stream") -> use self.stream_player
        """
        # 1. Shutdown the old player
        self.current_player.shutdown_player()

        # 2. Switch references
        if player_type.lower() == "stream":
            self.current_player = self.stream_player
        else:
            self.current_player = self.file_player

        # 3. Startup the new one
        self.current_player.startup()

    # -----------------------------------------------------------------
    # Implement the AbstractAudioPlayer interface by delegating to
    # self.current_player
    # -----------------------------------------------------------------

    def set_logger(self, logger):
        """Assign an external logger to both players, and store locally if desired."""
        self.logger = logger
        self.file_player.set_logger(logger)
        self.stream_player.set_logger(logger)
        self.podcast_player.set_logger(logger)

    def startup(self):
        """Initialize the currently active player."""
        self.current_player.startup()

    def shutdown_player(self):
        """Shutdown the currently active player."""
        self.current_player.shutdown_player()

    def is_playing(self) -> bool:
        """Return whether the currently active player is playing."""
        return self.current_player.is_playing()

    def play_pause_track(self):
        """Toggle play/pause for the currently active player's track."""
        self.current_player.play_pause_track()

    def pause_track(self):
        """Pause the currently active player's track."""
        self.current_player.pause_track()

    def play_feedback(self, feedback_type: str):
        """Play a feedback sound on the currently active player."""
        self.current_player.play_feedback(feedback_type)

    def set_repeat_album(self, repeat: bool):
        """Enable/disable repeating the current album on the active player."""
        self.current_player.set_repeat_album(repeat)

    def play_in_order_from_random_track(self):
        """Pick a random track on the currently active player and continue in order."""
        self.current_player.play_in_order_from_random_track()

    def get_current_track(self) -> str:
        """Return the path/name of the current track from the active player."""
        return self.current_player.get_current_track()
    
    def get_whats_playing(self) -> str:
        """Return the path/name of what is currently playing."""
        return self.current_player.get_whats_playing()

    def next_track(self):
        """Skip to the next track on the currently active player."""
        self.current_player.next_track()

    def prev_track(self):
        """Skip to the next track on the currently active player."""
        self.current_player.prev_track()
    
    def shuffle_unshuffle_tracks(self):
        """Shuffle or unshhuffle the current songs in the playlist of the active player."""
        self.current_player.shuffle_unshuffle_tracks()

    def middle_button_long_press(self):
        """ tell the player to do what it does for a middle button long press"""
        self.current_player.middle_button_long_press()

    
    def forward_button_short_press(self):
        """Jump to the next album on the currently active player."""
        self.current_player.forward_button_short_press()

    def back_button_short_press(self):
        """Jump to the previous album on the currently active player."""
        self.current_player.back_button_short_press()



    def forward_button_long_press(self):
        """Jump to the next album on the currently active player."""
        self.current_player.forward_button_long_press()

    def back_button_long_press(self):
        """Jump to the previous album on the currently active player."""
        self.current_player.back_button_long_press()

    def play_tracks(self, tracks: list, repeat: bool, shuffle: bool, remember_position: bool, rfid: int):
        """
        Play a list of tracks with specified options on the active player.
        """
        if self.current_player is not self.file_player:
            self.logger.debug(f'Switching to files player')    
            self.current_player.shutdown_player()
            self.current_player = self.file_player
            self.current_player.startup()

        self.current_player.play_tracks(tracks, repeat, shuffle, remember_position, rfid)

    def play_stream(self, stream_url: str, stream_name: str, rfid=int):
        
        if self.current_player is not self.stream_player:
            self.logger.debug(f'Switching to stream player')    
            self.current_player.shutdown_player()
            self.current_player = self.stream_player
            #self.current_player.startup()
        #else:
            # I don't need this because the player manages it's state
            # internally when switching between streams
            #self.current_player.shutdown_player() 

        self.current_player.play_stream(stream_url, stream_name)
    
    def play_podcast(self, podcast_url: str, podcast_name: str, rfid=int):
        
        if self.current_player is not self.podcast_player:
            self.logger.debug(f'Switching to podcast player')    
            self.current_player.shutdown_player()
            self.current_player = self.podcast_player
            #self.current_player.startup()
        else:
            self.current_player.shutdown_player() 

        self.current_player.play_podcast(podcast_url, podcast_name, rfid)

    def play_audiobook(self,  tracks: list, remember_position=False, rfid=int):
        if self.current_player is not self.podcast_player:
            self.logger.debug(f'Switching to audiobook player')    
            self.current_player.shutdown_player()
            self.current_player = self.podcast_player
            self.current_player.startup()
        else:
            self.current_player.shutdown_player() 

        self.current_player.play_audiobook(tracks, remember_position, rfid)


    # TODO: Implement this method
    def speak_current_track(self, intro_sound_file=None):
        self.current_player.speak_current_track(intro_sound_file)
        pass


    def _restart(self):
        pass

    