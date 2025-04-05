import vlc
import time
import aareporter
from abstract_audio_player import AbstractAudioPlayer
import configfile as CONFIG

class AlchemyStreamPlayer(AbstractAudioPlayer):
  
    def __init__(self):
        self.current_stream = None
        self.stream_name = None
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()
        self.feedback_instance = vlc.Instance()
        self.feedback_player = self.feedback_instance.media_player_new()
        self.logger = None

        self.min_volume = 50
        self.max_volume = 100
        self.feexback_volume = 100


    def startup(self):
        # For a stream player, there's no particular startup needed
        # But we must implement the method to fulfill the abstract class requirements.
        self.current_stream = None
        self.stream_name = None
        #commenting this out so we don't leak memory by creating lots of 
        #instances of vlc
        #self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()
        #self.feedback_instance = vlc.Instance()
        self.feedback_player = self.feedback_instance.media_player_new()
        
    def shutdown_player(self):
        """
        Shutdown the podcast player and cleanup all VLC resources
        """
        try:
            self.logger.debug(f"Shutting down stream player.")
            
            # Check if player attributes exist
            if not hasattr(self, 'player') or not hasattr(self, 'feedback_player'):
                self.logger.debug(f"Stream player attributes not initialized yet.")
                return
            
            if self.player is None and self.feedback_player is None:
                self.logger.debug(f"Stream player is already shutdown.")
                return
            
            # Stop playback
            if self.player is not None:
                self.player.stop()
            if self.feedback_player is not None:
                self.feedback_player.stop()
            
            # give vlc time to stop playing before we try to release the memory
            time.sleep(0.1)
            
            # Release main player resources
            self.logger.debug(f"Releasing vlc memory.")
            if self.player is not None:
                media = self.player.get_media()
                if media is not None:
                    media.release()
                self.player.release()
            
            # Release feedback player resources
            if self.feedback_player is not None:
                feedback_media = self.feedback_player.get_media()
                if feedback_media is not None:
                    feedback_media.release()
                self.feedback_player.release()
            
            # Clear track lists
            self.track_list = []
            self.track_list_original_order = []
            
            time.sleep(0.1)

            # Set players to None to ensure proper garbage collection
            # but keep VLC instances alive for reuse
            media = None
            feedback_media = None
            if hasattr(self, 'player'):
                del self.player
            if hasattr(self, 'feedback_player'):
                del self.feedback_player

        except Exception as e:
            self.logger.error(f'Failed to shutdown stream player: {e}')

    """def shutdown_player(self):
        try:
            self.logger.debug(f"Shutting down stream player.")
            self.stream_name = None
            self.current_stream = None

            if self.player is None and self.feedback_player is None:
                self.logger.debug(f"Stream player is already shutdown.")
                return

            self.player.stop()
            self.feedback_player.stop()

            # give vlc time to stop playing before we try to release the memory
            time.sleep(0.1)
            
            ## Lets free up the memory from the stream player
            self.logger.debug(f"Releaseing vlc memory.")
            media = self.player.get_media()
            if media is not None:
                media.release()  
          
            self.player.release()
            

            ## Lets free up the memory from the feedback stream player
            feedback_media = self.player.get_media()
            if feedback_media is not None:
                feedback_media.release()  
            self.feedback_player.release()

            
            
            time.sleep(0.1)

            #Now set all the media players to None.
            #So we really, really don't hold on to them.
            media = None 
            feedback_media = None
            del self.player, self.feedback_player
            time.sleep(0.1)

        except Exception as e:
            self.logger.error(f'Failed to shutdown stream player: {e}')   """


    def cleanup_memory(self):
        try:
            self.logger.debug(f"Cleaning up stream player memory.")
            self.shutdown_player()
            self.instance.release()
            self.feedback_instance.release()
            time.sleep(0.2)
            del self.instance, self.feedback_instance
            self.instance = vlc.Instance()
            self.feedback_instance = vlc.Instance()
            time.sleep(0.1)
            self.startup()
        except Exception as e:
            self.logger.error(f'Failed to cleanup memory for stream player: {e}')

    def get_current_track(self) -> str:
        return self.stream_name
    
    def get_whats_playing(self) -> str:
        return self.stream_name

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

        
    def play_stream(self, stream_url: str, stream_name: str):
        try:
            self.shutdown_player()
            self.startup()
            
            
            self.current_stream = stream_url
            self.stream_name = stream_name

            time.sleep(0.5)


            #self.player = self.instance.media_player_new()
            media = self.instance.media_new(self.current_stream)
            self.logger.debug(f"Initialized streaming URL: {self.current_stream}")
            self.player.set_media(media)
            time.sleep(0.1)

            current_volume = self.player.audio_get_volume()
            self.logger.debug(f"The current volume is: {current_volume}")

            self.logger.debug(f"Reducing stream audio.")
            self.player.audio_set_volume(self.min_volume)
            self.feedback_player.audio_set_volume(self.feexback_volume)

            
            self.logger.debug(f"Playing stream: {self.stream_name}")
            self.player.play()

            self.speak_current_track(CONFIG.FEEDBACK_STREAM_START)

            ## wait a second so the speach doesn't jump right in.
            time.sleep(1.0)

            ### VOLUME CHECK ###
            current_volume = self.player.audio_get_volume()
            self.logger.debug(f"just after playing The current volume is: {current_volume}")

            
            


            ## Pause after the Speech so it doesn't sound like the volume jumps right back up
            time.sleep(0.3)

     
            

            ## VOLUME CHECK ###
            current_volume = self.player.audio_get_volume()
            self.logger.debug(f"volumn should be {self.max_volume} now. The current volume is: {current_volume}")

            aareporter.log_track_play(self.stream_name, "stream")
        except Exception as e:
            self.logger.error(f'Unable to play stream "{stream_name}": {e}')    


    def speak_current_track(self, intro_sound_file: str = None):
        # Speak the name of the stream

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
            
            if self.prepare_speech_file(f"{self.stream_name}"):
                self.play_feedback(CONFIG.TEMP_SPEECH_WAV, wait=True)
            else:
                self.play_feedback(CONFIG.FEEDBACK_AUDIO_NOT_FOUND, wait=True)

            self.increase_player_to_max_volume()

        except Exception as e:
            self.logger.error(f'Error speaking track: {e}') 


    """def play_speech(self, speech_file: str):
       

        try:
            # 2) Lower the volume of your main player
            self.logger.debug(f"reducing stream audio.")
            self.player.audio_set_volume(70)
            time.sleep(0.2)

    
            
            
            
            self.feedback_player.set_media(self.feedback_instance.media_new(speech_file))

            
            self.feedback_player.audio_set_volume(self.max_volume)  # or whatever volume you want
            
            
            self.logger.debug(f"feedback_player.play()")
            self.feedback_player.play()
            time.sleep(0.2)
            # 4) Wait for the speech to finish (blocking approach)
            while self.feedback_player.is_playing():
                self.logger.debug(f"waiting for speech to finish.")
                time.sleep(0.1)
            self.feedback_player.stop()
            time.sleep(0.3)


            # 5) Raise the volume on the main player again
            self.player.audio_set_volume(self.max_volume)
        except Exception as e:
            self.logger.error(f'Unable to play speach: {e}')   """   

    def increase_player_to_max_volume(self):
        
        current_volume = self.player.audio_get_volume()
        self.logger.debug(f"Increasing volume to {self.max_volume} from: {current_volume}")
        
        for i in range(current_volume, self.max_volume + 1, 5):  # Start at 50, go up to 100, increment by 5
                self.player.audio_set_volume(i)
                time.sleep(0.1)

        current_volume = self.player.audio_get_volume()
        self.logger.debug(f"Volume increased to: {current_volume}")


    def is_playing(self) -> bool:

        if self.player is None:
            return False
        return self.player.is_playing() == 1
    

    def set_logger(self, logger):
        """Assign an external logger object to the player."""
        self.logger = logger
        pass

    

    def _restart(self):

        try:
            # this is going to take a few seconds to start
            self.player.play()

            # So let's play some feedback to let the user know that it's working.
            self.player.audio_set_volume(self.min_volume)
            
            self.play_feedback(CONFIG.VOICE_FEEDBACK_STREAM_RESTART, wait=False)
            
            time.sleep(0.3)
            
            self.increase_player_to_max_volume()

        except Exception as e:
            self.logger.error(f'Error restarting stream: {e}') 

        




    
    ####################################################################
    ##                                                                ##
    ##    EVERYTHING BELOW THIS LINE IS NOT APPLICABLE TO STREAMS     ##
    ##                                                                ##
    ####################################################################    



 

    def next_track(self):
        # Not applicable for streams
        pass


    def forward_button_short_press(self):
        # Not applicable for streams
        pass

    def back_button_short_press(self):
        # Not applicable for streams
        pass

    def forward_button_long_press(self):
        # Not applicable for streams
        pass

    def back_button_long_press(self):
        # Not applicable for streams
        pass


    def play_pause_track(self):
        
        state = self.player.get_state()
        #self.logger.debug(f"player state: {state}")

        if state == vlc.State.Paused:
            self.player.play()
        elif state == vlc.State.Stopped:
            self._restart()
        elif state == vlc.State.Playing:
            #self.player.pause()
            self.player.stop()
            self.logger.debug('Paused Stream.')
        elif state == vlc.State.Ended:
            self._restart()

    def pause_track(self):
        """Pause the currently playing stream if applicable."""
        pass

    def play_in_order_from_random_track(self):
        """No-op for streams; doesn't apply to continuous streaming."""
        pass
        
    def set_repeat_album(self, repeat: bool):
        """No-op for streams; no concept of album repeat here."""
        pass

    def shuffle_unshuffle_tracks(self):
        """No-op for streams; doesn't apply to continuous streaming."""
        pass

    def middle_button_long_press(self):
        """No-op for streams; doesn't apply to continuous streaming."""
        pass

 