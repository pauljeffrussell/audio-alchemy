# audio-alchemy

AudioAlchemy is the software component of a Raspberry Pi-based stereo system that provides a screen-free interface for streaming music.

## The Problem

Years ago, I had a CD library. When streaming music became mainstream, I gave away my CDs. However, streaming music never quite replicated the tactile experience of browsing through physical media. There was nothing to touch, and all the music was represented by small icons on a screen. It was impossible to visualize albums by genre.

Finding a specific album meant either knowing its name and searching for it or endlessly scrolling through a digital library. After spending a day working on a laptop, the last thing I wanted to do was look at another screen. I longed for a way to experience the tactile sensation of physical media while enjoying the convenience of streaming music.

## The Solution

To address this issue, I decided to build a music player that could connect to my home stereo system like a CD player. Instead of using CDs, I designed the system to use cards, with each card representing an album or playlist and equipped with an RFID tag. Here's how the system works:

1. I printed cards for each album on card stock, utilizing artwork available on the web.
2. I attached RFID tags to the back of each card.
3. I created a spreadsheet (see configfile.py) to list each album and its corresponding RFID tag.
4. I set up a Raspberry Pi to run AudioAlchemy.py on boot.
5. AudioAlchemy.py downloads the spreadsheet and uses it as the music database.
6. By tapping a card, the associated music is played.

## Hardware

This solution relies on the following hardware components:

- Raspberry Pi 3
- RFID reader
- Three buttons:
  - Previous Track
  - Play/Pause
  - Next Track

## Setup

Setup instructions can be found in configfile.py.  

Please note that several setup steps have been omitted from the instructions at this time because, well, I'm a bit lazy. Once the device started working I became much more interested in listening to music than writing instructions. 