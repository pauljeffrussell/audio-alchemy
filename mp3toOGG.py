import os
import subprocess

def convert_mp3_to_ogg(input_folder, output_folder, stop_file=None, bitrate="320k"):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    files = sorted(
        [f for f in os.listdir(input_folder) if f.endswith('.mp3') and "Shift Notes" not in f],
        reverse=True
    )

    for filename in files:
        if stop_file and filename == stop_file:
            print(f"Stopping processing at {filename}.")
            break

        mp3_path = os.path.join(input_folder, filename)
        ogg_path = os.path.join(output_folder, os.path.splitext(filename)[0] + '.ogg')
        
        if os.path.exists(ogg_path):
            print(f"Skipping {mp3_path}, {ogg_path} already exists.")
            continue

        command = [
            'ffmpeg', '-i', mp3_path,
            '-c:a', 'libvorbis', '-b:a', bitrate,
            '-compression_level', '10', ogg_path
        ]
        subprocess.run(command)
        print(f"Converted {mp3_path} to {ogg_path} with CBR {bitrate}")

# Specify your input and output folders
input_folder = '/Users/paul/Library/CloudStorage/GoogleDrive-russelldad@gmail.com/My Drive/media/audiobooks (shared)/1-Podcasts/The Midnight Burger Secret Menu!'
output_folder = '/Users/paul/audio-alchemy/library/MidnightBurger'

# Specify the stop file
stop_file = '2024-02-17_Episode 6- Champ.mp3'  # Replace with the actual filename to stop at, or set to None to process all files

convert_mp3_to_ogg(input_folder, output_folder, stop_file)

