# audio-alchemy
AudioAlchemy is the software portion of a raspberrypi based a stereo component that delivers a screen free 
interface for streaming music. 

## The Problem
Years ago I had a CD library. When streaming music became mainstream I gave away my CDs. 

But streaming music never quite had the same feel as looking through physical media. There was nothing to touch. 
All the music was represented by a small icon on a small screen and it was impossible to visualize albums by genera.

Finding the album I wanted meant I needed to know what it was and then search, or just scroll and scroll and scroll. And 
after a day of working on a laptop the last thing I wanted to do was look at a screen.


## A Solution
I decided to build a music player that connected to my home stereo like a CD player. Instead of 
CDs each album or playlist is represented by a card with and RFID tag on it. Here's how it works:

1. Cards were printed on card stock for each album using art available on the web.
2. RFID tags are put on the back of the cards. 
3. A spreadsheet (see configfile.py) is set up list each album and point to it's RFID tag 
4. A Raspberrypi is set up to run AudioAlchemy.py on boot.  
5. AudioAlchemy.py downloads the sheet and uses it as the music database. 
6. Tapping a card plays the music associated with that card.

## Hardware
This solution is built on top of the following hardware

- Raspberrypi 3. 
- RFID reader
- Three buttons
- - Previous Track
- - Play / Pause
- - Next Track

## Setup
Setup instructions are in configfile.py, but there's a lot of setup steps left out of the instructions at this time.


