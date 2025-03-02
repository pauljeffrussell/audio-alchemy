from abc import ABC, abstractmethod
import configfile as CONFIG
from gtts import gTTS
import subprocess
import time
import vlc

class AbstractAudioPlayer(ABC):
    """
    Abstract base class defining the interface for audio players (MP3, streaming, etc.).
    """

    def prepare_speech_file(self, text_to_speak):
    
        self.logger.debug(f'Text to convert to speech: {text_to_speak}')
        
        try:
            ## get the spoken audio from google in an mp3        
            self.logger.debug(f'Getting mp3 from google')
            tts = gTTS(text=text_to_speak, lang='en')
            tts.save(CONFIG.TEMP_SPEECH_MP3)  # Save the audio file
        
        
            ## we need to convert to wave because pygame can't play the mp3 format outputted by google.
            self.logger.debug(f'Converting mp3 to wav')
            # Command to convert MP3 to WAV using ffmpeg
            #command = ['ffmpeg', '-i', CONFIG.TEMP_SPEECH_MP3, CONFIG.TEMP_SPEECH_WAV, '-y']  # -y to overwrite without asking
        
            """command = [
                'ffmpeg',
                '-i', CONFIG.TEMP_SPEECH_MP3,  # Input file
                '-filter:a', 'volume=1.6',  # Increase volume by 50%
                CONFIG.TEMP_SPEECH_WAV,  # Output file
                '-y'  # Overwrite output file without asking
            ]"""

            command = [
                "ffmpeg",
                "-i", CONFIG.TEMP_SPEECH_MP3,     # input MP3
                "-ac", "2",                       # stereo channels
                "-ar", "44100",                   # 44.1 kHz sample rate
                "-c:a", "pcm_s16le",              # encode as 16-bit PCM
                "-filter:a", "volume=1.6",        # boost volume by 60%
                "-y",                             # overwrite output without asking
                CONFIG.TEMP_SPEECH_WAV            # output WAV
            ]

            subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        
            #self.logger.debug(f'Playing the resulting audio.')
        
            return True
            
        except Exception as e:
            self.logger.debug(f'Something went wrong getting or saving the audio. {e}')
            return False
           
    @abstractmethod
    def play_pause_track(self):
       pass

    @abstractmethod
    def _restart(self):
        pass        
            

    @abstractmethod
    def speak_current_track(self, intro_sound_file: str = None):
        """Speak the name of the currently playing track."""
        pass

    @abstractmethod
    def set_logger(self, logger):
        """Assign an external logger object to the player."""
        pass

    @abstractmethod
    def startup(self):
        """Initialize the audio player."""
        pass

    @abstractmethod
    def shutdown_player(self):
        """Shutdown the audio player."""
        pass

    @abstractmethod
    def is_playing(self) -> bool:
        """Return whether the player is currently playing."""
        pass


    @abstractmethod
    def pause_track(self):
        """Pause the currently playing track."""
        pass

    @abstractmethod
    def play_feedback(self, feedback_file: str):
        """Play a feedback sound (e.g., beep, record scratch)."""
        pass

    @abstractmethod
    def set_repeat_album(self, repeat: bool):
        """Enable/disable repeating the current album."""
        pass

    @abstractmethod
    def play_in_order_from_random_track(self):
        """Pick a random track in the album and then continue playing in order."""
        pass

    @abstractmethod
    def get_current_track(self) -> str:
        """Return the path (or name) of the current track."""
        pass

    @abstractmethod
    def shuffle_unshuffle_tracks(self):
        pass

    @abstractmethod
    def middle_button_long_press(self):
        pass



    @abstractmethod
    def next_track(self):
        """Skip to the next track."""
        pass

    @abstractmethod
    def forward_button_short_press(self):
        """Skip to the next track."""
        pass

    @abstractmethod
    def forward_button_long_press(self):
        """Jump to the next album in the playlist."""
        pass

    @abstractmethod
    def back_button_short_press(self):
        """Skip to the next track."""
        pass

    @abstractmethod
    def back_button_long_press(self):
        """Jump to the previous album in the playlist."""
        pass

   


   

    @abstractmethod
    def get_current_track(self) -> str:
        """Return the name of the currently playing track or stream."""
        return self.get_current_track()
    
    @abstractmethod
    def get_whats_playing(self) -> str:
        """Return the name of the currently playing track or stream."""
        pass

    