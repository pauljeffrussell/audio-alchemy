"""

This Python script automates the process of downloading audio files from specified RSS feeds,
often used for distributing podcasts or other audio content. Key functionalities include:

1. Sanitization of Filenames: Ensures filenames derived from podcast and episode titles are
   safe for filesystem use by removing or replacing invalid characters.

2. Identification of Audio Content: Checks if a URL points to audio by examining the
   'Content-Type' header in a HEAD request to confirm audio content presence.

3. Finding Audio URLs in HTML: If direct audio file links are not in the RSS feed, it attempts
   to find the audio URL within HTML content by searching for `<audio>` tags or `.mp3` links.

4. Downloading Audio from RSS Feeds: Parses RSS feeds, extracts podcast titles to create
   directories, and processes each feed entry. It checks for audio URLs, finds audio files if
   not directly available, formats publication dates, sanitizes episode titles for filenames,
   and downloads the audio to a specified location, avoiding re-downloads of existing files.

5. Organized Saving of Files: Downloads are saved in directories named after the podcast titles
   (sanitized for validity as directory names) within a specified location (`SAVE_LOCATION`) which
   is in your google drive media/audiobooks/1-podcasts.

6. Script Customization for Multiple Feeds: Demonstrates how the script can be customized to
   download from multiple sources sequentially by hardcoding calls to download audio from
   specific RSS feeds.

Place this explanation at the top of the code for a comprehensive overview of its functionality
and purpose, aiding future reference or modification by others.


"""
import requests
from bs4 import BeautifulSoup
import feedparser
import os
from urllib.parse import urlparse, urljoin
from datetime import datetime

SAVE_LOCATION = "/Users/paul/Library/CloudStorage/GoogleDrive-russelldad@gmail.com/My Drive/media/audiobooks (shared)/1-Podcasts"

def sanitize_filename(text):
    """Sanitize the filename by removing or replacing characters that are not allowed in filenames."""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        text = text.replace(char, '-')
    return text

def is_audio_content(url, headers={}):
    """Check if the URL points to an audio content by sending a HEAD request and checking the Content-Type header."""
    response = requests.head(url, headers=headers, allow_redirects=True)
    content_type = response.headers.get('Content-Type', '')
    return 'audio/' in content_type

def find_audio_url_in_html(url, headers={}):
    """Attempt to find an audio file URL within the HTML content of the given URL."""
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'lxml')
        audio_tags = soup.find_all('audio')
        if audio_tags:
            source_tags = audio_tags[0].find_all('source')
            if source_tags:
                return urljoin(url, source_tags[0]['src'])
        # Fallback: look for any link that could be an audio file by its file extension
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.endswith('.mp3'):
                return urljoin(url, href)
    except Exception as e:
        print(f"Failed to find audio in HTML content for {url}. Error: {e}")
    return None

def download_audio_from_rss(rss_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}

    # Download the RSS feed
    response = requests.get(rss_url, headers=headers)
    response.raise_for_status()

    # Parse the RSS feed
    feed = feedparser.parse(response.content)

    # Get the podcast title and sanitize it to use as a directory name
    podcast_title = sanitize_filename(feed.feed.title)
    ##downloads_dir = os.path.join("audio_downloads", podcast_title)
    downloads_dir = os.path.join(SAVE_LOCATION, podcast_title)
    
    # Ensure the directory for downloads exists
    os.makedirs(downloads_dir, exist_ok=True)

    # Process feed entries in their original order
    for entry in feed.entries:
        audio_url = entry.links[1].href if len(entry.links) > 1 else None
        if audio_url:
            if not is_audio_content(audio_url, headers):
                audio_url = find_audio_url_in_html(audio_url, headers)
            if audio_url:
                # Format the publication date
                pub_date = datetime(*entry.published_parsed[:6]).strftime('%Y-%m-%d')

                # Sanitize the episode title to make it safe for use as a filename
                episode_title = sanitize_filename(entry.title)

                # Create the filename with the publication date and episode title
                filename = f"{pub_date}_{episode_title}.mp3"
                file_path = os.path.join(downloads_dir, filename)

                # If the file already exists, stop the process
                if os.path.exists(file_path):
                    print(f"Complete. File {filename} already exists. ")
                    break

                # Download the audio file
                print(f"Downloading {filename}...")
                audio_response = requests.get(audio_url, headers=headers)
                try:
                    audio_response.raise_for_status()
                except requests.exceptions.HTTPError as e:
                    print(f"Failed to download {filename}. Error: {e}")
                    continue  # Skip this file and continue with the next

                # Save the audio file
                with open(file_path, 'wb') as audio_file:
                    audio_file.write(audio_response.content)
                print(f"Downloaded {filename} successfully.")
            else:
                print(f"Could not find an audio file for {entry.title}.")
        else:
            print(f"No audio URL found for {entry.title}.")

if __name__ == "__main__":
    #rss_url = input("Enter the RSS URL: ")
    #download_audio_from_rss(rss_url)
    
    
    print ("\n\nDownloading Midnight Burger")
    download_audio_from_rss('https://www.patreon.com/rss/midnightburger?auth=XeyYTfyvb1CSIRRZye-H-j7839rl13NL')

    print ("\n\nDownloading Amelia Project")
    download_audio_from_rss('https://www.patreon.com/rss/ameliapodcast?auth=x6MZPM4w9dihXBpwEmQ85JJ8b3QvmtbC')

    print ("\n\nDownloading The Phenomonon")
    download_audio_from_rss('https://phenomenonpod.libsyn.com/rss')

    print ("\n\nDownloading Hardcore History")
    download_audio_from_rss('https://feeds.feedburner.com/dancarlin/history?format=xml')

    #print ("\n\nDownloading Wolf 359")
    #download_audio_from_rss('https://www.patreon.com/rss/Wolf359Radio?auth=A5LnOnDYJjXLFfQjV00EGQ3tOfmygz0y')

    print ("\n\nDownloads Complete.")
    
    
    
