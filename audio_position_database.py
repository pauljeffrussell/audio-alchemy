import pandas as pd
import configfile as CONFIG

class AudioPositionDatabase:
    """
    Manages an audio track database stored in a CSV file. This class provides functionality to initialize the database,
    add new entries, update existing entries, save changes to disk, and retrieve track information.

    Attributes:
        filename (str): The name of the CSV file where the audio track data is stored.
        df (DataFrame): A pandas DataFrame holding the audio track data in memory.
    """

    def __init__(self):
        """
        Initializes the AudioPositionDatabase with a specified filename. If the file does not exist,
        it creates a new CSV file with appropriate headers.

        Args:
            filename (str, optional): The filename for the CSV file. Defaults to 'audio_position_data.csv'.
        """
        self.filename = CONFIG.DB_AUDIO_POSITION
        try:
            self.df = pd.read_csv(self.filename)
        except FileNotFoundError:
            # Initialize DataFrame with specified columns if the file does not exist
            self.df = pd.DataFrame(columns=['RFID', 'Track_Number', 'Time_in_Seconds'])
            # Create and save a new CSV file with the initial empty DataFrame
            self.df.to_csv(self.filename, index=False)
    
    def add_or_update_entry(self, id, track_number, time_in_seconds):
        """
        Adds a new entry or updates an existing entry in the database.

        Args:
            id (int): The unique identifier for the track.
            track_number (int): The track number associated with the track.
            time_in_seconds (int): The duration of the track in seconds.

        Updates the DataFrame in memory and saves the changes to the CSV file.
        """
        new_data = pd.DataFrame({'RFID': [id], 'Track_Number': [track_number], 'Time_in_Seconds': [time_in_seconds]})
        if id in self.df['RFID'].values:
            # Update existing entry
            self.df.loc[self.df['RFID'] == id, ['Track_Number', 'Time_in_Seconds']] = [track_number, time_in_seconds]
        else:
            # Add new entry if RFID does not exist using pd.concat
            self.df = pd.concat([self.df, new_data], ignore_index=True)
        # Save the updated DataFrame to the CSV file
        self.save()
    

   

    def save(self):
        """
        Saves the current state of the DataFrame to the CSV file.

        This method is called internally to persist changes after adding or updating entries.
        """
        self.df.to_csv(self.filename, index=False)

    def read_all(self):
        """
        Reads and returns all entries from the CSV file.

        Returns:
            DataFrame: A pandas DataFrame containing all entries from the database.
        """
        return pd.read_csv(self.filename)

    def get_position_info(self, id):
        """
        Retrieves the track number and time in seconds for a specific track RFID.

        Args:
            id (int): The unique identifier for the track to retrieve.

        Returns:
            tuple or None: Returns a tuple (track_number, time_in_seconds) if the track is found,
            otherwise returns None if the track is not found.
        """
        track_info = self.df.loc[self.df['RFID'] == id, ['Track_Number', 'Time_in_Seconds']]
        if not track_info.empty:
            return track_info.iloc[0]['Track_Number'], track_info.iloc[0]['Time_in_Seconds']
        else:
            return None
