import vlc
import time
import os
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
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()
        self.feedback_instance = vlc.Instance()
        self.feedback_player = self.feedback_instance.media_player_new()
        

    def shutdown_player(self):
        try:
            self.stream_name = None
            self.current_stream = None
            self.player.stop()
            self.feedback_player.stop()
            time.sleep(0.2)

        except Exception as e:
            self.logger.error(f'Failed to shutdown: {e}')   

    def play_pause_track(self):
        if self.is_playing():
            self.player.pause()
        else:
            self.player.play()


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

            
            """current_volume = self.player.audio_get_volume()
            self.logger.debug(f"The current player volume is: {current_volume}")
            current_volume = self.feedback_player.audio_get_volume()
            self.logger.debug(f"The current feedback_player volume is: {current_volume}")

            ##play audio feedback so the user knows the card tap worked
            ## it'll take a second before the audio plays back
            #self.play_feedback(CONFIG.FEEDBACK_PROCESSING)
            self.play_feedback(CONFIG.FEEDBACK_STREAM_START, wait=True)
            
            ### VOLUME CHECK ###
            current_volume = self.player.audio_get_volume()
            self.logger.debug(f"After Feedback The current volume is: {current_volume}")
"""
            self.logger.debug(f"Playing stream: {self.stream_name}")
            self.player.play()

            self.speak_current_track(CONFIG.FEEDBACK_STREAM_START)

            ## wait a second so the speach doesn't jump right in.
            time.sleep(1.0)

            ### VOLUME CHECK ###
            current_volume = self.player.audio_get_volume()
            self.logger.debug(f"just after playing The current volume is: {current_volume}")

            
            """self.logger.debug(f"Prepping speach file")
            # Speak the name of the stream
            if self.prepare_speech_file(f"{self.stream_name}"):
                self.play_feedback(CONFIG.TEMP_SPEECH_WAV, wait=True)
            else:
                self.play_feedback(CONFIG.FEEDBACK_AUDIO_NOT_FOUND)


            ## VOLUME CHECK ###
            current_volume = self.player.audio_get_volume()
            self.logger.debug(f"just after playing The current volume is: {current_volume}")"""

            ## Pause after the Speech so it doesn't sound like the volume jumps right back up
            time.sleep(0.3)

            #self.increase_player_to_max_volume()
            """for i in range(50, 101, 5):  # Start at 50, go up to 100, increment by 5
                self.player.audio_set_volume(i)
                time.sleep(0.1)"""

            ## VOLUME CHECK ###
            current_volume = self.player.audio_get_volume()
            self.logger.debug(f"volumn should be {self.max_volume} now. The current volume is: {current_volume}")

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
        return self.player.is_playing() == 1
    

    def set_logger(self, logger):
        """Assign an external logger object to the player."""
        self.logger = logger
        pass

    






    
    ####################################################################
    ##                                                                ##
    ##    EVERYTHING BELOW THIS LINE IS NOT APPLICABLE TO STREAMS     ##
    ##                                                                ##
    ####################################################################    



 

    def next_track(self):
        # Not applicable for streams
        pass

    def prev_track(self):
        # Not applicable for streams
        pass

    def jump_to_next_album(self):
        # Not applicable for streams
        pass

    def jump_to_previous_album(self):
        # Not applicable for streams
        pass
    def pause_track(self):
        """Pause the currently playing stream if applicable."""
        pass

    def play_in_order_from_random_track(self):
        """No-op for streams; doesn't apply to continuous streaming."""
        pass
        
    def set_repeat_album(self, repeat: bool):
        """No-op for streams; no concept of album repeat here."""
        pass

    def shuffle_current_songs(self):
        """No-op for streams; doesn't apply to continuous streaming."""
        pass

    def unshuffle_current_songs(self):
        """No-op for streams; doesn't apply to continuous streaming."""
        pass