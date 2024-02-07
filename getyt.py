import sys
import yt_dlp

def download_mp3(video_url):
    options = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': '%(title)s.%(ext)s',  # Save the file as <video_title>.mp3
        'noplaylist': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    }
    
    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([video_url])

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python getyt.py '<YouTube URL>'")
        sys.exit(1)

    video_url = sys.argv[1]
    download_mp3(video_url)
